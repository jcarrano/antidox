"""
    antidox.doxy
    ~~~~~~~~~~~~

    Parse Doxygen XML Files.

    .. admonition: note
        Not everything is supported: some kind of compounds and some
        attributes will be ignored.
"""
# TODO: add a better overview

import os
from io import StringIO
import re
import enum
import sqlite3
from collections import namedtuple
import itertools
import pathlib
import functools

from lxml import etree as ET

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"

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
    def compounds(cls):
        """Return a tuple containing all kinds that are compounds.

        While we generally disregard doxygen categories in this module, the
        member/compound definition is relevant because compounds have their
        own files.
        """
        return (cls.CLASS, cls.STRUCT, cls.UNION, cls.EXCEPTION,
                cls.FILE, cls.NAMESPACE, cls.GROUP, cls.PAGE, cls.DIR)

    @classmethod
    def synthetic_compounds(cls):
        """Return a tuple containing all kinds that are compounds and are defined
        by the user and not by the language syntax"""

        return (cls.GROUP, cls.PAGE, cls.DIR)

    # FIXME: add  instance methods (like "is_subordinate")

    @classmethod
    def subordinate(cls):
        """Return a tuple containing those kinds that are not proper members
        (i.e. they are not defined by memberdef) but rather are "children" of
        a member."""
        return (cls.ENUMVALUE,)

    @classmethod
    def tag_supported(cls, attr):
        """Check if we support a xml "kind" attribute"""
        return attr.upper() in cls.__members__

    @classmethod
    def from_attr(cls, attr):
        """Convert a xml "kind" attribute to a Kind object"""
        try:
            return cls[attr.upper()]
        except KeyError as e:
            # TODO: catch this exception and issue a warning
            raise NotImplementedError("kind=%s not supported" % attr) from e


sqlite3.register_converter("Kind", lambda x: Kind(int(x)))


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
            # see https://lxml.de/parsing.html#modifying-the-tree
            elem.clear()
            if elem.getprevious() is not None:
                elem.getparent()[0]


class DoxyFormatError(Exception):
    """Error for wrongly formatted doxygen files"""
    pass


class ConsistencyError(DoxyFormatError):
    """Raised when any of the assumptions made about the structure of the
    Doxygen XML files is violated. For example, if more than one file contains
    an element.
    This exception is meant to replace assertions. It makes it easier to
    understand what went wrong.
    """
    pass


class RefError(Exception):
    """Base class for errors related to refids and targets"""
    pass


class InvalidTarget(RefError):
    """Raised when an invalid target (one that resolved to zero entities) is
    encountered"""
    pass


class AmbiguousTarget(RefError):
    """Raised when a target that matches more than one entity is encountered.
    The second argument to the constructor should be a list of all matches."""
    pass


# Reverse engineered Doxygen refid:
#   "_" is a escape character. A literal "_" is represented by "__". "_1" is
#   the separator we are looking for, and represents ":".
#   refids are a sort of namespaced identifier. (:) separates components.
#   We will split it into an (optional) prefix, and an id, where the id cannot
#   contain ":"
_refid_re = re.compile(r"(?:((?:\w|-)+)_1)?((?:(?:[A-Za-z0-9-]+)|(?:_[^1]))+)")


_RefId = namedtuple("_RefId", "prefix id_")


class RefId(_RefId):
    """Reverse engineered Doxygen refid.

    refids are a sort of namespaced identifier. (:) separates components.
    We will split it into an (optional) prefix, and an id, where the id cannot
    contain ":"

    "_" is a escape character. A literal "_" is represented by "__". "_1" is
    the separator we are looking for, and represents ":".

    This object can be constructed in two ways:

    * From a string.
    * From separate ``prefix`` and ``id_`` components.
    """

    def __new__(cls, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            s = args[0]

            if isinstance(s, cls):
                return s

            match = _refid_re.fullmatch(s)
            if not match:
                raise DoxyFormatError("Cannot parse refid: %s" % s)

            p, h = match.groups()

            return super().__new__(cls, p or "", h)
        else:
            return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        prefix, id_ = self
        return "{}_1{}".format(prefix, id_) if prefix else id_


# String of the form  [[<dir>/]*<file>::][ns::]name
#                     <--- File path -> <---name-->
# Note that we allow everything in the name. The string for a file consists
# of an empty file path and the filename as the name.
_target_re = re.compile(r"(?:((?:[^/]+/)*[^/]+\.[^/:.]+)::)?(.+)")


_Target = namedtuple("_Target", "path name")


# On a test run, the following optimization alone cut execution time of
# sphinx-build from 3'30'' to 2'55'. This makes the total time be dominated
# by the writing step, which does not depend on this extension.
@functools.lru_cache(maxsize=32)
def _parse_xml(filename):
    """Parse a xml file into an ElementTree. This function is cached for
    performance since during normal use the same file is frequently accessed
    many times in a row."""
    with open(filename) as f:
        return ET.parse(f)


class Target(_Target):
    """Tuple uniquely identifying an entity.

    In contrast to a refid, a target string can be reasonably derived by a
    human by reading the source code.
    A target string of the form "some/dir/components/file::entity", with
    "some/dir/components" as long as necessary to make the file unique.
    The entity may be namespaced with "::" like in C++ if it is defined
    inside another entity (e.g. a struct member).

    This class represents the string as a tuple.

    This object can be constructed in two ways:

    * From a string.
    * From separate path and name components. Additionally, the name component
      may be either a string or an iterable yielding name sub-components.

    A file entity is represented as ``<path>::*`` (i.e., the name filed is
    ``*``).
    """
    def __new__(cls, *args):
        # FIXME: this does not match namedtuple's __new__ signature

        if len(args) == 1:
            if isinstance(args[0], cls):
                return args[0]

            match = _target_re.fullmatch(args[0])
            if not match:
                raise ValueError("Malformed target string: %s" % args[0])
            path, name = match.groups()
        else:
            path, name = args
            if not isinstance(name, str):
                name = "::".join(name)

        return super().__new__(cls, path, name)

    def __str__(self):
        return "{}::{}".format(*self) if self.path else self.name

    @property
    def name_components(self):
        return self.name.split('::')


SearchResult = namedtuple("SearchResult", "refid name kind")
"""Container for the result of find_children and find_parents queries."""


def _match_path(p1, p2):
    """Compare two paths from right to left and return True if they could refer
    to the same file.

    As a special case, if the second argument is None, or empty, it is always
    considered a match. This simplifies query logic when the target does not
    have a path component.

    If p2 starts with "./" then the paths must math entirely. This to allow
    addressing in the case where a path is a prefix of another.
    """
    if not p2:
        return True

    part1 = pathlib.Path(p1).parts
    part2 = pathlib.Path(p2).parts

    if p2.startswith(".") and part2 and not part2[0].startswith("."):
        minlen = 0
    else:
        minlen = min(len(part1), len(part2))

    return part1[-minlen:] == part2[-minlen:]


def _barename(n):
    """Strip the namespace part of a name."""
    return n.split('::')[-1]


def _refid_str(f):
    """Decorator to make a function that accepts a refid also accept the string"""

    @functools.wraps(f)
    def _f(self, refid, *args, **kwargs):
        return f(self, RefId(refid), *args, **kwargs)

    return _f


def _target_str(f):
    """Decorator to make a function that accepts a target also accept the string"""

    @functools.wraps(f)
    def _f(self, target, *args, **kwargs):
        return f(self, Target(target), *args, **kwargs)

    return _f


class DoxyDB:
    """Interface to the Doxygen DB

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

    Read-only index: After the initial database creation, no further modification are done by any
    method. This ensures DoxyDB is safe to use for parallel builds (where there
    will be multiple independent processes, each with a copy of the in-memory DB)

    refid: Each element in Doxygen is uniquely defined by a "refid", consisting of a
    string of the form string_part_1id_part.
    """
    # TODO: check if a file can be used (and shared) instead if ":memory:"

    def __init__(self, xml_dir):
        self._xml_dir = xml_dir
        self._db_conn = None

        self._init_db()

        self._read_index(os.path.join(self._xml_dir, "index.xml"))
        self._load_all_inner()
        self._vacuum()

    # Pickle support
    def __getstate__(self):
        """Dump the database as SQL commands so that it can be pickled."""
        db_dump = StringIO()

        # It should be safe to assume that the DB is connected (because it is
        # done in __init__
        db_dump.writelines(self._db_conn.iterdump())

        return {'_xml_dir': self._xml_dir, '_db_dump': db_dump.getvalue()}

    def __setstate__(self, state):
        self._xml_dir = state['_xml_dir']
        self._db_conn = None
        self._create_db_conn()
        self._db_conn.executescript(state['_db_dump'])
        self._vacuum()

    def _vacuum(self):
        old_isolation = self._db_conn.isolation_level
        self._db_conn.isolation_level = None
        try:
            self._db_conn.execute("VACUUM")
        finally:
            self._db_conn.isolation_level = old_isolation

    def _create_db_conn(self):
        """Initialize the DB connection and configure it."""

        if self._db_conn is not None:
            self._db_conn.close()
            self._db_conn = None

        # TODO: investigate the benefits of using an actual file for the DB
        self._db_conn = sqlite3.connect(':memory:',
                                        detect_types=sqlite3.PARSE_DECLTYPES)

        self._db_conn.row_factory = sqlite3.Row
        self._db_conn.create_function("match_path", 2, _match_path)
        self._db_conn.create_function("barename", 1, _barename)

    def _init_db(self):
        """Create a DB in memory and create empty tables."""
        self._create_db_conn()

        # Example:
        # <compound refid="fxos8700__regs_8h" kind="file"><name>fxos8700_regs.h</name>
        #   <member refid="fxos8700__regs_8h_1abd2eb1f9d6401758c261450bf6f78280" kind="define">
        #        <name>FXOS8700_REG_STATUS</name>
        #   </member>
        #  ....
        # An entry is added to the elements table:
        #   prefix=fxos8700__regs_8h, id=abd2eb1f9d6401758c261450bf6f78280,
        #   kind="define", name="FXOS8700_REG_STATUS"
        # And an entry will be added to the hierarchy table
        #   prefix=fxos8700__regs_8h, id=abd2eb1f9d6401758c261450bf6f78280,
        #   p_prefix="", p_id="fxos8700__regs_8h"
        #
        self._db_conn.executescript("""
        PRAGMA foreign_keys = 1;

        CREATE TABLE elements (
            prefix TEXT, id TEXT,
            name TEXT NOT NULL,
            kind Kind NOT NULL,
            PRIMARY KEY (prefix, id) ON CONFLICT IGNORE
            );

        CREATE TABLE hierarchy (
            prefix TEXT NOT NULL, id TEXT NOT NULL,
            p_prefix TEXT NOT NULL, p_id TEXT NOT NULL,
            UNIQUE (prefix, id, p_prefix, p_id) ON CONFLICT REPLACE,
            FOREIGN KEY(prefix, id) REFERENCES elements(prefix, id)
            );

        CREATE TABLE compound_kinds (kind Kind NOT NULL,
                                     UNIQUE(kind)
                                     );
        CREATE TABLE syn_compound_kinds (kind Kind NOT NULL,
                                         UNIQUE(kind)
                                         );
        """)

        _compounds = Kind.compounds()
        self._db_conn.executemany("INSERT INTO compound_kinds VALUES (?)",
                                  ((x,) for x in _compounds))

        _syn_compounds = Kind.synthetic_compounds()
        self._db_conn.executemany("INSERT INTO syn_compound_kinds VALUES (?)",
                                  ((x,) for x in _syn_compounds))

    def _insert_element(self, refid, name, kind, parent_refid=None):
        """Insert an element into the database."""

        try:
            self._db_conn.execute("INSERT INTO elements values "
                                  "(?, ?, ?, ?)",
                                  refid + (name, kind))
        except sqlite3.IntegrityError:
            print(refid, name, kind)  # FIXME: replace by proper logging
            raise

        if parent_refid is not None:
            self._db_conn.execute("INSERT INTO hierarchy values (?, ?, ?, ?)",
                                  refid + parent_refid)

    def _read_index(self, indexfile):
        """Parse index.xml and insert the elements in the database."""
        for event, elem in _ez_iterparse(indexfile, ("end",)):
            if elem.tag == "doxygenindex":
                continue

            # Doxygen puts the name of an element in a child element <name>
            # instead of an attribute. Here we move it so that it is like we
            # want it to be, and of course we skip the <name> element.
            if elem.tag == "name":
                elem.getparent().attrib["name"] = elem.text
                continue

            if elem.tag == "compound":
                p_refid = None
            elif elem.tag == "member":
                p_refid = RefId(elem.getparent().attrib["refid"])
            else:
                raise DoxyFormatError("Unknown tag in index: %s"
                                      % elem.tag)

            this_refid = RefId(elem.attrib["refid"])
            kind = Kind.from_attr(elem.attrib["kind"])

            # Doxygen wrongly places enumvalues as direct children of files
            # instead of the containing enum.
            # Let's skip the parent for now and we set it correctly when
            # reading the inner files.
            if kind == Kind.ENUMVALUE:
                p_refid = None

            try:
                name = elem.attrib["name"]
            except KeyError as e:
                raise DoxyFormatError("Element definition without a name: %s"
                                      % elem.attrib["refid"]) from e

            self._insert_element(this_refid, name, kind, p_refid)


    def _load_all_inner(self):
        """Load the XML file for each compound and assemble the hierarchy."""
        cur = self._db_conn.execute(
                "SELECT prefix, id FROM elements WHERE kind in compound_kinds")

        for refid in cur:
            fn = os.path.join(self._xml_dir, "{}.xml".format(RefId(*refid)))
            self._read_inner(fn)

    def _read_inner(self, compoundfile):
        """Gather all the inner elements for compounds in a file."""

        for event, elem in _ez_iterparse(compoundfile, ("start",)):
            if elem.tag == "doxygen":
                continue

            if elem.tag == "compounddef":
                p_refid = RefId(elem.attrib["id"])
            else:
                # the enumvalue is a workaround to nest enumvalues under enums
                if elem.tag == "enumvalue":
                    parent_elem = elem.getparent()
                    if not parent_elem.tag == "memberdef":
                        raise ConsistencyError(
                            "expected parent of enumvalue to be a memberdef")
                    this_parent = RefId(parent_elem.attrib["id"])
                    id_attr = elem.attrib["id"]
                else:
                    s, inner, innerkind = elem.tag.partition("inner")
                    if s:  # the tag does not start with "inner"
                        continue

                    if not Kind.tag_supported(innerkind):
                        continue

                    this_parent = p_refid
                    id_attr = elem.attrib["refid"]

                this_refid = RefId(id_attr)

                self._db_conn.execute("INSERT INTO hierarchy values (?, ?, ?, ?)",
                                      this_refid + this_parent)

    # TODO: this may need caching???
    @_refid_str
    def find_parents(self, refid):
        """Get the refid of the compounds where the given element is defined.

        Parameters
        ----------

        refid : refid or str
            Doxygen "id" field for the element.

        Returns
        -------

        results: iterable yielding SearchResult
            All direct ancestors of this element.
        """
        cur = self._db_conn.execute(
        """SELECT p_prefix, p_id, name, kind
        FROM hierarchy INNER JOIN elements
            ON hierarchy.p_prefix = elements.prefix AND hierarchy.p_id = elements.id
        WHERE hierarchy.prefix = ?
              AND hierarchy.id = ?
              AND kind in compound_kinds""", refid)

        return (SearchResult(RefId(*ref), name, kind) for *ref, name, kind in cur)

    @_refid_str
    def find_children(self, refid):
        """Find all members and compounds that are a direct descendants of this
        element.

        Returns
        -------

        members: list of SearchResult
            Descendents that cannot contain any children themselves.
        compounds: list of SearchResult
            Descendents that are compounds, and as such may contain children.
        """
        # TODO: add parameter to filter by kind
        cur = self._db_conn.execute(
        """SELECT hierarchy.prefix, hierarchy.id, name, kind,
                  kind IN compound_kinds as is_compound
        FROM hierarchy INNER JOIN elements
            ON hierarchy.prefix = elements.prefix AND hierarchy.id = elements.id
        WHERE hierarchy.p_prefix = ?
              AND hierarchy.p_id = ?
        ORDER BY
              is_compound""",
            refid)

        r = [(), ()]
        for iscompound, g in itertools.groupby(cur, lambda x: x["is_compound"]):
            r[iscompound] = [SearchResult(RefId(prefix, _id), name, kind)
                             for prefix, _id, name, kind, _ in g]

        return r

    def find(self, kinds = None, no_parent = False):
        """Find all elements of the specified kinds.

        Parameters
        ----------

        kinds: list of Kind to filter by. If not give, all kinds are retrieved
            (except those listed in Kind.subordinate())
        no_parent: if True, return only elements without a parent.

        Returns
        -------

        result: iterable yielding SearchResult
        """

        if kinds is not None:
            _kinds = kinds
        else:
            _kinds = list(set(Kind.__members__.values())
                          - set(Kind.subordinate()))

        query = (
        """WITH
            allowed_kinds (kind) AS (
                VALUES {}
            )
            SELECT elements.* FROM elements
            INNER JOIN allowed_kinds as ak
                ON ak.kind == elements.kind
        """).format(",".join(itertools.repeat("(?)", len(_kinds))))

        if no_parent:
            query += """
            LEFT JOIN hierarchy as h
                ON h.prefix == elements.prefix AND h.id == elements.id
            WHERE h.p_prefix IS NULL AND h.p_id IS NULL
            """

        cur = self._db_conn.execute(query, _kinds)

        return (SearchResult(RefId(*ref), name, kind)
                for *ref, name, kind in cur)

    @_refid_str
    def refid_to_target(self, refid):
        """Generate a target tuple uniquely identifying a refid.

        Since targets must be descendents if a file element, this method will
        fail for user-defined constructs like groups.
        """
        # If we omit user-defined constructs like groups, the elements form
        # a tree, where the files are roots.
        # The query below traverses the tree until it reaches a file and returns
        # the nodes.
        cur = self._db_conn.execute(
        """WITH RECURSIVE
            parent (level, prefix, id) AS (
                SELECT 0, prefix, id FROM elements
                    WHERE prefix = ? AND id = ?
                UNION
                SELECT parent.level + 1, elements.prefix, elements.id
                FROM parent
                    INNER JOIN hierarchy
                        ON hierarchy.prefix = parent.prefix AND
                           hierarchy.id = parent.id
                    INNER JOIN elements
                        ON hierarchy.p_prefix = elements.prefix AND
                           hierarchy.p_id = elements.id
                WHERE NOT elements.kind IN syn_compound_kinds
                LIMIT 20
            )
        SELECT name, kind FROM elements INNER JOIN parent
            ON elements.prefix = parent.prefix AND elements.id = parent.id
        GROUP BY level

        """, refid)

        nodes = list(cur)

        if not len(nodes) > 0:
            raise InvalidTarget("No such refid: %s" % str(refid))

        if not nodes[-1]['kind'] == Kind.FILE:
            raise ConsistencyError("Root node is not a file")

        if len(nodes) == 1:
            # Fix for #15. Check if the resulting name is ambiguous.
            path = nodes[0]['name']
            n_matching = self._db_conn.execute(
                """SELECT COUNT(*) FROM elements
                    WHERE kind = ? AND  match_path(name, ?)
                """, (Kind.FILE, path)).fetchone()[0]

            return Target(path if n_matching == 1
                          else ".{}{}".format(os.path.sep, path), '*')
        else:
            return Target(nodes[-1]['name'],
                          (n['name'] for n in reversed(nodes[:-1])))

    @_refid_str
    def get(self, refid):
        """Get the Name, Kind for of an element.

        Returns
        -------

        row object (similar to a named tuple)
            with fields "name", "kind".
        """
        cur = self._db_conn.execute(
            """SELECT name, kind FROM elements WHERE prefix = ? AND id = ?""",
            refid)

        # No need to check for more than one result, prefix and id are primary keys
        try:
            result = list(cur)[0]
        except IndexError as e:
            raise RefError("No such refid: %s" % str(refid)) from e

        return result

    @staticmethod
    def _cur_to_refid(cur, target, scoped = False):
        """Turn a cursor into a Refid. Raise errors if it is empty or has more
        than one element (except if scoped is True, see below.)

        The cursor should contain 3 columns, and be ordered in descending order
        according to the first one:

        in_scope
            true if the target is a direct descendant of a "scope"
            parameter. This is only relevant if scoped = True.
        prefix
            prefix of refid
        id
            id of refid

        Multiple results are tolerated if scoped is True, and there is exactly
        one result with in_scope = True.
        """

        r = list(cur)

        scoped_results = (x for x in r if x["in_scope"])

        if not r:
            raise InvalidTarget("Cannot resolve target: %s" % str(target))
        # FIXME: this is failing for paths that are a prefix of another one.
        if len(r) > 1 and (not scoped or not r[0]["in_scope"]
                           or len(list(scoped_results)) > 1):
            raise AmbiguousTarget("Target (%s) resolves to more than one element"
                                      % str(target), [RefId(*row[1:]) for row in r])

        return RefId(*r[0][1:])

    @_target_str
    def resolve_target(self, target, scope = None):
        """Convert a target string into a refid.

        This method accepts a string of the form
            [[<dir>/]*<file>::][ns::name]

        If scope is given it must be a RefId or refid-compatible string.

        The path and the amount of directory components included is optional as
        long as it resolves univocally.
        If the string is ambiguous (i.e., more than one entity matches, an error
        is raised).
        The scope parameter allows for disambiguation by preferring results that
        are children of a given refid. Even then, if there is more than one
        result that matches both conditions, it is still an error.
        Because of the way Doxygen works with C, if there is a namespace it
        must be specified. This only happens with structs/unions defined inside
        other struct/unions.
        """
        components = tuple(target.name_components)
        ncompo = len(components)

        # Accept matches at level zero if the target refers to a file.
        if ncompo == 1 and target.name == '*':
            accept_level = 0
        else:
            accept_level = ncompo

        path_filter = target.path

        scope_prefix, scope_id = RefId(scope) if scope else ("", "")

        # The call to barename is a kind of hack. It is necessary because
        #      doxygen stores some names with namespaces and some without.
        # The DISTINCT keyword is there because sometimes the search returns
        #      the same entity multiple times. I think it may only be because of
        #      some bug in doxygen (further investigation is needed.)
        cur = self._db_conn.execute(
        """WITH RECURSIVE
            components (level, compo) AS (
                VALUES %s
            ),
            follow (level, prefix, id) AS (
                SELECT 0, prefix, id FROM elements
                    WHERE kind = ? AND match_path(name, ?)
                UNION ALL
                SELECT f.level + 1, h.prefix, h.id
                FROM follow AS f
                    INNER JOIN hierarchy AS h
                        ON h.p_prefix = f.prefix AND h.p_id = f.id
                    INNER JOIN elements AS e
                        ON h.prefix = e.prefix AND h.id = e.id
                    INNER JOIN components AS c
                        ON f.level = c.level
                WHERE barename(e.name) = c.compo
            )
        SELECT MAX(h.p_prefix = ? AND h.p_id = ?) AS in_scope, f.prefix, f.id FROM
            (SELECT DISTINCT prefix, id FROM follow
                 WHERE level = ?
            ) AS f
            LEFT JOIN hierarchy AS h
                ON h.prefix = f.prefix AND h.id = f.id
        GROUP BY f.prefix, f.id
        ORDER BY in_scope DESC
        """ % ",".join("(%s, ?)" % i for i in range(ncompo)),
            components + (Kind.FILE, path_filter, scope_prefix, scope_id,
                          accept_level))

        return self._cur_to_refid(cur, target, scope is not None)

    def resolve_name(self, kind, name, scope = None):
        """Find an element with the specified kind and name. If kind is not given,
        all kinds are searched.

        More than one result will trigger an AmbiguousTarget exception.
        Less than one, and InvalidTarget.

        Ambiguity can be saved by providing a scope similar to `resolve_target`.
        """

        scope_prefix, scope_id = RefId(scope) if scope else ("", "")

        cur = self._db_conn.execute(
        """SELECT MAX(h.p_prefix = :scope_prefix AND h.p_id = :scope_id)
                AS in_scope, e.prefix AS prefix, e.id AS id
        FROM elements as e LEFT JOIN hierarchy as h
          ON h.prefix = e.prefix AND h.id = e.id
        WHERE (:ignore_kind OR e.kind = :kind) AND e.name = :name
        GROUP BY e.prefix, e.id
        ORDER BY in_scope DESC
        """,
        {"scope_prefix": scope_prefix, "scope_id": scope_id,
        "ignore_kind": not bool(kind), "kind": kind, "name": name})

        return self._cur_to_refid(cur, (kind, name), scope is not None)

    def _first_parent(self, refid, kind):
        """Return the first compound containing an entity."""
        if kind in Kind.subordinate():
            cur = self._db_conn.execute(
            """SELECT h1.p_prefix, h1.p_id
            FROM hierarchy as h1 INNER JOIN elements
                ON h1.p_prefix = elements.prefix AND h1.p_id = elements.id
            INNER JOIN hierarchy as h2
                ON h1.prefix = h2.p_prefix AND h1.id = h2.p_id
            WHERE h2.prefix = ?
                AND h2.id = ?
                AND kind in compound_kinds
            """, refid)
            solutions = (RefId(*ref) for ref in cur)
        else:
            solutions = (res.refid for res in self.find_parents(refid))

        # Doxygen defines the same member in more than one place.
        # It is wasteful, though it makes our life easier.
        try:
            return next(solutions)
        except StopIteration as e:
            raise ConsistencyError(
                    "Cannot find compound containing {}".format(refid)) from e

    @_refid_str
    def get_tree(self, refid):
        """Get the xml element tree for an element"""

        refkind = self.get(refid)['kind']
        if refkind in Kind.compounds():
            # compounds are defined in their own file.
            definition_file_base = refid
            xpathq = '//compounddef[@id=$id]'
        else:
            definition_file_base = self._first_parent(refid, refkind)

            # FIXME: this code looks ugly
            xpathq = ('//memberdef[@id=$id]'
                      if not refkind in Kind.subordinate()
                      else '//{}[@id=$id]'.format(refkind.name.lower()))

        # TODO: should we cache this?
        fn = os.path.join(self._xml_dir, "{}.xml".format(definition_file_base))
        compound_doc = _parse_xml(fn)

        return compound_doc.xpath(xpathq, id=str(refid))[0]

    # TODO: these should be supported. How?
    # For these ones, maybe have an indexing directive
    #   doxy.Kind.FILE = 4
    #   doxy.Kind.NAMESPACE = 5
    #   doxy.Kind.GROUP = 6
    #   doxy.Kind.EXAMPLE = 8
    # For these other ones maybe add new C roles
    #   doxy.Kind.PROPERTY = 11
    #   doxy.Kind.VARIABLE = 12
    #   doxy.Kind.ENUM = 14
    #   doxy.Kind.ENUMVALUE = 15
    # These ones we can ignore
    #   doxy.Kind.FRIEND = 17
    #   doxy.Kind.PAGE = 7
    #   doxy.Kind.DIR = 9

    _easy_kinds = {
        Kind.ENUM: 'type',
        Kind.STRUCT: 'type',
        Kind.UNION: 'type',
        Kind.TYPEDEF: 'type',
        Kind.DEFINE: 'macro',
        Kind.FUNCTION: 'function'
        }

    def guess_desctype(self, refid):
        """Try to guess the "real" type (a C domain role) of a doxygen element.

        This is somewhat related to the Kind, but also depends on the element's parent.
        """

        name, kind = self.get(refid)
        if kind in self._easy_kinds:
            return self._easy_kinds[kind]

        if kind == Kind.VARIABLE:
            # Doxygen uses "variable" for structure/class members and for
            # actual variables.
            # TODO: do this with a query
            _struct_like = (Kind.UNION, Kind.STRUCT)
            parent_is_struct = any(res.kind in _struct_like
                                   for res in self.find_parents(refid))

            return "member" if parent_is_struct else "var"

        # FIXME: is this correct?
        raise ValueError("No c desctype for %s" % kind)

    # TODO: hierarchy walker (sort of os.walkdir with compounds as dirs and members
    #       as files???????)
