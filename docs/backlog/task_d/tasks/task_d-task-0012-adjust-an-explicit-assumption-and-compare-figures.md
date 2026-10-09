- ID: task_d-task-0012
- Title: Adjust an explicit assumption and compare figures
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
Optional enhancement from the brief: let the user adjust an explicit assumption and compare the resulting figures.

## What to build
- One adjustable assumption (e.g. period boundaries) with the resulting gross / refunds / net shown side by side
  with the original.
- Depends on: task_d-task-0005. Only after the P0/P1 tickets are done.

## Threats and risks
- Changing an assumption could be mistaken for changing a domain rule. Mitigation: only assumptions listed in the
  investigation are adjustable; domain rules stay fixed.

## Done when
- Changing the assumption updates the compared figures, verified against the plain-Python calculator.

## Acceptance criteria
- Original and adjusted figures are both shown with their assumptions stated.
- Domain rules (half-open periods, cents, refund-by-refund_date) cannot be changed.
