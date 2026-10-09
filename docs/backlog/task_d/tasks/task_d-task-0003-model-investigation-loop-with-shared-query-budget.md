- ID: task_d-task-0003
- Title: Model investigation loop with shared query budget
- Type: task
- Status: todo
- Priority: P0
- Assignee: -
- Domain: implementation
- Parent: -
- Branch: -
- Created: 09-10-2026 11:51
- Closed: -
- Updated: 09-10-2026 12:01
- Work log: -
- Comments:
  - [09-10-2026 12:01] supixt: Decision change (D2, docs/decisions.md f008f54): the loop gets model replies through a message-source interface (history -> next AIMessage) with live (ChatDeepSeek.bind_tools([run_sql]).invoke), replay, and scripted-test implementations. Do not use GenericFakeChatModel: its bind_tools() raises NotImplementedError. Tests in this ticket use the scripted source. (via /comment)

## Business background
The model investigates a sales question by requesting SQL through a tool and choosing at least one follow-up
from the first results. The investigation must respect a hard query budget and make model failures visible.
Decisions: D2, D7, query budget, model-call timeout.

## What to build
- `app/prompts/system.md`: role, tool rules and limits, analysis rules (half-open UTC periods taken from the
  question, integer cents, aggregate orders and refunds separately before combining, at least one follow-up,
  never infer why customers requested refunds, list missing evidence), and the final-answer schema.
  `tasks/data/domain.md` and `tasks/data/schema.sql` inserted verbatim at runtime.
- `app/investigate.py`:
  - `ChatDeepSeek(model="deepseek-chat", temperature=0, max_tokens=2000, timeout=60, max_retries=0)` with one
    bound `run_sql` tool backed by `app/db.py`.
  - Own loop: 6 query attempts per investigation shared by the question and all follow-ups; failed, rejected,
    and timed-out queries count. At the limit the loop stops and returns partial results labelled `limit
    reached`.
  - Follow-up questions continue the same message history.
  - Final answer parsed and validated with pydantic (cited figures, breakdowns, observed facts, not established,
    assumptions, periods). Invalid output -> investigation `incomplete`, raw output kept.
  - Any model/API error -> investigation `incomplete` with the error shown; no retry.
  - Every query attempt logged with its question, SQL, and result or error.
- Tests in `tests/test_investigate.py` with a scripted fake chat model (no network).
- Depends on: task_d-task-0002.

## Threats and risks
- DeepSeek tool-calling or JSON output may be unreliable. Mitigation: strict pydantic validation; failures are
  visible and labelled, never silently repaired.
- Ambiguous periods in a question. Mitigation: the answer states its periods explicitly; the prompt asks the
  model to state assumptions.

## Done when
- `.venv/bin/python -m pytest tests/test_investigate.py` passes.
- One manual live run with `DEEPSEEK_API_KEY` set completes a question about the Aug -> Sep net-sales change
  (result noted with /comment).

## Acceptance criteria
- A scripted model that keeps requesting queries is stopped after exactly 6 attempts, counting a question and a
  follow-up together.
- A failing query consumes one attempt and its error is returned to the model and logged.
- A raised API error yields an `incomplete` investigation with the error message, and the fake model is called
  exactly once (no retry).
- Malformed final output yields `incomplete` with the raw output preserved.
- The system prompt sent to the model contains `domain.md` and `schema.sql` verbatim.
