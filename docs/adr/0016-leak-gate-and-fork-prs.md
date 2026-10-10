# ADR-0016: Leak gate design

- **Status:** Accepted (Giullia, 2026-10-10) (revised 2026-10-09: contributions closed)
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** SEC, CICD, DOC

## Context

The public repo must never contain identifying details of the homelab: internal hostnames, node names, CIDRs, tunnel IDs, zone names. The list of those identifiers is itself sensitive, so it lives in the private repo `atelier-env-fuhro`, and a CI job needs a secret to read it. Two facts shape the design:

1. GitHub Actions logs of a public repo are public. A gate that prints what it matched leaks the very thing it protects.
2. Workflows triggered by pull requests from forks run without secrets, and the usual workaround (`pull_request_target`) is dangerous whenever it checks out and runs pull request code.

The first draft of this ADR spent most of its effort on fork pull requests (label-gated runs, data-only checkouts). That complexity is unnecessary because the project accepts no outside contributions: only the owner opens pull requests.

## Decision

**Contribution policy (the foundation).**

- *Settings → General → Features → Pull requests → "Collaborators only".* Not the unticked box, which disables pull requests: the owner still uses pull requests to run required checks.
- *Settings → Actions → General → Require approval for all external contributors*, as a second layer.
- `CONTRIBUTING.md` states that outside contributions are not accepted. Issues are disabled or restricted.
- Workflows are triggered only by `push`, `pull_request`, `schedule` and `workflow_dispatch`. Never `pull_request_target`. If a fork pull request ever appeared, GitHub would still withhold secrets from it.

**Tier 1: public gates, no secrets.** Every push and pull request.

- gitleaks and trufflehog for credentials.
- Generic network regexes that need no private list: RFC1918 (10/8, 172.16/12, 192.168/16), CGNAT and Tailscale (100.64/10), link-local (169.254/16), and the suffixes `.local`, `.lan`, `.internal`, `.home.arpa`, `.ts.net`.
- Documentation ranges (192.0.2/24, 198.51.100/24, 203.0.113/24) and `example.*` / `*.test` names are allowed. An intentional exception carries an inline `leak-ok: <reason>` marker, visible in review.

**Tier 2: private pattern gate.** A required status check on `main`.

- Runs on every push and every same-repo pull request.
- Reads `leak-patterns/` from the private repo with a read-only fine-grained token (contents: read, that repo only), stored as an Actions secret and held on tmpfs.
- Output is redacted: category ID, file path and line number only. Never the matched text and never the pattern.
- A weekly scheduled run scans the full history of `main`.

**Tier 3: local.** A pre-commit hook reads patterns from the path in `$ATELIER_LEAK_PATTERNS`. Without the variable it does nothing, and Tier 1 still applies.

**Pattern files** (private repo, `leak-patterns/`): `patterns.txt` (generated), `manual.txt` (hand-curated), `allow.txt` (public facts such as `ebahn.fuhro.network`, stripped from a line before matching). Format: `CATEGORY<TAB>regex`, extended regex, case-insensitive.

## Consequences

- Simple: one trusted author, secrets available to every run, no label workflow, no oracle for outsiders to probe the pattern list.
- The protection depends on two repo settings and the owner's account. Both settings are verified in the Phase 0 exit check, and the owner account uses a passkey or hardware key. A compromised owner account defeats everything here, which is why the homelab also pins signed release tags (SPEC.md §7.1).
- Dependabot pull requests do not receive Actions secrets. Tier 2 would fail on them, so either leave Dependabot off for now or add the token as a Dependabot secret.
- `patterns.txt` is a map of the homelab. It stays in the private repo and is never pasted into chats, issues or screenshots.
- False positives are handled by `allow.txt` in the private repo, never by weakening rules in the public repo.
- A history audit with the same tiers is still required before the repo flips to public.

## Alternatives considered

- Accept outside pull requests with a label-gated `pull_request_target` check (the first draft): rejected as unnecessary complexity for a project that takes no contributions.
- `pull_request_target` on every pull request with the secret: rejected. One future edit that adds a checkout-and-run step turns it into code execution with secrets.
- Publish hashed patterns: rejected. Hostnames and node names are short and guessable, so hashes are brute-forceable.
- Generic regexes only: rejected. They cannot catch names, zones and tunnel IDs.

## Pi-vs-Azure note

Not applicable. The gate runs on GitHub-hosted runners and touches neither cluster.

## Interview probe

"How do you keep secrets out of a public repo's CI?" The answer covers redacted output, no `pull_request_target`, a read-only scoped token, and closing the contribution surface instead of defending a large one.
