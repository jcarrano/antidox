"""Test loading and saving a doxy-database."""

import os
import pickle
import subprocess

import pytest

from antidox import doxy

EXAMPLES_BASE = os.path.join(os.path.dirname(__file__), "../examples")

@pytest.fixture(scope="module",
                params=["tinycbor", "riot"])
def xml_dir(request):
    example_dir = os.path.join(EXAMPLES_BASE, request.param)

    def _clean_xml():
        subprocess.run(["make", "-C", example_dir, "clean"])

    request.addfinalizer(_clean_xml)

    subprocess.run(["make", "-C", example_dir, "doxy-xml"])

    with open(os.path.join(example_dir, "doxy-xml")) as f:
        relative_xml_dir = f.read().strip()

    return os.path.relpath(os.path.join(example_dir, relative_xml_dir))

@pytest.fixture(scope="class")
def doxy_db(request, xml_dir):
    request.cls.db = doxy.DoxyDB(xml_dir)

@pytest.mark.usefixtures("doxy_db")
class TestDB:
    def test_loaded(self):
        assert self.db._db_conn

        cur = self.db._db_conn.execute("""
        SELECT COUNT(*) AS total_elements FROM elements
        """)

        assert next(cur)[0] > 0

    def test_dump(self, tmpdir):
        """Test pickling and unpickling a database."""
        pickle_fn = os.path.join(tmpdir, "db.pickle")

        with open(pickle_fn, "wb+") as f:
            pickle.dump(self.db, f)

        with open(pickle_fn, "rb") as f:
            restored = pickle.load(f)

        elements1 = self.db._db_conn.execute("""
        SELECT * FROM elements SORT
        """)

        elements2 = restored._db_conn.execute("""
        SELECT * FROM elements SORT
        """)

        assert all(x == y for x, y in zip(elements1, elements2))


