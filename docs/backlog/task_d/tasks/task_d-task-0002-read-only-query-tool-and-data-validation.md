- ID: task_d-task-0002
- Title: Read-only query tool and data validation
- Type: task
- Status: in-progress
- Priority: P0
- Assignee: supixt
- Domain: implementation
- Parent: -
- Branch: task_d-task-0002
- Created: 09-10-2026 11:51
- Closed: -
- Updated: 09-10-2026 12:32
- Work log:
  - work started [1]: 09-10-2026 12:30
- Comments:
  - [09-10-2026 12:32] supixt: LLM-usage candidate: (1) the first timeout test passed vacuously because SQLite counts a 16M-row cross join in 0.1 s; caught by a failing assertion, fixed with a 4^16-row query and an explicit timeout assertion. (2) A manual run on data/sales.sqlite showed a DELETE rejection labelled LIMIT_VARIABLE_NUMBER: the action-name map took all SQLITE_* constants, which reuse numbers; fixed with an explicit action list and a test that checks the named action. (via /comment)

## Business background
The model must only read the three local tables. The brief requires read-only enforcement through database or
tool permissions, query time and result-size limits, and clear errors. Decisions: D4, D10, empty-result status.

## What to build
- `app/db.py`:
  - Open the database with SQLite `mode=ro` URI.
  - `set_authorizer`: allow only SELECT and reads of `customers`, `orders`, `refunds` (plus SQL functions);
    deny writes, PRAGMA, ATTACH, `sqlite_master`, and anything else.
  - `set_progress_handler` enforcing a per-query deadline; fetch at most limit + 1 rows to flag truncation.
  - Configurable constants: `QUERY_TIMEOUT_S = 2`, `MAX_ROWS = 200`.
  - Query result: `status` (`ok` / `empty` / `error` / `timeout` / `rejected`), `columns`, `rows`, `truncated`,
    `error` message. `empty` is an explicit status, not just zero rows.
  - Start-up data validation (same checks as D10); failures raise an error naming the failing check.
- Tests in `tests/test_db.py`.
- Depends on: none (tests can use `tasks/data/seed.sqlite`).

## Threats and risks
- SQLite has no native statement timeout. Mitigation: progress-handler deadline, tested with a slow cross join.
- Authorizer gaps (e.g. CTEs, `sqlite_master` reads, temp tables). Mitigation: explicit tests for each and a
  deny-by-default authorizer.

## Done when
- `.venv/bin/python -m pytest tests/test_db.py` passes.

## Acceptance criteria
- INSERT / UPDATE / DELETE / DROP / CREATE are rejected, and the database file hash is unchanged afterwards.
- PRAGMA, ATTACH, and reads of `sqlite_master` or any non-allowed table are rejected with a clear error.
- A slow query stops at the deadline with status `timeout`.
- A query returning more than `MAX_ROWS` rows returns `MAX_ROWS` rows with `truncated = true`.
- Malformed SQL returns status `error` with the SQLite message; no exception escapes.
- A valid query with no rows returns status `empty`.
- Start-up validation passes on `seed.sqlite` and fails with a named check on a broken copy.
