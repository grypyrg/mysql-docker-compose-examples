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

"""Miscellaneous utility functions"""


from distutils import log
from distutils.file_util import copy_file
from distutils.dir_util import mkpath
import os
import subprocess
import sys
import gzip
import tarfile

from distutils.sysconfig import get_python_version


PY2 = sys.version_info[0] == 2


def _parse_os_release():
    """Parse the contents of /etc/os-release file.

    Returns:
        A dictionary containing release information.
    """
    distro = {}
    os_release_file = os.path.join("/etc", "os-release")
    if not os.path.exists(os_release_file):
        return distro
    with open(os_release_file) as file_obj:
        for line in file_obj:
            key_value = line.split("=")
            if len(key_value) != 2:
                continue
            key = key_value[0].lower()
            value = key_value[1].rstrip("\n").strip('"')
            distro[key] = value
    return distro


def _parse_lsb_release():
    """Parse the contents of /etc/lsb-release file.

    Returns:
        A dictionary containing release information.
    """
    distro = {}
    lsb_release_file = os.path.join("/etc", "lsb-release")
    if os.path.exists(lsb_release_file):
        with open(lsb_release_file) as file_obj:
            for line in file_obj:
                key_value = line.split("=")
                if len(key_value) != 2:
                    continue
                key = key_value[0].lower()
                value = key_value[1].rstrip("\n").strip('"')
                distro[key] = value
    return distro


def _parse_lsb_release_command():
    """Parse the output of the lsb_release command.

    Returns:
        A dictionary containing release information.
    """
    distro = {}
    with open(os.devnull, "w") as devnull:
        try:
            stdout = subprocess.check_output(
                ("lsb_release", "-a"), stderr=devnull)
        except OSError:
            return None
        lines = stdout.decode(sys.getfilesystemencoding()).splitlines()
        for line in lines:
            key_value = line.split(":")
            if len(key_value) != 2:
                continue
            key = key_value[0].replace(" ", "_").lower()
            value = key_value[1].strip("\t")
            distro[key] = value.encode("utf-8") if PY2 else value
    return distro


def linux_distribution():
    """Tries to determine the name of the Linux OS distribution name.

    First tries to get information from ``/etc/os-release`` file.
    If fails, tries to get the information of ``/etc/lsb-release`` file.
    And finally the information of ``lsb-release`` command.

    Returns:
        A tuple with (`name`, `version`, `codename`)
    """
    distro = _parse_lsb_release()
    if distro:
        return (distro.get("distrib_id", ""),
                distro.get("distrib_release", ""),
                distro.get("distrib_codename", ""))

    distro = _parse_lsb_release_command()
    if distro:
        return (distro.get("distributor_id", ""),
                distro.get("release", ""),
                distro.get("codename", ""))

    distro = _parse_os_release()
    if distro:
        return (distro.get("name", ""),
                distro.get("version_id", ""),
                distro.get("version_codename", ""))

    return ("", "", "")


def get_dist_name(distribution, source_only_dist=False, platname=None,
                  python_version=None, commercial=False, edition=''):
    """Get the distribution name

    Get the distribution name usually used for creating the egg file. The
    Python version is excluded from the name when source_only_dist is True.
    The platname will be added when it is given at the end.

    Returns a string.
    """
    name = distribution.metadata.name
    if edition:
        name += edition
    if commercial:
        name += '-commercial'
    name += '-' + distribution.metadata.version
    if not source_only_dist or python_version:
        pyver = python_version or get_python_version()
        name += '-py' + pyver
    if platname:
        name += '-' + platname
    return name


def get_magic_tag():
    try:
        # For Python Version >= 3.2
        from imp import get_tag
        return get_tag()
    except ImportError:
        return ''


def unarchive_targz(tarball):
    """Unarchive a tarball

    Unarchives the given tarball. If the tarball has the extension
    '.gz', it will be first uncompressed.

    Returns the path to the folder of the first unarchived member.

    Returns str.
    """
    orig_wd = os.getcwd()

    (dstdir, tarball_name) = os.path.split(tarball)
    if dstdir:
        os.chdir(dstdir)

    if '.gz' in tarball_name:
        new_file = tarball_name.replace('.gz', '')
        gz = gzip.GzipFile(tarball_name)
        tar = open(new_file, 'wb')
        tar.write(gz.read())
        tar.close()
        tarball_name = new_file

    tar = tarfile.TarFile(tarball_name)
    tar.extractall()

    os.unlink(tarball_name)
    os.chdir(orig_wd)

    return os.path.abspath(os.path.join(dstdir, tar.getmembers()[0].name))


def add_docs(doc_path, doc_files=None):
    """Prepare documentation files for Connector/Python"""
    mkpath(doc_path)

    if not doc_files:
        doc_files = [
            'mysql-connector-python.pdf',
            'mysql-connector-python.html',
            'mysql-html.css',
        ]
    for file_name in doc_files:
        # Check if we have file in docs/
        doc_file = os.path.join('docs', file_name)
        if not os.path.exists(doc_file):
            # it might be in build/
            doc_file = os.path.join('build', file_name)
            if not os.path.exists(doc_file):
                # we do not have it, create a fake one
                log.warn("documentation '%s' does not exist; creating"
                         " empty", doc_file)
                open(doc_file, "w").close()

        if not os.path.exists(doc_file):
            # don't copy yourself
            copy_file(doc_file, doc_path)
