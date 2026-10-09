- ID: task_d-task-0001
- Title: Build extended dataset and five reference cases
- Type: task
- Status: done
- Priority: P0
- Assignee: supixt
- Domain: implementation
- Parent: -
- Branch: task_d-task-0001
- Created: 09-10-2026 11:51
- Closed: 09-10-2026 12:05
- Updated: 09-10-2026 12:05
- Work log:
  - work started [1]: 09-10-2026 12:01
  - work finished [1]: 09-10-2026 12:05
- Comments: -

## Business background
The investigator needs a dataset large enough for a useful period and segment breakdown, plus independently
verified expected results. The brief requires five checked reference cases whose expected values never come from
the application. Decisions: D9, D10 (docs/decisions.md).

## What to build
- `scripts/build_data.py`: loads `tasks/data/seed.json`, adds rows with `random.Random(42)` (~10 customers,
  ~30 orders, ~8 refunds), writes `data/sales.sqlite` using `tasks/data/schema.sql`. `tasks/data/seed.sqlite`
  stays untouched.
- Data content: all seed IDs and relationships kept; a third segment `medium`; orders July–September 2026; the
  refund-driven net-sales drop (Aug -> Sep) kept; order O3 with two refunds kept; a September refund on an
  August order (cross-month).
- Build-time validation (D10): referential integrity, non-negative integer cents, refunds per order not above
  the order amount, `YYYY-MM-DD` dates. The build fails and names the failing check.
- `data/reference-cases.json`: five cases covering the minimum-demonstration checks (period totals, multi-refund
  order counted once, segment breakdown sums, write rejection, refund discrepancy without a cause). Expected
  totals computed with plain Python loops over the rows (no SQL, no app code), each linked to its input rows
  and the domain rule that determines it. Seed expectations from `expected-seed-results.json` reproduced.
- `data/README.md`: generation method, random seed, row counts, and any ambiguity found in the rules.
- Depends on: none.

## Threats and risks
- Generated rows could change the meaning of the seed story (e.g. hide the refund increase). Mitigation: assert
  in the build script that Sep net < Aug net and that Aug/Sep gross stay similar.
- Expected values computed with the same logic as the app would hide bugs. Mitigation: plain-Python computation
  only, plus a manual check of each case recorded in `data/README.md`.

## Done when
- `.venv/bin/python scripts/build_data.py` run twice produces byte-identical `data/sales.sqlite`.
- `data/reference-cases.json` holds five cases, each checked by hand (noted in `data/README.md`).
- A pytest test confirms the seed totals in `expected-seed-results.json` are reproduced by the plain-Python
  calculator on the seed rows.

## Acceptance criteria
- All seed customers, orders, and refunds exist unchanged in `data/sales.sqlite`.
- Validation rejects a deliberately broken fixture (orphan refund, over-refund) with a named error.
- The dataset contains: three segments, a cross-month refund, an order with two or more refunds, and a
  September net-sales drop driven by refunds.
