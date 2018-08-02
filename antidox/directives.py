"""
    antidox.directives
    ~~~~~~~~~~~~~~~~~~

    C domain directives for documenting Doxygen elements. These directives try
    to take advantage of the work done by Doxygen to avoid having to parse C
    source.

"""

import os
from pkgutil import get_data

from lxml import etree as ET
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.locale import _
from sphinx.domains import Domain
from sphinx import addnodes

from . import doxy
from .__init__ import get_db


function_xslt = ET.XSLT(ET.XML(get_data(__package__,
                                          os.path.join("templates", "function.xsl"))))

def _get_node(tag):
    try:
        return getattr(addnodes, tag)
    except AttributeError:
        return getattr(nodes, tag)

def _etree_to_sphinx(e):
    """Convert an element tree to sphinx nodes."""

    curr_element = []

    print(str(e))

    for action, elem in ET.iterwalk(e, events=("start", "end")):
        print(action, elem, elem.text)
        if action == "start":
            nclass = _get_node(elem.tag)

            text = elem.text or (_(elem.text) if elem.attrib.get("{antidox}l", False)
                                 else elem.text)
            elem.attrib.pop("{antidox}l", False)
            arg = text if isinstance(nclass, nodes.Text) else ''

            node = nclass(arg, **elem.attrib)
            if not isinstance(nclass, nodes.Text) and elem.text:
                node += nodes.Text(elem.text, elem.text)

            curr_element.append(node)
            curr_element = node
        else:
            if curr_element.parent is not None:
                curr_element = curr_element.parent

            if elem.tail:
                curr_element.append(nodes.Text(elem.tail, elem.tail))

    return curr_element


def _macro_signature(tree, node):
    """Parse a doxy element tree into RST nodes representing a macro signature."""
    pass


def _struct_signature(tree, node):
    """Parse a doxy element tree into RST nodes representing a struct/union signature."""
    pass


class CAuto(Directive):
    """Auto-document a C language element.

    Options
    -------

    hidedef: hide macro definition.
    hideloc: hide the location of the definition.
    hidedoc: hide doxygen's documentation.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 0

    option_spec = {
        'noindex': directives.flag,
        'hidedef': directives.flag,
        'hideloc': directives.flag,
        'hidedoc': directives.flag,
    }


    def add_target_and_index(self, name, sig, signode):
        # type: (Any, unicode, addnodes.desc_signature) -> None
        """
        Add cross-reference IDs and entries to self.indexnode, if applicable.

        Parameters
        ----------

        name: refid for the object.
        sig: Signature. It is parsed as a doxy.Target string.
        """
        return  # do nothing by default

    @property
    def env(self):
        return self.state.document.settings.env

    def run(self):
        target = self.arguments[0]
        db = get_db(self.env)
        ref = db.resolve_target(target)
        sref = str(ref)

        node = addnodes.desc()
        node['domain'] = 'c'
        node['objtype'] = node['desctype'] = db.guess_desctype(ref)
        node['noindex'] = noindex = ('noindex' in self.options)
        # TODO: support noindex

        element_tree = db.get_tree(ref)

        et2 = function_xslt(element_tree)
        node = _etree_to_sphinx(et2)
        #_function_signature(element_tree, node)

        self.state.document.note_explicit_target(node)
        inv = self.env.domaindata['c']['objects']
        if sref in inv:
            self.state_machine.reporter.warning(
                'duplicate C object description of %s, ' % sref +
                'other instance in ' + self.env.doc2path(inv[sref][0]),
                line=self.lineno) # FIXME
        inv[sref] = (self.env.docname, node['objtype'])

        return [addnodes.index(entries=[("single", target, sref, '', None)]), node]


class DoxyCDomain(Domain):
    """Domain for objects documented through sphinx.

    The main function of this domain is to deal with references. Objects
    themselves are placed in the "c" domain, but the C domain has no support
    for "refid" references or targets.
    """

    name = 'doxy'
    label = 'Doxy'
    object_types = {
    }

    roles = {
    }
    initial_data = {
        'objects': {},
    }

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):

        if target not in self.data['objects']:
            return None

        obj = self.data['objects'][target]

        doxy_target = get_db(self.state.document.settings.env).refid_to_target(target)

        targetname = str(doxy_target).rstrip('::*')

        return make_refnode(builder, fromdocname, obj[0], doxy_target,
                            contnode, targetname)

