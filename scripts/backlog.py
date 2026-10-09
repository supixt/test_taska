#!/usr/bin/env python3
"""Backlog tool — the only writer of ticket files (see backlog-guide.md).

Tickets live in docs/backlog/<scope>/tasks/ on the `backlog` branch. This script reads and
writes them through a git worktree at .backlog/ (gitignored), so it works from any branch.
Every write is linted and secret-scanned before it is committed; any failure writes nothing.

    python scripts/backlog.py init [--scope <name>]
    python scripts/backlog.py new-scope <name>
    python scripts/backlog.py create <task|bug> "<title>" --body-file <path> [--scope] [--priority] [--domain]
    python scripts/backlog.py start <ID> [--domain <d>]
    python scripts/backlog.py pause <ID> "<reason>"
    python scripts/backlog.py release <ID> [--domain <d>]
    python scripts/backlog.py finish <ID> [--link <url>]
    python scripts/backlog.py cancel <ID> "<reason>"
    python scripts/backlog.py breakdown <ID> --child <type> "<title>" <body-file> [--child ...] [--priority] [--domain]
    python scripts/backlog.py priority <ID> <P0..P3> "<reason>"
    python scripts/backlog.py comment <ID> "<text>"
    python scripts/backlog.py show <ID>
    python scripts/backlog.py lint [--scope <name>]

Written to run on Python 3.9+ with the standard library only.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "backlog"
BASE_BRANCH = "main"
WT = ROOT / ".backlog"
BACKLOG_DIR = "docs/backlog"

FIELDS = ["ID", "Title", "Type", "Status", "Priority", "Assignee", "Domain", "Parent",
          "Branch", "Created", "Closed", "Updated", "Work log", "Comments"]
LISTS = ("Work log", "Comments")
CANON = {f.lower(): f for f in FIELDS}
TYPES = ("task", "bug")
STATUSES = ("todo", "in-progress", "paused", "done", "cancelled", "split")
TERMINAL = ("done", "cancelled", "split")
PRIORITIES = ("P0", "P1", "P2", "P3")
DOMAINS = ("design", "implementation", "product", "-")
SECTIONS = {
    "task": ["Business background", "What to build", "Threats and risks", "Done when",
             "Acceptance criteria"],
    "bug": ["Description", "Environment", "Observed behaviour", "Expected behaviour"],
}

TS_FMT = "%d-%m-%Y %H:%M"
TS_RE = re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}$")
ID_RE = re.compile(r"^([A-Za-z0-9_]+)-(task|bug)-(\d{4})$")
SCOPE_RE = re.compile(r"^[A-Za-z0-9_]+$")
WL_RE = re.compile(r"^work (started|finished) \[(\d+)\]:\s*(.+)$")
COMMENT_RE = re.compile(r"^\[(\d{2}-\d{2}-\d{4} \d{2}:\d{2})\] [^:]+: .+")

# event -> (allowed source statuses, target status; None = no status change)
EVENTS = {
    "start": (("todo", "paused"), "in-progress"),
    "pause": (("in-progress",), "paused"),
    "release": (("in-progress", "paused"), "todo"),
    "finish": (("in-progress", "done"), "done"),
    "cancel": (("todo", "in-progress", "paused"), "cancelled"),
    "breakdown": (("todo", "split"), "split"),
    "priority": (("todo", "in-progress", "paused"), None),
    "comment": (STATUSES, None),
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"xox[abpr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{16,}"),
]


class Fail(Exception):
    pass


# ---------------------------------------------------------------- git & environment

def git(*args, cwd=ROOT, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise Fail(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def now():
    return datetime.now(timezone.utc).strftime(TS_FMT)


def actor():
    return git("config", "user.name", check=False) or os.environ.get("USER", "unknown")


def has_remote():
    return bool(git("remote", check=False))


def worktree():
    """Return the backlog worktree, synced with the remote if one exists."""
    if not (WT / ".git").exists():
        if not git("rev-parse", "--verify", "--quiet", BRANCH, check=False):
            raise Fail(f"branch '{BRANCH}' does not exist; run `backlog.py init` first")
        git("worktree", "prune")
        git("worktree", "add", str(WT), BRANCH)
    if has_remote():
        git("pull", "--ff-only", cwd=WT, check=False)
    return WT


def ensure_clean():
    if git("status", "--porcelain", cwd=worktree()):
        raise Fail(f"{WT} has uncommitted changes; the backlog must only be changed by this script")


def commit(message):
    """Commit staged backlog changes; on failure (e.g. the pre-commit backstop) roll everything back."""
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=WT).returncode == 0:
        return  # nothing changed (e.g. a repeated /finish within the same minute)
    try:
        git("commit", "-q", "-m", message, cwd=WT)
    except Fail:
        git("reset", "-q", "--hard", "HEAD", cwd=WT)
        git("clean", "-qfd", cwd=WT)
        raise
    if has_remote():
        git("push", "-q", "origin", BRANCH, cwd=WT)


def scopes():
    base = worktree() / BACKLOG_DIR
    names = [p.name for p in base.iterdir() if p.is_dir()] if base.exists() else []
    return sorted(names, key=natural_key)


def natural_key(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]


# ---------------------------------------------------------------- ticket format

def parse(text):
    """Tolerant reader: field names are matched case-insensitively, bold is ignored."""
    head, _, body = text.partition("\n\n")
    t, cur, stray = {}, None, []
    for line in head.splitlines():
        m = re.match(r"^- \**([^:*]+?)\**:\s*(.*)$", line)
        if m and m.group(1).strip().lower() in CANON:
            cur = CANON[m.group(1).strip().lower()]
            val = m.group(2).strip()
            if cur in LISTS:
                t[cur] = [] if val in ("", "-") else [val]
            else:
                t[cur] = val
        elif cur in LISTS and re.match(r"^\s+- ", line):
            t[cur].append(line.strip()[2:])
        else:
            stray.append(line)
    return t, body, stray


def render(t, body):
    """Canonical writer: fields in fixed order, every field present."""
    out = []
    for f in FIELDS:
        v = t[f]
        if f in LISTS:
            if v:
                out.append(f"- {f}:")
                out += [f"  - {e}" for e in v]
            else:
                out.append(f"- {f}: -")
        else:
            out.append(f"- {f}: {v}")
    return "\n".join(out) + "\n\n" + body.strip("\n") + "\n"


def intervals(log):
    """Parse the work log into [n, start, finish|None] and report every rule it breaks."""
    ivs, errs = [], []
    for e in log:
        m = WL_RE.match(e)
        if not m:
            errs.append(f"malformed work-log entry: {e!r}")
            continue
        kind, n, ts = m.group(1), int(m.group(2)), m.group(3).strip()
        if not TS_RE.match(ts):
            errs.append(f"work-log timestamp not DD-MM-YYYY HH:MM: {e!r}")
        if kind == "started":
            if n != len(ivs) + 1:
                errs.append(f"work started [{n}] out of sequence")
            if ivs and ivs[-1][2] is None:
                errs.append(f"work started [{n}] while [{ivs[-1][0]}] is still open")
            ivs.append([n, ts, None])
        elif not ivs or ivs[-1][0] != n or ivs[-1][2] is not None:
            errs.append(f"work finished [{n}] has no matching open start")
        else:
            ivs[-1][2] = ts
    return ivs, errs


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:50].rstrip("-") or "item"


# ---------------------------------------------------------------- checks

def lint_ticket(path, text):
    t, body, stray = parse(text)
    errs = [f"unrecognised metadata line: {s!r}" for s in stray]
    missing = [f for f in FIELDS if f not in t]
    if missing:
        return errs + [f"missing fields: {', '.join(missing)}"]

    m = ID_RE.match(t["ID"])
    if not m:
        errs.append(f"ID {t['ID']!r} is not <scope>-<type>-<NNNN>")
    else:
        if not path.name.startswith(t["ID"] + "-"):
            errs.append(f"file name does not start with '{t['ID']}-'")
        if path.parent.parent.name != m.group(1):
            errs.append(f"ID scope '{m.group(1)}' does not match folder '{path.parent.parent.name}'")
        if m.group(2) != t["Type"]:
            errs.append(f"Type {t['Type']!r} does not match the ID")
    for field, allowed in (("Type", TYPES), ("Status", STATUSES), ("Priority", PRIORITIES),
                           ("Domain", DOMAINS)):
        if t[field] not in allowed:
            errs.append(f"{field} {t[field]!r} not in {'|'.join(allowed)}")
    if not t["Title"] or not t["Assignee"]:
        errs.append("Title and Assignee must not be empty (use '-' for no assignee)")
    if t["Parent"] != "-" and not ID_RE.match(t["Parent"]):
        errs.append(f"Parent {t['Parent']!r} is not an ID or '-'")
    if t["Branch"] not in ("-", t["ID"]):
        errs.append(f"Branch must be '-' or the ticket ID, got {t['Branch']!r}")
    for field in ("Created", "Updated"):
        if not TS_RE.match(t[field]):
            errs.append(f"{field} {t[field]!r} not DD-MM-YYYY HH:MM")
    if t["Closed"] != "-" and not TS_RE.match(t["Closed"]):
        errs.append(f"Closed {t['Closed']!r} not DD-MM-YYYY HH:MM or '-'")
    if (t["Status"] in TERMINAL) != (t["Closed"] != "-"):
        errs.append("Closed must be set exactly when Status is done, cancelled or split")

    ivs, wl_errs = intervals(t["Work log"])
    errs += wl_errs
    is_open = bool(ivs) and ivs[-1][2] is None
    if is_open != (t["Status"] == "in-progress"):
        errs.append("an interval must be open if and only if Status is in-progress")
    if t["Status"] == "split" and ivs:
        errs.append("a split item must have an empty work log")

    for c in t["Comments"]:
        if not COMMENT_RE.match(c):
            errs.append(f"comment not '[DD-MM-YYYY HH:MM] who: text': {c!r}")

    if t["Type"] in SECTIONS:
        heads = re.findall(r"^## (.+?)\s*$", body, re.M)
        lacking = [s for s in SECTIONS[t["Type"]] if s not in heads]
        if lacking:
            errs.append(f"body is missing sections: {', '.join(lacking)}")

    if not errs and render(t, body) != text:
        errs.append("non-canonical formatting (rewrite via a command, never by hand)")
    return errs


def secret_hits(text):
    t, body, _ = parse(text)
    parts = [(f, "\n".join(v) if isinstance(v, list) else v) for f, v in t.items()]
    parts.append(("body", body))
    return [f for f, v in parts if any(p.search(v) for p in SECRET_PATTERNS)]


def lint_relations(tickets):
    """Cross-ticket check for Parent: exists, same scope, parent is split, split has a child, no cycle."""
    errs = []
    by_id = {t["ID"]: t for t in tickets}
    children = {}
    for t in tickets:
        p = t["Parent"]
        if p == "-":
            continue
        children.setdefault(p, []).append(t["ID"])
        if p not in by_id:
            errs.append(f"{t['ID']}: parent {p} does not exist in this scope")
        elif by_id[p]["Status"] != "split":
            errs.append(f"{t['ID']}: parent {p} has status {by_id[p]['Status']}, expected split")
    for t in tickets:
        if t["Status"] == "split" and t["ID"] not in children:
            errs.append(f"{t['ID']}: split item has no children")
        seen, cur = set(), t["ID"]
        while cur in by_id and by_id[cur]["Parent"] != "-":
            if cur in seen:
                errs.append(f"{t['ID']}: parent chain forms a cycle")
                break
            seen.add(cur)
            cur = by_id[cur]["Parent"]
    return errs


# ---------------------------------------------------------------- reading & publishing

def scope_files(scope):
    d = worktree() / BACKLOG_DIR / scope / "tasks"
    return sorted(d.glob("*.md")) if d.exists() else []


def load(path):
    return parse(path.read_text())


def find(ticket_id):
    m = ID_RE.match(ticket_id)
    if not m:
        raise Fail(f"{ticket_id!r} is not a valid ID (<scope>-<type>-<NNNN>)")
    hits = list((worktree() / BACKLOG_DIR / m.group(1) / "tasks").glob(f"{ticket_id}-*.md"))
    if not hits:
        hits = list((WT / BACKLOG_DIR).glob(f"*/tasks/{ticket_id}-*.md"))
    if len(hits) != 1:
        raise Fail(f"{ticket_id}: found {len(hits)} ticket files, expected exactly 1")
    return hits[0]


def next_ids(scope, count):
    nums = []
    for p in scope_files(scope):
        m = ID_RE.match("-".join(p.name.split("-")[:3]))
        if m:
            nums.append(int(m.group(3)))
    start = max(nums, default=0) + 1
    return [f"{start + i:04d}" for i in range(count)]


def publish(files, message, relation_scope=None):
    """Validate every file, then write and commit all of them together, or nothing."""
    errs = []
    for path, text in files.items():
        errs += [f"{path.name}: {e}" for e in lint_ticket(path, text)]
        errs += [f"{path.name}: secret-like value in field '{f}' (value not shown)"
                 for f in secret_hits(text)]
    if relation_scope:
        staged = {p: parse(t)[0] for p, t in files.items()}
        existing = {p: load(p)[0] for p in scope_files(relation_scope) if p not in staged}
        errs += lint_relations(list(existing.values()) + list(staged.values()))
    if errs:
        raise Fail("refused, nothing written:\n  " + "\n  ".join(errs))
    ensure_clean()
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git("add", str(path.relative_to(WT)), cwd=WT)
    commit(message)


# ---------------------------------------------------------------- commands

def cmd_init(a):
    if not git("rev-parse", "--verify", "--quiet", BRANCH, check=False):
        empty_tree = git("hash-object", "-t", "tree", "/dev/null")
        sha = git("commit-tree", empty_tree, "-m", "backlog: initialise branch")
        git("branch", BRANCH, sha)
        print(f"created orphan branch '{BRANCH}'")
    worktree()
    install_hook()
    if a.scope:
        cmd_new_scope(a)
    print(f"backlog ready at {WT}; scopes: {', '.join(scopes()) or '(none)'}")


def install_hook():
    hook = Path(git("rev-parse", "--git-common-dir")).resolve() / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\n"
        "# Backstop: lint the whole backlog before any commit on the backlog branch.\n"
        f'[ "$(git rev-parse --abbrev-ref HEAD)" = "{BRANCH}" ] || exit 0\n'
        f'exec python3 "{ROOT}/scripts/backlog.py" lint\n'
    )
    hook.chmod(0o755)


def cmd_new_scope(a):
    if not SCOPE_RE.match(a.scope):
        raise Fail("scope names may contain only letters, digits and '_' (no '-')")
    if a.scope in scopes():
        print(f"scope '{a.scope}' already exists")
        return
    ensure_clean()
    for sub in ("tasks", "images"):
        d = WT / BACKLOG_DIR / a.scope / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").write_text("")
        git("add", str((d / ".gitkeep").relative_to(WT)), cwd=WT)
    commit(f"backlog: create scope {a.scope}")
    print(f"created scope '{a.scope}'")


def resolve_create_scope(requested):
    existing = scopes()
    if requested:
        if requested not in existing:
            raise Fail(f"scope '{requested}' does not exist (existing: {', '.join(existing)}); "
                       "create it with `new-scope` first")
        return requested
    if len(existing) == 1:
        return existing[0]
    raise Fail(f"several scopes exist ({', '.join(existing)}); pass --scope" if existing
               else "no scope exists; create one with `new-scope <name>`")


def read_body(path):
    text = sys.stdin.read() if path == "-" else Path(path).read_text()
    if not text.strip():
        raise Fail("the ticket body is empty")
    return text


def new_ticket(scope, num, typ, title, body, priority, domain, parent="-"):
    ts = now()
    tid = f"{scope}-{typ}-{num}"
    t = {"ID": tid, "Title": title, "Type": typ, "Status": "todo", "Priority": priority,
         "Assignee": "-", "Domain": domain, "Parent": parent, "Branch": "-", "Created": ts,
         "Closed": "-", "Updated": ts, "Work log": [], "Comments": []}
    path = WT / BACKLOG_DIR / scope / "tasks" / f"{tid}-{slugify(title)}.md"
    return tid, path, render(t, body)


def cmd_create(a):
    scope = resolve_create_scope(a.scope)
    (num,) = next_ids(scope, 1)
    tid, path, text = new_ticket(scope, num, a.type, a.title, read_body(a.body_file),
                                 a.priority, a.domain)
    publish({path: text}, f"{tid}: create")
    print(f"created {tid} ({path.relative_to(WT)})")


def transition(t, event, *, text=None, priority=None, domain=None, link=None):
    """Apply one event to a parsed ticket in place, following the rules in backlog-guide.md."""
    sources, target = EVENTS[event]
    if t["Status"] not in sources:
        raise Fail(f"{t['ID']}: /{event} is not allowed from status '{t['Status']}' "
                   f"(allowed: {', '.join(sources)})")
    ts, who = now(), actor()
    ivs, wl_errs = intervals(t["Work log"])
    if wl_errs:
        raise Fail(f"{t['ID']}: work log is corrupt, refusing to write: {'; '.join(wl_errs)}")
    is_open = bool(ivs) and ivs[-1][2] is None

    new_status = target or t["Status"]
    if t["Status"] != "in-progress" and new_status == "in-progress":
        if is_open:
            raise Fail(f"{t['ID']}: an interval is already open but status is {t['Status']}")
        t["Work log"].append(f"work started [{len(ivs) + 1}]: {ts}")
    elif t["Status"] == "in-progress" and new_status != "in-progress":
        if not is_open:
            raise Fail(f"{t['ID']}: status is in-progress but no interval is open")
        t["Work log"].append(f"work finished [{ivs[-1][0]}]: {ts}")

    t["Status"] = new_status
    if event == "start":
        t["Assignee"], t["Branch"] = who, t["ID"]
    elif event in ("pause", "release"):
        t["Assignee"] = "-"
    if event == "priority":
        t["Priority"] = priority
    if domain is not None and event in ("start", "release"):
        t["Domain"] = domain
    if event in ("finish", "breakdown", "cancel") and t["Closed"] == "-":
        t["Closed"] = ts
    t["Updated"] = ts

    entry = text
    if event == "finish":
        entry = f"result: {link}" if link and not any(link in c for c in t["Comments"]) else None
    if entry:
        t["Comments"].append(f"[{ts}] {who}: {entry} (via /{event})")


def attach_branch(tid):
    if git("status", "--porcelain"):
        raise Fail("working tree has uncommitted changes; commit or stash them before /start")
    if git("rev-parse", "--verify", "--quiet", tid, check=False):
        git("checkout", "-q", tid)
    else:
        git("checkout", "-q", "-b", tid, BASE_BRANCH)


def simple_event(event):
    def run(a):
        path = find(a.id)
        t, body, _ = load(path)
        if event == "start":
            transition(t, event, domain=a.domain)  # guard before touching git
            attach_branch(a.id)
        else:
            transition(t, event, text=getattr(a, "text", None), priority=getattr(a, "priority", None),
                       domain=getattr(a, "domain", None), link=getattr(a, "link", None))
        publish({path: render(t, body)}, f"{a.id}: {event}")
        print(f"{a.id}: {event} -> {t['Status']}")
    return run


def cmd_breakdown(a):
    path = find(a.id)
    parent, pbody, _ = load(path)
    if parent["Work log"]:
        raise Fail(f"{a.id} has recorded work and cannot be broken down; "
                   f"/cancel it with a reason and /create fresh items citing {a.id}")
    if not a.child:
        raise Fail("at least one --child is required")
    scope = ID_RE.match(a.id).group(1)
    files, ids = {}, []
    for (typ, title, body_file), num in zip(a.child, next_ids(scope, len(a.child))):
        if typ not in TYPES:
            raise Fail(f"child type must be task or bug, got {typ!r}")
        tid, cpath, text = new_ticket(scope, num, typ, title, read_body(body_file),
                                      a.priority or parent["Priority"],
                                      a.domain or parent["Domain"], parent=a.id)
        files[cpath] = text
        ids.append(tid)
    transition(parent, "breakdown", text=f"split into {', '.join(ids)}")
    files[path] = render(parent, pbody)
    publish(files, f"{a.id}: breakdown into {', '.join(ids)}", relation_scope=scope)
    print(f"{a.id} -> split; children: {', '.join(ids)}")


def cmd_show(a):
    print(find(a.id).read_text(), end="")


def cmd_lint(a):
    chosen = [a.scope] if a.scope else scopes()
    errs = []
    for s in chosen:
        files = scope_files(s)
        for p in files:
            text = p.read_text()
            errs += [f"{p.name}: {e}" for e in lint_ticket(p, text)]
            errs += [f"{p.name}: secret-like value in field '{f}' (value not shown)"
                     for f in secret_hits(text)]
        errs += lint_relations([load(p)[0] for p in files if "ID" in load(p)[0]])
    if errs:
        print("backlog lint failed:\n  " + "\n  ".join(errs), file=sys.stderr)
        sys.exit(1)
    print(f"backlog lint ok ({', '.join(chosen) or 'no scopes'})")


def main(argv=None):
    p = argparse.ArgumentParser(description="Backlog tool (see backlog-guide.md)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("--scope")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("new-scope")
    s.add_argument("scope")
    s.set_defaults(fn=cmd_new_scope)

    s = sub.add_parser("create")
    s.add_argument("type", choices=TYPES)
    s.add_argument("title")
    s.add_argument("--body-file", required=True, help="Markdown body, or '-' for stdin")
    s.add_argument("--scope")
    s.add_argument("--priority", choices=PRIORITIES, default="P1")
    s.add_argument("--domain", choices=DOMAINS, default="-")
    s.set_defaults(fn=cmd_create)

    s = sub.add_parser("start")
    s.add_argument("id")
    s.add_argument("--domain", choices=DOMAINS)
    s.set_defaults(fn=simple_event("start"))
    for name in ("pause", "cancel"):
        s = sub.add_parser(name)
        s.add_argument("id")
        s.add_argument("text", metavar="reason")
        s.set_defaults(fn=simple_event(name))
    s = sub.add_parser("release")
    s.add_argument("id")
    s.add_argument("--domain", choices=DOMAINS)
    s.set_defaults(fn=simple_event("release"))
    s = sub.add_parser("finish")
    s.add_argument("id")
    s.add_argument("--link", help="MR URL or other pointer to the delivered result")
    s.set_defaults(fn=simple_event("finish"))
    s = sub.add_parser("priority")
    s.add_argument("id")
    s.add_argument("priority", choices=PRIORITIES)
    s.add_argument("text", metavar="reason")
    s.set_defaults(fn=simple_event("priority"))
    s = sub.add_parser("comment")
    s.add_argument("id")
    s.add_argument("text")
    s.set_defaults(fn=simple_event("comment"))

    s = sub.add_parser("breakdown")
    s.add_argument("id")
    s.add_argument("--child", nargs=3, action="append", metavar=("TYPE", "TITLE", "BODY_FILE"))
    s.add_argument("--priority", choices=PRIORITIES)
    s.add_argument("--domain", choices=DOMAINS)
    s.set_defaults(fn=cmd_breakdown)

    s = sub.add_parser("show")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("lint")
    s.add_argument("--scope")
    s.set_defaults(fn=cmd_lint)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
