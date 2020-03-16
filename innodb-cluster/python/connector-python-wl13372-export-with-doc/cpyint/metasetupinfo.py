# Copyright (c) 2014,  2019, Oracle and/or its affiliates. All rights reserved.
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

from distutils import util
from distutils.dir_util import copy_tree
import os
import sys


def byte_compile(py_files, optimize=0, force=0, prefix=None, base_dir=None,
                 verbose=1, dry_run=0, direct=None):
    """Byte-compile Python source files

    This function calls the original distutils.util.byte_compile function but
    additionally removes the Python source files.

    This function is only to be used with non GPLv2 sources.
    """
    util.orig_byte_compile(py_files, optimize, force, prefix, base_dir,
                      verbose, dry_run, direct)

    for py_file in py_files:
        if 'mysql/__init__.py' in py_file:
            continue
        os.unlink(py_file)


try:
    from .cpydist.commands import (
        sdist, bdist, dist_rpm, dist_deb, dist_osx, dist_solaris
    )

    from distutils import dir_util
    dir_util.copy_tree = copy_tree

    command_classes = {
        'sdist': sdist.GenericSourceGPL,
        'sdist_gpl': sdist.SourceGPL,
        'bdist_com': bdist.BuiltCommercial,
        'bdist_com_rpm': dist_rpm.BuiltCommercialRPM,
        'sdist_gpl_rpm': dist_rpm.SDistGPLRPM,
        'sdist_com': sdist.SourceCommercial,
        'sdist_gpl_deb': dist_deb.DebianBuiltDist,
        'bdist_com_deb': dist_deb.DebianCommercialBuilt,
        'sdist_gpl_osx': dist_osx.BuildDistOSX,
        'bdist_com_osx': dist_osx.BuildDistOSXcom,
        'sdist_gpl_sunos': dist_solaris.BuildDistSunOS,
        'bdist_com_sunos': dist_solaris.BuildDistSunOScom,
    }

    try:
        from .cpydist.commands import dist_wheel
        command_classes['bdist_wheel'] = dist_wheel.BuildDistWheel
    except ImportError:
        # The wheel package is not available
        pass

    try:
        from .cpydist.commands import install
        command_classes.update({
            'install': install.InstallInternal,
            'install_lib': install.InstallLibInternal,
        })
    except ImportError:
        # Works for Connector/Python 2.1 and later
        pass

    if sys.version_info >= (2, 7):
        # MSI only supported for Python 2.7 and greater
        from .cpydist.commands import (dist_msi)
        command_classes.update({
            'bdist_com': bdist.BuiltCommercial,
            'bdist_com_msi': dist_msi.BuiltCommercialMSI,
            'sdist_gpl_msi': dist_msi.GPLMSI,
        })

except ImportError:
    # Part of Source Distribution
    command_classes = {}
    raise
