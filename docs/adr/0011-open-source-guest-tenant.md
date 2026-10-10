# ADR-0011: Open source with a public/private split; Atelier is a guest tenant

- **Status:** Accepted (Giullia, 2026-10-09)
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** SEC, DOC, HYB

## Context

The project is a portfolio piece, so it needs to be public. It also runs on the owner's homelab, whose zero-trust posture and internal apps must not be weakened or exposed. The brand's photos and trend data are commercial or third-party material.

## Decision

- Code is Apache-2.0, documentation is CC BY 4.0.
- Three repositories: the public `atelier`, the private `atelier-env-fuhro` (homelab overlay, policies, tunnel and WireGuard config, leak patterns) and the private `atelier-brand-data` (photos, reviewed metadata, trend corpus).
- The public repo describes a generic `edge` region and contains no homelab hostnames, addresses or topology. The one deliberately public name is `ebahn.fuhro.network`.
- On the homelab Atelier is a guest tenant: its own namespaces with quotas, deny-by-default network policy in both directions, its own Cloudflare tunnel (ADR-0014), and no cluster-scoped ownership.
- The repository is readable and runnable by anyone, but outside contributions are closed: pull requests are restricted to the maintainer.
- Leaks are prevented by gates in pre-commit and CI (ADR-0016).

## Consequences

- Strong portfolio value with a small attack surface and no review burden.
- The homelab overlay cannot be demonstrated publicly in full, so the `kind` reference edge stands in for it in documentation.
- The protection depends on repo settings and the owner's account, so both are checked at the end of Phase 0 and the account uses a passkey.

## Alternatives considered

- Fully private repository: no portfolio value.
- Accepting outside contributions: more attack surface and review work for no benefit to the goals.
- Homelab overlay in the public repo with placeholder values: easy to get wrong, and the history would be the risk.

## Pi-vs-Azure note

Azure resources are owned entirely by this project. The homelab is shared, so the isolation controls in SPEC.md section 16 apply there.

## Interview probe

"How do you publish infrastructure code without publishing your infrastructure?" Answer: split by sensitivity, scan for leaks before and after commit, fail closed, and shrink the contribution surface.
