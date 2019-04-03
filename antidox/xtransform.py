"""
    antidox.xtransform
    ~~~~~~~~~~~~~~~~~~

    XSLT handling code. This code is placed here so that is can be used without
    importing the sphinx/rest stuff.
"""

import os
import collections
import re
import functools
from pkgutil import get_data

from lxml import etree as ET

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


# Load basic text functions


def _to_text(nodes_or_text):
    """Convert a xpath object (a string or a list of nodes) to string"""
    element0 = (nodes_or_text[0] if isinstance(nodes_or_text, list)
                else nodes_or_text)
    return (element0 if isinstance(element0, str)
            else element0.xpath("string(.)"))


def _textfunc(f):
    """Decorator to convert the arguments of an XPath extension function to
    string."""
    @functools.wraps(f)
    def _f(ctx, nodes_or_text):
        return f(_to_text(nodes_or_text))

    return _f


_basic_ns = ET.FunctionNamespace("antidox")


@_basic_ns("upper-case")
@_textfunc
def _upper_case(text):
    return text.upper()


@_basic_ns("lower-case")
@_textfunc
def _lower_case(text):
    return text.lower()


@_basic_ns("string-to-ids")
@_textfunc
def _string_to_ids(text):
    """Convert a string into something that is safe to use as a docutils ids
    field."""
    return _NORMALIZE_SPACE.sub(
        "-", text.strip()).translate(_XLATE_TABLE)


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


def _textmeth(f):
    """Decorator to convert the arguments of an XPath extension method to
    string."""
    @functools.wraps(f)
    def _f(self, ctx, nodes_or_text):
        return f(self, ctx, _to_text(nodes_or_text))

    return _f


class _XPathExtensions:
    def __init__(self, locale_fn=None, doxy_db=None):
        self._locale_fn = locale_fn or (lambda x: x)
        self._doxy_db = doxy_db

    @_textmeth
    def l(self, _, text):
        """Stub locale function. This is here so we can run the XSL transform
        without having to import sphinx."""
        return self._locale_fn(text)

    @_textmeth
    def guess_desctype(self, _, text):
        return "" if not self._doxy_db else self._doxy_db.guess_desctype(text)

    @_textmeth
    def refid_to_target(self, _, text):
        return "" if not self._doxy_db else str(self._doxy_db.refid_to_target(text))


def get_stylesheet(stylesheet_filename=None, locale_fn=None, doxy_db=None):
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

    custom_extension = _XPathExtensions(locale_fn, doxy_db)

    ext = ET.Extension(custom_extension, ns="antidox")

    if stylesheet_filename:
        parser = ET.XMLParser()
        parser.resolvers.add(Resolver())
        xml_doc = ET.parse(stylesheet_filename, parser)
    else:
        xml_doc = ET.XML(_get_compound_xsl_text())

    return ET.XSLT(xml_doc, extensions=ext)
