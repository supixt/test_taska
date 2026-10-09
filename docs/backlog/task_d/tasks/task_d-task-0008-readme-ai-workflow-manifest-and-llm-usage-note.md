- ID: task_d-task-0008
- Title: README, AI-workflow manifest and LLM usage note
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
Reviewers need to run the project, understand decisions and limitations, and reproduce the AI setup. The brief
requires a README, a completed AI-workflow manifest and README, an LLM usage note, and a short walkthrough.

## What to build
- `README.md`: setup and run, architecture and data flow, model configuration, query limits (`QUERY_TIMEOUT_S`,
  `MAX_ROWS`, 6-attempt budget), data assumptions (including the current-segment limitation), replay without a
  key, time spent (taken from the backlog work logs), known limitations.
- `ai-workflow/manifest.json` and `ai-workflow/README.md` from the templates (templates removed): development
  tools and models, application model and parameters, prompts, backlog commands and scripts, permissions, the
  root `.env.example`; `not-used` / `default` / `redacted` / `not-exportable` recorded accurately.
- `docs/llm-usage.md`: tools and models, generated components, one representative instruction, one correction
  or verification step (from comments collected on tickets).
- `docs/walkthrough.md`: written walkthrough of approach and findings.
- Depends on: task_d-task-0007.

## Threats and risks
- Secrets or personal data leaking into config snapshots. Mitigation: sanitised snapshots only, secret scan,
  review `git diff` before commit.
- Time-spent figures drifting from reality. Mitigation: compute them from the work logs only.

## Done when
- A clean clone can be set up and replayed by following only the README.
- `ai-workflow/manifest.json` has no template placeholders and is valid JSON.

## Acceptance criteria
- Every category in the manifest has a status and, where used, a file path and version.
- The README time-spent section matches the backlog work logs.
- The LLM usage note contains one concrete correction with evidence (prompt excerpt or saved result).
