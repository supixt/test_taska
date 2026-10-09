# How to work on code

## Before writing
- Read the relevant code first and follow existing patterns. Don't guess APIs — verify them.
- State your assumptions explicitly. If a requirement is ambiguous, ask instead of silently picking one.
- If you see a contradiction in the task or a better approach, say so before implementing.

## Simplicity
- Write the minimum code that solves the problem. No speculative abstractions, extra layers, or config "for later".
- Three similar lines are better than a premature abstraction.
- Don't add dependencies unless necessary.

## Surgical changes
- Change only what the task requires. Don't refactor, rename, or reformat adjacent code unless asked.
- Match the surrounding code: naming, comment density, idioms.
- Remove code made dead by your changes. Don't leave commented-out code.

## Verifiable goals
- Before starting, define how to check the task is done (a test, a command, an expected output).
- After changes, run tests/linter/build. If something fails, report it honestly with the output.
- Don't say "done" without verifying. Never change tests just to make them pass.

## Quality
- Handle errors at system boundaries (user input, network, files), not everywhere.
- No secrets in code. Validate external input.
- Comments explain "why", not "what".

## Communication
- Be concise. No preambles, no restating what's already visible in the diff.
- If you don't know, say so — don't make things up.

## Project setup (already done — do not redo)
- Python 3.12 virtualenv in `.venv/` (Homebrew python@3.12). Use `.venv/bin/python` / `.venv/bin/pip`.
- Dependencies are pinned in `requirements.txt` (FastAPI, uvicorn, LangChain, langchain-deepseek,
  python-dotenv, pytest, httpx). Add new ones there with exact versions.
- Model provider: DeepSeek via LangChain. The key goes in `.env` as `DEEPSEEK_API_KEY` (see `.env.example`).
  Never read or print `.env`.
- Assignment inputs: `tasks/data/` (domain rules, schema, seed). Templates to complete: `ai-workflow/`.
  The hiring-team brief (`client-ai-project-research*.html`) and the starter-pack ZIP are gitignored
  reference material — read them, never commit them.
- Tests: `.venv/bin/python -m pytest`

## Backlog
- Rules: `backlog-guide.md`. Scope: `task_d`. Tickets live on the `backlog` branch, never on `main`.
- Use only the slash commands (`/create`, `/start`, `/pause`, `/release`, `/finish`, `/cancel`,
  `/breakdown`, `/priority`, `/comment`) or `python3 scripts/backlog.py <command>`. Never edit ticket files
  by hand.
- Read a ticket: `python3 scripts/backlog.py show <ID>`. Validate: `python3 scripts/backlog.py lint`.
- Work happens on the feature branch named after the ticket ID. Commit messages: `<ID>: <imperative summary>`.
