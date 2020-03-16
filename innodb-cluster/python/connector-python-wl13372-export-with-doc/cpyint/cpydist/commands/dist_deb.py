# Copyright (c) 2013, 2019, Oracle and/or its affiliates. All rights reserved.
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

"""Implements the Distutils commands creating Debian packages
"""

from datetime import datetime
import os
import subprocess
import platform
import re
import sys

from distutils.core import Command
from distutils.file_util import copy_file, move_file
from distutils.dir_util import remove_tree
from distutils import log

from ..utils import unarchive_targz, linux_distribution
from . import COMMON_USER_OPTIONS, CEXT_OPTIONS
from . import VERSION, VERSION_TEXT_SHORT, VERSION_EXTRA, EDITION
from . import get_openssl_link_args


DPKG_MAKER = 'dpkg-buildpackage'
DEBIAN_ROOT = os.path.join('cpyint', 'data', 'Debian')

class DebianBuiltDist(Command):
    description = 'create a source distribution Debian package'
    debian_files = [
        'control',
        'changelog',
        'copyright',
        'docs',
        'postinst',
        'postrm',
        'compat',
        'rules',
    ]
    linux_dist = linux_distribution()[0]
    user_options = [
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('debug', None,
         "turn debugging on"),
        ('dist-dir=', 'd',
         "directory to put final source distributions in"),
        ('platform=', 'p',
         "name of the platform in resulting files "
         "(default '%s')" % linux_dist.lower()),
        ('sign', None,
         "sign the Debian package"),
    ] + COMMON_USER_OPTIONS + CEXT_OPTIONS

    def initialize_options(self):
        """Initialize the options"""
        self.keep_temp = False
        self.debug = False
        self.dist_dir = None
        self.platform = linux_distribution()[0].lower()
        if "debian" in self.platform:
            # For debian we only use the first part of the version, Ubuntu two
            self.platform_version = linux_distribution()[1].split('.', 2)[0]
        else:
            self.platform_version = '.'.join(
                linux_distribution()[1].split('.', 2)[0:2])
        self.sign = False
        self.debian_support_dir = os.path.join(DEBIAN_ROOT, 'gpl')
        self.edition = EDITION
        self.codename = linux_distribution()[2].lower()
        self.version_extra = "-{0}".format(VERSION_EXTRA) \
                             if VERSION_EXTRA else ""
        self.with_mysql_capi = None
        self.with_protobuf_include_dir = None
        self.with_protobuf_lib_dir = None
        self.with_protoc = None
        self.with_cext = False
        self.extra_compile_args = None
        self.extra_link_args = None

    def finalize_options(self):
        """Finalize the options"""

        cmdbuild = self.get_finalized_command("build")
        self.build_base = cmdbuild.build_base

        if not self.dist_dir:
            self.dist_dir = 'dist'

        if self.sign:
            self.sign = True

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
                self.with_mysql_capi = os.path.abspath(self.with_mysql_capi)

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

    def _get_orig_name(self):
        """Returns name for tarball according to Debian's policies
        """
        return "%(name)s_%(version)s%(version_extra)s.orig" % {
            'name': self.distribution.get_name(),
            'version': self.distribution.get_version(),
            'version_extra': self.version_extra
            }

    @property
    def _have_python3(self):
        """Check whether this distribution has Python 3 support
        """
        try:
            devnull = open(os.devnull, 'w')
            subprocess.Popen(['py3versions'],
                stdin=devnull, stdout=devnull, stderr=devnull)
        except OSError:
            return False

        return True

    def _get_changes(self):
        log_lines = []
        found_version = False
        found_items = False
        with open('CHANGES.txt', 'r') as fp:
            for line in fp.readlines():
                line = line.rstrip()
                if line.endswith(VERSION_TEXT_SHORT):
                    found_version = True
                if not line.strip() and found_items:
                    break
                elif found_version and line.startswith('- '):
                    log_lines.append(' '*2 + '* ' + line[2:])
                    found_items = True

        return log_lines

    def _populate_debian(self):
        """Copy and make files ready in the debian/ folder
        """
        for afile in self.debian_files:
            copy_file(os.path.join(self.debian_support_dir, afile),
                      self.debian_base)

        copy_file(os.path.join(self.debian_support_dir, 'source', 'format'),
                  os.path.join(self.debian_base, 'source'))

        # Update the version and log in the Debian changelog
        changelog_file = os.path.join(self.debian_base, 'changelog')
        changelog = open(changelog_file, 'r').readlines()
        log.info("changing changelog '%s' version and log", changelog_file)
        log_lines = self._get_changes()
        if not log_lines:
            log.error("Failed reading change history from CHANGES.txt")
            log_lines.append('  * (change history missing)')
        newchangelog = []
        firstline = True
        regex = re.compile(r'.*\((\d+\.\d+.\d+-1)\).*')
        for line in changelog:
            line = line.rstrip()
            match = regex.match(line)
            if match:
                version = match.groups()[0]
                line = line.replace(version,
                                    '{0}.{1}.{2}-1'.format(*VERSION[0:3]))
            if firstline :
                if self.codename == '':
                    proc = subprocess.Popen(['lsb_release', '-c'],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                    codename = proc.stdout.read().split()[-1]
                    if sys.version_info[0] == 3:
                        self.codename = codename.decode()
                    else:
                        self.codename = codename
                line = line.replace('UNRELEASED', self.codename)
                line = line.replace('-1',
                                    '{version_extra}-1{platform}{version}'
                                    .format(platform=self.platform,
                                            version=self.platform_version,
                                            version_extra=self.version_extra))
                firstline = False
            if '* Changes here.' in line:
                for change in log_lines:
                    newchangelog.append(change)
            elif line.startswith(' --') and '@' in line:
                utcnow = datetime.utcnow().strftime(
                    "%a, %d %b %Y %H:%M:%S +0000")
                line = re.sub(r'( -- .* <.*@.*>  ).*', r'\1'+ utcnow, line)
                newchangelog.append(line + '\n')
            else:
                newchangelog.append(line)
        changelog = open(changelog_file, 'w')
        changelog.write('\n'.join(newchangelog))

    def _prepare(self, tarball=None, base=None):
        dist_dirname = self.distribution.get_fullname()

        # Rename tarball to conform Debian's Policy
        if tarball:
            self.orig_tarball = os.path.join(
                os.path.dirname(tarball),
                self._get_orig_name()) + '.tar.gz'
            move_file(tarball, self.orig_tarball)

            untared_dir = unarchive_targz(self.orig_tarball)
            self.debian_base = os.path.join(
                tarball.replace('.tar.gz', ''), 'debian')
        elif base:
            self.debian_base = os.path.join(base, 'debian')

        self.mkpath(self.debian_base)
        self.mkpath(os.path.join(self.debian_base, 'source'))

        self._populate_debian()

    def _make_dpkg(self):
        """Create Debian package in the source distribution folder
        """
        log.info("creating Debian package using '%s'" % DPKG_MAKER)

        orig_pwd = os.getcwd()
        os.chdir(os.path.join(self.build_base,
                 self.distribution.get_fullname()))
        cmd = [
            DPKG_MAKER,
            '-uc',
            ]

        if not self.sign:
            cmd.append('-us')

        success = True
        env = os.environ.copy()
        env['MYSQL_CAPI'] =  self.with_mysql_capi or ''
        env['MYSQLXPB_PROTOBUF_INCLUDE_DIR'] = self.with_protobuf_include_dir \
                                               or ''
        env['MYSQLXPB_PROTOBUF_LIB_DIR'] = self.with_protobuf_lib_dir or ''
        env['MYSQLXPB_PROTOC'] =  self.with_protoc or ''
        env['WITH_CEXT'] = '1' if self.with_cext else ''
        env['EXTRA_COMPILE_ARGS'] = self.extra_compile_args or ''
        env['EXTRA_LINK_ARGS'] = self.extra_link_args or ''
        env['MYSQL_VENDOR'] = os.path.join(os.getcwd(), "mysql-vendor")
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                env=env
        )
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        for line in stdout.split('\n'):
            if self.debug:
                log.info(line)
            if 'error:' in line or 'E: ' in line:
                if not self.debug:
                    log.info(line)
                success = False

        if stderr:
            for line in stderr.split('\n'):
                if self.debug:
                    log.info(line)
                if 'error:' in line or 'E: ' in line:
                    if not self.debug:
                        log.info(line)
                    success = False

        os.chdir(orig_pwd)
        return success

    def _move_to_dist(self):
        """Move *.deb files to dist/ (dist_dir) folder"""
        for base, dirs, files in os.walk(self.build_base):
            for filename in files:
                if '-py3' in filename and not self._have_python3:
                    continue
                if not self.with_mysql_capi and 'cext' in filename:
                    continue
                if filename.endswith('.deb'):
                    filepath = os.path.join(base, filename)
                    copy_file(filepath, self.dist_dir)

    def run(self):
        """Run the distutils command"""
        self.mkpath(self.dist_dir)

        sdist = self.reinitialize_command('sdist')
        sdist.dist_dir = self.build_base
        sdist.formats = ['gztar']
        sdist.ensure_finalized()
        sdist.run()


        if not self.extra_link_args:
            self.extra_link_args = get_openssl_link_args(self.with_mysql_capi)

        self._prepare(sdist.archive_files[0])
        success = self._make_dpkg()

        if not success:
            log.error("Building Debian package failed.")
        else:
            self._move_to_dist()

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)
            mysql_vendor = os.path.join(os.getcwd(), "mysql-vendor")
            if os.path.exists(mysql_vendor):
                remove_tree(mysql_vendor)


class DebianCommercialBuilt(DebianBuiltDist):
    description = 'create a commercial built distribution Debian package'


    def finalize_options(self):
        self.debian_support_dir = os.path.join(DEBIAN_ROOT, 'commercial')
        DebianBuiltDist.finalize_options(self)

    def run(self):
        self.mkpath(self.dist_dir)

        sdist = self.get_finalized_command('sdist_com')
        sdist.dist_dir = self.build_base
        sdist.formats = ['gztar']
        sdist.edition = self.edition
        self.run_command('sdist_com')

        if not self.extra_link_args:
            self.extra_link_args = get_openssl_link_args(self.with_mysql_capi)

        self._prepare(sdist.archive_files[0])
        success = self._make_dpkg()

        if not success:
            log.error("Building Debian package failed.")
        else:
            self._move_to_dist()

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)
            mysql_vendor = os.path.join(os.getcwd(), "mysql-vendor")
            if os.path.exists(mysql_vendor):
                remove_tree(mysql_vendor)

