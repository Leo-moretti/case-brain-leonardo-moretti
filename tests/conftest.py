import sqlite3
from pathlib import Path

import pytest

from pipeline.build import build

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def con(tmp_path_factory):
    db = build(ROOT / "dados", tmp_path_factory.mktemp("wh") / "pontua.db")
    c = sqlite3.connect(db)
    yield c
    c.close()


def one(con, sql):
    return con.execute(sql).fetchone()[0]
