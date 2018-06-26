==================================
Convert Doxygen XML into RST files
==================================

Why
===

* Because I want to be able to reuse API docs made with Doxygen in a Sphinx project.
* Because I want to have sensible defaults for automatic doc generation without
  having to manually write a reST document for each module.
* Because existing tools such as Breathe don't do exactly what I want, and have
  some resource usage issues when dealing with large files.

Design philosophy
=================

Doxygen is a great tool for parsing C code and extracting all kinds of
entities. Unfortunately, the output is a bit messy, because it is not
hierarchical: Groups are hierarchical, but entities also appear in file
compounds, and on their own (structs, for example). This means that if Doxygen
XML files are directly mapped to rst documents, one ends up with loads of
duplicate definitions.

C does not have the concept of packages/modules, it's up to the programmer that
is commenting the code to define those abstraction by using ``@ingroup``
directives. Some package documentation ends up in file compounds and some other
in groups. To make matters worse, a group does not have a fixed definition.

I propose to use Doxygen merely as a tool to parse code and comments.

How it works
============

The tool parses Doxygen XML output. The first document it be read is ``index.xml``.
Then the rest of the documents are read only do determine hierarchy relationships.

TODO
====

* It would be good to have a way of detecting that a XML file has not changed
  to avoid generating it again.
