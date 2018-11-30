"""
    antidox.directives
    ~~~~~~~~~~~~~~~~~~

    C domain directives for documenting Doxygen elements. These directives try
    to take advantage of the work done by Doxygen to avoid having to parse C
    source.

"""

import re

from lxml import etree as ET
from docutils import nodes
from docutils.parsers.rst import Directive, directives, DirectiveError
from sphinx.locale import _ as _locale
from sphinx.domains import Domain
from sphinx import addnodes
import sphinx.errors

from . import doxy
from .xtransform import get_stylesheet

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


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
    """Placeholder elements must be replaced before exiting when traversing the
    element tree.

    They must implement a method `e.replace_placeholder(state)` or a
    `run_directive`
    """
    def replace_placeholder(self, *args):
        """Run the directive and replace this node by the directive's output."""
        new = self.run_directive(*args)

        self.replace_self(new)


class Index(PlaceHolder, nodes.Inline, nodes.TextElement):
    """Add a cross-referenceable index entry to the parent of this element.
    """

    TAG_NAME = "{antidox}index"
    tagname = "antidox_index"
    # ~ ``(entrytype, entryname,
    # ~ target, ignored, key)``.

    def guess_objtype(self):
        """Try to find an objtype tag in an ancestor of this node."""

        ancestor = self.parent

        while True:
            if ancestor is None:
                raise ValueError("objtype not found")

            try:
                return ancestor['objtype']
            except KeyError:
                pass

            ancestor = ancestor.parent
        else:
            raise ValueError("objtype not found")

    def run_directive(self, *args, **kwargs):
        return [addnodes.index(entries=[("single", name, id_, '', None)])
                for id_, name in zip(self.parent['ids'], self.parent['names'])]

    def replace_placeholder(self, lineno, state, state_machine):
        state.document.note_explicit_target(self.parent)

        env = state.document.settings.env

        for domain, _, sref in (s.partition(".") for s in self.parent['ids']):
            inv = env.domaindata[domain]['objects']
            if sref in inv:
                state_machine.reporter.warning(
                    'duplicate %s object description of %s, ' % (domain, sref) +
                    'other instance in ' + env.doc2path(inv[sref][0]),
                    line=lineno)  # FIXME
            inv[sref] = (env.docname, self.guess_objtype())

        return super().replace_placeholder(lineno, state, state_machine)


class Interpreted(PlaceHolder, nodes.Element):
    TAG_NAME = "{antidox}interpreted"
    tagname = "interpreted"

    def run_directive(self, lineno, state, state_machine):
        text = self[0].astext()

        # If we did not parse anything before, language is not set and there is
        # an exception. I don't know if this is the proper way to fix it, but
        # I know no better. See the definition of Inliner.interpreted in
        # docutils to learn more.
        if not hasattr(state.inliner, "language"):
            state.inliner.parse("", lineno, state_machine.memo, None)

        nodes, messages = state.inliner.interpreted('', text,
                                                    self['role'], lineno)

        # fixme: do somethin with messages
        return nodes


class DirectiveArg(PseudoElement, nodes.Text):
    TAG_NAME = "{antidox}directive-argument"
    tagname = "argument"


class DirectiveContent(PseudoElement, nodes.Text):
    TAG_NAME = "{antidox}directive-content"
    tagname = "content"


class DirectivePlaceholder(PlaceHolder, nodes.Element):
    """A directive is specified using <antidox:directive>,
    <antidox:directive-argument>, <antidox:directive-content> tags.

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

        # what about this?
        # content_offset = 0
        # block_text = ''

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


# Generic attributes that are handled by _etree_to_sphinx and should be removed
# before creating a node.
_GLOBAL_ATTRIBUTES = {"{antidox}l", "{antidox}definition"}


def _get_node(tag):
    if tag in PseudoElementMeta.tag_map:
        return PseudoElementMeta.tag_map[tag]

    try:
        return getattr(addnodes, tag)
    except AttributeError:
        return getattr(nodes, tag)


_ENTITY_RE = re.compile(r"(?:(?P<kind>\w+)?\[(?P<name>\w+)\])|(?P<target>[^[]\S*)")


class InvalidEntity(sphinx.errors.SphinxError):
    pass


class DoxyExtractor(Directive):
    """
    Auto-document any doxygen entity:

    - C language elements are specified as a target string (as in
      antidox.doxy.Target.
    - Arbitrary doxygen entities can be specified as kind[name], where kind is
      optional (as long as there is no ambiguity.

    Options
    -------

    hidedef: hide macro definition.
    hideloc: hide the location of the definition.
    hidedoc: hide doxygen's documentation.
    """

    # TODO: do something with content
    has_content = True
    required_arguments = 1
    optional_arguments = 0

    option_spec = {
        'noindex': directives.flag,  # TODO: support noindex
        'hidedef': directives.flag,
        'hideloc': directives.flag,  # TODO: support hideloc
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
        # FIXME: what is this supposed to do?

        return  # do nothing by default

    @property
    def env(self):
        return self.state.document.settings.env

    @property
    def db(self):
        """Get the DoxyDB object."""
        return self.env.antidox_db

    def _etree_to_sphinx(self, e, nocontent=False, nodef=False):
        """Convert an element tree to sphinx nodes.

        A text node with a antidox:l attribute will be translated using sphinx
        locale features.

        If nocontent is True, then desc_content nodes will be skipped.
        """
        print(self.env)
        curr_element = []

        et_iter = ET.iterwalk(e, events=("start", "end"))
        skipped = False

        for action, elem in et_iter:
            # print(action, elem, elem.text)
            if action == "start":
                if nocontent and elem.tag == 'desc_content':
                    et_iter.skip_subtree()
                    skipped = True
                    continue

                if nodef and elem.attrib.get("{antidox}definition") == 'true':
                    et_iter.skip_subtree()
                    skipped = True
                    continue

                nclass = _get_node(elem.tag)

                text = elem.text or (_locale(elem.text)
                                     if elem.attrib.get("{antidox}l", False)
                                     else elem.text)

                arg = text if issubclass(nclass, nodes.Text) else ''

                # automatically handle list attributes
                filtered_attrs = {k: (v.split("|") if k in getattr(nclass, "list_attributes", ()) else v)
                                  for (k, v) in elem.attrib.items()
                                  if k not in _GLOBAL_ATTRIBUTES}

                node = nclass(arg, **filtered_attrs)
                if not isinstance(node, nodes.Text) and elem.text:
                    node += nodes.Text(elem.text, elem.text)

                curr_element.append(node)
                curr_element = node
            else:
                if skipped:
                    skipped = False
                    continue

                if isinstance(curr_element, PlaceHolder):
                    curr_element.replace_placeholder(self.lineno, self.state,
                                                     self.state_machine)

                if curr_element.parent is not None:
                    curr_element = curr_element.parent

                if elem.tail:
                    curr_element.append(nodes.Text(elem.tail, elem.tail))

        return curr_element

    def run_reference(self, ref):
        """Convert the doxygen XML of a reference into Sphinx nodes.

        Parameters
        ----------
        ref: a antidox.Doxy.RefId (or string)

        Returns
        -------
        nodes: List of sphinx nodes.
        """
        # TODO: support noindex

        element_tree = self.db.get_tree(ref)

        my_domain = self.env.domains['doxy']
        rst_etree = my_domain.stylesheet(element_tree)
        node = self._etree_to_sphinx(rst_etree,
                                     nocontent='hidedoc' in self.options,
                                     nodef='hidedef' in self.options)

        style_fn = my_domain.stylesheet_filename
        if style_fn:
            self.env.note_dependency(style_fn)

        return [node]

    def run(self):
        target_spec = _ENTITY_RE.fullmatch(self.arguments[0])

        if target_spec is None:
            raise InvalidEntity("Cannot parse entity: %s" % self.arguments[0])

        target = target_spec['target']

        if target:
            ref = self.db.resolve_target(target)
        else:
            kind_s = target_spec['kind']
            ref = self.db.resolve_name(kind_s and doxy.Kind.from_attr(kind_s),
                                       target_spec['name'])

        return self.run_reference(ref)


def target_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    """Create a cross reference for a doxygen object, given a human-readable
    target."""

    db = inliner.document.settings.env.antidox_db
    try:
        ref = db.resolve_target(text)
    except (doxy.AmbiguousTarget, doxy.InvalidTarget) as e:
        msg = inliner.reporter.error(e.args[0], line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    node = addnodes.pending_xref(rawsource=rawtext, reftarget=str(ref),
                                 refdomain='c', reftype='any')
    # FIXME: use a prettier formatting
    node += nodes.Text(text, text)

    return [node], []


class DoxyDomain(Domain):
    """Domain for Doxygen-related directives and roles.

    The cross reference data is stored in the C domain. The only reason this
    domain exists is to serve as a container for template and other data that
    should be shared but not be saved with the environment.

    Attributes
    ----------

    DoxyDomain.stylesheet_filename: File name of the XSL stylesheet. If None
        or empty, it means the embedded stylesheet that comes with this extension
        is being used.
    DoxyDomain.stylesheet: An lxml.etree.XSLT object to be used as a stylesheet
        for converting doxygen xml into reST nodes.
    """
    name = 'doxy'
    label = "Doxygen-documented entities"

    directives = {'c': DoxyExtractor}
    roles = {'r': target_role}

    def __init__(self, env):
        super().__init__(env)

        self.stylesheet_filename = env.app.config.antidox_xml_stylesheet

        self.stylesheet = get_stylesheet(self.stylesheet_filename)
