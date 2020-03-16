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

import os
import shutil
import zipfile
from distutils import log
from distutils.errors import DistutilsError, DistutilsOptionError
from distutils.dir_util import mkpath
from distutils.file_util import copy_file

class Egg(object):
    def __init__(self, name, destination, builtdir, info_file=None):
        self._egg_name = name
        self._destination = destination
        self._builtdir = builtdir
        self._info_file = info_file
        
        self._info_dir = os.path.join(self._builtdir, 'EGG-INFO')
    
    def get_archive_name(self):
        return os.path.join(self._destination, self._egg_name) + '.egg'
    
    def get_path_filename(self, suffix=''):
        return os.path.join(self._destination, self._egg_name) + '.pth'
    
    def _zip_safe(self, safe, dry_run=0):
        file_zip_safe = os.path.join(self._info_dir, 'zip-safe')
        file_not_zip_safe = os.path.join(self._info_dir, 'not-zip-safe')
        for filename in [file_zip_safe, file_not_zip_safe]:
            try:
                os.unlink(filename)
            except OSError:
                # We force unlinking
                pass
        if safe:
            log.info("adding '%s'" % file_zip_safe)
            if not dry_run:
                open(file_zip_safe, 'w').close()
        else:
            log.info("adding '%s'" % file_not_zip_safe)
            if not dry_run:
                open(file_not_zip_safe, 'w').close()
    
    def create(self, out,
               extra_info_files=[], zip_safe=False, dry_run=0):
        log.info("creating '%s' and adding '%s' to it" % (
                 out, self._builtdir))
        # Create and populate the EGG-INFO direcotry
        mkpath(self._info_dir)
        self._zip_safe(zip_safe, dry_run=dry_run)
        
        copy_file(self._info_file,
                  os.path.join(self._info_dir, 'PKG-INFO'))
        
        for extra_file, dest in extra_info_files:
            if not dest:
                dest = os.path.basename(extra_file)
            copy_file(extra_file,
                      os.path.join(self._info_dir, dest))
        
        return self._zip(out, dry_run=dry_run)

    def _zip(self, out, dry_run=0):
        mkpath(os.path.dirname(out), dry_run=dry_run)
        if not dry_run:
            zip_file = zipfile.ZipFile(out, "w",
                                       compression=zipfile.ZIP_DEFLATED)

        cwd = os.getcwd()
        log.debug("changing into '%s'" % self._builtdir)
        os.chdir(self._builtdir)
        for dirpath, dirnames, filenames in os.walk(os.curdir):
            for name in filenames:
                path = os.path.normpath(os.path.join(dirpath, name))
                if os.path.isfile(path):
                    if not dry_run:
                        zip_file.write(path, path)
                    log.info("adding '%s'" % path)
        if not dry_run:
            zip_file.close()
    
        os.chdir(cwd)
        return out

