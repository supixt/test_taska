- ID: task_d-task-0007
- Title: Record real runs and minimum-demonstration check report
- Type: task
- Status: todo
- Priority: P1
- Assignee: -
- Domain: implementation
- Parent: -
- Branch: -
- Created: 09-10-2026 11:51
- Closed: -
- Updated: 09-10-2026 11:51
- Work log: -
- Comments: -

## Business background
The submission must include saved responses from real model calls and a results table for the five
minimum-demonstration checks, with expected and observed values and any unresolved failures. Decision: D11.

## What to build
- Run real DeepSeek investigations on `data/sales.sqlite` (main Aug -> Sep question plus a segment follow-up,
  and runs needed for the other checks); commit the runs in `runs/`.
- `tests/test_demonstration.py`: the five checks run in replay against the saved runs and
  `data/reference-cases.json`:
  1. main investigation totals match the verified gross / refunds / net;
  2. the multi-refund order is not counted twice in gross;
  3. the follow-up breakdown is consistent with the totals and includes its queries, results, assumptions;
  4. a write attempt is rejected with the DB unchanged, and a failed query counts toward the limit;
  5. the saved report reproduces the refund discrepancy and keeps the refund cause under "not established".
- A script that writes `docs/check-results.md` (check, expected, observed, pass/fail, notes on failures).
- One live test marked `live`, skipped when `DEEPSEEK_API_KEY` is not set.
- Depends on: task_d-task-0001, task_d-task-0006.

## Threats and risks
- The real model may fail a check. Mitigation: report the failure honestly in `docs/check-results.md`; never
  edit expected values or tests to pass.
- Requires the DeepSeek key from the user. Mitigation: ask before starting the live runs.

## Done when
- `.venv/bin/python -m pytest` passes (live test skipped without a key), or remaining failures are explained.
- `docs/check-results.md` is generated from the saved runs and committed.

## Acceptance criteria
- All saved runs are labelled `live` and replay without a key.
- Each of the five checks shows expected vs observed values traced to `data/reference-cases.json`.
- Any failure is listed with its cause and why it was not fixed.
