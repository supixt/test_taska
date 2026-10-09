---
description: Mark an in-progress item done and open its pull request
argument-hint: <ID> [--link <url> | --no-pr]
---
1. Make sure you are on the item's feature branch `<ID>` and all work is committed there
   (`<ID>: <imperative summary>`). Never commit to main.
2. Run `python3 scripts/backlog.py finish $ARGUMENTS`. It pushes the branch, opens a pull request into main
   (or reuses the open one), records its URL on the ticket, and marks the item done.
   Use `--no-pr` only if the user asks for it.
3. Report the pull request URL. Merging is a separate human step.
