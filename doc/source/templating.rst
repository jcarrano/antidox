XML template reference
======================

XML to RST conversion
---------------------

Restructured Text documents (and fragments of documents) have a tree-like
structure that can be approximately described by an element tree. In fact,
Sphinx can output XML.

antidox works by converting a XML element tree that is the result of the
transform (we will call this "intermediate XML") into reST nodes. For most
elements the transformation is straightforward as there is a direct
correspondence. Special cases like directives, localization and indices are
handled via the ``antidox`` XML namespace.

During normal operation, the intermediate XML is never written to a document,
but it is kept in memory as an element tree.

Standard Sphinx and reST nodes
------------------------------

From the intermediate XML, all unqualified elements are converted to reST nodes
of the same name (``docutils.nodes`` and ``sphinx.addnodes`` are searched).
If the element does not map to a Text-derived node and there is a TEXT element
inside, a new Text node is created. Otherwise the text is used to create the
node.

Setting attributes
~~~~~~~~~~~~~~~~~~

Some nodes accept a list of values as arguments. XML element attributes, however,
are always string. To work around this issue, antidox allows encoding lists for
these attributes by using "|" as a separator.

Additionally, the strings ``true`` and ``false`` are converted to Python's
**bool()**.

.. _xml-additional:

Additional information
~~~~~~~~~~~~~~~~~~~~~~

reST nodes are constructed from an argument that is the "raw" source code for
that element, plus a set of keyword arguments. Only nodes derived from ``Text``
can contain text. The rest of the nodes must have a Text-derived node as a
child if the are to have text.

When creating nodes, the template interpreter in antidox sets the "raw" argument
to an empty string. Also, all line numbers are set to the line number of the
directive, for lack of a more meaningful value.

To apply the XSL transformation, the XML element corresponding to the entity
being documented (e.g. a ``<compounddef>`` or a ``<memberdef>``) is extracted
from its containing document and the transform is run as if that element was the
root element. This means XPath expressions may give different results when the
the same stylesheet is applied to a whole doxygen XML. In addition, an
:ref:`antidox-fakeroot` may be necessary if many top-level elements are to
be generated from a single XML node.

Global stylesheet parameters
----------------------------

The XSL following parameters are available at the global scope. Their value
is derived from the rst:dir:`doxy:c` directive options.

Boolean parameters
~~~~~~~~~~~~~~~~~~

These are set to ``true`` if the corresponding options is set, else they are
``false``: :ref:`noindex <noindex-option>`, :ref:`hideloc <hideloc-option>`,
:ref:`hidedoc <hidedoc-option>`, :ref:`hidedef <hidedef-option>`.

The typical use of ``noindex`` is to conditionally emit an
:ref:`index node <_antidox-indexnode>`:

.. code-block: xslt

  <xsl:if test="noindex!='true'"><antidox:index/></xsl:if>


antidox-specific attributes
---------------------------

``antidox:l`` (attribute)
~~~~~~~~~~~~~~~~~~~~~~~~~

When set to ``"true"`` in a Text-derived element, the text is run through
Sphinx's locale function.

``antidox:definition``
~~~~~~~~~~~~~~~~~~~~~~

When set to ``"true"`` in any element it indicates that it is a definition and
should be skipped when the `:hidedef:` option is given.

``antidox:content``
~~~~~~~~~~~~~~~~~~~

When set to ``"true"`` in any element it indicates that it contains the
documentation for the entity and thus must be skipped when the `:hidedoc:`
option is given.

`desc_content` will have this attribute automatically set to "true", though it
is still possible to override it.

antidox-specific (pseudo)elements
---------------------------------

``<antidox:usercontent>``
~~~~~~~~~~~~~~~~~~~~~~~~~

Placeholder for user-defined content, that is, content given in the body of the
rst:dir:`doxy:c` directive.

If this element is not present, antidox will try to nest the directive body
under a ``docutils.nodes.desc_content`` node. If none is found, it will be
placed as a child of the last top level element.

``<antidox:children>``
~~~~~~~~~~~~~~~~~~~~~~

Placeholder for child elements. This node will be replaced by the subtrees of
children that result from the :ref:`children option <children-option>` and
:ref:`no-children option <no-children-option>`. By default children subtrees are
appended to the last root element resulting from the transform.

.. _antidox-indexnode:

``<antidox:index>``
~~~~~~~~~~~~~~~~~~~

Places cross-reference entries (``sphinx.addnodes.index``). Additionally, if
its parent has an ``ids`` attribute, it registers it in the proper domain.

.. _antidox-fakeroot:

``<antidox:fakeroot>``
~~~~~~~~~~~~~~~~~~~~~~

As described in :ref:`xml-additional`, doxygen XML nodes are extracted to the
top (root) level before applying the XSL template. The result of a XSL tranform
must be a valid XML document which means that, normally, one would only be
able to emit a single (non nested) Sphinx node in a :rst:dir:`doxy:c` directive.

This node allows circumventing this restriction. After the XSLT step all
``<antidox:fakeroot>`` are "dissolved".


Generating roles and directives
-------------------------------

Directives in reST do not have their own nodes. Rather, they generate nodes that
are then inserted in the document. Interpreted text roles such as cross
references behave similarly.

.. _antidox-directive-elem:

``<antidox:directive>``
~~~~~~~~~~~~~~~~~~~~~~~

This element calls a directive. reST directives are not nodes: they generate
nodes that are added to the tree. This element can have the following attributes:

``antidox:name``
  Name of the directive to invoke ("directive type" in reST terminology.)

Other parameters
  Other parameters will be intepreted as directive options.

``<antidox:directive-argument>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Placed inside :ref:`antidox-directive-elem`, its TEXT is translated to arguments
for that directive.

``<antidox:directive-content>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This element's TEXT is the content of the containing directive.

``<antidox:interpreted>``
~~~~~~~~~~~~~~~~~~~~~~~~~

Inserts an interpreted text role (such as :rst:role:`ref`, :rst:role:`c:func`,
etc). The contents of the node (which must consist only of text, no child nodes)
is passed as the `text` argument to the interpreted role.

There is a single attribute, ``role``, which species the name if the role
(including the domain if necessary.)

Other
-----

``antidox:compound``
~~~~~~~~~~~~~~~~~~~~

Name of the built-in default stylesheet, to be used as ``href`` in ``xsl:import``
and ``xsl:include`` statements, for example

.. code-block: xslt

  <xsl:import href="antidox:compound"/>

The reason the built-in style is exposed this way and not with a filename is
that the file may not exist: for example, this extension may be installed as a
zipfile. You can obtain the contents of the built-in stylesheet using the shell.
