"""
    antidox
    ~~~~~~~

    Access Doxygen documentation from within Sphinx. Provides autodoc-like
    functionality.
"""

from . import doxy
from . import directives

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


def load_db(app, env, docnames):
    cfgdir = app.config.antidox_doxy_xml_dir

    if not hasattr(env, "antidox_db"):
        env.antidox_db = doxy.DoxyDB(cfgdir)


def setup(app):
    app.add_config_value("antidox_doxy_xml_dir", "", 'env')
    app.add_config_value("antidox_xml_stylesheet", "", 'env')
    app.add_event("antidox-include-children")

    # TODO: provide support for multiple Doxygen projects
    app.connect("env-before-read-docs", load_db)

    # app.add_directive('doxy', directives.CAuto)
    # roles.register_canonical_role('doxyt', directives.target_role)
    app.add_domain(directives.DoxyDomain)

    return {'version': '0.1.1', 'parallel_read_safe': True}
