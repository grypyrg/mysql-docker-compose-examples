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

"""Testing error code generation information"""

from datetime import datetime

from lib.mysql.connector import errorcode
from cpyint.metasupport.tests import SupportTests


class ErrorCodeTests(SupportTests):

    def test__GENERATED_ON(self):
        self.assertTrue(isinstance(errorcode._GENERATED_ON, str))
        try:
            generatedon = datetime.strptime(errorcode._GENERATED_ON,
                                            '%Y-%m-%d').date()
        except ValueError as err:
            self.fail(err)

        delta = (datetime.now().date() - generatedon).days
        self.assertTrue(
            delta < 120,
            "errorcode.py is more than 120 days old ({0})".format(delta))


class LocalesEngClientErrorTests(SupportTests):

    """Testing locales.eng.client_error"""

    def test__GENERATED_ON(self):
        try:
            from lib.mysql.connector.locales.eng import client_error
        except ImportError:
            self.fail("locales.eng.client_error could not be imported")

        self.assertTrue(isinstance(client_error._GENERATED_ON, str))
        try:
            generatedon = datetime.strptime(client_error._GENERATED_ON,
                                            '%Y-%m-%d').date()
        except ValueError as err:
            self.fail(err)

        delta = datetime.now().date() - generatedon
        self.assertTrue(
            delta.days < 120,  # pylint disable=E1103
            "eng/client_error.py is more than 120 days old ({0})".format(
                delta.days))  # pylint disable=E1103
