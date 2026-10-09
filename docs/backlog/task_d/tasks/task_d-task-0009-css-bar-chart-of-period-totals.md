- ID: task_d-task-0009
- Title: CSS-bar chart of period totals
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
Optional enhancement: a simple visual makes the net-sales change easier to read than the table alone. Decision:
D8 (chart deferred to P3).

## What to build
- CSS-only bars on the investigation page for gross / refunds / net per period, drawn from the same figures as
  the table. No chart library, no new dependency.
- Depends on: task_d-task-0006. Only after the P0/P1 tickets are done.

## Threats and risks
- Bars diverging from the table. Mitigation: render both from the same data object.

## Done when
- The bars render for a replayed run and match the figures table.

## Acceptance criteria
- Bar values equal the table values for every period.
- No new dependency in `requirements.txt` and no external script.
