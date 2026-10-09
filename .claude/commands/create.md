---
description: Create a backlog item and author its full body
argument-hint: <task|bug> "<title>" [--scope <s>] [--priority P0..P3] [--domain <d>]
---
Create a backlog item: $ARGUMENTS

1. Author the ticket body in Markdown, following backlog-guide.md. Use exactly these headings:
   - task: `## Business background`, `## What to build`, `## Threats and risks`, `## Done when`,
     `## Acceptance criteria`
   - bug: `## Description`, `## Environment`, `## Observed behaviour`, `## Expected behaviour`
   Make "Done when" and "Acceptance criteria" concrete and testable. Never put secrets in the body.
2. Write the body to a temporary file outside the repo, then run:
   `python3 scripts/backlog.py create <type> "<title>" --body-file <file> [flags from the arguments]`
3. If the script refuses (lint or secret-scan error), fix the body and retry. Never write ticket files by hand.
4. Report the new ID.
