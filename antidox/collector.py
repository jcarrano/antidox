"""
    antidox.collector
    ~~~~~~~~~~~~~~~~~

    Keep track of documents that need rebuilding when the Doxygen DB is
    modified.
"""


from sphinx.environment.collectors import EnvironmentCollector

__author__ = "Juan I Carrano"
__copyright__ = "Copyright 2018, Freie Universität Berlin"


class DoxyCollector(EnvironmentCollector):
    """Collect documents that can be affected by a change in the doxygen DB.
    A custom collector is needed because note_dependency() does not work
    with directories.
    In the future this could be made smarter about what to rebuild and what not
    to.
    """
    def merge_other(self, app, env, docnames, other):
        app.env.antidox_dependencies.update(other.antidox_dependencies)

    def clear_doc(self, app, env, docname):
        app.env.antidox_dependencies.discard(docname)

    def get_outdated_docs(self, app, env, added, changed, removed):
        if not hasattr(app.env, "antidox_dependencies"):
            app.env.antidox_dependencies = set()

        return [docname for docname in app.env.antidox_dependencies
                if docname not in app.env.all_docs
                or app.env.all_docs[docname] < app.env.antidox_db_date]

    def process_doc(self, *args):
        pass

    @staticmethod
    def note_dependency(env):
        """Mark the current document as depending on the doxygen database."""
        env.antidox_dependencies.add(env.docname)
