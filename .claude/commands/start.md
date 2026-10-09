---
description: Start (or resume) work on a backlog item
argument-hint: <ID> [--domain <d>]
---
Run `python3 scripts/backlog.py start $ARGUMENTS`.
It checks out (or creates from main) the feature branch named after the ID, sets the item in-progress,
assigns it to you and opens a work interval. The working tree must be clean. Report the result.
