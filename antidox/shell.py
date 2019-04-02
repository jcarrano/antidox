"""
    antidox.shell
    ~~~~~~~~~~~~~

    Simple debug shell. This application lets you query the database that
    is generated from Doxygen XML docs.

    Access it by typing::

      python -m antidox.shell

    or by using the ``antidox-shell`` console script.
"""


import cmd
import argparse
import functools
import pickle
import sqlite3
import timeit
import re
import pathlib

from lxml import etree as ET

from . import doxy
from .xtransform import get_stylesheet

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


def _catch(*args):
    """Wrap a function so that it catches errors"""
    exceptions = args or Exception

    def _catch_decorator(f):
        @functools.wraps(f)
        def _f(self, line):
            try:
                return f(self, line)
            except exceptions as e:
                print(" ".join(str(a) for a in e.args))

        return _f

    return _catch_decorator

_catch_doxy = _catch(doxy.RefError, doxy.DoxyFormatError)

def _any_to_refid(f):
    """Transform a method that takes a refid into one that takes a
    character "r" or "t" and either a refid or a target."""
    @functools.wraps(f)
    def _f(self, line):
        try:
            type, refid_or_target, *extra = line.split()
        except ValueError:
            print("Error: expected at least two arguments.")
            return

        if type not in ("r", "t"):
            print("Usage:")
            print(f.__doc__)
            return

        refid = (refid_or_target if type == 'r'
                 else self.db.resolve_target(refid_or_target))

        return f(self, refid, *extra)

    return _f


KIND_RE = re.compile(r'(?<=\s)Kind\.([A-Z]+)')


class Shell(cmd.Cmd):
    """Interact with the database created by that antidox.doxy module."""

    prompt = "antidox> "
    intro = 'This is the antidox debug shell. Type "?" or "help" for help'

    """Command that can be run withour a database loaded"""
    NOINIT_CMDS = ("", "info", "new", "restore", "load_sphinx", "?", "!", "EOF",
                   "help", "sty")

    def __init__(self, doxydb=None, **kwargs):
        self._stylesheet_fn = None
        self.db = doxydb

        super().__init__(**kwargs)

    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, value):
        self._db = value
        self._reload_sty()

    def precmd(self, line):
        if line and self.db is None and line.strip().split()[0] not in self.NOINIT_CMDS:
            print("No database loaded")
            return ""
        else:
            return line

    def emptyline(self):
        # do not repeat the last command.
        pass

    def do_EOF(self, _):
        print()
        return True

    def do_info(self, _):
        """Show information about the current database."""
        if self.db is None:
            print("No DB loaded")
            return

        print("xml dir:", self.db._xml_dir)
        print("DB tables:")
        tables = self.db._db_conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table'")
        for t in tables:
            print("\t", t[0])

        self._print_cursor(self.db._db_conn.execute("""
        SELECT kind AS element_kind, COUNT(*) FROM elements GROUP BY kind
        """))

        self._print_cursor(self.db._db_conn.execute("""
        SELECT COUNT(*) AS total_elements FROM elements
        """))

        self._print_cursor(self.db._db_conn.execute("""
        SELECT COUNT(*) AS number_of_parent_elements FROM
            (SELECT DISTINCT p_prefix, p_id FROM hierarchy)
        """))

    @_catch()
    def do_new(self, xml_dir):
        """\
        new <doxy xmCmd.emptyline()l dir>
        Read an XML directory and create a database. Old DB is discarded."""
        _f = lambda: doxy.DoxyDB(xml_dir)
        print("DB loaded in %f seconds" % timeit.timeit("self.db=_f()", number=1, globals=locals()))

    @_catch()
    def do_dump(self, filename):
        """\
        dump <filename>
        Dump DB as pickle"""
        with open(filename, "wb+") as f:
            pickle.dump(self.db, f)
        print("Done")

    @_catch()
    def do_restore(self, filename):
        """\
        restore <filename>
        Restore pickled DB"""
        with open(filename, "rb") as f:
            self.db = pickle.load(f)

    @_catch()
    def do_load_sphinx(self, sphinx_builddir):
        """\
        load_sphinx <sphinx_project/_build> [project_dir]
        Load the DB from a pickled Sphinx environment.
        Usually the xml directory is stored as a relative path within the DB
        instance. The default here is to take it relative to the env's srcdir
        but that can be overriden y specifying 'project_dir'"""
        builddir, *maybe_prjdir = sphinx_builddir.split()

        import sphinx.environment

        with open(pathlib.Path(
                  sphinx_builddir, "doctrees", "environment.pickle"), 'rb') as f:
            env = sphinx.environment.BuildEnvironment.load(f)

        self.db = env.antidox_db

        base_dir = maybe_prjdir[0] if maybe_prjdir else env.srcdir
        self.db._xml_dir = pathlib.Path(base_dir, self.db._xml_dir)

    @_catch_doxy
    def do_r(self, target_and_scope):
        """\
        r <target> [<scope>]
        Get the refid of a target.
        """
        if not target_and_scope:
            print("You must provide a refid")
            return

        target, *maybe_scope = target_and_scope.split()
        scope = maybe_scope[0] if maybe_scope else None
        print(self.db.resolve_target(target, scope))

    @_catch_doxy
    def do_t(self, refid):
        """\
        t <target>
        Get a target name for a refid.
        """
        if not refid:
            print("You must provide a refid")
            return

        print(self.db.refid_to_target(refid))

    @_catch_doxy
    def do_n(self, kind_name):
        """\
        n [<kind>] <name> ["in" <scope>]
        Get a refid with a name and of a kind (optional).
        """

        args = kind_name.split()

        if len(args) == 1:
            kind_s = None
            scope = None
            name = args[0]
            in_ = "in"
        elif len(args) == 2:
            kind_s, name = args
            scope = None
            in_ = "in"
        elif len(args) == 3:
            kind_s = None
            name, in_, scope = args
        elif len(args) == 4:
            kind_s, name, in_, scope = args
        else:
            print('Too many arguments')
            return

        if in_.lower() != "in":
            print('Invalid syntax (expected "in <scope>")')
            return

        kind = doxy.Kind.from_attr(kind_s) if kind_s else None

        print(self.db.resolve_name(kind, name, scope))

    def _print_results(self, rs):
        """Pretty print a list of SearchResults"""
        for r, n, k in rs:
            print("{}\t{}\t{}".format(r, k, n))

    @_catch_doxy
    @_any_to_refid
    def do_get(self, refid):
        """\
        get r <refid>
        get t target

        Show information for an entity, given as refid or target.
        """
        name, kind = self.db.get(refid)
        print("{}\t{}\t{}".format(refid, kind, name))

    @_catch_doxy
    def do_get_all(self, params):
        """\
        get-all [noparent] <kind>*

        Retrieve all entities of the specified kinds (or all kinds if none is
        given. The "noparent" parameter will filter only those entities with no
        parent.
        """

        args = params.split()
        noparent = bool(args and args[0] == 'noparent')
        kinds_s = args[1:] if noparent else args
        kinds = [doxy.Kind.from_attr(s) for s in kinds_s] or None

        self._print_results(self.db.find(kinds, no_parent=noparent))

    @_catch_doxy
    @_any_to_refid
    def do_parents(self, refid):
        """\
        parents r <refid>
        parents t <target>

        Get all compounds that include this element.
        """
        self._print_results(self.db.find_parents(refid))

    @_catch_doxy
    @_any_to_refid
    def do_children(self, refid):
        """\
        children r <refid>
        children t <target>

        Get all elements that are direct descendants of the given one.
        """
        members, compounds = self.db.find_children(refid)
        print("#members")
        self._print_results(members)
        print("#compounds")
        self._print_results(compounds)

    @_catch_doxy
    @_any_to_refid
    def do_show(self, refid):
        """\
        show r <refid>
        show t <target>

        Show the source for a given element.

        Note: this command does some whitespace modifications so that the resulting
        XML can be pretty-printed.
        """
        root = self.db.get_tree(refid)
        for element in root.iter():
            if element.tail is not None and not element.tail.strip():
                element.tail = None

            if element.text is not None and not element.text.strip():
                element.text = None

        print(ET.tostring(root, pretty_print=True, encoding='unicode'))

    @_catch(doxy.RefError, doxy.DoxyFormatError, ET.XMLSyntaxError)
    def do_sty(self, filename):
        """\
        sty [template.xsl]

        Load a XML template file. Call with no argument to restore the default.
        The database will be reloaded each time the database is loaded.
        """

        self.stylesheet = get_stylesheet(filename, doxy_db=self.db)
        self._stylesheet_fn = filename

    def _reload_sty(self):
        """Reload the stylesheet (after a database load)"""
        self.do_sty(self._stylesheet_fn)

    @_catch_doxy
    @_any_to_refid
    def do_xform(self, refid, *flags):
        """\
        xform r refid <flags>*
        xform t target <flags>*

        Fetch an element and apply the stylesheet to it.

        Note: this command does some whitespace modifications so that the resulting
        XML can be pretty-printed.

        Flags can be any of noindex, hideloc, hidedef, hidedoc.
        """
        root = self.db.get_tree(refid)

        flags = {k: "true()" for k in flags}

        transformed = self.stylesheet(root, **flags)
        for element in transformed.iter():
            if element.tail is not None and not element.tail.strip():
                element.tail = None

        print(ET.tostring(transformed, pretty_print=True, encoding='unicode'))

    def do_shell(self, line):
        """\
        Run an arbitrary SQL query on the database.
        As a shortcut you can use "!".
        As a convenience, any string of the form "Kind.XXXXX" will be replaced
        with the numeric value for that Kind (e.g Kind.GROUP, Kind.UNION).

        e.g.: `! SELECT name, id FROM elements WHERE kind in compound_kinds`
        """
        _line = KIND_RE.sub(lambda m: str(doxy.Kind[m[1]].value), line)

        try:
            self._print_cursor(self.db._db_conn.execute(_line))
        except sqlite3.Error as e:
            print("Exception while executing SQL:")
            print(e)

    @staticmethod
    def _print_cursor(cur):
        """Pretty-print the result of a query."""
        print("#{}".format("\t".join(cn[0] for cn in cur.description)))
        for r in cur:
            print("\t".join(str(x) for x in r))


def main():
    parser = argparse.ArgumentParser(description="antidox database debugger",
                                     epilog="""\
    Use the -e option to start the application with a database already open:
    shell.py -e "new path/to/xml" OR shell.py -e "restore saved_db.pickle"
    """)

    parser.add_argument('-e', action="append",
                        help="Run command as if it was given in the terminal. "
                             "Can be specified multiple times.")

    ns = parser.parse_args()

    app = Shell()

    for cmdline in ns.e or ():
        if app.onecmd(cmdline):
            break
    else:
        app.cmdloop()


if __name__ == "__main__":
    main()
