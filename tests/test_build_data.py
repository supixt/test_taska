import json
import shutil
import sqlite3

import pytest

from app.db import DataValidationError, validate_data
from scripts.build_data import DATA_DIR, TASK_DIR, build, period_totals


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    return out, build(out)


def test_calculator_reproduces_seed_expected_results():
    seed = json.loads((TASK_DIR / "seed.json").read_text())
    expected = json.loads((TASK_DIR / "expected-seed-results.json").read_text())
    for p in expected["periods"]:
        assert period_totals(seed, p["start"], p["end_exclusive"]) == {
            k: p[k] for k in ("gross_cents", "refunds_cents", "net_cents")}
    for segment, totals in expected["september_segments"].items():
        assert period_totals(seed, "2026-09-01", "2026-10-01", segment=segment) == totals


def test_build_is_byte_identical(built, tmp_path):
    out, _ = built
    build(tmp_path)
    for name in ("sales.sqlite", "sales.json", "reference-cases.json"):
        assert (tmp_path / name).read_bytes() == (out / name).read_bytes(), name


def test_committed_data_is_current(built):
    out, _ = built
    for name in ("sales.sqlite", "sales.json", "reference-cases.json"):
        assert (DATA_DIR / name).read_bytes() == (out / name).read_bytes(), f"rerun build_data: {name}"


def test_seed_rows_preserved(built):
    out, _ = built
    seed = json.loads((TASK_DIR / "seed.json").read_text())
    conn = sqlite3.connect(out / "sales.sqlite")
    for table, key in (("customers", "customer_id"), ("orders", "order_id"), ("refunds", "refund_id")):
        conn.row_factory = sqlite3.Row
        rows = {r[key]: dict(r) for r in conn.execute(f"SELECT * FROM {table}")}
        for row in seed[table]:
            assert rows[row[key]] == row


def test_dataset_covers_required_cases(built):
    _, data = built
    order_of = {o["order_id"]: o for o in data["orders"]}
    assert {c["segment"] for c in data["customers"]} == {"small", "medium", "large"}
    assert any(order_of[r["order_id"]]["order_date"][:7] != r["refund_date"][:7] for r in data["refunds"])
    assert sum(r["order_id"] == "O3" for r in data["refunds"]) == 2
    aug = period_totals(data, "2026-08-01", "2026-09-01")
    sep = period_totals(data, "2026-09-01", "2026-10-01")
    assert aug["gross_cents"] == sep["gross_cents"] and sep["net_cents"] < aug["net_cents"]


def test_reference_cases_has_five_cases(built):
    out, _ = built
    cases = json.loads((out / "reference-cases.json").read_text())["cases"]
    assert [c["id"] for c in cases] == ["RC1", "RC2", "RC3", "RC4", "RC5"]


@pytest.fixture
def seed_copy(tmp_path):
    path = tmp_path / "seed.sqlite"
    shutil.copy(TASK_DIR / "seed.sqlite", path)
    conn = sqlite3.connect(path)
    yield conn
    conn.close()


def test_validation_passes_on_seed(seed_copy):
    validate_data(seed_copy)


@pytest.mark.parametrize("sql, check", [
    ("INSERT INTO refunds VALUES ('RFX', 'O99', '2026-09-01', 100)", "refund references a missing order"),
    ("INSERT INTO refunds VALUES ('RFX', 'O1', '2026-09-01', 4500)", "refunds for an order exceed its amount"),
    ("INSERT INTO orders VALUES ('OX', 'C9', '2026-09-01', 100)", "order references a missing customer"),
    ("INSERT INTO orders VALUES ('OX', 'C1', '2026-09-01', 10.5)", "order amount is not non-negative integer"),
    ("INSERT INTO refunds VALUES ('RFX', 'O1', '2026-9-1', 100)", "refund_date is not a valid YYYY-MM-DD date"),
])
def test_validation_names_failing_check(seed_copy, sql, check):
    seed_copy.execute(sql)
    with pytest.raises(DataValidationError, match=check):
        validate_data(seed_copy)
