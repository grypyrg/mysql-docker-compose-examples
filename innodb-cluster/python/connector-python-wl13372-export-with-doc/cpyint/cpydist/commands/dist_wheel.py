# Copyright (c) 2017, 2019, Oracle and/or its affiliates. All rights reserved.
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

"""Implements the Distutils command for creating Wheel packages.
"""

import os
import sys
import shutil
import platform

from distutils import log
from distutils.dir_util import mkpath, remove_tree
from wheel.bdist_wheel import bdist_wheel

from . import CEXT_OPTIONS, get_openssl_link_args

CEXT_STATIC_OPTIONS = [
    ("static", None, "Link C libraries statically with the C Extension"),
]
ARCH_64BIT = sys.maxsize > 2**32

class BuildDistWheel(bdist_wheel):
    """Create a Wheel distribution."""
    user_options = bdist_wheel.user_options + CEXT_OPTIONS \
                   + CEXT_STATIC_OPTIONS

    def initialize_options(self):
        """Initialize the options."""
        bdist_wheel.initialize_options(self)
        self.with_mysql_capi = None
        self.with_protobuf_include_dir = None
        self.with_protobuf_lib_dir = None
        self.with_protoc = None
        self.extra_compile_args = None
        self.extra_link_args = None
        self.static = None

    def finalize_options(self):
        """Finalize the options."""
        bdist_wheel.finalize_options(self)
        if not any((self.with_mysql_capi, self.with_protobuf_include_dir,
                    self.with_protobuf_lib_dir, self.with_protoc)):
            self.root_is_pure = True
            self.universal = True
            return

        if not self.with_mysql_capi or \
           not os.path.isdir(self.with_mysql_capi):
            log.error("Location of MySQL C API (Connector/C) must be "
                      "provided.")
            sys.exit(1)
        self.with_mysql_capi = os.path.abspath(self.with_mysql_capi)

        if not self.with_protobuf_include_dir or \
           not os.path.isdir(self.with_protobuf_include_dir):
            log.error("Location of Protobuf include directory must be "
                      "provided.")
            sys.exit(1)
        self.with_protobuf_include_dir = \
            os.path.abspath(self.with_protobuf_include_dir)

        if not self.with_protobuf_lib_dir or \
           not os.path.isdir(self.with_protobuf_lib_dir):
            log.error("Location of Protobuf library directory must be "
                      "provided.")
            sys.exit(1)
        self.with_protobuf_lib_dir = \
            os.path.abspath(self.with_protobuf_lib_dir)

        if not self.with_protoc or not os.path.isfile(self.with_protoc):
            log.error("Location of protoc must be provided.")
            sys.exit(1)
        self.with_protoc = os.path.abspath(self.with_protoc)

        if platform.system() == "Linux" and not self.extra_link_args:
            self.extra_link_args = get_openssl_link_args(self.with_mysql_capi)

    def run(self):
        """Build the wheel packages."""
        install = self.reinitialize_command("install", reinit_subcommands=True)
        install.with_mysql_capi = self.with_mysql_capi
        install.with_protobuf_include_dir = self.with_protobuf_include_dir
        install.with_protobuf_lib_dir = self.with_protobuf_lib_dir
        install.with_protoc = self.with_protoc
        install.extra_compile_args = self.extra_compile_args
        install.extra_link_args = self.extra_link_args
        install.static = self.static
        install.is_wheel = True
        self.run_command("install")
        self.skip_build = True
        if self.distribution.data_files:
            # Copy data_files before bdist_wheel.run()
            for directory, files in self.distribution.data_files:
                dst = os.path.join(install.build_lib, directory)
                mkpath(dst)
                for filename in files:
                    src = os.path.join(os.getcwd(), filename)
                    log.info("copying {0} -> {1}".format(src, dst))
                    shutil.copy(src, dst)
            # Don't include data_files in wheel
            self.distribution.data_files = None

        # Create wheel
        bdist_wheel.run(self)

        # Remove build folder
        if not self.keep_temp:
            build = self.get_finalized_command("build")
            remove_tree(build.build_base, dry_run=self.dry_run)
            mysql_vendor = os.path.join(os.getcwd(), "mysql-vendor")
            if platform.system() == "Darwin" and os.path.exists(mysql_vendor):
                remove_tree(mysql_vendor)
            elif os.name == "nt":
                if ARCH_64BIT:
                    libraries = ["libmysql.dll", "libssl-1_1-x64.dll",
                                 "libcrypto-1_1-x64.dll"]
                else:
                    libraries = ["libmysql.dll", "libssl-1_1.dll",
                                 "libcrypto-1_1.dll"]
                for filename in libraries:
                    dll_file = os.path.join(os.getcwd(), filename)
                    if os.path.exists(dll_file):
                        os.unlink(dll_file)
