#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2012, 2019, Oracle and/or its affiliates. All rights reserved.

import os
from distutils.core import setup
from distutils.command.build import build
from distutils.dir_util import copy_tree

class Build(build):
    def run(self):
        copy_tree('mysql', os.path.join(self.build_lib, 'mysql'))
        copy_tree('mysqlx', os.path.join(self.build_lib, 'mysqlx'))

LONG_DESCRIPTION = """

MySQL driver written in Python which does not depend on MySQL C client
libraries and implements the DB API v2.0 specification (PEP-249).


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

setup(
    name = 'mysql-connector-python',
    version = '8.0.18',
    description = 'MySQL driver written in Python',
    long_description = LONG_DESCRIPTION,
    author = 'Oracle and/or its affiliates',
    author_email = '',
    license = 'Other/Proprietary License',
    keywords = 'mysql db',
    url = 'http://dev.mysql.com/doc/connector-python/en/index.html',
    download_url = 'http://dev.mysql.com/downloads/connector/python/',
    package_dir = { '': '' },
    packages = ['mysql', 'mysql.connector', 'mysql.connector.django',
       'mysql.connector.locales', 'mysql.connector.locales.eng', 'mysqlx',
       'mysqlx.locales', 'mysqlx.locales.eng', 'mysqlx.protobuf'],
    classifiers = ['Development Status :: 5 - Production/Stable', 'Environment :: Other Environment', 'Intended Audience :: Developers', 'Intended Audience :: Education', 'Intended Audience :: Information Technology', 'Intended Audience :: System Administrators', 'License :: Other/Proprietary License', 'Operating System :: OS Independent', 'Programming Language :: Python :: 3.8', 'Topic :: Database', 'Topic :: Software Development', 'Topic :: Software Development :: Libraries :: Application Frameworks', 'Topic :: Software Development :: Libraries :: Python Modules'],
    cmdclass = {
        'build': Build,
    }
)

