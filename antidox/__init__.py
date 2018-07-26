"""
    nodox
    ~~~~~

    Access Doxygen documentation from within Sphinx. Provides autodoc and
    autosummary functionality.
"""

from sphinx.errors import ExtensionError

from . import doxy

def load_doxydb(app):
    cfgdir = app.config.doxygen_xml_dir

    try:
        setup.DOXY_DB = doxy.DoxyDB(app.config.doxygen_xml_dir)
    except IOError as e:
        raise ExtensionError("[antidox]: cannot open Doxygen XML DB at %s"
                             %cfgdir) from e



def setup(app):
    pass

    # TODO: provide support for multiple Doxygen projects
    app.connect("builder-inited", load_doxydb)
    #

    app.add_config_value("doxygen_xml_dir", "", True)
