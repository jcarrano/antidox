Overview
========

About ``antidox``
-----------------

``antidox`` is a Sphinx extension that can read Doxygen XML "databases" and
insert documentation for entities- C language constructs as well as
Doxygen-specific things like groups- in Sphinx documents.

It is intended to be *fast* and simple, though *easily customizable*.

Document generation (i.e. conversion between doxy-xml and reStructuredText) is
driven by XML stylesheets (powered by lxml_,) while indexing and selection of
documentable entities is done by a SQL database (sqlite3_.)

Objectives
----------

* Reuse API docs made with Doxygen in a Sphinx project.
* Provide a smooth transition between 100% automatic API docs (what Doxygen
  generates) and semi-manual documentation.

  .. todo::

    Add Autoindex-like functionality.

* Have sensible defaults for automatic documentation generation while allowing
  customization.
* Deal with big projects efficiently: the main tool in use now (Breathe)
  has resource usage issues when dealing with large XML files.

  .. todo::

    It would be good to have a way of detecting that a XML file has not changed
     to avoid generating it again.

Design philosophy
-----------------

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


Quickstart
----------

First, you need to configure Doxygen to produce XML docs, edit your
``doxyfile``::

  GENERATE_XML = yes

If your project is huge, consider setting ``XML_PROGRAMLISTING = NO`` to reduce
the size of the generated files.

Enable the ``antidox`` plugin in your Sphinx project's ``conf.py`` and tell it
where to find the XML file::

  extensions = [
    # whatever extensions you have enabled
    'antidox',
  ]

  # ..... other extension's stuff ......

  # Configure antidox
  antidox_doxy_xml_dir = "path/to/doxygen/xml"

Now you can use the directives in a reST document. For example, to include the
documentation of function ``foo()`` defined in ``bar.h`` write::

  .. doxy:c:: bar.h::foo

You can later refer to it using the :rst:role:`doxy:r` role. You can also
include documentation for an entire file, or for a Doxygen group::

  .. doxy:c:: bar.h::*

  .. doxy:c:: group[name_of_the_group]

On huge projects, the fist time you run ``sphinx-build`` it may take a some time
to parse all the XML files. Subsequent runs should go faster as long as the
XML files are not touched.

Note: currently under development
---------------------------------

This software is currently under development and in alpha phase. This means all
work is being done on `master`, which may break, and APIs may change, all while
keeping version 0.1.1.

As soon as it is deemed stable enough, the version will be bumped to 0.1.2 and
this notice will be removed.

.. todolist::

.. _lxml: https://lxml.de/
.. _sqlite3: https://docs.python.org/3/library/sqlite3.html
