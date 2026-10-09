# Agreed design decisions — Task D (Business Data Investigator)

Agreed before implementation. Any change to a decision below must be agreed first and recorded here.

## Scope and inputs

- **Model**: LangChain `ChatDeepSeek`, model `deepseek-chat`; key in `.env` as `DEEPSEEK_API_KEY`. Model and
  parameters are recorded in `ai-workflow/manifest.json`.
- **Stack**: Python 3.12 + FastAPI serving one plain HTML/JS page; built-in `sqlite3`. No new dependencies.
- **Periods**: the model takes the periods from the user's question.
- **Segments**: the customer's current segment is used (no segment history exists); documented as a limitation.
- **Repository**: this folder is the submission repo. The hiring-team HTML and starter-pack ZIP are gitignored
  reference material, never committed.
- **Environment names**: only the root `.env.example` (`DEEPSEEK_API_KEY`); the manifest points to it.

## Design decisions

- **D1 Module structure**: flat package — `app/db.py` (read-only connection, query tool, data validation),
  `app/investigate.py` (model loop, budget), `app/store.py` (run persistence, replay), `app/report.py`
  (JSON/Markdown export), `app/main.py` (FastAPI), `app/static/index.html`, `app/prompts/system.md`;
  plus `scripts/build_data.py` and `tests/`.
- **D2 Query loop**: LangChain tool calling with a single `run_sql` tool, driven by our own loop that owns the
  attempt counter, the query log, and the stop rule.
- **D3 Grounding checks (code, not prompt)**: the final answer is structured; every reported figure cites a
  query attempt, row, and column, and code verifies it equals that logged cell. The app also runs fixed control
  SQL for gross / refunds / net over the model's periods and flags any disagreement. Every follow-up breakdown
  (e.g. by segment) must sum exactly to the control totals for the same period; any mismatch is flagged
  (acceptance criterion 3).
- **D4 Query-tool safety**: SQLite opened with `mode=ro`; `set_authorizer` allows only SELECT and reads of
  `customers`, `orders`, `refunds` (denies writes, PRAGMA, ATTACH, `sqlite_master`); `set_progress_handler`
  enforces the per-query deadline; at most 201 rows are fetched to detect and flag truncation.
- **D5 Storage and report**: one JSON file per investigation in `runs/` (question and follow-ups, definitions,
  assumptions, prompt and model config, raw model responses, every query attempt with result or error, final
  answers, check results). That file is the JSON export; the Markdown report is rendered from it.
- **D6 Replay**: replay feeds saved model responses, in order, to LangChain's fake chat model and runs the SQL
  live, comparing results with the saved ones. Every run is labelled `live`, `replay`, or `simulated`; a
  `--simulate` flag produces labelled failures.
- **D7 Prompt**: `app/prompts/system.md` includes `domain.md` and `schema.sql` verbatim at runtime, the tool
  rules and limits, the analysis rules (half-open UTC periods, cents, aggregate orders and refunds separately,
  at least one follow-up, no inferred refund reasons, list missing evidence), and the final-answer schema
  (validated with pydantic). Temperature 0, `max_tokens` 2000. Follow-ups continue the same conversation.
- **D8 UI**: one page — question input; status banner (complete / incomplete / limit reached; live / replay /
  simulated); explanation split into observed facts / not established / assumptions; figures table with
  query links and control-total checks; collapsible query attempts (SQL, status, result or error); follow-up
  input; JSON and Markdown download. Table only for the core; a CSS-bar chart is a P3 ticket.
- **D9 Extended data**: `scripts/build_data.py` loads `seed.json` and adds rows with `random.Random(42)` (~10
  customers, ~30 orders, ~8 refunds; third segment `medium`; July–September; a September refund on an August
  order). Seed rows and the refund-driven net-sales drop are kept. Output is `data/sales.sqlite`; `seed.sqlite`
  is untouched. Expected values for `data/reference-cases.json` are computed with plain Python over the rows
  (not SQL, not the app) and checked by hand.
- **D10 Data validation**: the build script and app start-up check referential integrity, non-negative integer
  cents, refunds per order not above the order amount, and `YYYY-MM-DD` dates. The app refuses to start and
  names the failing check.
- **D11 Tests**: unit tests for the query tool (write rejected with unchanged DB hash; PRAGMA / ATTACH / other
  tables rejected; timeout; row cap; malformed SQL); loop tests with a scripted fake model (shared budget,
  failed query counts, visible API failure, wrong cited figure caught); the five minimum-demonstration checks
  run against saved real responses in replay, with a script writing `docs/check-results.md`; one live DeepSeek
  test marked `live`, skipped without a key.

## Limits and failure handling

- **Query budget**: 6 query attempts per investigation (question plus all follow-ups), failed queries included.
- **Query limits**: 2-second timeout per query and at most 200 returned rows; configurable constants,
  documented in the README.
- **Model call**: 60-second request timeout and `max_retries=0` (the client's default would retry silently).
  Any API failure is shown on screen and the investigation is labelled incomplete.
- **Empty results**: an empty query result has its own explicit status in the UI and the report.

## Process

- All work goes through the backlog commands (`/start`, `/pause`, `/finish`) so the work log records time
  spent; the README's "time spent" section is taken from it.
