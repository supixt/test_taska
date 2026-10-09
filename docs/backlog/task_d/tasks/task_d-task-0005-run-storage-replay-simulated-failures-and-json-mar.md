- ID: task_d-task-0005
- Title: Run storage, replay, simulated failures and JSON/Markdown reports
- Type: task
- Status: todo
- Priority: P1
- Assignee: -
- Domain: implementation
- Parent: -
- Branch: -
- Created: 09-10-2026 11:51
- Closed: -
- Updated: 09-10-2026 12:01
- Work log: -
- Comments:
  - [09-10-2026 12:01] supixt: Decision change (D6, docs/decisions.md f008f54): replay uses the replay message source instead of LangChain's fake chat model; it returns saved AIMessages from runs/<id>.json in order and fails clearly if they run out or the conversation diverges. SQL still runs live and results are compared with the saved ones. The fake-chat-model wording in 'What to build' is superseded by this comment. (via /comment)

## Business background
Another person must be able to reproduce a finding, and reviewers must replay real model responses without an
API key. Runs must be labelled so cached and simulated responses are distinguishable. Decisions: D5, D6.

## What to build
- `app/store.py`: one JSON file per investigation in `runs/` with question and follow-ups, definitions,
  assumptions, prompt and model config, raw model responses, every query attempt with result or error, final
  answers, check results, and `mode` (`live` / `replay` / `simulated`) and status.
- Replay: feed saved model responses in order to LangChain's fake chat model, run the SQL live, compare each
  result with the saved one, and record any difference.
- Simulated failures: `--simulate <kind>` (at least an API error) produces a run labelled `simulated`.
- `app/report.py`: render the Markdown report from the JSON (question, definitions, assumptions, periods, each
  query with SQL and result or explicit empty / error status, explanation split into observed facts / not
  established / assumptions, check results, labels).
- `app/__main__.py`: `python -m app investigate "<question>"`, `python -m app replay <run.json>`,
  `--simulate <kind>`.
- Tests in `tests/test_store_report.py`.
- Depends on: task_d-task-0003, task_d-task-0004.

## Threats and risks
- Serialising LangChain messages may lose tool-call details. Mitigation: round-trip test with
  `messages_to_dict` / `messages_from_dict` on a message with tool calls.
- Replay could silently pass if SQL results drift. Mitigation: any difference marks the replay as diverged.

## Done when
- `.venv/bin/python -m pytest tests/test_store_report.py` passes.
- `python -m app replay <saved run>` works with no `DEEPSEEK_API_KEY` set.

## Acceptance criteria
- A saved run replays without a key and reports identical query results.
- Altering the database before replay marks the replay as diverged.
- `--simulate api_error` produces an `incomplete` run labelled `simulated`.
- The Markdown report contains every section listed above, and an empty result is shown with its own status.
