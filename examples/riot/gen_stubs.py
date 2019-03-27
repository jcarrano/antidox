"""Generate stubs for Doxygen Compounds.

This is not part of the antidox module because there is no one-size-fits-all
solution to generating stubs. Instead, adapt this script to your project's need.
"""

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

import argparse
import pathlib

from antidox import doxy

# Format this template with a doxy.SearchResult
COMPOUND_TEMPLATE = """
.. Documentation for
   {0.kind.name}[{0.name}]
.. doxy:c:: !{0.refid}
   :children:

"""

INDEX_HEAD = """
Index of {}s
===============

.. toctree::
   :maxdepth: 1
   :caption: Contents:

"""

INDEX_ENTRY = """\
   {}
"""


def _rst_at(dir, name):
    return pathlib.Path(dir, str(name)).with_suffix(".rst")


def prepare_dir(out_dir, kind):
    kind_dir = pathlib.Path(out_dir, kind.name.lower())
    kind_dir.mkdir(exist_ok=True)

    return kind_dir


def gen_stubs(doxy_db, kind_dir, kind):
    entities = doxy_db.find((kind,))

    for result in entities:
        members, compounds = doxy_db.find_children(result.refid)
        if not (members or compounds):
            continue

        outfile = _rst_at(kind_dir, result.refid)
        outfile.write_text(COMPOUND_TEMPLATE.format(result))

        yield result


def gen_index(entities, out_dir, kind_dir, kind):
    indexfile = _rst_at(out_dir, "{}-index".format(kind.name.lower()))

    with open(indexfile, 'w+') as f:
        f.write(INDEX_HEAD.format(kind.name.capitalize()))
        for result in entities:
            f.write(INDEX_ENTRY.format(
                pathlib.Path(kind_dir, str(result.refid)).relative_to(out_dir)))


def main():
    parser = argparse.ArgumentParser(
                    description="Example antidox stub generator")

    parser.add_argument('--groups', help="Generate stubs for groups.",
                        dest='kinds', action='append_const',
                        const=doxy.Kind.GROUP)

    parser.add_argument('--files', help="Generate stubs for files.",
                        dest='kinds', action='append_const',
                        const=doxy.Kind.FILE)

    parser.add_argument('xml_dir', help="Doxygen xml dir.",
                        type=pathlib.Path)

    parser.add_argument('out_dir', help="Output dir.",
                        type=pathlib.Path)

    ns = parser.parse_args()

    db = doxy.DoxyDB(ns.xml_dir)

    pathlib.Path(ns.out_dir).mkdir(exist_ok=True)

    for kind in ns.kinds or ():
        stub_dir = prepare_dir(ns.out_dir, kind)
        gen_index(gen_stubs(db, stub_dir, kind), ns.out_dir, stub_dir, kind)

    return 0


if __name__ == '__main__':
    exit(main())
