User Guide
==========

.. py:currentmodule:: antidox

Concepts
--------

Entities
~~~~~~~~

Throughout the docs (and the code,) the term "entity" is used to refer to any
object that can be documented by Doxygen. This includes C language constructs,
such as functions, structures, macros, as well as aggregations like files and
Doxygen groups.

Kinds
~~~~~

Entities have a "kind", which is corresponds to Doxygen's attribute of the same
name. Valid kinds are: ``class``, ``struct``, ``union``, ``exception``,
``file``, ``namespace``, ``group``, ``page``, ``example``, ``dir``, ``define``,
``property``, ``variable``, ``typedef``, ``enum``, ``enumvalue``, ``function``,
``friend``.

Not all kinds are currently supported.

.. todo::

  Some important doxygen constructs may be missing.

.. _entity_references:

References
~~~~~~~~~~

The standard way to refer to C language constructs in antidox is by
``file_path::entity_name``, (called a *target* in antidox terms) where
``file_path`` is base name of the file, along with enough directory components
to make the path unique (similar to the default settings in Doxygen.)

Note that while a target should correspond to only one code entity, the same
entity can be described by different targets. For example ``a/b.h::f`` and
``b.h::f``.

The target for a file has the form ``file_path::*``.

For entities that are not C-language elements (for example, a Doxygen group),
the "bracket syntax" ``[name]`` or ``kind[name]`` can be used. In the former the
name must be unique among all kinds of entities, while the latter allows
disambiguation by specifying the kind.

Inside a :rst:dir:`doxy:c` directives (i.e, when calling :rst:dir:`doxy:c` or
:rst:role:`doxy:r` inside the body, or via a a template) the extension will try
to resolve ambiguous names by prioritizing entities that are children of the
one currently being documented.

Directives, roles and domains
-----------------------------

Directives and roles are contained in an `doxy` domain.

.. rst:directive:: doxy:c

  This directive inserts the documentation corresponding to a doxygen-documented
  entity. The entity is specified either as a target string::

    .. doxy:c:: file.h::identifier

  or, if it is not a C-language element (for example, a Doxygen group) by using
  the syntax::

    .. doxy:c:: kind[name]

  Where ``kind`` is optional- if it is not given, then ``name`` should be unique.
  See :py:data:`directives.ENTITY_RE` for details on the reference format.

  There is nothing hardcoded about the reST nodes that get created. Everything,
  including index and cross reference creation is controlled by the XSL template,
  see `Customization`_.

  The following options are accepted:

  .. _hidedef-option:

  ``hidedef``
    For macros and variables, do not show the definition.

  .. _hideloc-option:

  ``hideloc``
    Do not print the location in the source code of the definition.

  .. _noindex-option:

  ``noindex``
    Do not add index entries. This options is inherited by children included
    automatically by the :ref:`:children: <children-option>` option.

  .. _hidedoc-option:

  ``hidedoc``
    Do not render the text of the documentation. This is useful if you want
    to replace the description with your own text in the reST source.

  .. _children-option:

  ``children``
    Include documentation for the given child elements. This option may be empty,
    in which case the default is to include all children whose `kind` is
    different from the current element.

  .. _no-children-option:

  ``no-children``
    Exclude the selected children. By default if this option is empty, it forces
    all children to be excluded.

  Children are normally specified by *name*. The default inclusion behavior can
  be overridden by responding the :event:`antidox-include-children` event.


.. rst:role:: doxy:r

  Insert a cross reference to an entity documented with :rst:dir:`doxy:c`. As
  with other Sphinx cross-reference roles, the link can be assigned an explicit
  title by using the syntax ``:ref:`Link title <reference>`.``

  The format for the reference is the same as in :rst:dir:`doxy:c`. Additionally,
  a :py:class:`Doxygen refid <doxy.RefId>` can be directly specified by
  prefixing it with `!`. This is meant to facilitate conversion of Doxygen's
  `<ref>` nodes to Sphinx references.

  If an explicit link title is not given, it is derived from the reference. If
  the reference is prefixed by `~` (tilde) then the path component will not be
  part of the title (e.g. ``file.h::X::Name`` will render as ``Name``).

  When customizing the template, it is recommended to use this directive to
  convert Doxygen's ``<ref>`` elements.

Configuration variables
-----------------------

.. confval:: antidox_doxy_xml_dir

  Directory where the doxygen XML files are to be found.

.. confval:: antidox_xml_stylesheet

  (Optional) Specify an alternative stylesheet. See `Customization`_ for
  instructions on how to define your own stylesheet.

Customization
-------------

antidox comes with a default template in the form of a XML stylesheet. It is
possible to change the rendering of elements and even add support for other
Doxygen constructs by supplying an alternate stylesheet through the
`antidox_xml_stylesheet` parameter.

A custom stylesheet can inherit from (or include) the default one by using an
`import` statement. A basic stylesheet can be

.. code-block:: xml

  <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:import href="antidox:compound"/>
  </xsl:stylesheet>

Currently, there is no access to the Doxygen database from within templates.
This means that it is not possible to query the relationships (parent,
children, etc) of the element being rendered from within the XSL template. The
only information available is that which is exposed by Doxygen's XML. That this
information is available is considered by the author of this extension to be a
design mistake, because it is a consequence of duplicate data all across
Doxygen-generated documents. Therefore, this information is not used in the
built-in templates, and it is recommended that user-supplied templates do not
either. Instead, a more flexible mechanism for including the documentation of
child elements is provided in the form of events- see the next section.

Events
------

.. event:: antidox-include-children (app, this, options)

  Emitted once for every :rst:dir:`c` directive, to determine which child
  elements should be included. antidox will select the first non-``None`` value.

  Handlers should return either ``None``, to fall back to the default behavior,
  or list of tuples of the form ``(refid, options)``. In the latter case,
  ``refid`` should be a doxy.RefId object and options a dictionary which will
  set the options for the nested :rst:dir:`doxy:c` directive.

  The default behavior is implemented by :py:func:`directives.default_inclusion_policy`.

  :param app: the Sphinx application object
  :param this: refid for the object currently being documented.
  :param options: dictionary with the options given to the directive.

  For example, you can use this event to exclude struct members that start with
  and underscore:

  .. literalinclude:: ../../examples/riot/conf.py
   :lines: 166-182,195-197
