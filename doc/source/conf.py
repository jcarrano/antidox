# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))


# -- Project information -----------------------------------------------------

project = 'antidox'
copyright = '2018, Freie Universität Berlin'
author = 'Juan I. Carrano'

# The short X.Y version
version = ''
# The full version, including alpha/beta/rc tags
release = '0.1.1'


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.napoleon'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx.
language = None

exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = None


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'

# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
html_static_path = ['_static']


# -- Extension configuration -------------------------------------------------

napoleon_numpy_docstring = True

autodoc_mock_imports = ['lxml']

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# Stolen from Sphinx' docs

import enum

from sphinx import addnodes  # noqa
import re

event_sig_re = re.compile(r'([a-zA-Z-]+)\s*\((.*)\)')

def parse_event(env, sig, signode):
    m = event_sig_re.match(sig)
    if not m:
        signode += addnodes.desc_name(sig, sig)
        return sig
    name, args = m.groups()
    signode += addnodes.desc_name(name, name)
    plist = addnodes.desc_parameterlist()
    for arg in args.split(','):
        arg = arg.strip()
        plist += addnodes.desc_parameter(arg, arg)
    signode += plist
    return name


def include_enum_values(app, what, name, obj, skip, options):
    if isinstance(obj, enum.Enum):
        return False


def setup(app):
    from sphinx.util.docfields import GroupedField

    app.add_object_type('confval', 'confval',
                        objname='configuration value',
                        indextemplate='pair: %s; configuration value')
    fdesc = GroupedField('parameter', label='Parameters',
                         names=['param'], can_collapse=True)
    app.add_object_type('event', 'event', 'pair: %s; event', parse_event,
                        doc_field_types=[fdesc])

    app.add_object_type('xpath-func', 'xpath', 'pair: %s; xpath-func',
                        parse_event)

    app.connect('autodoc-skip-member', include_enum_values)
