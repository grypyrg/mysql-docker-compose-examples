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

"""Implements the Distutils command 'bdist_com'

Implements the Distutils command 'bdist_com' which creates a built
commercial distribution into a folder.
"""

import os
from distutils import log
from distutils import util
from distutils.dir_util import remove_tree, mkpath, copy_tree
from distutils.file_util import copy_file
from distutils.sysconfig import get_python_version
from distutils.command.bdist import bdist

from .. import commercial
from . import COMMON_USER_OPTIONS
from . import VERSION, EDITION, generate_info_files
from ..utils import add_docs


class BuiltCommercial(bdist):
    """Create a Built Commercial distribution"""
    description = 'create a commercial built distribution'
    user_options = [
        ('debug', None,
         "turn debugging on"),
        ('bdist-dir=', 'd',
         "temporary directory for creating the distribution"),
        ('keep-temp', 'k',
         "keep the pseudo-installation tree around after " +
         "creating the distribution archive"),
        ('dist-dir=', 'd',
         "directory to put final built distributions in"),
        ('include-sources', None,
         "exclude sources built distribution (default: True)"),
    ] + COMMON_USER_OPTIONS

    boolean_options = [
        'keep-temp', 'include-sources'
    ]

    def initialize_options (self):
        """Initialize the options"""
        self.bdist_dir = None
        self.keep_temp = 0
        self.dist_dir = None
        self.include_sources = False
        self.plat_name = ''
        self.edition = EDITION
        self.debug = False

    def finalize_options(self):
        """Finalize the options"""
        def _get_fullname():
            if not self.include_sources:
                pyver = '-py' + get_python_version()
            return "{name}-commercial-{version}{edition}{pyver}".format(
                name=self.distribution.get_name(),
                version=self.distribution.get_version(),
                edition=self.edition or '',
                pyver=pyver
            )
        self.distribution.get_fullname = _get_fullname

        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'dist')

        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'),
                                   ('plat_name', 'plat_name'),)
        
        commercial_license = 'Other/Proprietary License'
        self.distribution.metadata.license = commercial_license
        
        python_version = get_python_version()
        if self.include_sources:
            pyver = python_version[0:2]
        else:
            pyver = python_version
        
        # Change classifiers
        new_classifiers = []
        for classifier in self.distribution.metadata.classifiers:
            if classifier.startswith("License ::"):
                classifier = "License :: " + commercial_license
            elif (classifier.startswith("Programming Language ::") and
                  (pyver not in classifier)):
                  log.info("removing classifier %s" % classifier)
                  continue
            new_classifiers.append(classifier)
        self.distribution.metadata.classifiers = new_classifiers
        self.distribution.metadata.long_description += \
            "\n" + commercial.COMMERCIAL_LICENSE_NOTICE

    def _remove_sources(self):
        """Remove Python source files from the build directory"""
        for base, dirs, files in os.walk(self.bdist_dir):
            for filename in files:
                if filename.endswith('.py'):
                    filepath = os.path.join(base, filename)
                    log.info("removing source '%s'", filepath)
                    os.unlink(filepath)

    def _write_setuppy(self):
        content = commercial.COMMERCIAL_SETUP_PY.format(**{
            'name': self.distribution.metadata.name,
            'version': self.distribution.metadata.version,
            'description': self.distribution.metadata.description,
            'long_description': self.distribution.metadata.long_description,
            'author': self.distribution.metadata.author,
            'author_email': self.distribution.metadata.author_email,
            'license': self.distribution.metadata.license,
            'keywords': ' '.join(self.distribution.metadata.keywords),
            'url': self.distribution.metadata.url,
            'download_url': self.distribution.metadata.download_url,
            'classifiers': self.distribution.metadata.classifiers,
        })
        
        fp = open(os.path.join(os.path.join(self.dist_target), 'setup.py'), 'w')
        fp.write(content)
        fp.close()

    def _copy_from_pycache(self, start_dir):
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
        """Run the distutils command"""
        log.info("installing library code to %s" % self.bdist_dir)

        log.info("generating INFO_SRC and INFO_BIN files")
        generate_info_files()

        dist_name = self.distribution.get_fullname()
        self.dist_target = os.path.join(self.dist_dir, dist_name)
        log.info("distribution will be available as '%s'" % self.dist_target)
        
        # build command: just to get the build_base
        cmdbuild = self.get_finalized_command("build")
        self.build_base = cmdbuild.build_base
        
        # install command
        install = self.reinitialize_command('install_lib', reinit_subcommands=1)
        install.compile = False
        install.warn_dir = 0
        install.install_dir = self.bdist_dir
        
        log.info("installing to %s" % self.bdist_dir)
        self.run_command('install_lib')

        # install extra files
        extra_files = {
        }
        for src, dest in extra_files.items():
            self.copy_file(src, dest)
        
        # install_egg_info command
        cmd_egginfo = self.get_finalized_command('install_egg_info')
        cmd_egginfo.install_dir = self.bdist_dir
        self.run_command('install_egg_info')

        installed_files = install.get_outputs()

        # remove the GPL license
        ignore = [
            os.path.join(self.bdist_dir,
                         os.path.normcase('mysql/__init__.py')),
            os.path.join(self.bdist_dir, 'mysql', 'connector', 'locales', 'eng',
                         '__init__.py'),
            cmd_egginfo.target,
        ]
        django_backend = os.path.join('connector', 'django')
        for pyfile in installed_files:
            if '.py' not in pyfile:
                continue
            if pyfile not in ignore and django_backend not in pyfile:
                commercial.remove_gpl(pyfile, dry_run=self.dry_run)

        log.info("setting license information in version.py")
        loc_version_py = os.path.join(
            self.bdist_dir,
            os.path.normcase('mysql/connector/version.py')
            )
        version_py = open(loc_version_py, 'r').readlines()
        for (nr, line) in enumerate(version_py):
            if line.startswith('LICENSE'):
                version_py[nr] = 'LICENSE = "Commercial"\n'
        fp = open(loc_version_py, 'w')
        fp.write(''.join(version_py))
        fp.close()

        # compile and remove sources
        if not self.include_sources:
            util.byte_compile(installed_files, optimize=0,
                               force=True, prefix=install.install_dir)
            self._remove_sources()
            if get_python_version().startswith('3'):
                log.info("copying byte code from __pycache__")
                self._copy_from_pycache(os.path.join(self.bdist_dir, 'mysql'))
                self._copy_from_pycache(os.path.join(self.bdist_dir, 'mysqlx'))
        
        # create distribution
        info_files = [
            ('cpyint/data/commercial/README_COM.txt', 'README.txt'),
            ('cpyint/data/commercial/LICENSE_COM.txt', 'LICENSE.txt'),
            ('README.rst', 'README.rst'),
            ('CONTRIBUTING.rst', 'CONTRIBUTING.rst'),
            ('docs/INFO_SRC', 'INFO_SRC'),
            ('docs/INFO_BIN', 'INFO_BIN'),
        ]
        copy_tree(self.bdist_dir, self.dist_target)
        mkpath(os.path.join(self.dist_target))
        xy_needle = 'Connector/Python X.Y'
        xy_sub = 'Connector/Python {0}.{1}'
        for src, dst in info_files:
            if dst is None:
                dest_name, _ = copy_file(src, self.dist_target)
            else:
                dest_name, _ = copy_file(src, os.path.join(self.dist_target, dst))

            with open(dest_name, 'r+') as fp:
                content = fp.readlines()
                for i, line in enumerate(content):
                    if xy_needle in line:
                        content[i] = line.replace(xy_needle,
                                                  xy_sub.format(*VERSION[0:2]))

                fp.seek(0)
                fp.write(''.join(content))

        add_docs(os.path.join(self.dist_target, 'docs'))

        self._write_setuppy()

        if not self.keep_temp:
            remove_tree(self.build_base, dry_run=self.dry_run)

