"""
    antidox
    ~~~~~~~

    Access Doxygen documentation from within Sphinx. Provides autodoc-like
    functionality.
"""

import os

from sphinx.util import logging

from . import doxy
from . import directives
from .collector import DoxyCollector

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


logger = logging.getLogger(__name__)


def load_db(app):
    cfgdir = app.config.antidox_doxy_xml_dir

    cfgdir_time = os.path.getmtime(cfgdir) if os.path.exists(cfgdir) else None

    logger.debug("Doxy XML last modified: %s", cfgdir_time)

    env = app.env

    if (not hasattr(env, "antidox_db")
        or cfgdir_time is None
        or not hasattr(env, "antidox_db_date")
        or env.antidox_db_date < cfgdir_time):

        logger.info("(Re-)Reading Doxygen DB")
        env.antidox_db = doxy.DoxyDB(cfgdir)
        env.antidox_db_date = cfgdir_time

    app.emit("antidox-db-loaded", env.antidox_db)


def setup(app):
    app.add_config_value("antidox_doxy_xml_dir", "", 'env')
    app.add_config_value("antidox_xml_stylesheet", "", 'env')
    app.add_event("antidox-include-default")
    app.add_event("antidox-include-children")
    app.add_event("antidox-db-loaded")

    # TODO: provide support for multiple Doxygen projects
    app.connect("builder-inited", load_db)
    app.add_env_collector(DoxyCollector)

    # app.add_directive('doxy', directives.CAuto)
    # roles.register_canonical_role('doxyt', directives.target_role)
    app.add_domain(directives.DoxyDomain)

    return {'version': '0.1.1', 'parallel_read_safe': True}
