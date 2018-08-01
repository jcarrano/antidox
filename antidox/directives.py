"""
    antidox.directives
    ~~~~~~~~~~~~~~~~~~

    C domain directives for documenting Doxygen elements. These directives try
    to take advantage of the work done by Doxygen to avoid having to parse C
    source.

"""

from lxml import etree as ET
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.domains import Domain
from sphinx import addnodes

from . import doxy
from .__init__ import get_db

def _parse_refs(xmlnode):
    """Parse a xml node, identify references and write the result as RST nodes.

    The references are done with c domain roles.
    """
    # FIXME: this only handles references, but there is more (ulink, etc)
    #        see <xsd:group name="docTitleCmdGroup"> in compound.xsd
    result = []

    for action, elem in ET.iterwalk(xmlnode, events=("start", "end")):
        if action == "start" and elem.tag != 'ref':
            result.append(nodes.Text(elem.text, elem.text))
        elif action == "end" and elem.tag == 'ref':
            result.append(addnodes.pending_xref(
                    c.text, refdomain='doxy', reftype='refid',
                    reftarget=elem.attrib["refid"]))

            result.append(nodes.Text(elem.tail, elem.tail))


    return result

def _function_signature(tree, node):
    """Parse a doxy element tree into RST nodes representing a function signature."""
    # TODO: parse the references
    node += addnodes.desc_type('','')
    node[-1].extend(_parse_refs(tree.find("type")))

    dname = " "+tree.find("name").text
    node += addnodes.desc_name(dname, dname)

    paramlist = addnodes.desc_parameterlist()
    params = tree.findall("param")

    for p in params:
        param = addnodes.desc_parameter('', '', noemph=True)

        param.extend(_parse_refs(p.find("type")))
        pname = " " + p.find("declname").text
        param += nodes.emphasis(pname, pname)

        paramlist += param

    node += paramlist

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

    def run(self):
        target = self.arguments[0]
        db = get_db(self.state.document.settings.env)
        ref = db.resolve_target(target)

        node = addnodes.desc()
        node['domain'] = 'c'
        node['objtype'] = node['desctype'] = db.guess_desctype(ref)
        node['noindex'] = noindex = ('noindex' in self.options)

        element_tree = db.get_tree(ref)

        _function_signature(element_tree, node)

        return [addnodes.index(entries=[("single", target, str(ref), '', None)]), node]


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

