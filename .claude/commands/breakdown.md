---
description: Split a todo item into smaller child items
argument-hint: <ID> "<split guidance>" [--priority P0..P3] [--domain <d>]
---
Break down backlog item: $ARGUMENTS

1. Read the parent: `python3 scripts/backlog.py show <ID>`. It must be `todo` (or `split`) with an empty work log.
   If not, stop and explain: worked items are /cancel'led and recreated with /create instead.
2. Decide the split from the guidance and the parent body. Each child must be independently deliverable and
   testable. Prefer fewer, larger children. At least one.
3. Author each child's body (same headings as /create) into temporary files outside the repo, then run once:
   `python3 scripts/backlog.py breakdown <ID> --child <type> "<title>" <file> [--child ...] [--priority] [--domain]`
   The parent and all children are written in one commit, or nothing is.
4. Report the parent and the child IDs.
