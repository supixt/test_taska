- ID: task_d-task-0011
- Title: Before/after comparison of a faulty join
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
Optional enhancement from the brief: a visual comparison of results before and after correcting a faulty join.

## What to build
- Show gross sales computed with a raw refunds-to-orders join (O3 counted twice) next to the correct grouped
  calculation, with the difference highlighted.
- Depends on: task_d-task-0004. Only after the P0/P1 tickets are done.

## Threats and risks
- Users may mistake the faulty figure for a real one. Mitigation: label it clearly as the incorrect method.

## Done when
- The comparison renders for September 2026 and the difference equals O3's amount times its extra refund rows.

## Acceptance criteria
- Both figures come from executed queries, with the SQL inspectable.
- The faulty figure is clearly labelled as incorrect.
