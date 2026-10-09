- ID: task_d-task-0010
- Title: Reusable report with selectable period
- Type: task
- Status: todo
- Priority: P3
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
Optional enhancement from the brief: save a useful investigation as a reusable report with a selectable period.

## What to build
- Rerun a saved investigation's executed queries with new period parameters (no model call), and produce a new
  labelled report.
- Depends on: task_d-task-0005. Only after the P0/P1 tickets are done.

## Threats and risks
- Model-written SQL may hardcode dates in ways that are hard to parametrise. Mitigation: parametrise only the
  period-bound queries the model labels as such; others are reported as not reusable.

## Done when
- A saved Aug -> Sep investigation reruns for Jul -> Aug and the totals match the plain-Python calculator.

## Acceptance criteria
- The rerun report states its new periods and that no model call was made.
- Control totals and breakdown checks pass on the rerun.
