.. py:module:: antidox.doxy

antidox.doxy
============

This module reads in all doxygen XML files and constructs a (in-memory) SQL
database that serves as index. We will be performing more or less complex
queries into a graph of objects; using SQL avoids having to hand-craft all
that logic.

To work around C's lack of namespaces, the `doxy` module defines a
human-readable `Target` string that can be used to uniquely refer to a
documented C construct, even if the name is defined in multiple files.

The first document to be read is ``index.xml``. Then the rest of the documents
are read only to determine hierarchy relationships.

.. autoclass:: Kind
    :members:

.. autoclass:: RefId

.. autoclass:: Target

.. autoclass:: DoxyDB
    :members:

.. autodata:: SearchResult
