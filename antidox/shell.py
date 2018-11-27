"""
    antidox.shell
    ~~~~~~~~~~~~~

    Simple debug shell. This application lets you query the database that
    is generated from Doxygen XML docs.
"""


import cmd
import argparse
import functools
import pickle
import sqlite3
import timeit
import re

from lxml import etree as ET

from . import doxy
from .xtransform import get_stylesheet

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"

def _catch(f):
    """Wrap a function so that it catches DB errors"""
    @functools.wraps(f)
    def _f(self, line):
        try:
            return f(self, line)
        except doxy.RefError as e:
            print(e.args[0])

    return _f

def _any_to_refid(f):
    """Transform a method that takes a refid into one that takes a
    character "r" or "t" and either a refid or a target."""
    @functools.wraps(f)
    def _f(self, line):
        try:
            type, refid_or_target = line.split()
        except ValueError:
            print("Error: expected two arguments.")
            return

        if type not in ("r", "t"):
            print("Usage:")
            print(f.__doc__)
            return

        refid = refid_or_target if type == 'r' else self.db.resolve_target(refid_or_target)

        return f(self, refid)

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
        self.db = doxydb

        super().__init__(**kwargs)

        self.do_sty("")

    def precmd(self, line):
        if line and self.db is None and line.strip().split()[0] not in self.NOINIT_CMDS:
            print("No database loaded")
            return ""
        else:
            return line

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

    def do_new(self, xml_dir):
        """\
        new <doxy xml dir>
        Read an XML directory and create a database. Old DB is discarded."""
        try:
            _f = lambda : doxy.DoxyDB(xml_dir)
            print("DB loaded in %f seconds"%timeit.timeit("self.db=_f()", number=1, globals=locals()))
        except Exception as e:
            print("error: ", "".join(e.args))

    def do_dump(self, filename):
        """\
        dump <filename>
        Dump DB as pickle"""
        try:
            with open(filename, "wb+") as f:
                pickle.dump(self.db, f)
        except Exception as e:
            print("error: ", "".join(e.args))
        else:
            print("Done")

    def do_restore(self, filename):
        """\
        restore <filename>
        Restore pickled DB"""
        try:
            with open(filename, "rb") as f:
                self.db = pickle.load(f)
        except Exception as e:
            print("error: ", "".join(e.args))

    def do_load_sphinx(self, sphinx_builddir):
        """\
        load_sphinx <sphinx_project/_build>
        Load the DB from a pickled Sphinx environment"""
        pass

    @_catch
    def do_r(self, target):
        """\
        r <target>
        Get the refid of a target.
        """
        print(self.db.resolve_target(target))

    @_catch
    def do_t(self, refid):
        """\
        r <target>
        Get a target name for a refid.
        """
        print(self.db.refid_to_target(refid))

    @_catch
    def do_n(self, kind_name):
        """\
        n [<kind>] <name>
        Get a refid with a name and of a kind (optional).
        """
        try:
            kind_s, name = kind_name.split()
        except ValueError:
            kind = None
            name = kind_name
        else:
            kind = doxy.Kind.from_attr(kind_s)

        print(self.db.resolve_name(kind, name))

    def _print_refids(self, rs):
        """Pretty print a list of refids"""
        for r in rs:
            n, k = self.db.get(r)
            print("{}\t{}\t{}".format(r, k, n))

    @_catch
    @_any_to_refid
    def do_get(self, refid):
        """\
        get r <refid>
        get t target

        Show information for an entity, given as refid or target.
        """
        self._print_refids((refid,))

    @_catch
    @_any_to_refid
    def do_parents(self, refid):
        """\
        parents r <refid>
        parents t <target>

        Get all compounds that include this element.
        """
        self._print_refids(self.db.find_parents(refid))

    @_catch
    @_any_to_refid
    def do_children(self, refid):
        """\
        children r <refid>
        children t <target>

        Get all elements that are direct descendants of the given one.
        """
        members, compounds = self.db.find_children(refid)
        print("#members")
        self._print_refids(members)
        print("#compounds")
        self._print_refids(compounds)

    @_catch
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

    @_catch
    def do_sty(self, filename):
        """\
        sty [template.xsl]

        Load a XML template file. Call with no argument to restore the default.
        """

        self.stylesheet = get_stylesheet(filename)

    @_catch
    @_any_to_refid
    def do_xform(self, refid):
        """\
        xform r refid
        xform t target

        Fetch an element and apply the stylesheet to it.

        Note: this command does some whitespace modifications so that the resulting
        XML can be pretty-printed.
        """
        root = self.db.get_tree(refid)

        transformed = self.stylesheet(root)
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
        epilog = """Use the -e option to start the application with a database already open:
    shell.py -e "new path/to/xml" OR shell.py -e "restore saved_db.pickle"
    """)

    parser.add_argument('-e', action="append",
                        help="Run command as if it was given in the terminal. Can be specified multiple times.")

    ns = parser.parse_args()

    app = Shell()

    for cmdline in ns.e or ():
        if app.onecmd(cmdline):
            break
    else:
        app.cmdloop()

if __name__ == "__main__":
    main()

