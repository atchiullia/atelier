#!/usr/bin/env python3
"""
leakcheck: keep homelab details out of the public repo (ADR-0016).

Tier 1 (always on, needs no secret): generic checks for private IP ranges and
internal-looking hostnames.
Tier 2 (optional): private patterns from a directory (patterns.txt, manual.txt,
allow.txt) kept in the private repo. Taken from --patterns or $ATELIER_LEAK_PATTERNS.

Modes (default: scan every git-tracked file in the working tree):
  --staged    scan what is staged in the index (pre-commit)
  --history   scan every line ever added on any ref (history audit)

Output is REDACTED on purpose: category, file and line number only. Never the
matched text, never a pattern. CI logs of a public repo are public.

A line containing "leak-ok:" is skipped, so an intentional exception is visible in review.

Exit codes: 0 clean, 1 findings, 2 configuration error. Configuration problems
fail CLOSED: a gate that silently loads zero patterns is worse than no gate.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 2_000_000

TIER1 = [
    ("PRIVATE-IP", re.compile(
        r"(?<![\d.])(?:10(?:\.\d{1,3}){3}"
        r"|192\.168(?:\.\d{1,3}){2}"
        r"|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
        r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2}"
        r"|169\.254(?:\.\d{1,3}){2})(?!\d)")),
    ("INTERNAL-HOST", re.compile(
        r"\b[a-z0-9][a-z0-9-]*\.(?:local|lan|internal|home\.arpa|ts\.net)\b", re.I)),
]

# Public facts that are never a leak.
BUILTIN_ALLOW = [
    re.compile(r"cluster\.local", re.I),
    re.compile(r"\bexample\.(?:com|org|net|test)\b", re.I),
]


def die(msg):
    print(f"leakcheck: configuration error: {msg}", file=sys.stderr)
    sys.exit(2)


def compile_lines(path, label, with_category):
    out = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if with_category:
            cat, sep, rx = raw.partition("\t")
            if not sep:
                die(f"{label} line {n}: expected CATEGORY<TAB>regex")
            cat = cat.strip() or "MANUAL"
        else:
            cat, rx = None, raw.strip()
        try:
            out.append((cat, re.compile(rx, re.I)))
        except re.error:
            die(f"{label} line {n}: invalid regex")   # never echo the regex
    return out


def load_patterns(dirpath):
    d = Path(dirpath)
    if not d.is_dir():
        die("patterns directory not found")
    pats = []
    for name in ("patterns.txt", "manual.txt"):
        f = d / name
        if f.is_file():
            pats += compile_lines(f, name, True)
        elif name == "patterns.txt":
            die("patterns.txt not found")
    allow = []
    af = d / "allow.txt"
    if af.is_file():
        allow = [rx for _, rx in compile_lines(af, "allow.txt", False)]
    if not pats:
        die("no patterns loaded")
    return pats, allow


def scan_line(line, tier2, allow):
    """Return the sorted list of categories that match this line."""
    if "leak-ok:" in line:
        return []
    for rx in list(allow) + BUILTIN_ALLOW:
        line = rx.sub("", line)
    cats = {cat for cat, rx in TIER1 if rx.search(line)}
    cats |= {cat for cat, rx in tier2 if rx.search(line)}
    return sorted(cats)


def is_binary(data):
    return b"\0" in data[:8000]


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if r.returncode != 0:
        die(f"git {args[0]} failed")
    return r.stdout


def scan_blob(label, data, tier2, allow):
    if is_binary(data) or len(data) > MAX_BYTES:
        return 0
    n = 0
    for i, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
        cats = scan_line(line, tier2, allow)
        if cats:
            print(f"LEAK {','.join(cats)} {label}:{i}")
            n += 1
    return n


def scan_tracked(root, tier2, allow):
    n = 0
    for p in git(root, "ls-files", "-z").split(b"\0"):
        if not p:
            continue
        f = Path(root) / p.decode("utf-8", errors="replace")
        if f.is_file():
            n += scan_blob(p.decode("utf-8", errors="replace"), f.read_bytes(), tier2, allow)
    return n


def scan_staged(root, tier2, allow):
    n = 0
    names = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    for p in names.split(b"\0"):
        if p:
            path = p.decode("utf-8", errors="replace")
            n += scan_blob(path, git(root, "show", f":{path}"), tier2, allow)
    return n


def scan_history(root, tier2, allow):
    out = git(root, "log", "--all", "-p", "-U0", "--no-color", "--no-ext-diff",
              "--format=@@commit %h")
    n, commit, path, lineno = 0, "?", "?", 0
    for raw in out.split(b"\n"):
        if raw.startswith(b"@@commit "):
            commit = raw[9:].decode()
        elif raw.startswith(b"+++ "):
            tail = raw[4:].decode("utf-8", errors="replace")
            path = tail[2:] if tail.startswith("b/") else tail
        elif raw.startswith(b"@@ "):
            m = re.search(rb"\+(\d+)", raw)
            lineno = int(m.group(1)) - 1 if m else 0
        elif raw.startswith(b"+"):
            lineno += 1
            cats = scan_line(raw[1:].decode("utf-8", errors="replace"), tier2, allow)
            if cats:
                print(f"LEAK {','.join(cats)} {commit} {path}:{lineno}")
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patterns", default=os.environ.get("ATELIER_LEAK_PATTERNS"),
                    help="private leak-patterns directory (default: $ATELIER_LEAK_PATTERNS)")
    ap.add_argument("--require-patterns", action="store_true",
                    help="exit 2 when no private patterns are available (use in CI)")
    ap.add_argument("--root", default=".", help="repository root")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--history", action="store_true")
    args = ap.parse_args()

    tier2, allow = [], []
    if args.patterns:
        tier2, allow = load_patterns(args.patterns)
    elif args.require_patterns:
        die("private patterns required but not provided")
    else:
        print("leakcheck: tier 2 skipped (no private patterns configured)", file=sys.stderr)

    if args.staged:
        n = scan_staged(args.root, tier2, allow)
    elif args.history:
        n = scan_history(args.root, tier2, allow)
    else:
        n = scan_tracked(args.root, tier2, allow)

    print(f"leakcheck: {n} finding(s)")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
