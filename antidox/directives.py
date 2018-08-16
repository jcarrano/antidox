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
from docutils.parsers.rst import Directive, directives, DirectiveError
from sphinx.locale import _
from sphinx.domains import Domain
from sphinx import addnodes

from . import doxy
from .__init__ import get_db


function_xslt = ET.XSLT(ET.XML(get_data(__package__,
                                        os.path.join("templates", "function.xsl"))))

class PseudoElementMeta(type):
    """Metaclass for all elements which appear in the output of the XSLT filter
    but are not actual reST elements.

    PseudoElementMeta.tag_map keeps a registry of tag name -> class.
    """
    tag_map = {}

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cls.tag_map[cls.TAG_NAME] = cls


class PseudoElement(metaclass=PseudoElementMeta):
    TAG_NAME = None

class PlaceHolder(PseudoElement):
    """Placeholder elements must be replace before exiting when traversing the
    element tree.

    They must implement a method `e.replace_placeholder(state)`
    """
    pass


class DirectiveArg(PseudoElement, nodes.Text):
    TAG_NAME = "{antidox}directive-argument"
    tagname = "argument"


class DirectiveContent(PseudoElement, nodes.Text):
    TAG_NAME = "{antidox}directive-content"
    tagname = "content"


class DirectivePlaceholder(PlaceHolder, nodes.Element):
    """A directive is specified using <antidox:directive>, <antidox:directive-argument>
    <antidox:directive-content> tags.

    Each <antidox:directive> can contain zero or more <antidox:argument> and
    an optional content.

    <antidox:directive> Attributes:

    - antidox:name    Name of the directive
    - other tags: Intgerpreted as directive options.

    <antidox:directive-argument> Arguments to the directive.
    <antidox:directive-content> Text contents of the directive.
    """
    TAG_NAME = "{antidox}directive"
    tagname = "directive_pholder"

    def run_directive(self, lineno, state, state_machine):
        """Execute the directive generate a list of nodes."""

        name = self["{antidox}name"]

        directive_class, messages = directives.directive(
                                    name, state.memo.language, state.document)

        raw_options = self.attlist()
        options = {k: directive_class.option_spec[k](v) for k, v in raw_options
                      if not k.startswith("{antidox}")}

        arguments = [n.astext() for n in self.children if n.tagname == "argument"]
        content = [n.astext() for n in self.children if n.tagname == "content"]

        content_offset = 0
        block_text = ''

        directive_instance = directive_class(
                            name, arguments, options, content, lineno,
                            0, "", state, state_machine)

        try:
            result = directive_instance.run()
            result += messages
        except DirectiveError as error:
            msg_node = state.reporter.system_message(error.level, error.msg,
                                                     line=lineno)
            result = [msg_node]

        return result

    def replace_placeholder(self, *args):
        """Run the directive and replace this node by the directive's output."""
        new = self.run_directive(*args)

        self.replace_self(new)


def _get_node(tag):
    if tag in PseudoElementMeta.tag_map:
        return PseudoElementMeta.tag_map[tag]

    try:
        return getattr(addnodes, tag)
    except AttributeError:
        return getattr(nodes, tag)

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


    def _etree_to_sphinx(self, e):
        """Convert an element tree to sphinx nodes.

        A text node with a antidox:l attribute will be translated using sphinx
        locale features.
        """

        curr_element = []

        #print(str(e))

        for action, elem in ET.iterwalk(e, events=("start", "end")):
            print(action, elem, elem.text)
            if action == "start":
                nclass = _get_node(elem.tag)

                text = elem.text or (_(elem.text) if elem.attrib.get("{antidox}l", False)
                                     else elem.text)

                arg = text if issubclass(nclass, nodes.Text) else ''

                # automatically handle list attributes
                filtered_attrs = {k: (v.split("|") if k in getattr(nclass, "list_attributes", ()) else v)
                                  for (k, v) in elem.attrib.items()}

                filtered_attrs.pop("{antidox}l", False)

                node = nclass(arg, **filtered_attrs)
                if not isinstance(node, nodes.Text) and elem.text:
                    node += nodes.Text(elem.text, elem.text)

                curr_element.append(node)
                curr_element = node
            else:
                if isinstance(curr_element, PlaceHolder):
                    curr_element.replace_placeholder(self.lineno, self.state, self.state_machine)

                if curr_element.parent is not None:
                    curr_element = curr_element.parent

                if elem.tail:
                    curr_element.append(nodes.Text(elem.tail, elem.tail))

        return curr_element


    def run(self):
        target = self.arguments[0]
        db = get_db(self.env)
        ref = db.resolve_target(target)
        sref = str(ref)
        #n = db.get(ref)[0]
        # TODO: support noindex

        element_tree = db.get_tree(ref)

        et2 = function_xslt(element_tree)
        node = self._etree_to_sphinx(et2)

        signode = node[node.first_child_matching_class(addnodes.desc_signature)]
        signode['first'] = False
        print(signode["ids"])
        self.state.document.note_explicit_target(signode)
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

