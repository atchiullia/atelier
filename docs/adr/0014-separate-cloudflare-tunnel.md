# ADR-0014: Separate Cloudflare Tunnel for Ebahn

- **Status:** Accepted, including Amendments 1 and 2 (Giullia, 2026-10-10).
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** NET, SEC, HYB

## Context

Ebahn is a public demo (`ebahn.fuhro.network`, showcases only) running as a guest tenant on a shared Raspberry Pi 5 cluster. The DNS zone is shared with the homelab, and Cloudflare API tokens are scoped to a zone, not to a record. Any path from the internet into the cluster must not be able to reach the homelab's internal apps.

## Decision

Ebahn gets its own Cloudflare Tunnel (own tunnel ID, credentials and connector), one ingress rule for `ebahn.fuhro.network`, no private-network routes, no Cloudflare API token on the tenant, and no DNS automation on the shared zone. The connector runs with zero replicas outside showcases. Full control list: SPEC.md §16.6.

## Amendment 1: TLS on the edge, Cloudflare Origin CA on the last hop (resolves Q12)

**Status:** Accepted (2026-10-10). Option C chosen by the owner (revised from the first draft, which used plain HTTP on the last hop).

**Problem.** The original networking table had cert-manager issuing Let's Encrypt certificates by DNS-01 on the edge. DNS-01 needs a DNS API token for the zone, which this ADR forbids. HTTP-01 cannot be used either, because the tunnel connector is off between showcases.

**Decision.**

- The public certificate is Cloudflare's edge certificate. `ebahn.fuhro.network` is a first-level subdomain of the zone, so Universal SSL covers it.
- Cloudflare to `cloudflared` is encrypted by the tunnel itself.
- `cloudflared` to `atelier-gw` is **HTTPS**, using a **Cloudflare Origin CA certificate** issued for exactly `ebahn.fuhro.network` (no wildcard). Key type ECDSA, validity one year.
- The private key is generated on the owner's machine with `openssl`. Only the CSR is pasted into the Cloudflare dashboard (SSL/TLS, Origin Server, Create Certificate, "Use my private key and CSR"). Cloudflare never holds the key.
- The certificate and key are stored as a `kubernetes.io/tls` Secret named `atelier-gw-origin-tls` in `atelier-edge`. In Git it exists only as a SOPS/age-encrypted file in the private env repo. The Gateway HTTPS listener references it.
- `cloudflared` verifies the gateway: `originRequest.originServerName: ebahn.fuhro.network` and `originRequest.caPool` pointing at Cloudflare's published Origin CA root (a public file, mounted from a ConfigMap). `noTLSVerify` is forbidden.
- No ACME issuer, no DNS token and no cert-manager resources on the edge tenant. Creating an Origin CA certificate does not change the zone's SSL settings, which stay with the homelab.
- Rotation is manual, once a year. Until the Phase 6 expiry alert exists, a calendar reminder 30 days before expiry is the control. An expired certificate makes `cloudflared` return 502; the impact is limited because the demo is up only during showcases.
- With more than one edge node nothing changes: the last hop is already encrypted. Cilium transparent encryption stays a homelab-level option, not a requirement.
- Azure core is unchanged: cert-manager with DNS-01 against Azure DNS through workload identity, owned entirely by this project.

**Consequences.**

- Cloudflare terminates public TLS, so it sees request plaintext. That is acceptable with test data and a public demo. It must be revisited at go-live because real customer data would then transit a third-party processor (LGPD/GDPR processor terms). It is on the go-live checklist in SPEC.md section 13.
- The Origin CA certificate is trusted only by Cloudflare. A browser that reached the gateway directly would reject it, which is fine because the gateway is not exposed.
- One manual step per year, and a private key held in an encrypted Secret instead of nothing.

**Alternatives considered.**

- Plain HTTP on the last hop (first draft): simplest, but the final hop is unencrypted on a shared node.
- Namespaced CA `Issuer`: needs cert-manager on the shared cluster. Atelier does not own cert-manager there and must not install cluster-scoped components.
- Let's Encrypt via DNS-01: needs a zone-wide DNS token (forbidden) and adds nothing, since visitors already get Cloudflare's certificate.
- Let's Encrypt via HTTP-01: renewal fails whenever the tunnel is down.

**Interview probe.** "Who can read the traffic at each hop?" Answer: visitor to Cloudflare under Cloudflare's certificate; Cloudflare to the cluster inside the tunnel; connector to gateway under an Origin CA certificate whose key never left my machine; Cloudflare sees plaintext, which is why real customer data waits for a processor review.

## Amendment 2: no per-PR environments on the homelab (resolves Q13)

**Status:** Accepted (2026-10-10). Option 1 with option 2 as a complement. The rule applied: the choice must not open an attack surface.

**Problem.** The plan was per-PR hostnames `pr-N.ebahn.fuhro.network` plus per-PR namespaces. That fails on three counts:

1. Those names are two levels below the zone, outside the free Universal certificate.
2. Creating them needs DNS automation, which this ADR forbids.
3. A preview runs unmerged code on a shared Pi next to the homelab's internal apps, and each preview competes for the 2.5 GB tenant budget.

**Decision.**

- Pull request previews run as an ephemeral `kind` cluster inside GitHub Actions, using the same `atelierctl bootstrap kind` path contributors use. The job runs the smoke tests and the k6 smoke scenario, then the cluster is destroyed with the runner.
- To click through a change before merging, the owner runs the stack locally on `kind` (complement). Nothing is exposed beyond the owner's own machine.
- The homelab only ever runs signed release tags, deployed by Argo CD. There are no `atelier-preview-*` namespaces and no per-PR hostnames.
- The preview job runs unmerged code, so it is hardened:
  1. No secrets. In particular it never receives `PATTERNS_TOKEN`; that secret is used only by the `leak-gate` workflow.
  2. `permissions: contents: read` and nothing more.
  3. The trigger is `pull_request`, never `pull_request_target`. Pull requests are restricted to collaborators, and fork workflows still need approval.
  4. Nothing is published from the runner. Ports are used only inside the job.
  5. Test artifacts contain synthetic data and redacted output only, because artifacts on a public repo are public.
  6. Third-party Actions are pinned by SHA in Phase 6, because the runner's supply chain is the remaining risk.
- Optional: run the job on an arm64 runner as well as x86, to exercise the architecture the Pi uses.

**Consequences.** We lose "click a URL for this PR". For previews we need no per-PR DNS records and no per-PR certificates, and no unmerged code ever runs on the shared homelab node, which keeps R13 (a workload becoming a pivot into fuhro's internal apps) from growing. The risk moves to the GitHub runner, where it is limited by the hardening list above. The CI job also continuously proves that anyone can bring the stack up (P13). If shareable previews are wanted later, that is a new decision: it would open a public endpoint running unmerged code, so it would need its own ADR, the Azure core in an isolated namespace, and Cloudflare Access.

## Alternatives considered

- Advanced Certificate Manager (paid) for `*.ebahn.fuhro.network`: costs money and still needs DNS automation.
- A scoped Cloudflare token for DNS-01: Cloudflare tokens can be limited to a zone, not to a record name, so the token could still rewrite homelab records.
- Previews on the Pi behind Cloudflare Access: solves who can see them, not what they run.
- Previews on the Azure core behind Cloudflare Access: opens a public endpoint running unmerged code and costs money; deferred to a future ADR.

## Pi-vs-Azure note

Edge uses Cloudflare's edge certificate and a hand-issued Origin CA certificate, with no in-cluster issuer. Core uses cert-manager and Azure DNS. The contrast is deliberate.

## Interview probe

"Where does TLS terminate, and who can read the plaintext?" The answer names Cloudflare's edge, the encrypted tunnel leg, the Origin-CA-protected last hop, and the go-live implication.
