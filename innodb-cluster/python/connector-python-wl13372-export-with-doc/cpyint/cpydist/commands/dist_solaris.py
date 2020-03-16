# Copyright (c) 2016, 2019, Oracle and/or its affiliates. All rights reserved.
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

"""Implements the Distutils commands making packages for Solaris"""

import os
import platform
import re
import string
import subprocess
import sys
import time

from distutils import log
from distutils.archive_util import make_tarball
from distutils.command.bdist import bdist
from distutils.errors import DistutilsExecError
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, remove_tree

from . import VERSION, VERSION_EXTRA, CEXT_OPTIONS, generate_info_files

SOLARIS_PKGS = {
    'pure': os.path.join('cpyint', 'data', 'SOLARIS', 'pure'),
}
if VERSION >= (2, 1):
    SOLARIS_PKGS.update({
        'cext': os.path.join('cpyint', 'data', 'SOLARIS', 'cext'),
    })

COMMERCIAL_DATA = os.path.join('cpyint', 'data', 'commercial')

PKGINFO = (
    'PKG="{pkg}"\n'
    'NAME="MySQL Connector/Python {ver} {lic}, MySQL driver written in '
    'Python"\n'
    'VERSION="{ver}"\n'
    'ARCH="all"\n'
    'CLASSES="none"\n'
    'CATEGORY="application"\n'
    'VENDOR="ORACLE Corporation"\n'
    'PSTAMP="{tstamp}"\n'
    'EMAIL="MySQL Release Engineering <mysql-build@oss.oracle.com>"\n'
    'BASEDIR="/"\n'
)


class BuildDistSunOS(bdist):

    """Distutils Command building Solaris package"""

    platf_n = '-solaris'
    platf_v = platform.version().split('.')[0]
    platf_a = 'sparc' if platform.processor() == 'sparc' else 'x86'
    description = 'create solaris GPL distribution package'
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('debug', None,
         "turn debugging on"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting file "
         "(default '{0}')".format(platf_n)),
        ('platform-version=', 'v',
         "version of the platform in resulting file "
         "(default '{0}')".format(platf_v)),
        ('platform-version=', 'a',
         "architecture, i.e. 'sparc' or 'x86' in the resulting file "
         "(default '{0}')".format(platf_a)),
        ('static', None,
         "build the c extension static (by default dynamic)."),
        ('trans', 't',
         "transform the package into data stream (default 'False')"),
    ] + CEXT_OPTIONS

    boolean_options = ['keep-temp', 'create-dmg', 'sign', 'static',]

    def initialize_options(self):
        """Initialize the options"""
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()
        self.version_extra = "-{0}".format(VERSION_EXTRA) \
                             if VERSION_EXTRA else ""
        self.keep_temp = None
        self.create_dmg = False
        self.dist_dir = None
        self.started_dir = os.getcwd()
        self.platform = self.platf_n
        self.platform_version = self.platf_v
        self.architecture = self.platf_a
        self.debug = False
        self.sun_pkg_name = "{0}-{1}{2}.pkg".format(self.name, self.version,
                                                    self.version_extra)
        self.dstroot = "dstroot"
        self.sign = False
        self.identity = "MySQL Connector/Python"
        self.static = False
        self.trans = False
        self.with_mysql_capi = None
        self.with_protobuf_include_dir = None
        self.with_protobuf_lib_dir = None
        self.with_protoc = None
        self.extra_compile_args = None
        self.extra_link_args = None

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

    def _prepare_pgk_base(self, template_name, data_dir, root='', gpl=True):
        """Create and populate the src base directory
        """
        log.info("-> _prepare_pgk_base()")
        log.info("  template_name: {0}".format(template_name))
        log.info("  data_dir: {0}".format(data_dir))
        log.info("  root: {0}".format(root))
        log.info("  gpl: {0}".format(gpl))

        # copy and create necessary files
        sun_dist_name = template_name.format(self.name, self.version)
        self.sun_pkg_name = "{0}.pkg".format(sun_dist_name)
        log.info("  sun_pkg_name: {0}".format(self.sun_pkg_name))

        sun_path = os.path.join(root, self.dstroot)
        log.info("  sun_path: {0}".format(sun_path))
        cwd = os.path.join(os.getcwd())
        log.info("Current directory: {0}".format(cwd))

        copy_file_src_dst = []

        # No special folder for GPL or commercial. Files inside the directory
        # will determine what it is.
        data_path = os.path.join(
            sun_path, 'usr', 'share',
            template_name.format(self.name, self.version)
        )
        self.mkpath(data_path)

        if gpl:
            lic = '(GPL)'
        else:
            lic = '(Commercial)'
        sun_pkg_info = os.path.join(sun_path, 'pkginfo')
        log.info("sun_pkg_info path: {0}".format(sun_pkg_info))
        with open(sun_pkg_info, 'w') as f_pkg_info:
            f_pkg_info.write(PKGINFO.format(ver=self.version, lic=lic,
                                            pkg=self.name,
                                            tstamp=time.ctime()))
            f_pkg_info.close()

        if gpl:
            data_path = os.path.join(
                sun_path, 'usr', 'share',
                template_name.format(self.name, self.version))
            copy_file_src_dst += [
                (os.path.join(cwd, "README.txt"),
                 os.path.join(data_path, "README.txt")),
                (os.path.join(cwd, "LICENSE.txt"),
                 os.path.join(data_path, "LICENSE.txt")),
                (os.path.join(cwd, "CHANGES.txt"),
                 os.path.join(data_path, "CHANGES.txt")),
            ]
        else:
            copy_file_src_dst += [
                (os.path.join(COMMERCIAL_DATA, "README_COM.txt"),
                 os.path.join(data_path, "README.txt")),
                (os.path.join(COMMERCIAL_DATA, "LICENSE_COM.txt"),
                 os.path.join(data_path, "LICENSE.txt")),
                (os.path.join(cwd, "CHANGES.txt"),
                 os.path.join(data_path, "CHANGES.txt")),
            ]

        copy_file_src_dst += [
            (os.path.join(cwd, "docs", "INFO_SRC"),
             os.path.join(data_path, "INFO_SRC")),
            (os.path.join(cwd, "docs", "INFO_BIN"),
             os.path.join(data_path, "INFO_BIN")),
            (os.path.join(cwd, "README.rst"),
             os.path.join(data_path, "README.rst")),
            (os.path.join(cwd, "CONTRIBUTING.rst"),
             os.path.join(data_path, "CONTRIBUTING.rst")),
        ]

        for src, dst in copy_file_src_dst:
            copy_file(src, dst)

        info_files = [
            os.path.join(data_path, "README.txt"),
            os.path.join(data_path, "LICENSE.txt"),
        ]
        re_needle = 'Connector/Python \d{1,2}.\d{1,2}'
        xy_needle = 'Connector/Python X.Y'
        version_fmt = 'Connector/Python {0}.{1}'
        for info_file in info_files:
            log.info("correcting version in %s", info_file)
            with open(info_file, 'r+') as fp:
                content = fp.readlines()
                for i, line in enumerate(content):
                    content[i] = re.sub(re_needle,
                                        version_fmt.format(*VERSION[0:2]),
                                        line)
                    content[i] = line.replace(xy_needle,
                                              version_fmt.format(*VERSION[0:2]))

                fp.seek(0)
                fp.write(''.join(content))

    def _create_pkg(self, template_name, dmg=False, sign=False, root='',
                    identity=''):
        """reate the Solaris package using the OS dependient commands.
        """
        log.info("-> _create_pkg()")
        log.info("template_name: {0}".format(template_name))
        log.info("identity: {0}".format(identity))

        sun_dist_name = template_name.format(self.name, self.version)
        self.sun_pkg_name = "{0}.pkg".format(sun_dist_name)
        sun_pkg_contents = os.path.join(self.sun_pkg_name, 'Contents')

        log.info("sun_dist_name: {0}".format(sun_dist_name))
        log.info("sun_pkg_name: {0}".format(self.sun_pkg_name))
        log.info("sun_pkg_contents: {0}".format(sun_pkg_contents))

        sun_path = os.path.join(root, self.dstroot)
        os.chdir(sun_path)
        log.info("Root directory for Prototype: {0}".format(os.getcwd()))

        # creating a Prototype file, this containts a table of contents of the
        # Package, that is suitable to be used for the package creation tool.
        log.info("Creating Prototype file on {0} to describe files to install"
                 "".format(self.dstroot))

        prototype_path = 'Prototype'
        proto_tmp = 'Prototype_temp'

        with open(proto_tmp, "w") as f_out:
            cmd = ['pkgproto', '.']
            pkgp_p = subprocess.Popen(cmd, shell=False, stdout=f_out,
                                      stderr=f_out)
            res = pkgp_p.wait()
            if res != 0:
                log.error("pkgproto command failed with: {0}".format(res))
                raise DistutilsExecError("pkgproto command failed with: {0}"
                                         "".format(res))
            f_out.flush()

        # log Prototype contents
        log.info("/n>> Prototype_temp contents >>/n")
        with open(proto_tmp, 'r') as f_in:
            log.info(f_in.readlines())
        log.info("/n<< Prototype_temp contents end <</n")

        # Fix Prototype file, incert pkginfo and remove Prototype
        log.info("Fixing folder permissions on Prototype contents")
        with open(prototype_path, 'w') as f_out:
            with open(proto_tmp, 'r') as f_in:
                # add pkginfo entry at begining of the Prototype file
                f_out.write("i pkginfo\n")
                f_out.flush()
                for line in f_in:
                    if line.startswith("f none Prototype"):
                        continue
                    elif line.startswith("f none pkginfo"):
                        continue
                    elif line.startswith("d"):
                        tokeep = line.split(' ')[:-3]
                        tokeep.extend(['?', '?', '?', '\n'])
                        f_out.write(' '.join(tokeep))
                    elif line.startswith("f"):
                        tokeep = line.split(' ')[:-2]
                        tokeep.extend(['root', 'bin', '\n'])
                        f_out.write(' '.join(tokeep))
                    else:
                        f_out.write(line)
                f_out.flush()

        # log Prototype contents
        log.info("/n>> Prototype contents >>/n")
        with open(prototype_path, 'r') as f_in:
            log.info(f_in.readlines())
        log.info("/n<< Prototype contents end <</n")

        # Create Solaris package running the package creation command pkgmk
        log.info("Creating package with pkgmk")

        log.info("Root directory for pkgmk: {0}".format(os.getcwd()))
        self.spawn(['pkgmk', '-o', '-r', '.', '-d', '../', '-f',
                    prototype_path])
        os.chdir('../')
        if self.debug:
            log.info("current directory: {0}".format(os.getcwd()))

        # gzip the package folder
        log.info("creating tarball")

        make_tarball(self.sun_pkg_name, self.name, compress='gzip')

        if self.trans:
            log.info("Transforming package into data stream with pkgtrans")
            log.info("Current directory: {0}".format(os.getcwd()))
            self.spawn([
                'pkgtrans',
                '-s',
                os.getcwd(),
                os.path.join(os.getcwd(), self.sun_pkg_name),
                self.name
            ])

        for base, _, files in os.walk(os.getcwd()):
            for filename in files:
                if filename.endswith('.gz') or filename.endswith('.pkg'):
                    new_name = filename.replace(
                        '{0}'.format(self.version),
                        '{0}{1}{2}{3}-{4}'.format(self.version,
                                                  self.version_extra,
                                                  self.platform,
                                                  self.platform_version,
                                                  self.architecture)
                    )
                    file_path = os.path.join(base, filename)
                    file_dest = os.path.join(self.started_dir,
                                             self.dist_dir, new_name)
                    copy_file(file_path, file_dest)
            break

    def run(self):
        """Run the distutils command"""
        self.mkpath(self.dist_dir)
        self.debug = self.verbose

        log.info("generating INFO_SRC and INFO_BIN files")
        generate_info_files()

        cmd_build = self.get_finalized_command('build')
        build_base = os.path.abspath(cmd_build.build_base)
        metadata_name = self.distribution.metadata.name

        if self.with_mysql_capi:
            dist_type = 'cext'
        else:
            dist_type = 'pure'
        data_dir = SOLARIS_PKGS[dist_type]

        sun_root = os.path.join(build_base, 'sun_' + dist_type)

        # build static
        cmd_build_cext_static = self.reinitialize_command('build_ext_static')
        cext_path = os.path.join(build_base, 'python_cext')
        cmd_build_cext_static.build_lib = cext_path
        if 'cext' in SOLARIS_PKGS:
            cmd_build_cext_static.with_mysql_capi = self.with_mysql_capi
        cmd_build_cext_static.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_build_cext_static.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_build_cext_static.with_protoc = self.with_protoc
        cmd_build_cext_static.extra_compile_args = self.extra_compile_args
        cmd_build_cext_static.extra_link_args = self.extra_link_args
        log.info('-> running build_cext_static command')
        cmd_build_cext_static.debug = self.debug
        self.run_command('build_ext_static')
        log.info('<- finished build_cext_static command')
        log.info('*> cext_path: %s', cext_path)

        cmd_install = self.reinitialize_command('install',
                                                reinit_subcommands=1)
        cmd_install.compile = False
        if dist_type == 'cext':
            cmd_install.distribution.metadata.name = metadata_name + '-cext'
            cmd_install.with_mysql_capi = self.with_mysql_capi
        else:
            cmd_install.distribution.metadata.name = metadata_name
            cmd_install.with_mysql_capi = None
            cmd_install.need_ext = False
        cmd_install.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_install.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_install.with_protoc = self.with_protoc
        cmd_install.extra_compile_args = self.extra_compile_args
        cmd_install.extra_link_args = self.extra_link_args
        cmd_install.static = self.static
        cmd_install.root = os.path.join(sun_root, self.dstroot)

        cmd_install.ensure_finalized()
        cmd_install.run()

        if dist_type is not 'pure':
            template_name = "{0}-%s-{1}" % dist_type
        else:
            template_name = "{0}-{1}"

        self._prepare_pgk_base(template_name, data_dir, root=sun_root)

        self._create_pkg(template_name, dmg=self.create_dmg, root=sun_root,
                         sign=self.sign, identity=self.identity)

        os.chdir(self.started_dir)

        if not self.keep_temp:
            remove_tree(build_base, dry_run=self.dry_run)


class BuildDistSunOScom(BuildDistSunOS):

    """Distutils Command building commercial Solaris package"""

    description = 'create Solaris commercial distribution package'

    boolean_options = ['keep-temp', 'create-dmg', 'sign', 'static',]

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'))

    def run(self):
        """Run the distutils command"""
        self.mkpath(self.dist_dir)
        self.debug = self.verbose

        log.info("generating INFO_SRC and INFO_BIN files")
        generate_info_files()

        cmd_build = self.get_finalized_command('build')
        build_base = os.path.abspath(cmd_build.build_base)
        metadata_name = self.distribution.metadata.name

        if self.with_mysql_capi:
            dist_type = 'cext'
        else:
            dist_type = 'pure'
        data_dir = SOLARIS_PKGS[dist_type]

        sun_root = os.path.join(build_base, 'sun_' + dist_type)

        # build static
        cmd_build_cext_static = self.reinitialize_command('build_ext_static')
        cext_path = os.path.join(build_base, 'python_cext')
        cmd_build_cext_static.build_lib = cext_path
        if dist_type == 'cext':
            cmd_build_cext_static.with_mysql_capi = self.with_mysql_capi
        cmd_build_cext_static.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_build_cext_static.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_build_cext_static.with_protoc = self.with_protoc
        cmd_build_cext_static.extra_compile_args = self.extra_compile_args
        cmd_build_cext_static.extra_link_args = self.extra_link_args
        log.info('-> running build_cext_static command')
        cmd_build_cext_static.debug = self.debug
        self.run_command('build_ext_static')
        log.info('<- finished build_cext_static command')
        log.info('*> cext_path: %s', cext_path)

        cmd_install = self.reinitialize_command('install',
                                                reinit_subcommands=1)
        cmd_install.compile = True  # True! Important for Commercial
        cmd_install.commercial = True
        cmd_install.byte_code_only = 1
        if dist_type == 'cext':
            cmd_install.distribution.metadata.name = metadata_name + '-cext'
            cmd_install.with_mysql_capi = self.with_mysql_capi
        else:
            cmd_install.distribution.metadata.name = metadata_name
            cmd_install.with_mysql_capi = None
            cmd_install.need_ext = False
        cmd_install.with_protobuf_include_dir = self.with_protobuf_include_dir
        cmd_install.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        cmd_install.with_protoc = self.with_protoc
        cmd_install.extra_compile_args = self.extra_compile_args
        cmd_install.extra_link_args = self.extra_link_args
        cmd_install.static = self.static
        cmd_install.root = os.path.join(sun_root, self.dstroot)

        cmd_install.ensure_finalized()
        cmd_install.run()

        if dist_type is not 'pure':
            template_name = "{0}-%s-commercial-{1}" % dist_type
        else:
            template_name = "{0}-commercial-{1}"

        self._prepare_pgk_base(template_name, data_dir, root=sun_root,
                               gpl=False)

        self._create_pkg(template_name, dmg=self.create_dmg, root=sun_root,
                         sign=self.sign, identity=self.identity)

        os.chdir(self.started_dir)

        if not self.keep_temp:
            remove_tree(build_base, dry_run=self.dry_run)

    def run_old(self):
        """Run the distutils command"""
        log.info("self.name = {0}".format(self.name))
        self.mkpath(self.dist_dir)

        self.debug = self.verbose

        build_path = 'build'
        root = os.path.join(build_path, 'solaris')
        sun_path = os.path.join(root, self.dstroot)
        self.mkpath(sun_path)

        bdist = self.get_finalized_command('bdist_com')
        bdist.dist_dir = root
        bdist.prefix = sun_path
        log.info("install_cmd.prefix {0}".format(bdist.prefix))
        if not self.debug:
            bdist.verbose = 0
        bdist.compile = False
        bdist.keep_temp = True
        purelib_path = os.path.join(sun_path, 'Library', 'Python',
                                    sys.version[0:3], 'site-packages')
        log.info("py_version {0}".format(purelib_path))
        bdist.bdist_dir = purelib_path

        bdist.bin_install_dir = os.path.join(sun_path, 'bin')
        self.run_command('bdist_com')

        log.info("bdist_com cmd finish")

        if self.distribution.data_files:
            install_cmd = self.get_finalized_command('install_data')
            log.info("install_cmd.dist_dir {0}".format(root))
            install_cmd.install_dir = root
            log.info("install_cmd.root {0}".format(sun_path))
            install_cmd.root = sun_path
            log.info("install_cmd.prefix {0}".format(bdist.prefix))

            self.run_command('install_data')
            log.info("install_cmd cmd finish")

        template_name = "{0}-commercial-{1}"
        self._prepare_pgk_base(template_name, sun_path, root=root, gpl=False)

        self._create_pkg(template_name,
                         dmg=self.create_dmg, root=root,
                         sign=self.sign, identity=self.identity)

        os.chdir(self.started_dir)

        if not self.keep_temp:
            remove_tree(build_path, dry_run=self.dry_run)

