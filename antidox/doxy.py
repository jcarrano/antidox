"""Parse Doxygen XML Files.

Note that not everything is supported: some kind of compounds and some
attributes will be ignored.
"""

import os
import re
import sqlite3
import enum
from lxml import etree as ET

# TODO: proper logging of warnings

@enum.unique
class Kind(enum.Enum):
    """Combination of Doxygen's "CompoundKind" and "MemberKind".
    Only the kinds that make sense for C and C++ are included.
    """
    CLASS = 0
    STRUCT = 1
    UNION = 2
    EXCEPTION = 3
    FILE = 4
    NAMESPACE = 5
    GROUP = 6
    PAGE = 7
    EXAMPLE = 8
    DIR = 9
    DEFINE = 10
    PROPERTY = 11
    VARIABLE = 12
    TYPEDEF = 13
    ENUM = 14
    ENUMVALUE = 15
    FUNCTION = 16
    FRIEND = 17

    # TODO: factor this out into a superclass
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return str(self.value)

    @classmethod
    def supported(cls, attr):
        return attr.upper() in cls.__members__

    @classmethod
    def from_attr(cls, attr):
        try:
            return cls[attr.upper()]
        except KeyError as e:
            # TODO: catch this exception and issue a warning
            raise NotImplementedError("kind=%s not supported"%attr) from e

def _parent(node):
    """Get the parent of a node or None if it has no parent."""
    return next(node.iterancestors(), None)

def _ez_iterparse(filename, events=()):
    """Wrapper around ElementTree.iterparse() that clears away elements after
    they are used, thus freeing memory.

    Note that when the "end" event is emmited for a parent, it's children will
    have already been cleared.

    To make sure the elements are garbage collected, do not keep any references.
    """

    _events = tuple(set(events + ("end",)))

    for event, elem in ET.iterparse(filename, events=_events):
        if event in events:
            yield event, elem

        if event == "end":
            parent_node = _parent(elem)
            if parent_node is not None:
                parent_node.remove(elem)


class DoxyFormatError(Exception):
    """Error for wrongly formatted doxygen files"""
    pass


# Reverse engineered Doxygen refid:
#   "_" is a escape character. A literal "_" is represented by "__". "_1" is
#   the separator we are looking for, and represents ":".
#   refids are a sort of namespaced identifier. (:) separates components.
#   We will split it into an (optional) prefix, and an id, where the id cannot
#   contain ":"
_refid_re = re.compile(r"(?:(\w+)_1)?((?:(?:[A-Za-z0-9]+)|(?:_[^1]))+)")

def _split_refid(s):
    """Convert a string refid into a tuple of (prefix, id)
    """
    match = _refid_re.fullmatch(s)
    if not match:
        raise DoxyFormatError("Cannot parse refid: %s"%s)

    p, h = match.groups()

    return p or "", h


def _join_refid(prefix, id_):
    # FIXME: do not place _1 if prefix is empty
    return "{}_1{}".format(prefix, id_) if prefix else id_


class DoxyDB:
    """
    Interface to the Doxygen DB
    ===========================

    The Doxygen DB is just a directory filled with xml files. It should contain
    an "index.xml".

    Doxygen contains compounds and members. We will refer to both as "elements".
    The nesting of elements seems quite arbitrary, things like "function" can
    appear nested under both a "file" and a "group". "struct" in the other hand,
    appear as top-level in the index, though in reality they are contained in a
    file and in maybe a group.

    DoxyDB uses a SQLite database to sort this problem. Interestingly, doxygen
    can create a sqlite3 db, but it's not very well documented (ironic, isn't
    it?).

    refid
    -----

    Each element in Doxygen is uniquely defined by a "refid", consisting of a
    string of the form string_part_1id_part.

    """

    _supported_compoundfiles = [Kind.from_attr(k) for k in
                ("class", "struct", "union", "exception", "file", "namespace",
                 "group","page", "dir")]

    def __init__(self, xml_dir):
        self._xml_dir = xml_dir
        # TODO: set check_same_thread to false
        self._db_conn = None

        self._init_db()

        self._read_index(os.path.join(self._xml_dir, "index.xml"))
        self._load_all_inner()

    def _init_db(self):
        """Create a DB in memory and create empty tables."""
        if self._db_conn is not None:
            self._db_conn.close()
            self._db_conn = None

        # TODO: investigate the benefits of using an actual file.
        self._db_conn = sqlite3.connect(':memory:')
        # Example:
        # <compound refid="fxos8700__regs_8h" kind="file"><name>fxos8700_regs.h</name>
        #   <member refid="fxos8700__regs_8h_1abd2eb1f9d6401758c261450bf6f78280" kind="define"><name>FXOS8700_REG_STATUS</name></member>
        #  ....
        # An entry is added to the elements table:
        #   prefix=fxos8700__regs_8h, id=abd2eb1f9d6401758c261450bf6f78280,
        #   kind="define", name="FXOS8700_REG_STATUS", file = TO BE FILLED LATER
        # And an entry will be added to the hierarchy table
        #   prefix=fxos8700__regs_8h, id=abd2eb1f9d6401758c261450bf6f78280,
        #   p_prefix="", p_id="fxos8700__regs_8h"
        #
        self._db_conn.executescript("""
        CREATE TABLE elements (prefix TEXT, id TEXT,
                                   name TEXT NOT NULL,
                                   kind INTEGER NOT NULL,
                                   PRIMARY KEY (prefix, id)
                              );
        CREATE TABLE hierarchy (prefix TEXT NOT NULL, id TEXT NOT NULL,
                                   p_prefix TEXT NOT NULL, p_id TEXT NOT NULL,
                    UNIQUE (prefix, id, p_prefix, p_id) ON CONFLICT REPLACE
                                );
        """)


    def _read_index(self, indexfile):
        """Parse index.xml and insert the elements in the database."""
        for event, elem in _ez_iterparse(indexfile, ("end",)):
            if elem.tag == "doxygenindex":
                continue

            if event == "end":
                if elem.tag == "name":
                    _parent(elem).attrib["name"] = elem.text
                    continue
                elif elem.tag == "compound":
                    p_prefix, p_id = None, None
                elif elem.tag == "member":
                    p_prefix, p_id = _split_refid(_parent(elem).attrib["refid"])
                else:
                    raise DoxyFormatError("Unknown tag in index: %s"
                                          %elem.tag)

                prefix, id_ = _split_refid(elem.attrib["refid"])
                kind = Kind.from_attr(elem.attrib["kind"])
                try:
                    name = elem.attrib["name"]
                except KeyError as e:
                    raise DoxyFormatError("Element definition without a name: %s"
                                          %elem.attrib["refid"])

                self._db_conn.execute("INSERT INTO elements values "
                                     "(?, ?, ?, ?)",
                                     (prefix, id_, name, kind))

                if p_prefix is not None:
                    self._db_conn.execute("INSERT INTO hierarchy values (?, ?, ?, ?)",
                                         (prefix, id_, p_prefix, p_id))


    def _load_all_inner(self):
        """Load the XML file for each compound and assemble the hierarchy."""
        _in = self._supported_compoundfiles
        cur = self._db_conn.execute(
                "SELECT prefix, id FROM elements WHERE kind in (%s)"%",".join(["?"]*len(_in)),
                        _in
                        )

        for prefix, id_ in cur:
            fn = os.path.join(self._xml_dir, "{}.xml".format(_join_refid(prefix, id_)))
            self._read_inner(fn)


    def _read_inner(self, compoundfile):
        """Gather all the inner elements for compounds in a file."""

        p_prefix, p_id = None, None

        for event, elem in _ez_iterparse(compoundfile, ("start",)):
            if elem.tag == "doxygen":
                continue

            if elem.tag == "compounddef":
                p_prefix, p_id = _split_refid(elem.attrib["id"])
            else:
                s, inner, innerkind = elem.tag.partition("inner")
                if s: # the tag does not start with "inner"
                    continue

                if not Kind.supported(innerkind):
                    continue

                prefix, id_ = _split_refid(elem.attrib["refid"])

                self._db_conn.execute("INSERT INTO hierarchy values (?, ?, ?, ?)",
                                         (prefix, id_, p_prefix, p_id))

