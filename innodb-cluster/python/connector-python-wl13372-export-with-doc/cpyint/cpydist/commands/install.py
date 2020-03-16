# Copyright (c) 2014, 2019, Oracle and/or its affiliates. All rights reserved.
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

"""Custom install Distutils commands"""

import os
from distutils import log
from distutils.sysconfig import get_python_version

try:
    from lib.cpy_distutils import Install, InstallLib
except ImportError:
    # We have Connector/Python 2.0 or earlier
    from distutils.command.install import install as Install
    from distutils.command.install_lib import install_lib as InstallLib

from ..commercial import remove_gpl

COMMERCIAL_OPTIONS = [
    ('commercial', None,
     'Install commercial (non-GPL) distribution'),
]


class InstallLibInternal(InstallLib):

    """Used Internally with the InstallInternal command"""

    user_options = InstallLib.user_options + COMMERCIAL_OPTIONS

    boolean_options = InstallLib.boolean_options + ['commercial']

    def initialize_options(self):
        InstallLib.initialize_options(self)
        self.commercial = None
        self.byte_code_only = None

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('commercial', 'commercial'))
        InstallLib.finalize_options(self)

        if self.byte_code_only is None:
            self.byte_code_only = False

    def remove_gpl_license(self, files):
        """Remove GPL license from Python source files"""
        if not files:
            return
        ignore = [
            os.path.join(self.install_dir,
                         os.path.normcase('mysql/__init__.py')),
            os.path.join(self.install_dir,
                         os.path.normcase('mysqlx/protobuf/__init__.py')),
            os.path.join(self.install_dir, 'mysql', 'connector',
                         'locales', 'eng', '__init__.py'),
            os.path.join(self.install_dir, 'mysqlx', 'locales', 'eng',
                         '__init__.py'),
        ]
        django_backend = os.path.join('connector', 'django')
        for pyfile in files:
            if not pyfile.endswith('.py') or pyfile.endswith('egg-info'):
                continue
            if os.path.normpath(pyfile) not in ignore \
                    and django_backend not in pyfile:
                remove_gpl(pyfile, dry_run=self.dry_run)

    def _copy_bytecode_from_pycache(self, start_dir):
        log.info("copying bytecode files from __pycache__ in %s", start_dir)
        for base, dirs, files in os.walk(start_dir):
            for filename in files:
                if filename.endswith('.pyc'):
                    filepath = os.path.join(base, filename)
                    new_name = filename.split('.')[0] + '.pyc'
                    os.rename(filepath, os.path.join(base, '..', new_name))

        for base, dirs, files in os.walk(start_dir):
            if base.endswith('__pycache__'):
                os.rmdir(base)

    def run(self):
        self.build()
        outfiles = self.install()

        if self.commercial:
            # We remove license even though .py might be deleted, making
            # sure there is no comment mentioning the GPL.
            self.remove_gpl_license(outfiles)
            self.byte_code_only = 1

        if self.byte_code_only and outfiles:
            self.byte_compile(outfiles)
            if get_python_version().startswith('3'):
                self._copy_bytecode_from_pycache(self.install_dir)
            for source_file in outfiles:
                if os.path.join('mysql', '__init__.py') in source_file:
                    continue
                if source_file.endswith('.py'):
                    log.info("Removing %s", source_file)
                    os.remove(source_file)


class InstallInternal(Install):

    """Install Connector/Python with commercial option

    This command is used internally for packaging.
    """

    user_options = Install.user_options + COMMERCIAL_OPTIONS

    boolean_options = Install.boolean_options + ['commercial']

    def initialize_options(self):
        Install.initialize_options(self)
        self.commercial = None
        self.is_wheel = False

    def finalize_options(self):
        Install.finalize_options(self)

    def run(self):
        Install.run(self)
