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
  generates) and semi-manual documentation.
* Have sensible defaults for automatic documentation generation while allowing
  customization.
* Deal with big projects efficiently: the main tool in use now (Breathe)
  has resource usage issues when dealing with large XML files.

.. _lxml: https://lxml.de/
.. _sqlite3: https://docs.python.org/3/library/sqlite3.html
