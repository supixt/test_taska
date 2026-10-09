"""Build the extended investigation dataset and its reference cases (D9, D10).

    .venv/bin/python -m scripts.build_data

Loads tasks/data/seed.json, adds deterministic rows (random.Random(42)), validates the result, and writes:
  data/sales.sqlite          the database the application queries
  data/sales.json            the same rows as a readable snapshot
  data/reference-cases.json  five reference cases; expected values computed in plain Python below,
                             deliberately without SQL or application code
"""
import json
import os
import random
import sqlite3
import sys
from pathlib import Path

from app.db import DataValidationError, validate_data

ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = ROOT / "tasks" / "data"
DATA_DIR = ROOT / "data"
SEED = 42

AUG = ("2026-08-01", "2026-09-01")
SEP = ("2026-09-01", "2026-10-01")


def generate():
    """Return {customers, orders, refunds}: the seed rows unchanged plus generated rows."""
    data = json.loads((TASK_DIR / "seed.json").read_text())
    rng = random.Random(SEED)

    # Cycling segments guarantees the third segment exists regardless of the random draws.
    segments = ["medium", "small", "large"]
    for i in range(3, 11):
        data["customers"].append({"customer_id": f"C{i}", "segment": segments[(i - 3) % 3]})
    customer_ids = [c["customer_id"] for c in data["customers"]]

    def add_order(month, day, amount):
        order = {"order_id": f"O{len(data['orders']) + 1}", "customer_id": rng.choice(customer_ids),
                 "order_date": f"2026-{month:02d}-{day:02d}", "amount_cents": amount}
        data["orders"].append(order)
        return order

    july = [add_order(7, rng.randint(1, 31), rng.randrange(1000, 10001, 500)) for _ in range(8)]
    august = [add_order(8, rng.randint(1, 31), rng.randrange(1000, 10001, 500)) for _ in range(9)]
    # Each September order mirrors an August amount so gross sales stay equal across the two months,
    # keeping the seed's story: the net-sales change is driven by refunds. The first one sits on the
    # period boundary to exercise the half-open rule.
    september = [add_order(9, 1 if i == 0 else rng.randint(1, 30), a["amount_cents"])
                 for i, a in enumerate(august)]

    def add_refund(order, month, last_day, day=None):
        order_month, order_day = int(order["order_date"][5:7]), int(order["order_date"][8:])
        if day is None:
            day = rng.randint(order_day if order_month == month else 1, last_day)
        data["refunds"].append({
            "refund_id": f"RF{len(data['refunds']) + 1}", "order_id": order["order_id"],
            "refund_date": f"2026-{month:02d}-{day:02d}",
            "amount_cents": rng.randrange(500, order["amount_cents"] // 2 + 1, 100)})

    aug_targets = rng.sample(august, 2)
    sep_targets = rng.sample(september, 2)
    add_refund(rng.choice(july), 7, 31)
    add_refund(aug_targets[0], 8, 31, day=31)  # last day of August: must stay in August
    add_refund(aug_targets[1], 9, 30)          # August order refunded in September (cross-month)
    for order in sep_targets:
        add_refund(order, 9, 30)
    return data


def period_totals(data, start, end, segment=None):
    """Gross by order_date, refunds by refund_date, half-open [start, end); refunds take the segment of
    the customer on the original order (domain.md rules 2-4)."""
    segment_of = {c["customer_id"]: c["segment"] for c in data["customers"]}
    order_segment = {o["order_id"]: segment_of[o["customer_id"]] for o in data["orders"]}
    gross = sum(o["amount_cents"] for o in data["orders"]
                if start <= o["order_date"] < end and segment in (None, order_segment[o["order_id"]]))
    refunds = sum(r["amount_cents"] for r in data["refunds"]
                  if start <= r["refund_date"] < end and segment in (None, order_segment[r["order_id"]]))
    return {"gross_cents": gross, "refunds_cents": refunds, "net_cents": gross - refunds}


def faulty_join_gross(data, start, end):
    """Gross as a raw orders LEFT JOIN refunds would sum it: each order counted once per refund row."""
    refund_rows = {}
    for r in data["refunds"]:
        refund_rows[r["order_id"]] = refund_rows.get(r["order_id"], 0) + 1
    return sum(o["amount_cents"] * max(1, refund_rows.get(o["order_id"], 0))
               for o in data["orders"] if start <= o["order_date"] < end)


def ids_in(rows, key, date_key, start, end):
    return [r[key] for r in rows if start <= r[date_key] < end]


def reference_cases(data):
    aug, sep = period_totals(data, *AUG), period_totals(data, *SEP)
    segments = sorted({c["segment"] for c in data["customers"]})
    multi = sorted(o for o in {r["order_id"] for r in data["refunds"]}
                   if sum(r["order_id"] == o for r in data["refunds"]) > 1)
    period = lambda p: {"start": p[0], "end_exclusive": p[1]}
    return {
        "generated_by": "scripts/build_data.py (plain-Python calculator; no SQL, no application code)",
        "dataset": "data/sales.sqlite",
        "units": "integer USD cents",
        "periods": "UTC dates, half-open: start included, end excluded",
        "cases": [
            {"id": "RC1", "check": "Main investigation totals match the verified gross, refund and net totals",
             "rule": "domain.md rules 2-3",
             "input": {"periods": [period(AUG), period(SEP)]},
             "expected": {"august": aug, "september": sep,
                          "net_change_cents": sep["net_cents"] - aug["net_cents"]},
             "supporting_ids": {"orders": ids_in(data["orders"], "order_id", "order_date", AUG[0], SEP[1]),
                                "refunds": ids_in(data["refunds"], "refund_id", "refund_date", AUG[0], SEP[1])}},
            {"id": "RC2", "check": "An order with multiple refunds is counted once in gross sales",
             "rule": "domain.md rule 3",
             "input": {"period": period(SEP), "orders_with_multiple_refunds": multi},
             "expected": {"gross_cents": sep["gross_cents"],
                          "faulty_left_join_gross_cents": faulty_join_gross(data, *SEP)},
             "supporting_ids": {"orders": ids_in(data["orders"], "order_id", "order_date", *SEP),
                                "refunds": [r["refund_id"] for r in data["refunds"] if r["order_id"] in multi]}},
            {"id": "RC3", "check": "Segment breakdown sums to the period totals",
             "rule": "domain.md rules 2-4 (refund takes the segment of the original order's customer)",
             "input": {"period": period(SEP), "breakdown": "segment"},
             "expected": {"segments": {s: period_totals(data, *SEP, segment=s) for s in segments},
                          "total": sep},
             "supporting_ids": {"orders": ids_in(data["orders"], "order_id", "order_date", *SEP),
                                "refunds": ids_in(data["refunds"], "refund_id", "refund_date", *SEP)}},
            {"id": "RC4", "check": "A write attempt is rejected without changing the database, and a failed "
                                   "query counts toward the execution limit",
             "rule": "brief, Technical Implementation (read-only tool, six attempts per investigation)",
             "input": {"queries": ["DELETE FROM refunds", "SELECT FROM orders"]},
             "expected": {"statuses": ["rejected", "error"], "database_unchanged": True,
                          "attempts_used": 2}},
            {"id": "RC5", "check": "Saved report reproduces the refund discrepancy without explaining "
                                   "customer behaviour",
             "rule": "domain.md rule 4 (records show amounts and dates, not refund reasons)",
             "input": {"question": "Why did net sales change from August to September 2026?"},
             "expected": {"gross_change_cents": sep["gross_cents"] - aug["gross_cents"],
                          "refunds_change_cents": sep["refunds_cents"] - aug["refunds_cents"],
                          "net_change_cents": sep["net_cents"] - aug["net_cents"],
                          "not_established": "why customers requested refunds"}},
        ],
    }


def check_story(data):
    """Generation must keep the seed's story; fail the build instead of silently changing it."""
    aug, sep = period_totals(data, *AUG), period_totals(data, *SEP)
    order_month = {o["order_id"]: o["order_date"][:7] for o in data["orders"]}
    refund_counts = [sum(r["order_id"] == o["order_id"] for r in data["refunds"]) for o in data["orders"]]
    required = {
        "August and September gross are equal": aug["gross_cents"] == sep["gross_cents"],
        "September refunds exceed August refunds": sep["refunds_cents"] > aug["refunds_cents"],
        "September net falls": sep["net_cents"] < aug["net_cents"],
        "three segments exist": {"small", "medium", "large"} <= {c["segment"] for c in data["customers"]},
        "a cross-month refund exists":
            any(order_month[r["order_id"]] != r["refund_date"][:7] for r in data["refunds"]),
        "an order has multiple refunds": max(refund_counts) > 1,
    }
    missing = [name for name, ok in required.items() if not ok]
    if missing:
        raise ValueError(f"generated data breaks the seed story: {', '.join(missing)}")


def write_db(data, path):
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.executescript((TASK_DIR / "schema.sql").read_text())
        for table, key_order in (("customers", ("customer_id", "segment")),
                                 ("orders", ("order_id", "customer_id", "order_date", "amount_cents")),
                                 ("refunds", ("refund_id", "order_id", "refund_date", "amount_cents"))):
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(key_order))})",
                             [tuple(row[k] for k in key_order) for row in data[table]])
        conn.commit()
        validate_data(conn)
    finally:
        conn.close()


def build(out_dir=DATA_DIR):
    data = generate()
    check_story(data)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "sales.sqlite.tmp"
    try:
        write_db(data, tmp)
    except DataValidationError:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, out_dir / "sales.sqlite")
    (out_dir / "sales.json").write_text(json.dumps(data, indent=2) + "\n")
    (out_dir / "reference-cases.json").write_text(json.dumps(reference_cases(data), indent=2) + "\n")
    return data


if __name__ == "__main__":
    try:
        built = build()
    except DataValidationError as e:
        sys.exit(f"data validation failed: {e}")
    print(f"wrote {DATA_DIR.relative_to(ROOT)}/: {len(built['customers'])} customers, "
          f"{len(built['orders'])} orders, {len(built['refunds'])} refunds")
