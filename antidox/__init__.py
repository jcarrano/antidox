"""
    antidox
    ~~~~~~~

    Access Doxygen documentation from within Sphinx. Provides autodoc-like
    functionality.
"""

from sphinx.errors import ExtensionError

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"

# FIXME: this get_db stuff is dirty

M = {}

def get_db(app):
    from . import doxy

    cfgdir = app.config.doxygen_xml_dir
    if cfgdir not in M:
        M[cfgdir] = doxy.DoxyDB(cfgdir)

    return M[cfgdir]

def setup(app):
    from docutils.parsers.rst import roles
    from . import directives

    app.add_config_value("doxygen_xml_dir", "", True)

    # TODO: provide support for multiple Doxygen projects
    #app.connect("builder-inited", load_doxydb)
    #

    app.add_directive('doxy', directives.CAuto)
    roles.register_canonical_role('doxyt', directives.target_role)

    return {'version': '0.1.1', 'parallel_read_safe': True}
