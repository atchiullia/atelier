# ADR-0014: Separate Cloudflare Tunnel for Ebahn

- **Status:** Accepted (decision 2026-10-09). Amendments 1 and 2: **Proposed**, pending approval.
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** NET, SEC, HYB

## Context

Ebahn is a public demo (`ebahn.fuhro.network`, showcases only) running as a guest tenant on a shared Raspberry Pi 5 cluster. The DNS zone is shared with the homelab, and Cloudflare API tokens are scoped to a zone, not to a record. Any path from the internet into the cluster must not be able to reach the homelab's internal apps.

## Decision

Ebahn gets its own Cloudflare Tunnel (own tunnel ID, credentials and connector), one ingress rule for `ebahn.fuhro.network`, no private-network routes, no Cloudflare API token on the tenant, and no DNS automation on the shared zone. The connector runs with zero replicas outside showcases. Full control list: SPEC.md §16.6.

## Amendment 1: TLS termination on the edge (resolves Q12)

**Problem.** The original networking table had cert-manager issuing Let's Encrypt certificates by DNS-01 on the edge. DNS-01 needs a DNS API token for the zone, which this ADR forbids.

**Decision.**

- The public certificate is Cloudflare's edge certificate. `ebahn.fuhro.network` is a first-level subdomain of the zone, so Universal SSL covers it.
- Cloudflare to `cloudflared` is encrypted by the tunnel itself.
- `cloudflared` to `atelier-gw` is plain HTTP inside the cluster. On the current single-node Pi this hop never leaves the node.
- No ACME issuer and no DNS token on the edge tenant. The zone's SSL settings belong to the homelab and are not changed by this project.
- If the edge ever has more than one node, pick one of: Cilium transparent encryption (a cluster-wide choice owned by the homelab), or HTTPS between `cloudflared` and the gateway using a namespaced CA `Issuer` that needs no external token.
- Azure core is unchanged: cert-manager with DNS-01 against Azure DNS through workload identity, owned entirely by this project.

**Consequences.** Cloudflare terminates TLS, so it sees request plaintext. That is acceptable with test data and a public demo. It must be revisited at go-live because real customer data would then transit a third-party processor (LGPD/GDPR processor terms). Add it to the go-live checklist in SPEC.md §13.

## Amendment 2: no per-PR environments on the homelab (resolves Q13)

**Problem.** The plan was per-PR hostnames `pr-N.ebahn.fuhro.network` plus per-PR namespaces. That fails on three counts:

1. Those names are two levels below the zone, outside the free Universal certificate.
2. Creating them needs DNS automation, which this ADR forbids.
3. A preview runs unmerged code on a shared Pi next to the homelab's internal apps, and each preview competes for the 2.5 GB tenant budget.

**Decision.**

- Pull request previews run as an ephemeral `kind` cluster inside GitHub Actions, using the same `atelierctl bootstrap kind` path contributors use. The job runs the smoke tests and the k6 smoke scenario, then the cluster is destroyed with the runner.
- The homelab only ever runs signed release tags, deployed by Argo CD. There are no `atelier-preview-*` namespaces and no per-PR hostnames.
- To click through a change before merging, run the stack locally on `kind`.

**Consequences.** We lose "click a URL for this PR". We gain a smaller attack surface (R12, R13), no DNS or certificate work, and a CI job that continuously proves anyone can bring the stack up (P13). If shareable previews are wanted later, build them on the Azure core in an isolated namespace behind Cloudflare Access.

## Alternatives considered

- Advanced Certificate Manager (paid) for `*.ebahn.fuhro.network`: costs money and still needs DNS automation.
- A scoped Cloudflare token for DNS-01: Cloudflare tokens can be limited to a zone, not to a record name, so the token could still rewrite homelab records.
- Previews on the Pi behind Cloudflare Access: solves who can see them, not what they run.

## Pi-vs-Azure note

Edge uses Cloudflare's certificate and no in-cluster issuer. Core uses cert-manager and Azure DNS. The contrast is deliberate.

## Interview probe

"Where does TLS terminate, and who can read the plaintext?" The answer names Cloudflare's edge, the encrypted tunnel leg, the in-node plain HTTP hop, and the go-live implication.
