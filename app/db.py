"""Database access for the investigator: data validation (D10)."""
import sqlite3

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
