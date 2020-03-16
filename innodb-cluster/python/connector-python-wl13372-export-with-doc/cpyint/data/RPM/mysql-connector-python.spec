# Copyright (c) 2015, 2019, Oracle and/or its affiliates. All rights reserved.
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

%if 0%{?rhel} && 0%{?rhel} <= 5 || 0%{?suse_version} <= 1200
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

%if 0%{?suse_version} && 0%{?suse_version} <= 1200
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

%if 0%{?suse_version} == 1315
%global dist            .sles12
%endif

%if 0%{?suse_version} == 1110
%global dist            .sles11
%endif

%if 0%{?suse_version} == 1500
%global dist            .sl15
%endif

%{?fedora: %global with_python3 1}

%{!?__python2: %global __python2 %{__python}}
%{!?python2_sitearch: %global python2_sitearch %{python_sitearch}}

%{?mysql_capi: %global with_mysql_capi %{mysql_capi}}
%{?protobuf_include_dir: %global with_protobuf_include_dir %{protobuf_include_dir}}
%{?protobuf_lib_dir: %global with_protobuf_lib_dir %{protobuf_lib_dir}}
%{?protoc: %global with_protoc %{protoc}}
%{?extra_compile_args: %global extra_compile_args %{extra_compile_args}}
%{?extra_link_args: %global extra_link_args %{extra_link_args}}

%{!?version: %global version 8.0.18}

%if 0%{?commercial}
%global license_type    Commercial
%global product_suffix  -commercial
%global byte_code_only  --byte-code-only=1
%else
%global license_type    GPLv2
%global byte_code_only  --byte-code-only=0
%endif

Summary:       Standardized MySQL database driver for Python
Name:          mysql-connector-python%{?product_suffix}
Version:       %{version}
Release:       1%{?version_extra:.%{version_extra}}%{?commercial:.1}%{?dist}
License:       Copyright (c) 2015, 2019, Oracle and/or its affiliates. All rights reserved. Under %{?license_type} license as shown in the Description field.
Group:         Development/Libraries
URL:           https://dev.mysql.com/downloads/connector/python/            
Source0:       https://cdn.mysql.com/Downloads/Connector-Python/mysql-connector-python-%{?commercial:commercial-}%{version}.tar.gz
#BuildArch:     noarch
%{!?with_mysql_capi:BuildRequires: mysql-devel}
%if 0%{?rhel} >= 8
BuildRequires:  python2-devel
%else
BuildRequires:  python-devel
%endif
%if 0%{?with_python3}
BuildRequires: python3-devel
%endif # if with_python3
%if 0%{?commercial}
Obsoletes:     mysql-connector-python < %{version}-%{release}
Provides:      mysql-connector-python = %{version}-%{release}
%endif
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%description
MySQL Connector/Python enables Python programs to access MySQL
databases, using an API that is compliant with the Python DB API
version 2.0. It is written in pure Python and does not have any
dependencies except for the Python Standard Library.
The MySQL software has Dual Licensing, which means you can use the

MySQL software free of charge under the GNU General Public License
(http://www.gnu.org/licenses/). You can also purchase commercial MySQL
licenses from Oracle and/or its affiliates if you do not wish to be
bound by the terms of the GPL. See the chapter "Licensing and Support"
in the manual for further info.

The MySQL web site (http://www.mysql.com/) provides the latest news
and information about the MySQL software. Also please see the
documentation and the manual for more information.

%package       cext
Summary:       Standardized MySQL driver for Python with C Extension
Group:         Development/Libraries
%if 0%{?commercial}
Requires:      mysql-connector-python-commercial = %{version}-%{release}
Obsoletes:     mysql-connector-python-cext < %{version}-%{release}
Provides:      mysql-connector-python-cext = %{version}-%{release}
%else
Requires:      mysql-connector-python = %{version}-%{release}
%endif

%description   cext
MySQL Connector/Python enables Python programs to access MySQL
databases, using an API that is compliant with the Python DB API
version 2.0. This is a optional C Extension to the pure Python driver,
it's linked with MySQL Connector/C.

The MySQL software has Dual Licensing, which means you can use the
MySQL software free of charge under the GNU General Public License
(http://www.gnu.org/licenses/). You can also purchase commercial MySQL
licenses from Oracle and/or its affiliates if you do not wish to be
bound by the terms of the GPL. See the chapter "Licensing and Support"
in the manual for further info.

The MySQL web site (http://www.mysql.com/) provides the latest news
and information about the MySQL software. Also please see the
documentation and the manual for more information.

%if 0%{?with_python3}
%package    -n mysql-connector-python3%{?product_suffix}
Summary:       Standardized MySQL database driver for Python 3
Group:         Development/Libraries
%if 0%{?commercial}
Obsoletes:     mysql-connector-python3 < %{version}-%{release}
Provides:      mysql-connector-python3 = %{version}-%{release}
%endif

%description -n mysql-connector-python3%{?product_suffix}
MySQL Connector/Python enables Python programs to access MySQL
databases, using an API that is compliant with the Python DB API
version 2.0. It is written in pure Python and does not have any
dependencies except for the Python Standard Library.

This is the Python 3 version of the driver.

The MySQL software has Dual Licensing, which means you can use the
MySQL software free of charge under the GNU General Public License
(http://www.gnu.org/licenses/). You can also purchase commercial MySQL
licenses from Oracle and/or its affiliates if you do not wish to be
bound by the terms of the GPL. See the chapter "Licensing and Support"
in the manual for further info.

The MySQL web site (http://www.mysql.com/) provides the latest news
and information about the MySQL software. Also please see the
documentation and the manual for more information.

%package    -n mysql-connector-python3%{?product_suffix}-cext
Summary:       Standardized MySQL driver for Python with C Extension
Group:         Development/Libraries
%if 0%{?commercial}
Requires:      mysql-connector-python3-commercial = %{version}-%{release}
Obsoletes:     mysql-connector-python3-cext < %{version}-%{release}
Provides:      mysql-connector-python3-cext = %{version}-%{release}
%else
Requires:      mysql-connector-python3 = %{version}-%{release}
%endif

%description -n mysql-connector-python3%{?product_suffix}-cext
MySQL Connector/Python enables Python programs to access MySQL
databases, using an API that is compliant with the Python DB API
version 2.0. This is a optional C Extension to the pure Python driver,
it's linked with MySQL Connector/C.

This is the Python 3 version of the extension.

The MySQL software has Dual Licensing, which means you can use the
MySQL software free of charge under the GNU General Public License
(http://www.gnu.org/licenses/). You can also purchase commercial MySQL
licenses from Oracle and/or its affiliates if you do not wish to be
bound by the terms of the GPL. See the chapter "Licensing and Support"
in the manual for further info.

The MySQL web site (http://www.mysql.com/) provides the latest news
and information about the MySQL software. Also please see the
documentation and the manual for more information.
%endif # if with_python3

%prep
%setup -q
%if 0%{?with_python3}
rm -rf %{py3dir}
cp -a . %{py3dir}
%endif # if with_python3

%install
COMMON_INSTALL_ARGS="\
    install \
    --prefix=%{_prefix} \
    --root=%{buildroot} \
    --with-protobuf-include-dir=%{with_protobuf_include_dir} \
    --with-protobuf-lib-dir=%{with_protobuf_lib_dir} \
    --with-protoc=%{with_protoc} \
    --static \
"

%if 0%{?extra_compile_args:1}
EXTRA_COMPILE_ARGS=%extra_compile_args
%else
EXTRA_COMPILE_ARGS=""
%endif

%if 0%{?extra_link_args:1}
EXTRA_LINK_ARGS=%extra_link_args
%else
EXTRA_LINK_ARGS=""
%endif

rm -rf %{buildroot}
# skip-build is broken
%{__python2} setup.py ${COMMON_INSTALL_ARGS} \
    --extra-compile-args="${EXTRA_COMPILE_ARGS}" \
    --extra-link-args="${EXTRA_LINK_ARGS}" \
    --with-mysql-capi=%{with_mysql_capi} %{byte_code_only}
rm -rf %{buildroot}%{python2_sitearch}/mysql
rm -rf %{buildroot}%{python2_sitearch}/mysqlx
%{__python2} setup.py ${COMMON_INSTALL_ARGS} \
    --extra-compile-args="${EXTRA_COMPILE_ARGS}" \
    --extra-link-args="${EXTRA_LINK_ARGS}" %{byte_code_only}
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py ${COMMON_INSTALL_ARGS} \
    --extra-compile-args="${EXTRA_COMPILE_ARGS}" \
    --extra-link-args="${EXTRA_LINK_ARGS}" \
    --with-mysql-capi=%{with_mysql_capi} %{byte_code_only}
rm -rf %{buildroot}%{python3_sitearch}/mysql
rm -rf %{buildroot}%{python3_sitearch}/mysqlx
%{__python3} setup.py ${COMMON_INSTALL_ARGS} \
    --extra-compile-args="${EXTRA_COMPILE_ARGS}" \
    --extra-link-args="${EXTRA_LINK_ARGS}" %{byte_code_only}
popd
%endif # with_python3

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root, -)
%doc LICENSE.txt CHANGES.txt README.txt README.rst CONTRIBUTING.rst docs/INFO_SRC docs/INFO_BIN
# For old generic python modules
%{python2_sitearch}/mysql
%{python2_sitearch}/mysqlx
%if 0%{?rhel} > 5 || 0%{?fedora} > 12 || 0%{?suse_version} >= 1100
%{python2_sitearch}/mysql_connector_python-*.egg-info
%endif

%files cext
%defattr(-, root, root, -)
%doc LICENSE.txt CHANGES.txt README.txt README.rst CONTRIBUTING.rst docs/INFO_SRC docs/INFO_BIN
%{python2_sitearch}/_mysql_connector.so
%{python2_sitearch}/_mysqlxpb.so
%{python2_sitearch}/mysql_connector_python-*.egg-info

%if 0%{?with_python3}
%files -n mysql-connector-python3%{?product_suffix}
%defattr(-, root, root, -)
%doc LICENSE.txt CHANGES.txt README.txt README.rst CONTRIBUTING.rst docs/INFO_SRC docs/INFO_BIN
%{python3_sitearch}/mysql
%{python3_sitearch}/mysqlx
%{python3_sitearch}/mysql_connector_python-*.egg-info

%files -n mysql-connector-python3%{?product_suffix}-cext
%defattr(-, root, root, -)
%doc LICENSE.txt CHANGES.txt README.txt README.rst CONTRIBUTING.rst docs/INFO_SRC docs/INFO_BIN
%{python3_sitearch}/_mysql_connector.cpython*.so
%{python3_sitearch}/_mysqlxpb.cpython*.so
%{python3_sitearch}/mysql_connector_python-*.egg-info
%endif # with_python3

%changelog
* Fri Aug 23 2019  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.18-1
- Updated for 8.0.18

* Mon May 27 2019  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.17-1
- Updated for 8.0.17

* Tue Feb 5 2019  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.16-1
- Updated for 8.0.16

* Fri Jan 25 2019  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.15-1
- Updated for 8.0.15

* Wed Nov 28 2018  Nawaz Nazeer Ahamed <nawaz.nazeer.ahamed@oracle.com> - 8.0.14-2
- Updated copyright year from 2018 to 2019

* Wed Nov 28 2018  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.14-1
- Updated for 8.0.14

* Fri Sep 14 2018  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.13-1
- Updated for 8.0.13

* Sat Sep 1 2018  Israel Gomez <israel.gomez@oracle.com> - 8.0.12-2
- Updated rpm pakage name of open SUSE from sles15 to sl15

* Fri Jun 8 2018  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.12-1
- Updated for 8.0.12

* Fri Mar 16 2018  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.11-1
- Updated for 8.0.11

* Mon Dec 11 2017  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.6-1
- Updated for 8.0.6

* Mon Aug 21 2017  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.5-1
- Updated for 8.0.5

* Mon May 22 2017  Nuno Mariz <nuno.mariz@oracle.com> - 8.0.4-1
- Updated for 8.0.4

* Tue Mar 7 2017  Nuno Mariz <nuno.mariz@oracle.com> - 2.2.3-1
- Updated for 2.2.3

* Tue Oct 4 2016  Nuno Mariz <nuno.mariz@oracle.com> - 2.2.2-1
- Updated for 2.2.2

* Fri Aug 12 2016  Nuno Mariz <nuno.mariz@oracle.com> - 2.2.1-1
- Updated for 2.2.1

* Tue May 24 2016  Nuno Mariz <nuno.mariz@oracle.com> - 2.2.0-1
- Updated for 2.2.0

* Wed Feb 10 2016  Geert Vanderkelen <geert.vanderkelen@oracle.com> - 2.1.4-1
- Updated for 2.1.4

* Fri Jul 31 2015 Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 2.1.3-1
- New spec file with support for cext, license options and Python 3 support

