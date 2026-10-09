- ID: task_d-task-0006
- Title: Investigation web page
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
Users need one page to ask what changed, inspect the supporting SQL and results, ask a follow-up, and export
the investigation. Decision: D8.

## What to build
- `app/main.py` (FastAPI): serve `app/static/index.html`; endpoints to start an investigation, ask a follow-up,
  fetch a run, and download its JSON and Markdown. Data validation runs at start-up (refuses to start on failure).
- `app/static/index.html` (plain HTML/JS): question input; status banner (complete / incomplete / limit reached;
  live / replay / simulated); explanation split into observed facts / not established / assumptions; figures
  table with query links and control-total check marks; collapsible query attempts (SQL, status, result table or
  error, explicit empty status); follow-up input; JSON and Markdown download buttons. Table only, no chart.
- Tests in `tests/test_api.py` using FastAPI's test client and a fake model.
- Depends on: task_d-task-0005.

## Threats and risks
- A synchronous request may take tens of seconds. Mitigation: a visible "running" state; the 60 s model timeout
  bounds each call.
- Rendering model text as HTML could inject markup. Mitigation: insert text with `textContent`, never `innerHTML`.

## Done when
- `.venv/bin/python -m pytest tests/test_api.py` passes.
- `.venv/bin/uvicorn app.main:app` serves the page and a replayed or live investigation renders fully in the browser.

## Acceptance criteria
- A question and a follow-up both render, and the follow-up shows the shared remaining query budget.
- Every executed SQL statement and its result table (or error / empty status) is inspectable.
- An API failure and a limit-reached run each show a clear banner.
- The downloaded JSON and Markdown match the stored run.
