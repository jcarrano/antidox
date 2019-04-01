"""
    antidox.xtransform
    ~~~~~~~~~~~~~~~~~~

    XSLT handling code. This code is placed here so that is can be used without
    importing the sphinx/rest stuff.
"""

import os
import collections
import re
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


_az = range(ord('a'), ord('z'))
_09 = range(ord('0'), ord('9'))
_dash = [ord("-"), ord("_")]

_XLATE_TABLE = collections.defaultdict(
    lambda: None,
    list(zip(_az, _az)) + list(zip(_09, _09))
    + [(ord(chr(x).upper()), x) for x in _az]
    + list(zip(_dash, _dash)) + [(ord(" "), ord("-"))])


_NORMALIZE_SPACE = re.compile(" +")


def _to_text(nodes_or_text):
    nodes_or_text = nodes_or_text or ""
    return (nodes_or_text if isinstance(nodes_or_text, str)
            else (nodes_or_text[0].xpath("string(.)")))


class _StaticExtensions:
    def __init__(self, locale_fn=None):
        self._locale_fn = locale_fn or (lambda x: x)

    def l(self, _, nodes_or_text):
        """Stub locale function. This is here so we can run the XSL transform
        without having to import sphinx."""
        return self._locale_fn(_to_text(nodes_or_text))

    def string_to_ids(self, _, nodes_or_text):
        """Convert a string into something that is safe to use as a docutils ids
        field."""
        return _NORMALIZE_SPACE.sub(
                "-", _to_text(nodes_or_text)).strip().translate(_XLATE_TABLE)


def get_stylesheet(stylesheet_filename=None, locale_fn=None):
    """Get a XSLT stylesheet.

    If stylesheet_filename is not specified, the default sheet will be returned.

    If a file is given, it will be loaded with a special loader that exposes
    the default one under the "antidox:compound".

    Parameters
    ----------
    stylesheet_filename: XSL style sheet, or None to load the default value.
    locale_fn: A translation function mapping strings to strings. This will be
               to implement the "antidox:l" XPath function. If not given,
               the identity function will be used.
    """

    statics = _StaticExtensions(locale_fn)

    ext = ET.Extension(statics, ns="antidox")

    if stylesheet_filename:
        parser = ET.XMLParser()
        parser.resolvers.add(Resolver())
        xml_doc = ET.parse(stylesheet_filename, parser)
    else:
        xml_doc = ET.XML(_get_compound_xsl_text())

    return ET.XSLT(xml_doc, extensions=ext)
