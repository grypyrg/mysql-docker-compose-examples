# Copyright (c) 2019, Oracle and/or its affiliates. All rights reserved.
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


"""Windows MSI descriptor parser.
Customization utility functions for the C/py product msi descriptor
"""

from distutils.errors import DistutilsInternalError
from xml.dom.minidom import parse, parseString
from distutils import log as logger
import os

# 64bit Conditional check, only includes VCPPREDIST2015 property.
vc_red_64 = (
    '<Product>'
    '<!-- Check Visual c++ Redistributable is Installed -->'
    '<Property Id="VS14REDIST">'
    '  <RegistrySearch Id="FindRedistVS14" Root="HKLM"'
    '   Key="SOFTWARE\\Microsoft\\DevDiv\\vc\\Servicing\\14.0\\RuntimeMinimum"'
    '   Name="Version" Type="raw" />'
    '</Property>'
    '<Condition Message="This application requires Visual Studio 2015'
    ' Redistributable. Please install the Redistributable then run this'
    ' installer again.">'
    '  Installed OR VS14REDIST'
    '</Condition>'
    '</Product>'
)

# 64bit Conditional check, only install if OS is 64bit. Used in MSI-64
only_64bit = (
    '<Product>'
    '<Condition Message="This version of the installer is only suitable to'
    ' run on 64 bit operating systems.">'
    '<![CDATA[Installed OR (VersionNT64 >=600)]]>'
    '</Condition>'
    '</Product>'
)


def append_child_from_unparsed_xml(father_node, unparsed_xml):
    """Append child xml nodes to a node.
    """
    dom_tree = parseString(unparsed_xml)
    if dom_tree.hasChildNodes():
        first_child = dom_tree.childNodes[0]
        if first_child.hasChildNodes():
            child_nodes = first_child.childNodes
            for _ in range(len(child_nodes)):
                childNode = child_nodes.item(0)
                father_node.appendChild(childNode)
            return

    raise DistutilsInternalError("Could not Append append elements to "
                                 "the Windows msi descriptor.")


def get_element(dom_msi, tag_name, name=None, id_=None):
    """Get a xml element defined on Product.
    """
    product = dom_msi.getElementsByTagName("Product")[0]
    elements = product.getElementsByTagName(tag_name)
    for element in elements:
        if name and id_:
            if element.getAttribute('Name') == name and \
               element.getAttribute('Id') == id_:
                return element
        elif id_:
            if element.getAttribute('Id') == id_:
                return element


def _print(log, msg):
    """Log and print messages
    """
    if log:
        log.info(msg)
    else:
        logger.info(msg)


def add_64bit_elements(dom_msi, log, add_vs_redist=True):
    """Helper method for add the properties and conditions elements to the xml
    msi descriptor.
    """
    # Get the Product xml element
    product = dom_msi.getElementsByTagName("Product")[0]
    # Append childrens
    if add_vs_redist:
        _print(log, "Adding vc_red_64 element.")
        append_child_from_unparsed_xml(product, vc_red_64)
    _print(log, "Adding only_64bit element.")
    append_child_from_unparsed_xml(product, only_64bit)


def add_arch_dep_elems(xml_path, result_path, for32=False, log=None,
                       add_vs_redist=True):
    """Adds the architecture dependient properties and conditions.

    xml_path:      The original xml msi descriptor path
    result_path:   Path to save the resulting xml
    log:           Build command log instance
    add_vs_redist: Add the VS redistributable requirement
    """
    dom_msi = parse(xml_path)
    if for32:
        _print(log, "No elements to add for 32bit msi")
    else:
        _print(log, "Adding 64bit elements")
        add_64bit_elements(dom_msi, log, add_vs_redist)

    _print(log, "Saving xml to:{0} working directory:{1}"
           "".format(result_path, os.getcwd()))
    with open(result_path, "w+") as file:
        file.write(dom_msi.toprettyxml())
        file.flush()
        file.close()
