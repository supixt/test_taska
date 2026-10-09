import hashlib
import shutil
import sqlite3

import pytest

from app import db
from app.db import DataValidationError, ReadOnlyDB, open_database
from scripts.build_data import TASK_DIR


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "seed.sqlite"
    shutil.copy(TASK_DIR / "seed.sqlite", path)
    return path


@pytest.fixture
def rodb(db_path):
    return ReadOnlyDB(db_path)


# 4^16 rows on the seed: minutes of work, so any short deadline must interrupt it.
SLOW_SQL = "SELECT sum(t0.amount_cents) FROM " + ", ".join(f"orders t{i}" for i in range(16))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_select_returns_columns_and_rows(rodb):
    r = rodb.query("SELECT order_id, amount_cents FROM orders ORDER BY order_id")
    assert r["status"] == "ok"
    assert r["columns"] == ["order_id", "amount_cents"]
    assert r["rows"] == [["O1", 5000], ["O2", 5000], ["O3", 5000], ["O4", 5000]]
    assert r["truncated"] is False and r["error"] is None


def test_cte_and_join_over_allowed_tables(rodb):
    r = rodb.query("WITH r AS (SELECT order_id, SUM(amount_cents) AS refunded FROM refunds GROUP BY order_id) "
                   "SELECT c.segment, SUM(r.refunded) FROM r JOIN orders o USING (order_id) "
                   "JOIN customers c USING (customer_id) GROUP BY c.segment")
    assert r["status"] == "ok"
    assert r["rows"] == [["small", 4000]]


@pytest.mark.parametrize("sql", [
    "INSERT INTO refunds VALUES ('RFX', 'O1', '2026-09-01', 100)",
    "UPDATE orders SET amount_cents = 0",
    "DELETE FROM refunds",
    "DROP TABLE orders",
    "CREATE TABLE x (a)",
    "CREATE TEMP TABLE x (a)",
])
def test_writes_rejected_and_file_unchanged(db_path, rodb, sql):
    before = file_hash(db_path)
    r = rodb.query(sql)
    assert r["status"] == "rejected"
    assert "not allowed" in r["error"]
    assert file_hash(db_path) == before


@pytest.mark.parametrize("sql, named", [
    ("DELETE FROM refunds", "DELETE refunds"),
    ("PRAGMA table_info(orders)", "PRAGMA table_info orders"),
    ("SELECT name FROM sqlite_master", "READ sqlite_master"),
])
def test_rejection_names_denied_action(rodb, sql, named):
    assert named in rodb.query(sql)["error"]


@pytest.mark.parametrize("sql", [
    "PRAGMA table_info(orders)",
    "SELECT * FROM pragma_table_info('orders')",
    "ATTACH DATABASE ':memory:' AS other",
    "SELECT name FROM sqlite_master",
    "SELECT count(*) FROM sqlite_master",
    "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 3) SELECT x FROM n",
])
def test_non_select_and_other_tables_rejected(rodb, sql):
    r = rodb.query(sql)
    assert r["status"] == "rejected", r
    assert r["rows"] == []


def test_slow_query_times_out(rodb, monkeypatch):
    monkeypatch.setattr(db, "QUERY_TIMEOUT_S", 0.5)
    r = rodb.query(SLOW_SQL)
    assert r["status"] == "timeout"
    assert "0.5 s" in r["error"]


def test_connection_usable_after_timeout(rodb, monkeypatch):
    monkeypatch.setattr(db, "QUERY_TIMEOUT_S", 0.2)
    assert rodb.query(SLOW_SQL)["status"] == "timeout"
    assert rodb.query("SELECT count(*) FROM orders")["rows"] == [[4]]


def test_row_cap_truncates(rodb):
    # 4^5 = 1024 rows from a cross join, above MAX_ROWS.
    r = rodb.query("SELECT a.order_id FROM orders a, orders b, orders c, orders d, orders e")
    assert r["status"] == "ok"
    assert len(r["rows"]) == db.MAX_ROWS
    assert r["truncated"] is True


@pytest.mark.parametrize("sql", ["SELEC * FROM orders", "SELECT FROM orders", "SELECT nope FROM orders",
                                 "SELECT 1; SELECT 2", ""])
def test_malformed_sql_returns_error(rodb, sql):
    r = rodb.query(sql)
    assert r["status"] == "error"
    assert r["error"]


def test_empty_result_has_own_status(rodb):
    r = rodb.query("SELECT order_id FROM orders WHERE order_date >= '2027-01-01'")
    assert r["status"] == "empty"
    assert r["columns"] == ["order_id"] and r["rows"] == []


def test_open_database_validates(db_path):
    assert open_database(db_path).query("SELECT count(*) FROM refunds")["rows"] == [[3]]


def test_open_database_refuses_broken_data(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO refunds VALUES ('RFX', 'O1', '2026-09-01', 4500)")
    conn.commit()
    conn.close()
    with pytest.raises(DataValidationError, match="refunds for an order exceed its amount: O1"):
        open_database(db_path)
