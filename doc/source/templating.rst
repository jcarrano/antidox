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

``antidox:compound`` (stylesheet)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Name of the built-in stylesheet. Use it to inherit from it and extend it, as in::

  <xsl:import href="antidox:compound"/>

The reason the built-in style is exposed this way and not with a filename is
that the file may not exist: for example, this extension may be installed as a
zipfile. You can obtain the contents of the built-in stylesheet using the shell.
