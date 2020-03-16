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

"""Module containing distutils commands for commercial packaging"""


from datetime import date
from distutils import log
from distutils.errors import DistutilsError
import errno

GPL_NOTICE_LINENR = 25

COMMERCIAL_LICENSE_NOTICE = """
This is a release of MySQL Connector/Python, Oracle's dual-
license Python Driver for MySQL. For the avoidance of
doubt, this particular copy of the software is released
under a commercial license and the GNU General Public
License does not apply. MySQL Connector/Python is brought
to you by Oracle.

Copyright (c) 2011, 2019, Oracle and/or its affiliates. All rights reserved.

This distribution may include materials developed by third
parties. For license and attribution notices for these
materials, please refer to the documentation that accompanies
this distribution (see the "Licenses for Third-Party Components"
appendix) or view the online documentation at 
<http://dev.mysql.com/doc/>
"""

COMMERCIAL_SETUP_PY = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2012, %d, Oracle and/or its affiliates. All rights reserved.

import os
from distutils.core import setup
from distutils.command.build import build
from distutils.dir_util import copy_tree

class Build(build):
    def run(self):
        copy_tree('mysql', os.path.join(self.build_lib, 'mysql'))
        copy_tree('mysqlx', os.path.join(self.build_lib, 'mysqlx'))

LONG_DESCRIPTION = \"\"\"
{long_description}
\"\"\"

setup(
    name = '{name}',
    version = '{version}',
    description = '{description}',
    long_description = LONG_DESCRIPTION,
    author = '{author}',
    author_email = '{author_email}',
    license = '{license}',
    keywords = '{keywords}',
    url = '{url}',
    download_url = '{download_url}',
    package_dir = {{ '': '' }},
    packages = ['mysql', 'mysql.connector', 'mysql.connector.django',
       'mysql.connector.locales', 'mysql.connector.locales.eng', 'mysqlx',
       'mysqlx.locales', 'mysqlx.locales.eng', 'mysqlx.protobuf'],
    classifiers = {classifiers},
    cmdclass = {{
        'build': Build,
    }}
)

""" % date.today().year

IGNORE_FILES = [
    "test.py",
]


def remove_gpl(pyfile, dry_run=0):
    """Remove the GPL license form a Python source file

    Raise DistutilsError when a problem is found.
    """
    start = "you can redistribute it and/or modify"
    end = "MA 02110-1301  USA"

    intentionally_empty = "# Following empty comments are intentional.\n"
    pb_generated = "Generated by the protocol buffer compiler"

    # skip files on ignore list.
    for ignore in IGNORE_FILES:
        if pyfile.endswith(ignore):
            log.warn("Ignoring file %s from remove gpl license", pyfile)
            return

    result = []
    removed = 0
    num_lines = 0
    try:
        fp = open(pyfile, "r")
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            # file does not exists, nothing to do
            return
        raise

    line = fp.readline()
    num_lines+= 1
    done = False
    while line:
        if line.startswith(intentionally_empty):
            # We already removed the GPL license
            return
        if pb_generated in line:
            # Generated file by Protocol Buffer compiler
            return
        if line.strip().endswith(start) and not done:
            log.info("removing GPL license from %s", pyfile)
            result.append(intentionally_empty)
            removed += 1
            line = fp.readline()
            num_lines+= 1
            while line:
                result.append("#\n")
                removed += 1
                line = fp.readline()
                num_lines+= 1
                if line.strip().endswith(end):
                    done = True
                    line = fp.readline()
                    num_lines+= 1
                    result.append("# End empty comments.\n")
                    removed += 1
                    break
        result.append(line)
        line = fp.readline()
        num_lines+= 1
    fp.close()
    result.append("\n")

    if removed != GPL_NOTICE_LINENR and num_lines > 2:
        msg = ("Problem removing GPL license. Removed %d lines from "
               "file %s" % (removed, pyfile))
        raise DistutilsError(msg)
    elif removed != GPL_NOTICE_LINENR:
        log.warn("file %s does not have gpl license on header", pyfile)

    if not dry_run:
        fp = open(pyfile, "w")
        fp.writelines(result)
        fp.close()
