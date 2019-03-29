"""
    antidox.xtransform
    ~~~~~~~~~~~~~~~~~~

    XSLT handling code. This code is placed here so that is can be used without
    importing the sphinx/rest stuff.
"""

import os
import collections
from pkgutil import get_data

from lxml import etree as ET

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


def _get_compound_xsl_text():
    return get_data(__package__, os.path.join("templates", "compound.xsl"))


class Resolver(ET.Resolver):
    """Resolve the basic stylesheet as "antidox:compound".

    If this package is installed as a zip, the XML may not even be a file, so
    we hide those details from the user."""

    def resolve(self, url, id, context):
        if url == "antidox:compound":
            return self.resolve_string(_get_compound_xsl_text(), context)

_XLATE_TABLE =

class _StaticExtensions:
    def l(self, _, text):
        """Stub locale function. This is here so we can run the XSL transform
        without having to import sphinx."""
        return text

    def string_to_ids(self, _ text):
        """Convert a string into something that is safe to use as a docutils ids
        field."""


def get_stylesheet(stylesheet_filename=None,
                   doxy_db=None, locale_fn=None):
    """Get a XSLT stylesheet.

    If stylesheet_filename is not specified, the default sheet will be returned.

    If a file is given, it will be loaded with a special loaded that exposes
    the default one under the "antidox:compound".
    """

    if locale_fn:
        class _ThisExt(_StaticExtensions):
            def l(self, _, text):
                return locale_fn(text)
    else:
        _ThisExt = _StaticExtensions

    if stylesheet_filename:
        parser = ET.XMLParser()
        parser.resolvers.add(Resolver())
        xml_doc = ET.parse(stylesheet_filename, parser)
    else:
        xml_doc = ET.XML(_get_compound_xsl_text())

    return ET.XSLT(xml_doc)
