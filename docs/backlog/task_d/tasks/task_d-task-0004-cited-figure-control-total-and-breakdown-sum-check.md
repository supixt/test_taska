- ID: task_d-task-0004
- Title: Cited-figure, control-total and breakdown-sum checks
- Type: task
- Status: todo
- Priority: P0
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
Reported figures must be connected to executed results, and a follow-up breakdown must stay consistent with the
totals (acceptance criterion 3). These are code checks, not prompt instructions. Decision: D3.

## What to build
- In `app/investigate.py` (or a small module next to it), after a final answer:
  - Cited-cell check: every figure cites a query attempt, row, and column; the value must equal that logged cell.
  - Control totals: fixed, known-correct SQL for gross / refunds / net for each period in the answer, run by the
    app (not counted in the model's budget). Any reported period total that disagrees is flagged.
  - Breakdown sums: every breakdown (e.g. by segment) must sum exactly to the control totals for the same period;
    any mismatch is flagged.
- Check results stored on the investigation (pass / fail with details) for the UI and report.
- Tests in `tests/test_checks.py`.
- Depends on: task_d-task-0003.

## Threats and risks
- Control SQL itself could be wrong. Mitigation: tested against the seed expected results and reference cases.
- A breakdown the model labels poorly may not map to a period. Mitigation: the answer schema requires a period
  per breakdown; a breakdown without one is flagged, not skipped.

## Done when
- `.venv/bin/python -m pytest tests/test_checks.py` passes.

## Acceptance criteria
- A figure whose cited cell differs from the reported value is flagged.
- A figure citing a non-existent attempt, row, or column is flagged.
- Control totals for Aug and Sep 2026 on the seed equal `expected-seed-results.json`.
- A segment breakdown built from a raw refunds-to-orders join (O3 gross counted twice) is flagged as not summing
  to the control totals.
- A correct segment breakdown passes.
