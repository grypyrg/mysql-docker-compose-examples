# Copyright (c) 2012, 2019, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2.0, as
# published by the Free Software Foundation.
#
# This program is also distributed with certain software (including
# but not limited to OpenSSL) that is licensed under separate terms,
# as designated in a particular file or component or in included license
# documentation.  The authors of MySQL hereby grant you an
# additional permission to link the program and your derivative works
# with the separately licensed software that they have included with
# MySQL.
#
# Without limiting anything contained in the foregoing, this file,
# which is part of MySQL Connector/Python, is also subject to the
# Universal FOSS Exception, version 1.0, a copy of which can be found at
# http://oss.oracle.com/licenses/universal-foss-exception.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License, version 2.0, for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA

"""Implements the Distutils command 'bdist_com_msi'

Implements the Distutils command 'bdist_com_msi' which creates a built
commercial distribution Windows Installer using Windows Installer XML 3.5.
The WiX file is available in the folder '/support/MSWindows/' of the
Connector/Python source.
"""

import os
import json
import re
import sys
import shutil
import zipfile

from distutils import log
from distutils.errors import DistutilsError, DistutilsOptionError
from distutils.dir_util import remove_tree, copy_tree
from distutils.sysconfig import get_python_version
from distutils.core import Command
from distutils.util import get_platform

from ..utils import get_magic_tag, add_docs
from ..msi_descriptor_parser import add_arch_dep_elems
from .. import wix
from . import (COMMON_USER_OPTIONS, EDITION, VERSION, VERSION_EXTRA, ARCH_64BIT,
               generate_info_files)

COMMERCIAL_DATA = os.path.abspath(os.path.join('cpyint', 'data', 'commercial'))
MSIDATA_ROOT = os.path.join('cpyint', 'data', 'MSWindows')
DIST_PATH_FORMAT = 'wininst_{}{}'

if VERSION >= (2, 1):
    CEXT_OPTIONS = [
        ('with-mysql-capi=', None,
         "Location of MySQL C API installation (Connector/C or MySQL Server)"),
        ('with-protobuf-include-dir=', None,
         "Location of Protobuf include directory"),
        ('with-protobuf-lib-dir=', None,
         "Location of Protobuf library directory"),
        ('with-protoc=', None,
         "Location of Protobuf protoc binary"),
        ('extra-compile-args=', None,
         "Extra compile arguments"),
        ('extra-link-args=', None,
         "Extra link arguments"),
    ]
else:
    CEXT_OPTIONS = []


class _MSIDist(Command):

    """"Create a MSI distribution"""

    user_options = [
        ('bdist-dir=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('wix-install=', None,
         "location of the Windows Installer XML installation"
         "(default: %s)" % wix.WIX_INSTALL_PATH),
        ('wix-required-version=', None,
         "required version the Windows Installer XML installation"
         "(default: %s)" % wix.WIX_REQUIRED_VERSION),
        ('python-version=', None,
         "target Python version"),
        ('prepare-stage', 'p',
         "only stage installation for this python {} version, used later for"
         "a single msi".format(get_python_version()[:3])),
        ('combine-stage', 'c',
         "Unify the prepared msi stages to only one single msi"),
    ] + COMMON_USER_OPTIONS + CEXT_OPTIONS

    boolean_options = [
        'keep-temp', 'include-sources', 'prepare-stage', 'combine-stage'
    ]

    negative_opt = {}

    def initialize_options(self):
        self.prefix = None
        self.build_base = None
        self.bdist_dir = None
        self.keep_temp = 0
        self.dist_dir = None
        self.include_sources = True
        self.wix_install = wix.WIX_INSTALL_PATH
        self.wix_required_version = wix.WIX_REQUIRED_VERSION
        self.python_version = get_python_version()[:3]
        self.edition = EDITION
        self.with_mysql_capi = None
        self.with_protobuf_include_dir = None
        self.with_protobuf_lib_dir = None
        self.with_protoc = None
        self.with_cext = False
        self.extra_compile_args = None
        self.extra_link_args = None
        self.connc_lib = None
        self.connc_lib = None
        self.prepare_stage = False
        self.combine_stage = False

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_base', 'build_base'))
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

        if not self.prefix:
            self.prefix = os.path.join(
                self.build_base, DIST_PATH_FORMAT.format(self.python_version[0],
                                                       self.python_version[2]))

        self.supported_versions = [
            '2.7', '3.4', '3.5', '3.6', '3.7', '3.8']

        self.dist_path = {}

        for py_ver in self.supported_versions:
            self.dist_path[py_ver] = os.path.join(
                self.build_base, DIST_PATH_FORMAT.format(*py_ver.split('.')))

        if self.python_version not in self.supported_versions:
            raise DistutilsOptionError(
                "The --python-version should be a supported version, one "
                "of %s" % ','.join(self.supported_versions))

        if self.python_version[0] != get_python_version()[0]:
            raise DistutilsError(
                "Python v3 distributions need to be build with a "
                "supported Python v3 installation.")

        self.with_cext = any((self.with_mysql_capi,
                              self.with_protobuf_include_dir,
                              self.with_protobuf_lib_dir, self.with_protoc))

        if self.with_cext:
            if not self.with_mysql_capi or \
               not os.path.isdir(self.with_mysql_capi):
                log.error("Location of MySQL C API (Connector/C) must be "
                          "provided.")
                sys.exit(1)
            else:
                cmd_build = self.get_finalized_command('build')
                self.connc_lib = os.path.join(cmd_build.build_temp, 'connc',
                                              'lib')
                self.connc_include = os.path.join(cmd_build.build_temp,
                                                  'connc', 'include')

                self._finalize_connector_c(self.with_mysql_capi)

            if not self.with_protobuf_include_dir or \
               not os.path.isdir(self.with_protobuf_include_dir):
                log.error("Location of Protobuf include directory must be "
                          "provided.")
                sys.exit(1)
            else:
                self.with_protobuf_include_dir = \
                    os.path.abspath(self.with_protobuf_include_dir)

            if not self.with_protobuf_lib_dir or \
               not os.path.isdir(self.with_protobuf_lib_dir):
                log.error("Location of Protobuf library directory must be "
                          "provided.")
                sys.exit(1)
            else:
                self.with_protobuf_lib_dir = \
                    os.path.abspath(self.with_protobuf_lib_dir)

            if not self.with_protoc or not os.path.isfile(self.with_protoc):
                log.error("Protobuf protoc binary is not valid.")
                sys.exit(1)
            else:
                self.with_protoc = os.path.abspath(self.with_protoc)

    def _finalize_connector_c(self, connc_loc):
        if not os.path.isdir(connc_loc):
            log.error("MySQL C API should be a directory")
            sys.exit(1)

        copy_tree(os.path.join(connc_loc, 'lib'), self.connc_lib)
        copy_tree(os.path.join(connc_loc, 'include'), self.connc_include)

        if ARCH_64BIT:
            for filename in ["libssl-1_1-x64.dll", "libcrypto-1_1-x64.dll"]:
                src = os.path.join(connc_loc, "bin", filename)
                dst = self.connc_lib
                log.info("copying {0} -> {1}".format(src, dst))
                shutil.copy(src, dst)
        else:
            for filename in ["libssl-1_1.dll", "libcrypto-1_1.dll"]:
                src = os.path.join(connc_loc, "bin", filename)
                dst = self.connc_lib
                log.info("copying {0} -> {1}".format(src, dst))
                shutil.copy(src, dst)

        for lib_file in os.listdir(self.connc_lib):
            if os.name == 'posix' and not lib_file.endswith('.a'):
                os.unlink(os.path.join(self.connc_lib, lib_file))

    def finalize_msi_descriptor(self):
        """Returns the finalized and customized path of the msi descriptor.
        """
        base_xml_path = os.path.join(MSIDATA_ROOT, "product.wxs")
        result_xml_path = os.path.join(MSIDATA_ROOT, 'cpy_product_desc.wxs')

        if get_platform() == 'win32':
            add_arch_dep_elems(base_xml_path, result_xml_path, for32=True,
                               log=log, add_vs_redist=False)
        else:
            add_arch_dep_elems(base_xml_path, result_xml_path, log=log,
                               add_vs_redist=self.with_cext)

        return result_xml_path

    def _get_wixobj_name(self, myc_version=None, python_version=None):
        """Get the name for the wixobj-file

        Returns a string
        """
        raise NotImplementedError

    def find_bdist_paths(self):
        """Find compresed distribution files or valid distribution paths.
        """
        valid_bdist_paths = {}
        bdist_paths = {
            '2.7': os.path.join(
                os.path.abspath(self.dist_path['2.7']), 'Lib', 'site-packages'),
            '3.4': os.path.join(
                os.path.abspath(self.dist_path['3.4']), 'Lib', 'site-packages'),
            '3.5': os.path.join(
                os.path.abspath(self.dist_path['3.5']), 'Lib', 'site-packages'),
            '3.6': os.path.join(
                os.path.abspath(self.dist_path['3.6']), 'Lib', 'site-packages'),
            '3.7': os.path.join(
                os.path.abspath(self.dist_path['3.7']), 'Lib', 'site-packages'),
            '3.8': os.path.join(
                os.path.abspath(self.dist_path['3.8']), 'Lib', 'site-packages')
        }

        for py_ver in self.supported_versions:
            bdist_paths[py_ver] = os.path.join(
                os.path.abspath(self.dist_path[py_ver]), 'Lib', 'site-packages')
            zip_fn = "{}.zip".format(
                DIST_PATH_FORMAT.format(*py_ver.split(".")))

            log.info("Locating zip: %s at %s", zip_fn, os.path.curdir)
            bdist_path = None
            if os.path.exists(zip_fn) and \
               zipfile.is_zipfile(zip_fn):
                with zipfile.ZipFile(zip_fn) as zip_f:
                    zip_f.extractall()
            else:
                log.warn("Unable to find zip: %s at %s", zip_fn, os.path.curdir)
            if bdist_path is None:
                bdist_path = bdist_paths[py_ver]
                log.info("Checking for extracted distribution at %s",
                         bdist_path)
            if os.path.exists(bdist_path):
                valid_bdist_paths[py_ver] = bdist_path
                log.info("Distribution path found at %s", bdist_path)
            else:
                log.warn("Unable to find distribution path for %s", py_ver)

        return valid_bdist_paths

    def _create_msi(self, dry_run=0):
        """Create the Windows Installer using WiX

        Creates the Windows Installer using WiX and returns the name of
        the created MSI file.

        Raises DistutilsError on errors.

        Returns a string
        """
        # load the upgrade codes
        with open(os.path.join(MSIDATA_ROOT, 'upgrade_codes.json')) as fp:
            upgrade_codes = json.load(fp)

        # version variables for Connector/Python and Python
        mycver = self.distribution.metadata.version
        match = re.match("(\d+)\.(\d+).(\d+).*", mycver)
        if not match:
            raise ValueError("Failed parsing version from %s" % mycver)
        (major, minor, patch) = match.groups()
        pyver = self.python_version
        pymajor = pyver[0]
        pyminor = pyver[2]

        # check whether we have an upgrade code
        try:
            upgrade_code = upgrade_codes[mycver[0:3]][pyver]
        except KeyError:
            raise DistutilsError(
                "No upgrade code found for version v{cpy_ver}, "
                "Python v{py_ver}".format(
                    cpy_ver=mycver, py_ver=pyver
                ))
        log.info("upgrade code for v%s, Python v%s: %s" % (
                 mycver, pyver, upgrade_code))

        self.pyver_bdist_paths = self.find_bdist_paths()

        # wixobj's basename is the name of the installer
        wixobj = self._get_wixobj_name()
        msi = os.path.abspath(
            os.path.join(self.dist_dir, wixobj.replace('.wixobj', '.msi')))
        wixer = wix.WiX(self.wxs,
                        out=wixobj,
                        msi_out=msi,
                        base_path=self.build_base,
                        install=self.wix_install)

        # correct newlines and version in text files
        log.info("Fixing newlines in text files")
        info_files = []
        for txt_file_dest, txt_file_path in self.fix_txtfiles.items():
            txt_fixed = os.path.join(self.build_base, txt_file_dest)
            info_files.append(txt_fixed)
            content = open(txt_file_path, 'rb').read()

            if b'\r\n' not in content:
                log.info("converting newlines in %s", txt_fixed)
                content = content.replace(b'\n', b'\r\n')
                open(txt_fixed, 'wb').write(content)
            else:
                log.info("not converting newlines in %s, this is odd",
                         txt_fixed)
                open(txt_fixed, 'wb').write(content)

        digit_needle = 'Connector/Python \d{1,2}.\d{1,2}'
        xy_needle = 'Connector/Python X.Y'
        xy_sub = 'Connector/Python {0}.{1}'
        for info_file in info_files:
            log.info("correcting version in %s", info_file)
            with open(info_file, 'r+') as fp:
                content = fp.readlines()
                for i, line in enumerate(content):
                    content[i] = re.sub(digit_needle,
                                        xy_sub.format(*VERSION[0:2]),
                                        line)
                    line = content[i]
                    content[i] = re.sub(xy_needle,
                                        xy_sub.format(*VERSION[0:2]),
                                        line)
                fp.seek(0)
                fp.write(''.join(content))

        plat_type = 'x64' if ARCH_64BIT else 'x86'
        win64 = 'yes' if ARCH_64BIT else 'no'
        pyd_arch = 'win_amd64' if ARCH_64BIT else 'win32'
        directory_id = 'ProgramFiles64Folder' if ARCH_64BIT else \
            'ProgramFilesFolder'

        # For 3.5 the driver names are pretty complex, see
        # https://www.python.org/dev/peps/pep-0425/
        if pymajor == '3' and int(pyminor) >= 5:
            pyd_ext = ".cp%s%s-%s.pyd" % (pyver[0],5,pyd_arch)
        else:
            pyd_ext = ".pyd"

        cext_lib_name = "_mysql_connector" + pyd_ext
        cext_xpb_name = "_mysqlxpb" + pyd_ext

        if self.connc_lib:
            if ARCH_64BIT:
                libcrypto_dll_path = os.path.join(
                    os.path.abspath(self.connc_lib), 'libcrypto-1_1-x64.dll')
                libssl_dll_path = os.path.join(
                    os.path.abspath(self.connc_lib), 'libssl-1_1-x64.dll')
            else:
                libcrypto_dll_path = os.path.join(
                    os.path.abspath(self.connc_lib), 'libcrypto-1_1.dll')
                libssl_dll_path = os.path.join(
                    os.path.abspath(self.connc_lib), 'libssl-1_1.dll')
        else:
            libcrypto_dll_path =  ''
            libssl_dll_path = ''

        # WiX preprocessor variables
        params = {
            'Version': '.'.join([major, minor, patch]),
            'FullVersion': mycver,
            'PythonVersion': pyver,
            'PythonMajor': pymajor,
            'PythonMinor': pyminor,
            'Major_Version': major,
            'Minor_Version': minor,
            'Patch_Version': patch,
            'Platform': plat_type,
            'Directory_Id': directory_id,
            'PythonInstallDir': 'Python%s' % pyver.replace('.', ''),
            'PyExt': 'pyc' if not self.include_sources else 'py',
            'UpgradeCode': upgrade_code,
            'ManualPDF': os.path.abspath(
                os.path.join('docs', 'mysql-connector-python.pdf')),
            'ManualHTML': os.path.abspath(
                os.path.join('docs', 'mysql-connector-python.html')),
            'UpgradeCode': upgrade_code,
            'MagicTag': get_magic_tag(),
            'BuildDir': os.path.abspath(self.build_base),
            'LibMySQLDLL': os.path.join(
                os.path.abspath(self.connc_lib), 'libmysql.dll') \
                    if self.connc_lib else '',
            'LIBcryptoDLL': libcrypto_dll_path,
            'LIBSSLDLL': libssl_dll_path,
            'Win64': win64,
            'BitmapDir': os.path.join(os.getcwd(), "cpyint", "data",
                                      "MSWindows"),
        }
        for py_ver in self.supported_versions:
            ver = py_ver.split(".")
            params['BDist{}{}'.format(*ver)] = ""

            if ver[0] == '3' and int(ver[1]) >= 5:
                pyd_ext = ".cp%s%s-%s.pyd" % (ver[0], ver[1], pyd_arch)
            else:
                pyd_ext = ".pyd"

            params['CExtLibName{}{}'.format(*ver)] = \
               "_mysql_connector{}".format(pyd_ext)
            params['CExtXPBName{}{}'.format(*ver)] = \
               "_mysqlxpb{}".format(pyd_ext)
            params['HaveCExt{}{}'.format(*ver)] = 0

            if py_ver in self.pyver_bdist_paths:
                params['BDist{}{}'.format(*ver)] = \
                   self.pyver_bdist_paths[py_ver]
                if os.path.exists(
                    os.path.join(self.pyver_bdist_paths[py_ver],
                                 params['CExtLibName{}{}'.format(*ver)])):
                    params['HaveCExt{}{}'.format(*ver)] = 1

        log.info("### wixer params:")
        for param in params:
            log.info("  %s: %s", param, params[param])
        wixer.set_parameters(params)

        if not dry_run:
            try:
                wixer.compile()
                wixer.link()
            except DistutilsError:
                raise

        if not self.keep_temp and not dry_run:
            log.info('WiX: cleaning up')
            os.unlink(msi.replace('.msi', '.wixpdb'))

        return msi

    def _prepare(self):
        log.info("Preparing installation in %s", self.build_base)
        cmd_install = self.reinitialize_command('install', reinit_subcommands=1)
        cmd_install.prefix = self.prefix
        cmd_install.with_mysql_capi = self.with_mysql_capi
        cmd_install.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_install.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_install.with_protoc = self.with_protoc
        cmd_install.extra_compile_args = self.extra_compile_args
        cmd_install.extra_link_args = self.extra_link_args
        cmd_install.static = False
        cmd_install.ensure_finalized()
        cmd_install.run()

    def run(self):
        """Run the distutils command"""

        if os.name != 'nt':
            log.info("This command is only useful on Windows. "
                     "Forcing dry run.")
            self.dry_run = True

        log.info("generating INFO_SRC and INFO_BIN files")
        generate_info_files()

        if not self.combine_stage:
            self._prepare()

        if self.prepare_stage:
            zip_fn = os.path.join(self.dist_dir,
                                  "{}.zip".format(os.path.abspath(self.prefix)))
            log.info("generating stage: %s", zip_fn)
            with zipfile.ZipFile(zip_fn, "w", zipfile.ZIP_DEFLATED) as zip_f:
                # Read all directory, subdirectories and file lists
                for root, _, files in os.walk(self.prefix):
                    for filename in files:
                        # Create the full filepath by using os module.
                        filePath = os.path.join(root, filename)
                        log.info("  adding file: %s", filePath)
                        zip_f.write(filePath)
            log.info("stage created: %s", zip_fn)
        else:
            wix.check_wix_install(wix_install_path=self.wix_install,
                                  wix_required_version=self.wix_required_version,
                                  dry_run=self.dry_run)

            # create the Windows Installer
            msi_file = self._create_msi(dry_run=self.dry_run)
            log.info("created MSI as %s" % msi_file)

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)
            if ARCH_64BIT:
                for filename in ["libssl-1_1-x64.dll", "libcrypto-1_1-x64.dll"]:
                    dll_file = os.path.join(os.getcwd(), filename)
                    if os.path.exists(dll_file):
                        os.unlink(dll_file)
            else:
                for filename in ["libssl-1_1.dll", "libcrypto-1_1.dll"]:
                    dll_file = os.path.join(os.getcwd(), filename)
                    if os.path.exists(dll_file):
                        os.unlink(dll_file)


class BuiltCommercialMSI(_MSIDist):
    """Create a Built Commercial MSI distribution"""

    description = 'create a commercial built MSI distribution'
    user_options = [
        ('include-sources', None,
         "exclude sources built distribution (default: True)"),
    ] + _MSIDist.user_options

    boolean_options = _MSIDist.boolean_options + ['include-sources']

    def initialize_options(self):
        """Initialize the options"""
        _MSIDist.initialize_options(self)
        self.include_sources = None

    def finalize_options(self):
        """Finalize the options"""
        _MSIDist.finalize_options(self)

        self.wxs = _MSIDist.finalize_msi_descriptor(self)

        self.fix_txtfiles = {
            'README.txt': os.path.join(COMMERCIAL_DATA, 'README_COM.txt'),
            'LICENSE.txt': os.path.join(COMMERCIAL_DATA, 'LICENSE_COM.txt'),
            'CHANGES.txt': os.path.join(os.getcwd(), 'CHANGES.txt'),
            'README.rst': os.path.join(os.getcwd(), 'README.txt'),
            'CONTRIBUTING.rst': os.path.join(os.getcwd(), 'CONTRIBUTING.rst'),
            'INFO_SRC': os.path.join(os.getcwd(), 'docs', 'INFO_SRC'),
            'INFO_BIN': os.path.join(os.getcwd(), 'docs', 'INFO_BIN'),
        }

    def _get_wixobj_name(self, myc_version=None):
        """Get the name for the wixobj-file

        Return string
        """
        mycver = myc_version or self.distribution.metadata.version

        name_fmt = "mysql-connector-python-commercial-" \
                   "{conver}{version_extra}{edition}"

        if VERSION < (2, 1):
            name_fmt += ".wixobj"
        else:
            name_fmt += "-{arch}.wixobj"

        return name_fmt.format(
                    conver=mycver,
                    edition=self.edition,
                    version_extra="-{0}".format(VERSION_EXTRA)
                        if VERSION_EXTRA else "",
                    arch='windows-x86-64bit'
                        if ARCH_64BIT else 'windows-x86-32bit'
                )

    def _prepare(self):
        """Prepare the distribution"""
        # set license information
        log.info("Setting license information in version.py")
        loc_version_py = os.path.normcase('lib/mysql/connector/version.py')
        log.info("Writing to file: {}".format(loc_version_py))
        with open(loc_version_py, 'r') as version_py:
            version_lines = version_py.readlines()
            for (nr, line) in enumerate(version_lines):
                if line.startswith('LICENSE'):
                    version_lines[nr] = 'LICENSE = "Commercial"\n'
        with open(loc_version_py, 'w') as changed_version_py:
            changed_version_py.write(''.join(version_lines))

        log.info("Preparing installation in %s", self.build_base)
        cmd_install = self.reinitialize_command('install', reinit_subcommands=1)
        cmd_install.prefix = self.prefix
        cmd_install.with_mysql_capi = self.with_mysql_capi
        cmd_install.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_install.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_install.with_protoc = self.with_protoc
        cmd_install.byte_code_only = 1
        cmd_install.commercial = 1
        cmd_install.static = False
        cmd_install.ensure_finalized()
        cmd_install.run()

        # documentation files should be available, even when empty
        add_docs('docs')


class GPLMSI(_MSIDist):
    """Create a GPL MSI distribution"""

    description = 'create a GPL MSI distribution'

    def finalize_options(self):
        """Finalize the options"""
        _MSIDist.finalize_options(self)

        self.wxs = _MSIDist.finalize_msi_descriptor(self)
        self.fix_txtfiles = {
            'README.txt': os.path.join(os.getcwd(), 'README.txt'),
            'LICENSE.txt': os.path.join(os.getcwd(), 'LICENSE.txt'),
            'CHANGES.txt': os.path.join(os.getcwd(), 'CHANGES.txt'),
            'README.rst': os.path.join(os.getcwd(), 'README.txt'),
            'CONTRIBUTING.rst': os.path.join(os.getcwd(), 'CONTRIBUTING.rst'),
            'INFO_SRC': os.path.join(os.getcwd(), 'docs', 'INFO_SRC'),
            'INFO_BIN': os.path.join(os.getcwd(), 'docs', 'INFO_BIN'),
        }

    def _get_wixobj_name(self, myc_version=None):
        """Get the name for the wixobj-file

        Return string
        """
        mycver = myc_version or self.distribution.metadata.version
        name_fmt = ("mysql-connector-python-{conver}{version_extra}{edition}")
        if VERSION < (2, 1):
            name_fmt += ".wixobj"
        else:
            name_fmt += "-{arch}.wixobj"
        return name_fmt.format(
                    conver=mycver,
                    edition=self.edition,
                    version_extra="-{0}".format(VERSION_EXTRA)
                        if VERSION_EXTRA else "",
                    arch='windows-x86-64bit'
                        if ARCH_64BIT else 'windows-x86-32bit'
                )
