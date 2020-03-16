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

"""Testing version information"""

try:
    from docutils.core import publish_doctree
except ImportError:
    raise ImportError("docutils is required for running internal tests")
import os
import re

from cpyint.metasupport.tests import SupportTests, CHECK_CPY_VERSION


class VersionTest(SupportTests):
    """Testing the version of Connector/Python"""
    def test_version(self):
        """Test validity of version"""
        version = self.get_connector_version()

        self.assertEqual(CHECK_CPY_VERSION, version)

        self.assertTrue(all(
            [isinstance(version[0], int),
            isinstance(version[1], int),
            isinstance(version[2], int),
            (isinstance(version[3], str) or (version[3] == None)),
            isinstance(version[4], int)]))

    def test_changelog(self):
        """Check version entry in changelog"""
        version = self.get_connector_version()
        if version[3]:
            version_text = self.get_connector_version_text(suffix=True)
        else:
            version_text = self.get_connector_version_text()
        found = False
        line = None
        with open('CHANGES.txt', 'r') as log:
            doctree = publish_doctree(log.read()).asdom()
            log.seek(0)
            for line in log.readlines():
                if version_text in line:
                    found = True
                    break

        self.assertTrue(found, "Version {0} not found in CHANGES.txt".format(
            version_text
        ))

        re_version_title = re.compile(r'^v\d+\.\d+.\d+')
        releases = []

        for title in doctree.getElementsByTagName('title'):
            title_text = title.childNodes[0].nodeValue

            match = re_version_title.match(title_text)
            if match:
                # Change Log entries can only be list items
                for item in title.nextSibling.childNodes:
                    self.assertEqual(item.nodeName, 'list_item',
                                     "Change log entries must be list items")


    def test_files_mentioning_version(self):
        """Check for version number important files

        Test whether the current version is being mentioned in some
        important files like README or the license files.
        """
        files = [
            'README.txt',
            os.path.join('cpyint', 'data', 'MSWindows', 'upgrade_codes.json'),
        ]
        ver = '.'.join([ str(val) for val in self.get_connector_version()[0:2]])

        for afile in files:
            with open(afile, 'r') as fp:
                content = fp.read()
            if ver not in content:
                self.fail("Version {ver} not mentioned in file {afile}".format(
                    ver=ver, afile=afile))

