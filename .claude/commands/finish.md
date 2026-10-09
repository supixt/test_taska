---
description: Mark an in-progress item done
argument-hint: <ID> [--link <url>]
---
1. Commit all work for the item on its feature branch (`<ID>: <imperative summary>`). Never commit to main.
2. Run `python3 scripts/backlog.py finish $ARGUMENTS` (pass `--link` with the MR URL if there is one).
3. Report the result. Merging to main is a separate human step.
