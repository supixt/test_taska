"""Database access for the investigator: read-only query tool (D4) and data validation (D10)."""
import sqlite3
import time
from pathlib import Path

QUERY_TIMEOUT_S = 2
MAX_ROWS = 200
ALLOWED_TABLES = {"customers", "orders", "refunds"}
# Run the deadline check every N SQLite VM instructions.
PROGRESS_STEPS = 1000

# Authorizer action codes only: other SQLITE_* constants (limits, error codes) reuse the same numbers.
_ACTION_NAMES = {getattr(sqlite3, f"SQLITE_{n}"): n for n in (
    "CREATE_INDEX CREATE_TABLE CREATE_TEMP_INDEX CREATE_TEMP_TABLE CREATE_TEMP_TRIGGER CREATE_TEMP_VIEW "
    "CREATE_TRIGGER CREATE_VIEW DELETE DROP_INDEX DROP_TABLE DROP_TEMP_INDEX DROP_TEMP_TABLE DROP_TEMP_TRIGGER "
    "DROP_TEMP_VIEW DROP_TRIGGER DROP_VIEW INSERT PRAGMA READ SELECT TRANSACTION UPDATE ATTACH DETACH "
    "ALTER_TABLE REINDEX ANALYZE CREATE_VTABLE DROP_VTABLE FUNCTION SAVEPOINT RECURSIVE").split()}


class ReadOnlyDB:
    """A connection the model's SQL runs through.

    mode=ro blocks writes to the database file, but still allows e.g. CREATE TEMP TABLE, so a deny-by-default
    authorizer additionally limits statements to SELECT over the three allowed tables.
    """

    def __init__(self, path: Path):
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self._denied = []
        self.conn.set_authorizer(self._authorize)

    def _authorize(self, action, arg1, arg2, db_name, trigger):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and arg1 in ALLOWED_TABLES:
            return sqlite3.SQLITE_OK
        what = arg1 if action == sqlite3.SQLITE_READ else " ".join(a for a in (arg1, arg2) if a)
        self._denied.append(f"{_ACTION_NAMES.get(action, action)} {what}".strip())
        return sqlite3.SQLITE_DENY

    def query(self, sql: str) -> dict:
        """Run one statement. Never raises for SQL problems; the status says what happened."""
        result = {"status": "ok", "columns": [], "rows": [], "truncated": False, "error": None}
        self._denied.clear()
        deadline = time.monotonic() + QUERY_TIMEOUT_S
        self.conn.set_progress_handler(lambda: time.monotonic() > deadline, PROGRESS_STEPS)
        try:
            cur = self.conn.execute(sql)
            if cur.description is None:
                return {**result, "status": "error", "error": "statement returned no result set"}
            rows = cur.fetchmany(MAX_ROWS + 1)
        except sqlite3.Error as e:
            if self._denied:
                return {**result, "status": "rejected",
                        "error": f"not allowed: {', '.join(dict.fromkeys(self._denied))}. Only SELECT over "
                                 f"{', '.join(sorted(ALLOWED_TABLES))} is permitted."}
            if str(e) == "interrupted":
                return {**result, "status": "timeout", "error": f"query exceeded {QUERY_TIMEOUT_S} s"}
            return {**result, "status": "error", "error": str(e)}
        finally:
            self.conn.set_progress_handler(None, 0)
        result["columns"] = [d[0] for d in cur.description]
        result["rows"] = [list(r) for r in rows[:MAX_ROWS]]
        result["truncated"] = len(rows) > MAX_ROWS
        if not rows:
            result["status"] = "empty"
        return result


def open_database(path: Path) -> ReadOnlyDB:
    """Open the database read-only and refuse to continue if the data breaks the domain rules."""
    db = ReadOnlyDB(path)
    validate_data(db.conn)
    return db

# Each check is a query returning offending IDs. SQLite does not enforce REFERENCES unless
# foreign_keys is on, so relationships are checked explicitly.
CHECKS = {
    "order references a missing customer":
        "SELECT order_id FROM orders WHERE customer_id NOT IN (SELECT customer_id FROM customers)",
    "refund references a missing order":
        "SELECT refund_id FROM refunds WHERE order_id NOT IN (SELECT order_id FROM orders)",
    "order amount is not non-negative integer cents":
        "SELECT order_id FROM orders WHERE typeof(amount_cents) != 'integer' OR amount_cents < 0",
    "refund amount is not non-negative integer cents":
        "SELECT refund_id FROM refunds WHERE typeof(amount_cents) != 'integer' OR amount_cents < 0",
    "refunds for an order exceed its amount":
        "SELECT o.order_id FROM orders o JOIN (SELECT order_id, SUM(amount_cents) AS refunded"
        " FROM refunds GROUP BY order_id) r ON r.order_id = o.order_id WHERE r.refunded > o.amount_cents",
    # date() normalises or rejects anything that is not a real YYYY-MM-DD date.
    "order_date is not a valid YYYY-MM-DD date":
        "SELECT order_id FROM orders WHERE date(order_date) IS NOT order_date",
    "refund_date is not a valid YYYY-MM-DD date":
        "SELECT refund_id FROM refunds WHERE date(refund_date) IS NOT refund_date",
}


class DataValidationError(Exception):
    pass


def validate_data(conn: sqlite3.Connection) -> None:
    """Raise DataValidationError naming every failing check and its offending IDs."""
    problems = []
    for name, sql in CHECKS.items():
        ids = [row[0] for row in conn.execute(sql)]
        if ids:
            problems.append(f"{name}: {', '.join(map(str, ids))}")
    if problems:
        raise DataValidationError("; ".join(problems))
