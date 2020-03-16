import os
import sys
import platform

from datetime import datetime
from distutils.spawn import find_executable
from subprocess import Popen, PIPE

try:
    from dateutil.tz import tzlocal
    NOW = datetime.now(tzlocal())
except ImportError:
    NOW = datetime.now()

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl


VERSION = [999, 0, 0, 'a', 0]  # Set correct after version.py is loaded
VERSION_EXTRA = ''
EDITION = 'CPYINT'
ARCH_64BIT = sys.maxsize > 2**32

# Try setting VERSION, VERSION_TEXT and EDITION from version.py found in CPY
version_py = os.path.join('lib', 'mysql', 'connector', 'version.py')
try:
    with open(version_py, 'rb') as fp:
        exec(compile(fp.read(), version_py, 'exec'))
except IOError:
    # We are not in CPY repository
    pass
else:
    if VERSION[3] and VERSION[4]:
        VERSION_TEXT = '{0}.{1}.{2}{3}{4}'.format(*VERSION)
    else:
        VERSION_TEXT = '{0}.{1}.{2}'.format(*VERSION[0:3])
    VERSION_TEXT_SHORT = '{0}.{1}.{2}'.format(*VERSION[0:3])

COMMON_USER_OPTIONS = [
    ('edition=', None,
     "Edition added in the package name after the version"),
]

CEXT_OPTIONS = [
    ('with-mysql-capi=', None,
     "Location of MySQL C API installation or path to mysql_config"),
    ('with-protobuf-include-dir=', None,
     "Location of Protobuf include directory"),
    ('with-protobuf-lib-dir=', None,
     "Location of Protobuf library directory"),
    ('with-protoc=', None,
     "Location of Protobuf protoc binary"),
    ('extra-compile-args=', None,
     "Extra compile arguments"),
    ('extra-link-args=', None,
     "Extra link arguments"),
]

MYSQL_MIN_VERSION_FOR_OPENSSL = (8, 0, 4)  # MySQL min version to link OpenSSL


def get_openssl_link_args(mysql_config):
    """Get OpenSSL link flags."""
    cmd = []
    if os.path.isdir(mysql_config):
        # If directory, and no mysql_config is available, figure out the
        # lib/ and include/ folders from the the filesystem
        cmd.append(os.path.join(mysql_config, "bin", "mysql_config"))
    else:
        cmd.append(mysql_config)
    cmd.append("--version")

    try:
        proc = Popen(cmd, stdout=PIPE, universal_newlines=True)
        stdout, _ = proc.communicate()
    except OSError as exc:
        raise Exception("Failed executing mysql_config: {0}".format(str(exc)))

    ver = stdout.strip("\n")
    if "-" in ver:
        ver, _ = ver.split("-", 2)
    version = tuple([int(val) for val in ver.split('.')[0:3]])

    if version < MYSQL_MIN_VERSION_FOR_OPENSSL:
        return None

    try:
        cmd = ["pkg-config", "--libs", "openssl"]
        proc = Popen(cmd, stdout=PIPE, universal_newlines=True)
        stdout, _ = proc.communicate()
    except OSError as exc:
        raise Exception("Failed executing mysql_config: {0}".format(str(exc)))

    return stdout.strip("\n")


def get_git_info():
    """Get Git information about the last commit.

    Returns a dict.
    """
    is_git_repo = False
    if find_executable("git") is not None:
        # Check if it's a Git repository
        proc = Popen(["git", "branch"], stdout=PIPE, universal_newlines=True)
        proc.communicate()
        is_git_repo = proc.returncode == 0

    if is_git_repo:
        cmd = ["git", "log", "-n", "1", "--date=iso",
               "--pretty=format:'branch=%D&date=%ad&commit=%H&short=%h'"]
        proc = Popen(cmd, stdout=PIPE, universal_newlines=True)
        stdout, _ = proc.communicate()
        git_info = dict(parse_qsl(stdout.replace("'", "").replace("+", "%2B")
                                  .split(",")[-1:][0].strip()))
        git_info["branch"] = stdout.split(",")[0].split("->")[1].strip()
        return git_info
    else:
        branch_src = os.getenv("BRANCH_SOURCE")
        push_rev = os.getenv("PUSH_REVISION")
        if branch_src and push_rev:
            git_info = {
                "branch": branch_src.split()[-1],
                "date": None,
                "commit": push_rev,
                "short": push_rev[:7]
            }
            return git_info
    return None


def generate_info_files(mysql_version=None):
    # Generate docs/INFO_SRC
    git_info = get_git_info()
    if git_info:
        with open(os.path.join("docs", "INFO_SRC"), "w") as info_src:
            info_src.write("version: {}\n".format(VERSION_TEXT))
            if git_info:
                info_src.write("branch: {}\n".format(git_info["branch"]))
                if git_info.get("date"):
                    info_src.write("date: {}\n".format(git_info["date"]))
                info_src.write("commit: {}\n".format(git_info["commit"]))
                info_src.write("short: {}\n".format(git_info["short"]))

    # Generate docs/INFO_BIN
    now = NOW.strftime("%Y-%m-%d %H:%M:%S %z")
    with open(os.path.join("docs", "INFO_BIN"), "w") as info_bin:
        info_bin.write("build-date: {}\n".format(now))
        info_bin.write("os-info: {}\n".format(platform.platform()))
        if mysql_version:
            info_bin.write("mysql-version: {}\n".format(mysql_version))
