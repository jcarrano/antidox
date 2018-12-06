==============================================
Antidox: Use Doxygen sanely from within Sphinx
==============================================

---------------------------
An antidote to doxy-madness
---------------------------

Note: currently under development
=================================

This software is currently under development and in alpha phase. This means all
work is being done on `master`, which may break, and APIs may change, all while
keeping version 0.1.1.

As soon as it is deemed stable enough, the version will be bumped to 0.1.2 and
this notice will be removed.

Summary
=======

``antidox`` is a Sphinx extension that can read Doxygen XML "databases" and insert
documentation for entities in sphinx documents.

It is intended to be *fast* and simple, though *easily customizable*.

Document generation (i.e. conversion between doxy-xml and reStructuredText) is
driven by XML stylesheets (powered by lxml_,) while indexing and selection of
documentable entities is done by a SQL database (sqlite3_.)

Objectives
==========

* Reuse API docs made with Doxygen in a Sphinx project.
* Provide a smooth transition between 100% automatic API docs (what Doxygen
  generates) and semi-manual documentaion.
* Have sensible defaults for automatic documentation generation while allowing
  customization.
* Deal with big projects efficiently: the main tool in use now (Breathe)
  has resource usage issues when dealing with large XML files.

Functionality
=============

References
----------

The standard way to refer to entities in antidox is by ``file_path::entity_name``,
(called a *target* in antidox terms) where ``file_path`` is base name of the
file, along with enough directory components to make the path unique
(similar to the default settings in Doxygen.)

Note that while a target should correspond to only one code entity, the same
entity can be described by different targets. For example ``a/b.h::f`` and
``b.h::f``.

Directives, roles and domains
-----------------------------

Directives and roles are contained in an `doxy` domain.

.. rst:directive:: c

  This directive inserts the documentation corresponding to a doxygen-documented
  entity. The entity is specified either as a target string::

    .. doxy:c:: file.h::identifier

  or, if it is not a C-language element (for example, a Doxygen group) by using
  the syntax::

    .. doxy:c:: kind[name]

  Where ``kind`` is optional- if it is not given, then ``name`` should be unique.

  There is nothing hardcoded about the reST nodes that get created. Everything,
  including index and cross reference creation is controlled by the XSL template,
  see `Customization`_.

  The following options are accepted:

  ``hidedef``
    For macros and variables, do not show the definition.

  ``hideloc``
    Do not print the location in the source code of the definition (not
    currently implemented.)

  ``noindex``
    Do not add index entries (not currently implemented.)

  ``hidedoc``
    Do not render the text of the documentation. This is useful if you want
    to replace the description with your own text in the reST source.

  To be implemented:

  ``children``
    Include documentation for the given child elements. This option may be empty,
    in which case the default is to include all children whose `kind` is
    different from the current element.

  ``no-children``
    Exclude the selected children. By default if this option is empty, it forces
    all children to be excluded.

  Children are normally specified by name. The default inclusion behavior can be
  overridden by responding the `antidox-include-children`_ event.


.. rst:directive:: r

  Insert a cross reference to the given target's documentation.

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
`import` statement. A basic stylesheet can be::

  <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:import href="antidox:compound"/>
  </xsl:stylesheet>

Because the XML templating system is designed so as to make it possible to apply
the transforms offline with standard tools (see `Design philosophy`_), there is
no access to the Doxygen database from within templates. This means that it is
not possible to query the relationships (parent, children, etc) of the element
being rendered from within the XSL template. The only information available is
that which is exposed by Doxygen's XML. That this information is available is
considered by the author of this extension to be a design mistake, because it
is a consequence of duplicate data all across Doxygen-generated documents.
Therefore, this information is not used in the built-in templates, and it is
recommended that user-supplied templates do not either. Instead, a more flexible
mechanism for including the documentation of child elements is provided in the
form of events- see the next section.

Events
------

.. note::

  This functionality is currently under development.

.. event:: antidox-include-children (app, this, options)

  Emitted once for every :rst:dir:`c` directive, to determine which child
  elements should be included. antidox will select the first non-``None`` value.

  Handlers should return either ``None``, to fall back to the default behavior,
  or list of tuples of the form ``(refid, options)``. In the latter case,
  ``refid`` should be a doxy.RefId object and options a dictionary which will
  set the options for the nested :rst:dir:`doxy:c` directive.

  :param app: the Sphinx application object
  :param this: refid for the object currently being documented.
  :param options: dictionary with the options given to the directive.


Implemetation Overview
======================

``antidox.doxy``
----------------

This module reads in all doxygen XML files and constructs a (in-memory) SQL
database that serves as index. We will be performing more or less complex
queries into a graph of objects; using SQL avoids having to hand-craft all
that logic.

To work around C's lack of namespaces, the `doxy` module defines a
human-readable `Target` string that can be used to uniquely refer to a
documented C construct, even if the name is defined in multiple files.

The first document to be read is ``index.xml``. Then the rest of the documents
are read only to determine hierarchy relationships.

``antidox.directive``
---------------------

The main functionality of the module (on the python side) is implemented as a
directive that fetches the XML generated by doxygen, runs a XSL transform (in
memory) and converts the resulting XML element tree into reST nodes.

``compound.xsl``
----------------

The code in ``antidox.directive`` is a fairly generic mechanism. The "policy"
specifying how the XML is converted is coded entirely as a stylesheet.

There are a couple of antidox-specific nodes that are used for directives, roles
and translations because those are not implemented by nodes on the reST side.


Design philosophy
=================

Doxygen is a great tool for parsing C code and extracting all kinds of
entities. Unfortunately, the output is a bit messy, because it is not
hierarchical: Groups are hierarchical, but entities also appear in file
compounds, and on their own (structs, for example). This means that if Doxygen
XML files are directly mapped to rst documents, one ends up with loads of
duplicate definitions.

Also, Doxygen seems to make a lot of decisions in what it considers to be a
top-level entity and what not (of course, it's heavily influenced by C++
concepts).

C does not have the concept of packages/modules, it's up to the programmer that
is commenting the code to define those abstraction by using ``@ingroup``
directives. Some package documentation ends up in file compounds and some other
in groups. To make matters worse, a group does not have a fixed definition.

This tool tries to reduce Doxygen to a tool for parsing code and comments and
to give documentation writers explicit control over the layout and placement of
the different entities.

The templating and XML handling logic is designed so that in the future it is
possible to run the XSL transformation online, using generic tools. For this
reason, there should not be any custom functions defined and no stylesheet
parameters that depend on the plugin to set them.

Defining XML templates
======================

Restructured Text documents (and fragments of documents) have a tree-like
structure that can be approximately described by an element tree. In fact,
Sphinx can output XML.

antidox works by converting a XML element tree that is the result of the
transform (we will call this "intermediate XML") into reST nodes. For most
elements the transformation is straightforward as there is a direct
correspondence. Special cases like directives, localization and indices are
handled via the ``antidox`` XML namespace.

The XSL processing step (converting to Doxygen XML into intermediate XML) is
done in such a way that it should be possible to do it offline, using a generic
XML processor. That means there a no special functions and no special template
parameters. During normal operation, the intermediate XML is never written to
a document, but it is kept in memory as an element tree.

reST nodes are constructed from an argument that is the "raw" source code for
that element, plus a set of keyword arguments. Only nodes derived from ``Text``
can contain text. The rest of the nodes must have a Text-derived node as a
child if the are to have text.

From the intermediate XML, all unqualified elements are converted to reST nodes
of the same name (``docutils.nodes`` and ``sphinx.addnodes`` are searched).
If the element does not map to a Text-derived node and there is a TEXT element
inside, a new Text node is created. Otherwise the text is used to create the
node.

antidoc-specific extensions
---------------------------

``antidox:l`` (attribute)
~~~~~~~~~~~~~~~~~~~~~~~~~

When set to ``"true"`` in a Text-derived element, the text is run through
Sphinx's locale function.

``antidox:definition`` (attribute)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When set to ``"true"`` in any element it indicates that it is a definition and
should be skipped when the ":hidedef:" option is given.

``antidox:directive``
~~~~~~~~~~~~~~~~~~~~~

This element calls a directive. reST directives are not nodes: they generate
nodes that are added to the tree. This element can have the following parameters:

``antidox:name``
  Name of the directive to invoke ("directive type" in reST terminology.)

Other parameters
  Other parameters will be intepreted as directive options.

``antidox:directive-argument``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Placed inside `antidox:directive`_, its TEXT is translated to arguments for that
directive.

``antidox:directive-content``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This element's TEXT is the content of the containing directive.

``antidox:compound``
~~~~~~~~~~~~~~~~~~~~

Name of the builtin default stylesheet, to be used as ``href`` in ``xsl:import``
and ``xsl:include`` statements.

Since this package can be installed as a zip, the actual XSL file may not exist
as such in the filesystem. For this reason a custom resolver is defined.

TODO
====

* It would be good to have a way of detecting that a XML file has not changed
  to avoid generating it again.
* Autoindex functionality.
* Document custom XML nodes (antidox namespace).
* Complete docs.
* Some important doxygen constructs are missing.
* Add glossary.

.. _lxml: https://lxml.de/
.. _sqlite3: https://docs.python.org/3/library/sqlite3.html
