"""
    antidox.nodes
    ~~~~~~~~~~~~~

    Special reST nodes used by the XML engine. These nodes never make it to the
    final output. They are replaced by the doxy:c directive.
"""

import abc

from docutils import nodes as _nodes
from docutils.parsers.rst import directives, DirectiveError
from sphinx import addnodes

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


class PseudoElementMeta(abc.ABCMeta):
    """Metaclass for all elements which appear in the output of the XSLT filter
    but are not actual reST elements.

    PseudoElementMeta.tag_map keeps a registry of tag name -> class.
    """
    tag_map = {}

    def __new__(mcls, name, bases, namespace, **kwargs):
        _name = namespace.pop("_name", None)
        if _name:
            namespace.setdefault("tagname",  "antidox_{}".format(_name))
            namespace.setdefault("TAG_NAME", "{{antidox}}{}".format(_name))

        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        if (not isinstance(cls.TAG_NAME, property)
            or not cls.TAG_NAME.__isabstractmethod__):
            mcls.tag_map[cls.TAG_NAME] = cls

        return cls


class PseudoElement(metaclass=PseudoElementMeta):
    """Base class for elements that get replaced by the "c" directive.

    The metaclass ensures that if ``_name`` is set (to the tag name without
    namespace) TAG_NAME and tagname will be set automatically.
    """
    @property
    @abc.abstractmethod
    def TAG_NAME(self):
        """Tag name for the XML transformer. Should be of the form
        {antidox}name to be correctly namespaced (it will result in a tag
        named <antidox:name>."""

    @property
    @abc.abstractmethod
    def tagname(self):
        """Tag name for docutils."""


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


class FakeRoot(PlaceHolder, _nodes.Element):
    """Sometimes it is desired to emit several nodes (a list) from a template.
    This implementation transforms each doxygen entity as a root node, and
    because well formed XML can only have one root node, this would be
    impossible.

    """
    _name = "fakeroot"

    def replace_placeholder(self, *args):
        """Replace this element by it's children."""
        self.replace_self(self.children)


class DeferredPlaceholder(PseudoElement, _nodes.Element):
    """Base class for placeholders that are replaced by content that depends on
    the directive contents and options."""


class Children(DeferredPlaceholder):
    """This element gets replaced by the documentation of the current entity's
    children."""
    _name = "children"


class UserContent(DeferredPlaceholder):
    """Placeholder for the content given in the directive's body."""
    _name = "usercontent"


class Index(PlaceHolder, _nodes.Inline, _nodes.TextElement):
    """Add a cross-referenceable index entry to the parent of this element.
    """
    _name = "index"
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
        key = self.get("key", None)
        return [addnodes.index(entries=[("single", name, id_, '', key)])
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
    _name = "interpreted"

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
    _name = "directive-argument"


class DirectiveContent(PseudoElement, _nodes.Text):
    _name = "directive-content"


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
    _name = "directive"

    def run_directive(self, lineno, state, state_machine):
        """Execute the directive generate a list of nodes."""

        name = self["{antidox}name"]

        directive_class, messages = directives.directive(
                                    name, state.memo.language, state.document)

        raw_options = self.attlist()
        options = {k: directive_class.option_spec[k](v) for k, v in raw_options
                   if not k.startswith("{antidox}")}

        arguments = [n.astext() for n in self.children
                     if n.tagname == "antidox_directive-argument"]
        content = [n.astext() for n in self.children
                   if n.tagname == "antidox_directive-content"]

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
