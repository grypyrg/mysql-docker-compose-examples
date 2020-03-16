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

"""Implements the Distutils command 'bdist_com_rpm'

Implements the Distutils command 'bdist_com_rpm' which creates a built
commercial distribution RPM using the spec files available under
folder 'data/RPM/'.
"""


from distutils import log
from distutils.errors import DistutilsError
from distutils.dir_util import remove_tree, mkpath
from distutils.file_util import copy_file
from distutils.core import Command
import os
import subprocess
import sys

from . import (
    COMMON_USER_OPTIONS, CEXT_OPTIONS, EDITION, VERSION, VERSION_TEXT_SHORT,
    VERSION_EXTRA, get_openssl_link_args
)

SPEC_DATA = os.path.join('cpyint', 'data', 'RPM')


class _RPMDist(Command):
    """Create a RPM distribution"""

    user_options = [
        ('build-base=', 'd',
         "base directory for build library"),
        ('rpm-base=', 'd',
         "base directory for creating RPMs (default <bdist-dir>/rpm)"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after "
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('pre-release', None,
         "This is a pre-release (changes RPM release number)")
    ] + COMMON_USER_OPTIONS + CEXT_OPTIONS

    boolean_options = [
        'keep-temp', 'include-sources'
    ]

    rpm_specs = {}

    def initialize_options(self):
        """Initialize the options"""
        self.build_base = None
        self.keep_temp = 0
        self.dist_dir = None
        self.edition = EDITION
        self.rpm_base = None
        self.with_mysql_capi = None
        self.with_protobuf_include_dir = None
        self.with_protobuf_lib_dir = None
        self.with_protoc = None
        self.extra_compile_args = None
        self.extra_link_args = None
        self.pre_release = False

    def finalize_options(self):
        """Finalize the options"""
        self.set_undefined_options('build',
                                   ('build_base', 'build_base'))
        self.set_undefined_options(self.cmd_dist_tarball,
                                   ('dist_dir', 'dist_dir'))

        if not self.rpm_base:
            self.rpm_base = os.path.abspath(
                os.path.join(self.build_base, 'rpmbuild'))

            if not self.with_mysql_capi or \
                    not os.path.isdir(self.with_mysql_capi):
                log.error("Location of MySQL C API (Connector/C)"
                          " must be provided.")
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

    def _populate_rpm_topdir(self, rpm_base):
        """Create and populate the RPM topdir"""
        mkpath(rpm_base)
        dirs = ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']
        self._rpm_dirs = {}
        for dirname in dirs:
            self._rpm_dirs[dirname] = os.path.join(rpm_base, dirname)
            self.mkpath(self._rpm_dirs[dirname])

    def _check_rpmbuild(self):
        """Check if we can run rpmbuild

        Raises DistutilsError when rpmbuild is not available.
        """
        try:
            devnull = open(os.devnull, 'w')
            subprocess.Popen(['rpmbuild', '--version'],
                stdin=devnull, stdout=devnull, stderr=devnull)
        except OSError:
            raise DistutilsError("Could not execute rpmbuild. Make sure "
                                 "it is installed and in your PATH")

    def _create_rpm(self, rpm_name, spec):
        log.info("creating RPM using rpmbuild")
        macro_bdist_dir = "bdist_dir " + os.path.join(rpm_name, '')
        cmd = ['rpmbuild',
            '-ba',
            '--define', macro_bdist_dir,
            '--define', "_topdir " + os.path.abspath(self.rpm_base),
            '--define', "version " + VERSION_TEXT_SHORT,
            spec
            ]

        if not self.verbose:
           cmd.append('--quiet')
        if self.edition:
            cmd.extend(['--define', "edition " + self.edition])

        if "commercial" in rpm_name:
            cmd.extend(['--define', "commercial 1"])

        if self.pre_release:
            cmd.extend(['--define', "pre_release 1"])

        if VERSION_EXTRA:
            cmd.extend(['--define', "version_extra " + VERSION_EXTRA])
        cmd.extend(['--define', "mysql_capi " + self.with_mysql_capi])
        cmd.extend(['--define', "protobuf_include_dir " + self.with_protobuf_include_dir])
        cmd.extend(['--define', "protobuf_lib_dir " + self.with_protobuf_lib_dir])
        cmd.extend(['--define', "protoc " + self.with_protoc])
        if self.extra_compile_args:
            cmd.extend(['--define',
                        "extra_compile_args '{0}'"
                        "".format(self.extra_compile_args)])
        if self.extra_link_args:
            cmd.extend(['--define',
                        "extra_link_args '{0}'".format(self.extra_link_args)])

        self.spawn(cmd)

        for base, dirs, files in os.walk(self.rpm_base):
            for filename in files:
                if filename.endswith('.rpm'):
                    filepath = os.path.join(base, filename)
                    copy_file(filepath, self.dist_dir)

    def run(self):
        """Run the distutils command"""
        # check whether we can execute rpmbuild
        if not self.dry_run:
            self._check_rpmbuild()

        self.mkpath(self.dist_dir)  # final location of RPMs
        self._populate_rpm_topdir(self.rpm_base)

        cmd_sdist = self.get_finalized_command(self.cmd_dist_tarball)
        cmd_sdist.dist_dir = self._rpm_dirs['SOURCES']
        cmd_sdist.run()

        if not self.extra_link_args:
            self.extra_link_args = get_openssl_link_args(self.with_mysql_capi)

        for name, rpm_spec in self.rpm_specs.items():
            self._create_rpm(rpm_name=name, spec=rpm_spec)

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)

    def run_old(self):
        """Run the distutils command"""
        # check whether we can execute rpmbuild
        if not self.dry_run:
            try:
                devnull = open(os.devnull, 'w')
                subprocess.Popen(['rpmbuild', '--version'],
                                 stdin=devnull, stdout=devnull)
            except OSError:
                raise DistutilsError("Cound not execute rpmbuild. Make sure "
                                     "it is installed and in your PATH")

        mkpath(self.dist_dir)

        # build command: to get the build_base
        cmdbuild = self.get_finalized_command("build")
        cmdbuild.verbose = self.verbose 
        self.build_base = cmdbuild.build_base
        self._populate_rpm_topdir(self.rpm_base)

        for name, rpm_spec in self.rpm_specs.items():
            self._prepare_distribution(name)
            self._create_rpm(rpm_name=name, spec=rpm_spec)

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)
            mysql_vendor = os.path.join(os.getcwd(), "mysql-vendor")
            if os.path.exists(mysql_vendor):
                remove_tree(mysql_vendor)


class BuiltCommercialRPM(_RPMDist):
    """Create a Built Commercial RPM distribution"""
    user_options = _RPMDist.user_options + [
        ('include-sources', None,
         "exclude sources built distribution (default: True)"),
    ] + COMMON_USER_OPTIONS

    rpm_specs = {
        'mysql-connector-python-commercial': os.path.join(
            SPEC_DATA, 'mysql-connector-python.spec'),
    }

    cmd_dist_tarball = 'sdist_com'
    
    def initialize_options(self):
        """Initialize the options"""
        _RPMDist.initialize_options(self)
        self.include_sources = False
        self.bdist_base = None

    def finalize_options(self):
        _RPMDist.finalize_options(self)
    

class SDistGPLRPM(_RPMDist):
    """Create a source distribution packages as RPM"""
    description = "create a RPM distribution (GPL)"

    rpm_specs = {
        'mysql-connector-python': os.path.join(
            SPEC_DATA, 'mysql-connector-python.spec'),
    }

    cmd_dist_tarball = 'sdist'

    def finalize_options(self):
        _RPMDist.finalize_options(self)
