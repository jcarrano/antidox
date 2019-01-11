"""
    antidox.directives
    ~~~~~~~~~~~~~~~~~~

    C domain directives for documenting Doxygen elements. These directives try
    to take advantage of the work done by Doxygen to avoid having to parse C
    source.

"""

import re

from lxml import etree as ET
from docutils.parsers.rst import Directive, directives
from docutils.nodes import Text, Structural, literal
from sphinx.util.nodes import split_explicit_title
from sphinx.locale import _ as _locale
from sphinx.domains import Domain
from sphinx import addnodes
import sphinx.errors

from . import doxy
from .xtransform import get_stylesheet
from .nodes import nodeclass_from_tag, PlaceHolder, DeferredPlaceholder

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


# Generic attributes that are handled by _etree_to_sphinx and should be removed
# before creating a node.
_GLOBAL_ATTRIBUTES = {"{antidox}l", "{antidox}definition"}


class InvalidEntity(sphinx.errors.SphinxError):
    pass


ENTITY_RE = re.compile(r"(?:!(?P<refid>\w+))|(?:(?P<kind>\w+)?\[(?P<name>\w+)\])|(?P<target>[^[]\S*)")
"""Regular expression for references to entities.

Catches either target strings (a/b.h::c), kind[name] strings or refid strings
(prefixed with an exclamation mark "!").

Capture groups:

``refid``:
    If the string starts with "!", then returns the rest of it, unmodified.

``target``
    The target string if the reference is a antidox.doxy.Target-compatible
    target spec, else None.

``kind``
    None if kind was not specified or if the string is a target.

``name``
    The name if the string is kind[name] or [name] (i.e. not a target).
"""

def _get_current_scope(env):
    """Get the refid that is being currently documented. Also, create the scope
    stack it it does not exist."""
    scope_stack = env.ref_context.setdefault('doxy:refid', [])

    try:
        scope = scope_stack[-1]
    except IndexError:
        scope = 0

    return scope


def resolve_refstr(env, ref_str):
    """Transform a reference string (see :py:data:`ENTITY_RE`) into a RefId.
    If ref_str is already a refid, it is still validated.

    Returns
    -------

    ref: RefId for the element
    ref_spec: re.Match object, the result of parsing ref_str.
    """

    ref_spec = ENTITY_RE.fullmatch(ref_str)

    if ref_spec is None:
        raise InvalidEntity("Cannot parse entity: %s" % ref_str)

    scope = _get_current_scope(env)

    db = env.antidox_db

    target = ref_spec['target']
    refid_s = ref_spec['refid']

    if target:
        ref = db.resolve_target(target, scope)
    elif refid_s:
        # just validate that the reference is valid
        ref = doxy.RefId(refid_s)
        db.get(ref)
    else:
        kind_s = ref_spec['kind']
        ref = db.resolve_name(kind_s and doxy.Kind.from_attr(kind_s),
                              ref_spec['name'], scope)

    return ref, ref_spec


class _Universal:
    """Container containing everything."""
    def __contains__(self, k):
        """Returns True always because this container contains everything."""
        return True


_Universe = _Universal()
"""Singleton universal object"""


def _empty_to_universe(s):
    return (s or _Universe) if s is not None else ()


def default_inclusion_policy(app, this, options):
    """Default behavior used when no callback handles the
    ``antidox-include-children`` event.

    If ``no-children`` is empty, it is taken to mean "exclude everything". If
    ``children`` is empty it is taken include everything (with exceptions).

    The exceptions are that children with the same kind as the parent won't be
    included unless explicitly named and if they are included they will have
    ``no-children`` set.
    """
    db = app.env.antidox_db

    no_children = _empty_to_universe(options.get('no-children'))
    yes_children = _empty_to_universe(options.get('children'))

    if yes_children and no_children is not _Universe:
        all_child_members, all_child_compounds = db.find_children(this)

        this_kind = db.get(this)['kind']

        def _member_accept(name, kind):
            return ((kind != this_kind) if yes_children is _Universe
                    else (name in yes_children))

        inclusion_list = [(ref, {}) for ref, name, kind in all_child_members
                          if name in yes_children
                          and name not in no_children]

        inclusion_list.extend(
            (ref, {} if kind != this_kind else {'no-children': ''})
            for ref, name, kind in all_child_compounds
            if _member_accept(name, kind)
            and name not in no_children)

        return inclusion_list


def string_list(argument):
    """Parse a list of strings. If no argument is given, return an empty
    list."""
    return argument.split() if argument is not None else []


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
        'children': string_list,
        'no-children': string_list,
    }

    _node_hidings_opts = {'hidedef', 'hidedoc'}

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
        """Shortcut to get this document's environment."""
        return self.state.document.settings.env

    @property
    def db(self):
        """Get the DoxyDB object."""
        return self.env.antidox_db

    @staticmethod
    def _iterwalk_with_hiding(etree, hidedoc=False, hidedef=False):
        """Iterator around ET.iterwalk that transparently skips desc_content
        and {antidox}definition based on hidedoc and hidedef.

        Returns
        -------

        Iterator yielding event, element just like ET.iterwalk. The events are
        ("start", "end").
        """
        et_iter = ET.iterwalk(etree, events=("start", "end"))
        skipped = False

        for action, elem in et_iter:
            if action == "start":
                if hidedoc and elem.tag == 'desc_content':
                    et_iter.skip_subtree()
                    skipped = True
                elif hidedef and elem.attrib.get("{antidox}definition") == 'true':
                    et_iter.skip_subtree()
                    skipped = True
                else:
                    yield action, elem
            else:
                if skipped:
                    skipped = False
                else:
                    yield action, elem

    def _etree_to_sphinx(self, etree, **kwargs):
        """Convert an element tree to sphinx nodes.

        A text node with a antidox:l attribute will be translated using sphinx
        locale features.

        kwargs will be passed to _iterwalk_with_hiding to determine which nodes
        to skip.

        Return
        ------

        nodes: List of sphinx nodes
        special: dictionary if special placeholder nodes.
            Currently defined elements are:
            antidox_children
                placeholder that should be replaced by this element's children.
        """
        curr_element = []
        root = curr_element

        special = {}

        for action, elem in self._iterwalk_with_hiding(etree, **kwargs):
            if action == "start":
                nclass = nodeclass_from_tag(elem.tag)

                text = elem.text or (_locale(elem.text)
                                     if elem.attrib.get("{antidox}l", False)
                                     else elem.text)

                arg = text if issubclass(nclass, Text) else ''

                # automatically handle list attributes
                list_attributes = getattr(nclass, "list_attributes", ())
                filtered_attrs = {k: (v.split("|")
                                      if k in list_attributes else v)
                                  for (k, v) in elem.attrib.items()
                                  if k not in _GLOBAL_ATTRIBUTES}

                node = nclass(arg, **filtered_attrs)
                if not isinstance(node, Text) and elem.text:
                    node += Text(elem.text, elem.text)

                curr_element.append(node)

                # FIXME: this smells hacky
                if isinstance(node, Structural) and node['ids']:
                    self.state.document.note_explicit_target(node)

                curr_element = node
            else:
                if isinstance(curr_element, PlaceHolder):
                    curr_element.replace_placeholder(self.lineno, self.state,
                                                     self.state_machine)

                if isinstance(curr_element, DeferredPlaceholder):
                    special[curr_element.tagname] = curr_element

                curr_element = curr_element.parent or root

                if elem.tail:
                    curr_element.append(Text(elem.tail, elem.tail))

        return root, special

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
        nodes, special = self._etree_to_sphinx(
            rst_etree,
            **{k: k in self.options for k in self._node_hidings_opts})

        style_fn = my_domain.stylesheet_filename
        if style_fn:
            self.env.note_dependency(style_fn)

        return nodes, special

    def run(self):
        arg0 = self.arguments[0]

        if isinstance(arg0, doxy.RefId):
            ref = arg0
        else:
            ref = resolve_refstr(self.env, arg0)[0]

        context_stack = self.env.ref_context['doxy:refid']
        context_stack.append(ref)

        try:
            nodes, special = self.run_reference(ref)

            ev_args = (ref, self.options)
            inclusion_list = (self.env.app.emit_firstresult(
                                "antidox-include-children", *ev_args)
                              or default_inclusion_policy(self.env.app, *ev_args)
                              or ())

            this_directive = type(self)

            nodes_to_insert = (internal_node
                               for refid, options in inclusion_list
                               for internal_node in this_directive(
                                   'doxy:c', [refid], options, [], self.lineno,
                                   0, "", self.state, self.state_machine).run())
        finally:
            context_stack.pop()

        # just in case the elements produced not output, it should not be an
        # error.
        if "antidox_children" in special:
            # replace_self needs an indexable sequence
            special["antidox_children"].replace_self(list(nodes_to_insert))
        else:
            (nodes[-1] if nodes else nodes).extend(nodes_to_insert)

        return nodes


def target_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    """Create a cross reference for a doxygen object, given a human-readable
    target.

    The target is interpreted by resolve_refstr. It can be prefixed by ``~``,
    which causes target-strings to drop the path.
    """

    db = inliner.document.settings.env.antidox_db

    is_explicit, title, _target = split_explicit_title(text.strip())

    title = title.strip()
    _target=_target.strip()

    remove_path = _target.startswith("~")

    target = _target[1:] if remove_path else _target

    try:
        ref, match = resolve_refstr(inliner.document.settings.env, target)
    except doxy.RefError as e:
        msg = inliner.reporter.error(e.args[0], line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    try:
        reftype = db.guess_desctype(ref)
    except ValueError:
        # if there is no type, it means it is a construct that does not fit in
        # the C domain and therefore it will be a cross reference in std.
        refdomain = 'std'
        reftype = 'ref'
        innernode = Text
    else:
        refdomain = 'c'
        innernode = literal

    node = addnodes.pending_xref(rawsource=rawtext, reftarget=str(ref),
                                 refdomain=refdomain, reftype=reftype, refexplicit=is_explicit,
                                 refdoc=inliner.document.settings.env.docname,
                                 refwarn=True)
    if not is_explicit:
        # FIXME: make this fomatting customizable
        if match["name"]:
            linktext = match["name"]
        else:
            doxy_target = (doxy.Target(match["target"]) if match["target"]
                           else db.refid_to_target(match["refid"]))
            linktext = doxy_target.name if remove_path else str(doxy_target)

        if reftype == "function":
            linktext += "()"

        if match["kind"]:
            linktext += " ({})".format(match["kind"])

        node += innernode(text, linktext)
    else:
        node += Text(title, title)

    return [node], []


class DoxyDomain(Domain):
    """Domain for Doxygen-related directives and roles.

    The cross reference data is stored in the C domain. The only reason this
    domain exists is to serve as a container for template and other data that
    should be shared but not be saved with the environment.

    Attributes
    ----------

    DoxyDomain.stylesheet_filename: File name of the XSL stylesheet. If None
        or empty, it means the embedded stylesheet that comes with this
        extension is being used.
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
