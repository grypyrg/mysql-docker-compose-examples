# Copyright (c) 2013, 2017, Oracle and/or its affiliates. All rights reserved.
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

"""Parse MySQL supported Character Sets and Collations
"""

import codecs
import logging
import os
import sys

sys.path.insert(0, 'lib')
sys.path.insert(0, '.')

import mysql.connector
from cpyint.metasupport import (
    MIN_MYSQL_VERSION,
    check_python_version,
    check_mysql_version,
    check_mysql_version_freshness,
    get_cli_arguments,
    write_cpy_source_header,
    write_cext_source_header
)

check_python_version(v2=(2, 7), v3=(3, 2))

# Name of the module and header which will contain the character sets
CHARSET_MODULE = 'charsets.py'
CHARSET_HEADER = 'charsets.h'

# Default database configuration
_DB_CONFIG = {
    'user': 'root',
    'password': '',
    'database': 'INFORMATION_SCHEMA',
    'host': '127.0.0.1',
    'port': 3306,
    'unix_socket': None,
}

_CMD_ARGS = {
    ('', '--output'): {
        'metavar': 'DIR',
        'help': "Where to write the modules (used for debugging)"
    },
    ('', '--host'): {
        'dest': 'host', 'default': _DB_CONFIG['host'], 'metavar': 'NAME',
        'help': (
            "MySQL server for retrieving character set information. Must be "
            "version {0}.{1}.{2}.").format(*MIN_MYSQL_VERSION)
    },
    ('', '--port'): {
        'dest': 'port', 'default': _DB_CONFIG['port'], 'metavar': 'PORT',
        'help': (
            "TCP/IP port of the MySQL server")
    },

    ('', '--user'): {
        'dest': 'user', 'default': _DB_CONFIG['user'], 'metavar': 'NAME',
        'help': (
            "User for connecting with the MySQL server")
    },

    ('', '--password'): {
        'dest': 'password', 'default': _DB_CONFIG['password'],
        'metavar': 'PASSWORD',
        'help': (
            "Password for connecting with the MySQL server")
    },
    ('-S', '--socket'): {
        'dest': 'unix_socket', 'default': _DB_CONFIG['unix_socket'],
        'metavar': 'NAME',
        'help': "Socket file for connecting with the MySQL server"
    },
    ('', '--debug'): {
        'dest': 'debug', 'action': 'store_true', 'default': False,
        'help': 'Show/Log debugging messages'
    },
}

def get_charset_info(dbconfig=None):
    if not dbconfig:
        dbconfig = _DB_CONFIG.copy()

    cnx = mysql.connector.connect(**dbconfig)
    cur = cnx.cursor()

    cur.execute(
        "SELECT id, character_set_name, collation_name, is_default "
        "FROM collations ORDER BY id"
    )
    result = cur.fetchall()
    cnx.close()
    return result

def write_module(version, charset_info, output_folder):
    """Write the Python module"""
    charset_module = os.path.join(output_folder, CHARSET_MODULE)
    logging.debug("Writing character sets to '{}'".format(
                  charset_module))

    fp = codecs.open(charset_module, 'w', 'utf8')
    write_cpy_source_header(fp, version, start_year=2013)

    fp.write('"""This module contains the MySQL Server Character Sets"""\n\n')

    fp.write('MYSQL_CHARACTER_SETS = [\n')
    fp.write('    # (character set name, collation, default)\n')
    prev_id = 0
    for (id, charset, collation, default) in charset_info:
        for i in range(id - prev_id):
            fp.write('    None,\n')
        if default == 'Yes':
            default = 'True'
        else:
            default = 'False'
        fp.write('    ("{0}", "{1}", {2}),  # {3}\n'.format(
                 charset, collation, default, id))
        prev_id = id + 1
    fp.write("]\n\n")
    print("Wrote {0}".format(charset_module))

    fp.close()


def write_header(version, charset_info, output_folder=None):
    """Write the Python module"""
    output_folder = output_folder

    charset_module = os.path.join(output_folder, CHARSET_HEADER)
    logging.debug("Writing character sets to '{}'".format(
                  charset_module))

    fp = codecs.open(charset_module, 'w', 'utf8')
    write_cext_source_header(fp, version, start_year=2015)

    fp.write('// This module contains the MySQL Server Character Sets\n\n')

    fp.write('const int mysql_charsets_count= %d;\n' % len(charset_info))
    fp.write('const MYSQL_CHARACTER_SET_INFO mysql_character_sets[]=\n{\n')
    fp.write('    // (character set name, collation, default, id)\n')
    prev_id = 0
    last_id = charset_info[-1][0]
    for (id, charset, collation, default) in charset_info:
        for i in range(id - prev_id):
            fp.write('    {NULL, NULL, 0, 0},  // Not used\n')
        if default == 'Yes':
            default = 1
        else:
            default = 0
        fp.write('    {{"{name}", "{collation}", {default}, {id}}},\n'.format(
                 name=charset, collation=collation, default=default, id=id))
        prev_id = id + 1

    fp.write('    {NULL, NULL, 0, 0}  // end\n};\n')

    fp.write("\n\n#endif // MYCONNPY_CHARSETS_H\n")

    print("Wrote {0}".format(charset_module))

    fp.close()


def main():
    """Start the script"""
    args = get_cli_arguments(
        _CMD_ARGS, description="mysql_charsets")
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    try:
        check_mysql_version_freshness()
    except ValueError as err:
        print("Update script: {}".format(err))
        exit(3)

    config = _DB_CONFIG.copy()
    config['host'] = args.host
    config['port'] = args.port
    config['user'] = args.user
    config['password'] = args.password
    config['unix_socket'] = args.unix_socket

    mysql_version = (99, 9, 9)
    try:
        cnx = mysql.connector.connect(**config)
        mysql_version = cnx.get_server_version()
        cnx.close()
        check_mysql_version(mysql_version)
    except mysql.connector.Error as exc:
        print("Failed connecting to MySQL server: {error}".format(
            error=str(exc)))
        exit(3)
    except ValueError as err:
        print("The given MySQL server can not be used: {}".format(err))
        exit(3)
    else:
        logging.debug("Using MySQL v{ver}".format(
            ver="{:d}.{:d}.{:d}".format(*mysql_version)))

    if args.output:
        output_folder = args.output
        cext_output_folder = args.output
    else:
        output_folder = os.path.join('lib', 'mysql', 'connector')
        cext_output_folder = os.path.join('src', 'include')


    charset_info = get_charset_info(config)
    write_module(mysql_version, charset_info, output_folder)
    # Header file is not needed with current code
    # write_header(mysql_version, charset_info, cext_output_folder)

if __name__ == '__main__':
    main()
