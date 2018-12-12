"""
    antidox.nodes
    ~~~~~~~~~~~~~

    Special reST nodes used by the XML engine. These nodes never make it to the
    final output. They are replaced by the doxy:c directive.
"""

from docutils import nodes as _nodes
from docutils.parsers.rst import directives, DirectiveError
from sphinx import addnodes

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

        if cls.TAG_NAME:
            cls.tag_map[cls.TAG_NAME] = cls


class PseudoElement(metaclass=PseudoElementMeta):
    """Base class for elements that get replaced by the "c" directive."""
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


class DeferredPlaceholder(PseudoElement, _nodes.Element):
    """Base class for placeholders that are replaced by content that depends on
    the directive contents and options."""


class Children(DeferredPlaceholder):
    TAG_NAME = "{antidox}children"
    tagname = "antidox_children"


class Index(PlaceHolder, _nodes.Inline, _nodes.TextElement):
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


class Interpreted(PlaceHolder, _nodes.Element):
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


class DirectiveArg(PseudoElement, _nodes.Text):
    TAG_NAME = "{antidox}directive-argument"
    tagname = "argument"


class DirectiveContent(PseudoElement, _nodes.Text):
    TAG_NAME = "{antidox}directive-content"
    tagname = "content"


class DirectivePlaceholder(PlaceHolder, _nodes.Element):
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


def nodeclass_from_tag(tag):
    """Get the class for a reST node given its tag name.
    This searches in antidox's pseudo-elements, docutils' nodes and sphinx'
    addnodes.
    """
    if tag in PseudoElementMeta.tag_map:
        return PseudoElementMeta.tag_map[tag]

    try:
        return getattr(addnodes, tag)
    except AttributeError:
        return getattr(_nodes, tag)
