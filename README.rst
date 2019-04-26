==============================================
Antidox: Use Doxygen sanely from within Sphinx
==============================================

---------------------------
An antidote to doxy-madness
---------------------------

|docs| |pypi|


Summary
=======

``antidox`` is a Sphinx_ extension that can read Doxygen_ XML "databases" and
insert documentation for entities in Sphinx documents, similar to Breathe_.

It is intended to be *fast* and simple, though *easily customizable*.

Document generation (i.e. conversion between doxy-xml and reStructuredText) is
driven by XML stylesheets (powered by lxml_,) while indexing and selection of
documentable entities is done by a SQL database (sqlite3_.)

Here is an `example project <cbor_example_>`_ showing showing this extension in
action.

Note: Beta
==========

Though usable, this extension is still under development. Backwards
compatibility will be kept for all releases with the same major/minor version.

Be aware, however, that after updating this extension you may need to do a clean
build of your docs to see the results.

Objectives
==========

* Reuse API docs made with Doxygen in a Sphinx project.
* Provide a smooth transition between 100% automatic API docs (what Doxygen
  generates) and semi-manual documentation (autodoc-style).
* Have sensible defaults for automatic documentation generation while allowing
  customization.
* Deal with big projects efficiently: the main tool in use now (Breathe)
  has resource usage issues when dealing with large XML files.

.. |docs| image:: https://readthedocs.org/projects/antidox/badge/?version=latest&style=for-the-badge
    :alt: Documentation Status
    :scale: 100%
    :target: https://antidox.readthedocs.io/en/latest/?badge=latest

.. |pypi| image:: https://img.shields.io/pypi/v/antidox.svg?style=for-the-badge
    :alt: PyPI
    :scale: 200%
    :target: https://pypi.org/project/antidox/

.. _Sphinx: https://www.sphinx-doc.org
.. _Doxygen: http://www.doxygen.nl/
.. _Breathe: https://breathe.readthedocs.io/en/latest/
.. _lxml: https://lxml.de/
.. _sqlite3: https://docs.python.org/3/library/sqlite3.html
.. _cbor_example: https://antidox-example.readthedocs.io/en/latest/
