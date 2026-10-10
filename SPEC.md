# SPEC.md — Fashion E-Commerce Platform & Black Friday-Grade Kubernetes Platform

> **Single source of truth.** If a decision, scope item, SLO or phase is not in this file (or an ADR it links to), it is not agreed. Every change to scope, architecture or roadmap is a PR against this file.

| Field | Value |
|---|---|
| Status | `DRAFT v0.8` — Phase 0 artefacts written (walkthrough, leakcheck, ADRs); v1.0 pending Q3, Q10 and approval of ADR-014 amendments / ADR-016 (§15) |
| License | Code **Apache-2.0**; docs **CC BY 4.0**; brand assets & real catalog **all rights reserved, never in the public repo** (§16) |
| Owner | Giullia Lazaro (`atchiullia`) |
| Mentor/pair | Claude (senior platform architect role) |
| Created | 2026-10-09 |
| Working name | **Atelier** (platform) / **Ebahn** (brand store) — public demo at `ebahn.fuhro.network` |
| Repo layout | monorepo `atelier/` — see §6.5 |
| Conventions | ADRs in `docs/adr/`, runbooks in `docs/runbooks/`, postmortems in `docs/postmortems/` |

---

## 1. Vision

Build and operate a **real, production-grade fashion e-commerce platform** for Giullia's own clothing brand, where every garment carries structured, queryable metadata; where the latest Paris Fashion Week trends are extracted into the *same* metadata schema; and where a matching service curates a "Trending now, from our collection" landing page that regenerates as trends change.

Underneath, run it on a **two-region hybrid platform** — the `fuhro-network` Raspberry Pi 5 homelab as the *edge region* and Azure AKS as the *core region* — with a single GitOps source of truth, eBPF networking, progressive delivery, SLO-driven observability, supply-chain security, and a repeatable **Black Friday simulation** (load + chaos game days) proving the system survives a busy season.

Two outcomes, equally weighted:

1. **Product:** a demo-grade store that can be switched to real customers later with minimal rework.
2. **Career:** demonstrable evidence for Platform / Cloud Networking / Kubernetes roles (Farfetch-style requirements, §10 mapping), with each phase producing portfolio artefacts (README section, diagram, write-up, CV bullet).

### 1.1 Guiding principles

- **Boring by default, cutting-edge where the industry is clearly going:** GitOps, eBPF/Cilium, Gateway API, OpenTelemetry, workload identity, SLOs.
- **Always demoable:** every phase leaves `main` deployable to the homelab.
- **Networking is a discipline, not plumbing:** every packet path from browser to database must be explainable and traceable.
- **Homelab ≠ cloud, on purpose:** every ARM64/RAM/SD-I/O constraint that forces a different choice than Azure is written down as a learning asset.
- **Metadata is code:** schemas are versioned, validated and tested.
- **Cost is a feature:** visible, budgeted, scale-to-zero by default.
- **Open source by design, isolated by design:** the public repo must be runnable by a stranger on a `kind` cluster, and must contain *nothing* that identifies, reaches, or weakens `fuhro-network`. Atelier is a **guest tenant** on the homelab, never a co-owner of it (§16).

---

## 2. Constraints & Assumptions

| # | Constraint / assumption | Source | Impact |
|---|---|---|---|
| C1 | Azure budget ceiling **≈ US$50 / month** | Giullia | AKS runs scale-to-zero outside sessions; Front Door/WAF only during game days; aggressive teardown automation (§12). |
| C2 | **15+ h / week** available | Giullia | Roadmap of **~16 weeks** (§10). |
| C3 | **Portfolio/demo first**; real customers later | Giullia | Sandbox payments (Stripe test mode), synthetic customers, PCI scope minimised; LGPD obligations designed-in but not yet operational. |
| C4 | Storefront = **Go backend rendering HTML templates** (`html/template` + HTMX for interactivity) | Giullia | Maximises Go practice; frontend polish is secondary; SSR is natural. |
| C5 | Edge region = `fuhro-network`, Raspberry Pi 5, **upstream Kubernetes via kubeadm**, ARM64, FOSS only | Giullia | All images multi-arch (`linux/amd64,linux/arm64`); memory-tight; SD/NVMe I/O is the first bottleneck. |
| C6 | Core region = **Azure AKS**, Terraform-provisioned | Giullia | Hub/spoke VNets, private endpoints, workload identity. |
| C7 | Trend data only from **legitimate public sources** (RSS, official APIs, editorial pages honouring robots.txt and ToS); no paywalls/logins; responsible caching | Giullia / ethics | Trend corpus is text-first; runway imagery is referenced by URL, not stored. |
| C8 | Python for data/ML services; Go for storefront + at least one internal CLI | Giullia | Two language toolchains in CI. |
| C9 | Vision-language model for metadata first pass; human review before publish | Giullia | API cost counted in C1; local model fallback evaluated. |
| C12 | **59 product photos, PNG**; angles-per-piece unknown until ingest | Giullia (Q2) | Batch ingestion; PNG → WebP/JPEG variants; piece grouping decided during review (§5.2). |
| C13 | Brand **Ebahn**, demo URL `ebahn.fuhro.network`, **public only during showcases** | Giullia (Q1, Q6) | Hostname is a deliberate public fact; the Cloudflare zone is shared with fuhro-network, so Atelier gets **no DNS write access** (§7.2); tunnel connector is scaled to 0 outside showcases. |
| C14 | fuhro-network's existing services **all keep running**; Atelier **shares the single Pi 5** at first | Giullia (Q4, Q8) | Hard ResourceQuota for the tenant; edge stack trimmed (§6.4); ADR-012 accepted as shared-cluster tenancy. |
| C15 | VLM = **Anthropic Claude** (vision); no Keycloak — **Microsoft Entra** for identity | Giullia (Q5, Q11) | Identity lives in Azure, not on the Pi (saves ~1 GB RAM, removes a service from the tenant); Claude has no embeddings API → local open embedding models (§5.2). |
| C16 | **Cloudflare** account available (DNS, Tunnel) | Giullia (Q7) | Cloudflare is the default global edge; Azure Front Door only as a game-day experiment (ADR-009). |
| C10 | Project is **open source to read, clone and run, with contributions closed**: public GitHub repo under `atchiullia`, only Giullia opens pull requests | Giullia | Public/private repo split, secret-scanning gates, synthetic sample data, runnable by anyone on `kind`; PR creation restricted to collaborators (§16.3). |
| C11 | Must **not weaken fuhro-network's Zero Trust posture or expose its internal apps** | Giullia | Atelier runs as an isolated tenant: own namespaces, own identity tenant (Entra External ID), own ingress/tunnel, own WireGuard peer, no cluster-scoped ownership on the homelab (§16). |
| A3 | Most recent PFW at project start = **Paris Fashion Week Spring/Summer 2027 womenswear (late Sep – early Oct 2026)** | calendar | Trend ingestion v1 targets this season; schema holds `season` so later seasons append. |

---

## 3. Success Criteria (Definition of Done for the whole project)

**Product**

- P1. ≥ 95 % of brand pieces have reviewed, schema-valid metadata (v1 schema, §5.1) and text+image embeddings.
- P2. Trend ingestion produces ≥ 25 distinct, sourced trend objects for the target PFW season in the shared schema.
- P3. Matching service returns ranked, *explained* matches; the curated landing page regenerates automatically within 15 min of a trend update.
- P4. Full funnel works end-to-end: PLP → PDP → cart → sandbox checkout → order created → inventory decremented → confirmation page, with OIDC login via Entra External ID.

**Platform**

- P5. Both regions reconcile from one Git repo via ArgoCD; a change merged to `main` reaches the homelab with no manual `kubectl`.
- P6. Black Friday game day: the defined traffic shapes (§9) run against the core region while meeting SLOs (§8) **or** breaches are documented with a fix and a re-run that passes.
- P7. At least 4 chaos experiments executed with postmortems.
- P8. All images signed (cosign) and SBOM'd; Kyverno blocks unsigned images; default-deny network policies in every app namespace.
- P9. Every packet path (browser → Front Door → AKS Gateway → service → PgBouncer → Postgres; homelab ↔ Azure over WireGuard) is documented with a diagram and verified with Hubble/tcpdump evidence.
- P10. Monthly Azure spend ≤ US$50 in every month, evidenced by cost reports.

**Career**

- P11. Eight portfolio write-ups (one per phase), one architecture overview, and an interview narrative built around the game day.
- P12. Every Farfetch requirement in §10.1 maps to at least one shipped artefact.

**Open source & isolation**

- P13. A stranger can clone the public repo and run the full stack with synthetic data on `kind` via `atelierctl bootstrap kind` in under 30 minutes, with zero access to Giullia's accounts or homelab.
- P14. Secret scanning (gitleaks) and a "fuhro-leak" grep gate (§16.3) pass on every commit in history; a one-off history audit is done before the repo goes public.
- P15. An isolation test suite proves that, from any Atelier pod on the homelab, fuhro-network internal services, LAN ranges and internal DNS names are unreachable (Hubble-verified), and vice versa — including from the Ebahn `cloudflared` connector, and that the Ebahn tunnel has no private-network routes (§16.6).

---

## 4. Scope

### 4.1 In scope

Catalog + metatag engine; trend ingestion; matching/ranking; curated landing page; storefront (PLP, PDP, cart, checkout, account); order + inventory services; Entra OIDC; sandbox payments; two Kubernetes regions; Terraform for Azure; GitOps; Cilium/Gateway API networking; WireGuard site-to-site; Front Door/WAF (game days); autoscaling (HPA/KEDA/cluster); caching; observability stack; supply-chain security; k6 load suite; chaos experiments; ADRs; runbooks; docs site; Go CLI `atelierctl`.

### 4.2 Out of scope (v1)

Real payments and real customer PII; returns/refunds workflow; multi-currency/tax engines; recommendation personalisation per user; mobile apps; Backstage (re-evaluate after Phase 7); service mesh beyond what Cilium provides (SPIFFE/SPIRE only if an ADR justifies it); multi-cloud beyond Azure; storing runway imagery.

---

## 5. Product Specification

### 5.1 Metadata schema v1 (shared by products **and** trends)

Defined as Pydantic models in `libs/schema/` and exported to JSON Schema (`schemas/garment-v1.json`). Breaking changes bump the major version and ship a migration.

```yaml
GarmentMetadata (v1):
  id: uuid
  kind: enum [product, trend]           # same shape, different origin
  schema_version: "1.0"
  garment_type: enum [dress, top, shirt, blouse, trousers, skirt, jacket, coat, knitwear, suit, jumpsuit, accessory, footwear, other]
  silhouette: enum [fitted, straight, a-line, oversized, boxy, draped, column, bias-cut, voluminous, tailored, other]
  cut_details: list[str]                 # e.g. ["dropped shoulder", "asymmetric hem"]
  fabric: list[enum [cotton, linen, silk, wool, denim, leather, satin, sheer, knit, technical, jersey, velvet, lace, other]]
  texture: list[str]
  colors:
    dominant: ColorRef                   # {name: normalized vocab (ISCC-NBS-like, ~40 names), hex: "#RRGGBB"}
    accents: list[ColorRef]
  pattern: enum [solid, stripe, check, floral, animal, abstract, logo, polka, other]
  season: {year: int, season: enum [SS, AW, resort, pre-fall]}
  styling_context: list[enum [daywear, eveningwear, office, streetwear, resort, occasion, athleisure]]
  mood: list[str]                        # free vocabulary, lower-cased, deduped
  brand: str
  price_tier: enum [entry, mid, premium, luxury] | null   # null for trends
  description: str                       # ≤ 600 chars, human-reviewed for products
  sources: list[SourceRef]               # trends only: {url, publisher, retrieved_at, license_note}
  review: {status: enum [draft, reviewed, published], reviewer, reviewed_at}
  embeddings: {text: vector(1024), image: vector(768) | null}   # stored in pgvector, not in JSON
```

Rules: colors must come from the normalised vocabulary (`libs/schema/colors.yaml`); free-text fields are lower-cased and trimmed; every trend must have ≥ 1 source; products cannot be `published` without `reviewed`.

### 5.2 Catalog + metatag engine

- **Input:** photos in `data/raw/<sku>/*.png` (C12). Ingestion normalises to WebP/JPEG, strips EXIF GPS, resizes variants (thumb/medium/full) to object storage (MinIO on homelab, Azure Blob in core).
- **First pass:** **Anthropic Claude** vision model (ADR-003) called with the JSON Schema as a tool definition so the output is schema-valid by construction; a deterministic colour extractor (k-means on the garment mask) cross-checks `colors`. Embeddings come from **local open models** (text: `bge-m3` or `e5`; image: `SigLIP`/`CLIP` via ONNX, run as a batch job on the core region or a laptop — not on the Pi). The pipeline has a `stub` provider so anyone can run it without an API key.
- **Input reality (C12):** 59 PNGs; ingest converts to WebP + JPEG variants, groups photos into pieces (`sku`) during review, and strips metadata.
- **Review:** CLI `atelierctl catalog review <sku>` opens the draft, shows the image path and validation errors, and sets `review.status`. Nothing reaches the storefront unpublished.
- **Storage:** Postgres (`products`, `product_metadata` JSONB validated by trigger against the schema version, `product_embeddings` with pgvector HNSW index).
- **API:** `catalog-api` (Python/FastAPI) — filter queries (`?garment_type=&colors.dominant=&season=`) and `POST /similar` (vector search with optional filters).

### 5.3 Trend intelligence

- **Sources (allow-list in `services/trend-ingest/sources.yaml`):** editorial RSS feeds and public review pages (e.g. fashion-press sites, brand press releases, show notes) — each entry records ToS check date and robots.txt result. Anything behind a login/paywall is rejected at config-validation time.
- **Pipeline (worker, Python):** fetch → dedupe (content hash) → extract candidate trend statements with an LLM constrained to the v1 schema → cluster near-duplicates by embedding → persist as `kind=trend` with sources → emit `trend.updated` event.
- **Politeness:** per-host rate limit (≤ 1 req / 5 s), conditional GET (ETag/If-Modified-Since), cache TTL 24 h, identifiable User-Agent with contact.
- **Output:** trend objects queryable like products; a `trend_snapshots` table so the landing page can be reproduced for any date.

### 5.4 Matching / ranking

`match-svc` (Python) scores each published product against the active trend set:

`score = 0.45·cosine(text_emb) + 0.25·cosine(image_emb vs trend text via CLIP) + 0.30·structured_overlap(colors, silhouette, fabric, styling_context)`

Weights live in config and are A/B-able. Each result carries an **explanation** (`"matches 'liquid satin, column silhouette' — dominant color 'oxblood' appears in 3 SS27 shows"`) generated from the overlapping fields plus source links. Results are cached in Redis and published as `curation.updated`.

### 5.5 Storefront & commerce

| Capability | Behaviour |
|---|---|
| Landing page | "Trending now, from our collection": top-N matches with explanations; rebuilt on `curation.updated`; served from cache; falls back to last good snapshot. |
| PLP / PDP | Filters driven by schema enums; PDP shows metadata, "why it's on-trend", similar items. |
| Cart | Server-side session (Redis), HTMX partials. |
| Auth | **Microsoft Entra External ID** (CIAM tenant, free tier) as the customers' OIDC provider — PKCE, no shared cookie domain with anything fuhro; **Entra ID workforce** app registration for admin/`atelierctl`; guest checkout allowed in demo. No Keycloak on the homelab (ADR-013). |
| Checkout | Stripe test mode (hosted Checkout Session → webhook); never touches card data. |
| Orders | `order-svc` (Go): creates order, emits `order.placed`; idempotency key on checkout. |
| Inventory | `inventory-svc` (Go): consumes `order.placed`, reserves stock, emits `inventory.reserved` / `inventory.rejected`; compensating `order.cancelled`. |
| Degradation | If `order-svc` or payments are unhealthy the gateway flips the store to **read-only catalog mode** (banner + disabled checkout). |

---

## 6. Architecture

### 6.1 Services

| Service | Lang | Responsibility | Scaling signal |
|---|---|---|---|
| `storefront` | Go | SSR HTML, HTMX, cart, OIDC client | RPS (HPA) |
| `catalog-api` | Python/FastAPI | Products, filters, vector search | RPS |
| `trend-ingest` | Python worker | Source fetching, extraction, clustering | CronJob + KEDA on queue |
| `match-svc` | Python | Scoring, explanations, curation snapshots | Event-driven (KEDA) |
| `order-svc` | Go | Orders, checkout orchestration, Stripe webhooks | Queue depth (KEDA) |
| `inventory-svc` | Go | Stock, reservations | Queue depth (KEDA) |
| `atelierctl` | Go CLI | Dev golden paths: bootstrap, review, deploy, loadtest, teardown | — |

### 6.2 Data & messaging

Postgres 16 + pgvector (CloudNativePG operator in both regions; PgBouncer in front); Redis (cache, sessions); **NATS JetStream** for events (ADR-004: chosen over Kafka/Redpanda for Pi memory footprint; revisit if partition-ordering needs grow); MinIO (edge) / Azure Blob (core) for images.

### 6.3 Events

`trend.updated`, `curation.updated`, `order.placed`, `inventory.reserved`, `inventory.rejected`, `order.paid`, `order.cancelled`. CloudEvents envelope, JSON payload versioned alongside the schema.

### 6.4 Regions

| | Edge — `fuhro-network` | Core — Azure |
|---|---|---|
| Cluster | **Guest tenant** on the existing fuhro-network kubeadm cluster (Pi 5, ARM64) — or a dedicated node/cluster if Q8 allows | AKS, system pool B2s/B2ps (ARM, cheaper), user pool scale-to-zero — fully owned by Atelier |
| Ownership | fuhro-network owns Cilium, ArgoCD, cert-manager, external-dns, monitoring. Atelier owns only `atelier-*` namespaces. | Atelier owns everything, provisioned from the public repo |
| Role | Dev/staging, always-on demo, chaos sandbox (namespace-scoped chaos only) | Production-shaped target for Black Friday game days |
| Ingress | Dedicated Gateway (`atelier-gw`) in `atelier-edge`; **own Cloudflare Tunnel** (separate tunnel ID/token) routing only `ebahn.fuhro.network`; `cloudflared` **0 replicas by default**, scaled up by `atelierctl showcase start` | Azure LB → Cilium Gateway API; Cloudflare in front by default, Front Door + WAF as a game-day experiment |
| Edge footprint | Trimmed: no Keycloak, no Loki/Tempo (metrics-only via Prometheus agent → core), embeddings computed off-Pi, Postgres single-instance with small `shared_buffers`; target ≤ **2.5 GB RAM** for the whole tenant | Full stack |
| Storage | PVCs from the cluster's existing StorageClass, quota-limited | Azure Disk CSI |
| Secrets | External Secrets → Azure Key Vault over the Atelier WireGuard peer (SOPS/age fallback); never fuhro's secret stores | External Secrets → Key Vault via workload identity |
| Reference edge | **`kind` cluster** (public, runnable by anyone) stands in for the homelab in docs and CI | — |

### 6.5 Repository layout — public / private split

**Public: `github.com/atchiullia/atelier`** (Apache-2.0)

```
atelier/
  SPEC.md                      # this file
  LICENSE  CONTRIBUTING.md  SECURITY.md  CODE_OF_CONDUCT.md
  docs/{adr,runbooks,postmortems,diagrams,writeups}/
  libs/schema/                 # Pydantic + JSON Schema + colors.yaml
  services/{storefront,catalog-api,trend-ingest,match-svc,order-svc,inventory-svc}/
  tools/atelierctl/
  infra/terraform/{modules,envs/core}/        # Azure only; no homelab Terraform
  platform/core/               # ArgoCD app-of-apps for AKS: cilium, cert-manager, external-dns, eso, keda, argo-rollouts, kyverno, monitoring, cnpg, nats, redis
  platform/kind/               # minimal platform for the reference edge anyone can run
  apps/{base,overlays/kind,overlays/core}/    # Kustomize per service — NO homelab overlay here
  data/sample/                 # synthetic catalog (CC0 images or generated), synthetic trends
  loadtest/k6/  chaos/
  .github/workflows/           # incl. gitleaks + fuhro-leak gate
```

**Private: `atchiullia/atelier-env-fuhro`** (never public, lives alongside fuhro-network's own repo)

```
atelier-env-fuhro/
  argocd/appproject-atelier.yaml       # AppProject: allowed repos, destinations = atelier-* namespaces only
  argocd/applicationset.yaml           # sources: public repo pinned by tag/SHA + this overlay
  overlays/edge/                        # Kustomize overlay: hostnames, tunnel connector, storage class, quotas
  policies/                             # CiliumClusterwideNetworkPolicy: atelier ↔ fuhro deny
  secrets/*.sops.yaml                   # age-encrypted; keys never leave the homelab
  wireguard/                            # Atelier peer config (restricted AllowedIPs)
  leak-patterns/                        # patterns.txt, suggestions.txt, manual.txt, allow.txt (ADR-016)
  tools/collect-patterns.py             # builds the pattern list; prints counts only
```

**Private: `atchiullia/atelier-brand-data`** — real product photos, reviewed metadata, trend corpus. Mounted at ingest time only; never published.

---

## 7. Platform Specification

### 7.1 Delivery (GitOps)

- ArgoCD in each region, **ApplicationSets** generate per-service apps from `apps/overlays/<region>`. On the homelab the ApplicationSet lives in the private env repo, uses an **AppProject** restricted to `atelier-*` namespaces, denies cluster-scoped resources, and pins the public repo by **signed tag or commit SHA** (never a branch) so a bad merge to the public repo (or a compromised account) can never auto-deploy to the homelab.
- Image promotion by digest via CI PR to the overlay (no `latest`).
- **Argo Rollouts** canary (10 % → 50 % → 100 %) with AnalysisTemplates on Prometheus: error rate < 1 %, p95 < SLO; auto-rollback.
- CI (GitHub Actions): lint/test → multi-arch build (buildx) → Trivy/Grype scan → syft SBOM → cosign sign (keyless, OIDC) → push GHCR → PR to overlay. Terraform: `fmt`/`validate`/`tflint`/`checkov` + `plan` on PR, `apply` on merge with OIDC federation to Azure (no static secrets).
- Preview environments: **none on the homelab** (ADR-014 Amendment 2). Each pull request gets an ephemeral `kind` cluster inside GitHub Actions (same path as `atelierctl bootstrap kind`) running smoke tests and the k6 smoke scenario, destroyed with the runner. The homelab only runs signed release tags.

### 7.2 Networking (first-class)

| Layer | Edge | Core | Must be able to explain |
|---|---|---|---|
| CNI | Cilium, kube-proxy replacement, Hubble UI | Cilium (BYO CNI on AKS) | eBPF datapath vs iptables; conntrack under load |
| L7 | Gateway API (`GatewayClass` cilium), HTTPRoute per service, rate limiting, timeouts, retries | same + Front Door origin | L4 LB → Gateway → Service → Pod hops |
| DNS | **No external-dns on edge**: Cloudflare API tokens are zone-scoped, and the zone `fuhro.network` is shared, so a token for Atelier would be able to rewrite fuhro records. The `ebahn` CNAME → tunnel is created once from the private repo. CoreDNS tuning (NodeLocal DNSCache) | external-dns → Azure DNS (own zone, e.g. `core.ebahn.<brand-domain>` once a brand domain exists); private DNS zones | Blast radius of API tokens; DNS failure modes, ndots, negative caching |
| TLS | **Cloudflare edge certificate** terminates public TLS; Cloudflare→`cloudflared` is encrypted by the tunnel; `cloudflared`→`atelier-gw` is plain HTTP inside the single node. No ACME issuer and no DNS token on the tenant (ADR-014 Amendment 1) | cert-manager DNS-01 against Azure DNS via workload identity; Front Door managed certs when used | Where TLS terminates and who can read plaintext; HTTP/2; session resumption |
| Site-to-site | **WireGuard** as a dedicated *Atelier* peer (pod in `atelier-net` or its own netns on the Pi), `AllowedIPs` = Atelier pod/service CIDR slice **only**; fuhro LAN and internal CIDRs never advertised; Pi initiates outbound | hub VNet with WireGuard VM, spoke VNet for AKS, NSGs, UDRs; Azure Firewall only during game days (cost) | Routing tables, MTU/MSS clamping, split tunnel, why AllowedIPs is the real firewall |
| Private access | — | Private endpoints for Key Vault, Blob, Postgres (if managed) | Why private endpoints, DNS for them |
| Zero Trust | Default-deny `CiliumNetworkPolicy` per namespace; L7-aware policies; Cilium mTLS (WireGuard transparent encryption) for pod-to-pod | same | Identity-based vs IP-based policy; when SPIFFE/SPIRE is justified |
| Evidence | Hubble flow exports + `tcpdump` captures stored in `docs/diagrams/packet-paths/` | | |

### 7.3 Scalability & resilience

HPA on RPS/CPU; KEDA scalers on NATS consumer lag; AKS cluster autoscaler with user pool min 0; PDBs for every Deployment; topology spread across zones (core); requests/limits derived from VPA recommendations after load tests; Redis cache-aside with stale-while-revalidate for landing/PLP; PgBouncer transaction pooling; gateway rate limits per IP and per route; circuit breaking via Go client (`sony/gobreaker`) with read-only degradation; order queue as load leveller.

### 7.4 Observability

OpenTelemetry SDK in every service (traces, metrics, logs with trace IDs) → OTel Collector → Prometheus (kube-prometheus-stack), **Tempo**, **Loki**; Grafana dashboards: SLO burn-rate, RED per service, USE per node, business funnel (views → carts → orders); Hubble for flows; alerting (Alertmanager → ntfy/Telegram) with each alert linking a runbook; **OpenCost** + Azure Cost Management export, weekly cost report in `docs/writeups/cost/`.

### 7.5 Security & compliance

Supply chain as in §7.1; **Kyverno** policies: verify cosign signatures, require requests/limits, disallow `latest`, enforce Pod Security `restricted`; External Secrets Operator + Key Vault; Azure Workload Identity for all cloud access; RBAC least privilege with per-team namespaces; audit logging to Loki; threat model (STRIDE, 1 page) in `docs/security/threat-model.md`; compliance map: PCI-DSS SAQ-A posture via hosted Stripe Checkout (card data never enters our systems), LGPD/GDPR data inventory and retention policy for when real customers arrive (C3).

### 7.6 Developer platform

`atelierctl` golden paths: `bootstrap edge|core`, `catalog ingest|review`, `trends run`, `deploy <svc>`, `loadtest <scenario>`, `gameday start|stop`, `teardown core`; service template (`templates/service-go`, `templates/service-python`) with OTel, health probes, Dockerfile, Kustomize base pre-wired; docs site (MkDocs Material) built from `docs/`; ADR required for every item flagged `ADR-xxx` here.

---

## 8. SLOs (defined before load testing)

| SLI | SLO (28-day window) | Measured at |
|---|---|---|
| Storefront availability (non-5xx) | 99.5 % | Gateway |
| Landing/PLP latency | p95 < 300 ms, p99 < 800 ms | Gateway |
| PDP latency | p95 < 400 ms | Gateway |
| Checkout success rate (started → order created, excluding declined test cards) | 99 % | `order-svc` |
| Order event processing lag | p95 < 5 s | NATS consumer |
| Curation freshness | landing rebuilt ≤ 15 min after `trend.updated` | `match-svc` |

Error budget policy: burn-rate alerts at 14.4× (1 h) and 6× (6 h); a breached budget freezes feature work in favour of reliability for the next sprint.

---

## 9. Black Friday Simulation

**Traffic model (k6, `loadtest/k6/`):** virtual-user journeys with think times — *browser* (landing → PLP → PDP, 60 %), *shopper* (adds to cart, 30 %), *buyer* (completes checkout with Stripe test card, 10 %).

| Scenario | Shape | Pass criteria |
|---|---|---|
| Baseline | 20 VUs, 15 min | establishes p95 reference |
| Ramp | 0 → 500 VUs over 20 min, hold 20 min | SLOs hold; autoscaling observed |
| Spike (door-buster) | 50 → 1 500 VUs in 60 s, hold 5 min | ≤ 1 % errors; read-only mode never triggers falsely |
| Sustained peak | 800 VUs, 60 min | no memory growth, no pool exhaustion |
| Flash sale | spike on a single SKU | inventory never oversold; idempotency holds |

**Chaos (Chaos Mesh, during sustained peak):** pod-kill `order-svc`; node drain user pool; 200 ms latency + 5 % loss to Postgres; DNS failure for Redis; Stripe webhook outage (mock). Each run → `docs/postmortems/YYYY-MM-DD-<experiment>.md` (impact, timeline, detection time, root cause, fix, re-run result).

**Cost guard:** game days run on a dedicated day, cluster scaled up ≤ 4 h, Front Door/WAF enabled only for that window, torn down by `atelierctl gameday stop`.

---

## 10. Roadmap (16 weeks @ 15 h/week ≈ 240 h)

### 10.1 Requirement mapping key (Farfetch-style)

`NET` cloud networking · `IAC` Terraform/IaC · `K8S` Kubernetes & k8s networking · `CICD` Git workflows & CI/CD (ArgoCD) · `LANG` Python/Go tooling · `SEC` security & compliance · `OBS` observability/monitoring · `DOC` standards & documentation · `HYB` hybrid/Zero Trust (nice-to-have) · `LEAD` roadmap/communication.

### 10.2 Phases

| # | Phase | Weeks | Goal | Key deliverables | Learn | Evidences | Exit criteria |
|---|---|---|---|---|---|---|---|
| 0 | **Foundation, spec & open-source hygiene** | 1 | Agree spec, repos, budget and leak guardrails | SPEC.md v1.0, public repo skeleton with LICENSE/SECURITY/CONTRIBUTING, private env + brand-data repos, gitleaks + fuhro-leak CI gate, pre-commit, ADR-001/002/011/014/016, Azure budget alert at $40 | ADRs, FinOps basics, OSS hygiene, threat of public GitOps repos | DOC, LEAD, SEC | Spec approved; leak gate blocks a seeded test secret; budget alert fires in test; PR creation restricted to collaborators verified (tested after the repo goes public; GitHub Free has no branch rules on private repos, so rulesets are created right after the flip) |
| 1 | **Tenant on the edge + reference `kind` cluster + GitOps** | 2 | Atelier reconciled as an isolated tenant on fuhro-network; identical stack on `kind` for anyone who clones the repo | **Week 1 hardware inventory** (RAM, NVMe HAT, free memory under current fuhro load → sets the tenant quota), fuhro GitOps convention (AppProject-per-tenant, ADR-015), `platform/kind`, `atelier-*` namespaces + quotas, AppProject + ApplicationSet (private repo), CiliumClusterwideNetworkPolicy isolation, dedicated Gateway + tunnel connector, isolation test suite (P15), MkDocs site | Multi-tenancy, AppProject boundaries, Gateway API, Cilium identity-based policy, Hubble | K8S, CICD, NET, SEC, DOC | `hello` HTTPRoute reachable with valid TLS via Git only; P15 isolation tests green on the homelab |
| 2 | **Schema, catalog & metatags** | 2 | Products with reviewed metadata + embeddings | `libs/schema` v1 + tests, ingestion, VLM draft pipeline (ADR-003), `atelierctl catalog`, CNPG Postgres + pgvector, `catalog-api` | Data modelling, vector search, Python packaging | LANG, DOC | P1 met on real photos; API filter + similarity queries pass tests |
| 3 | **Storefront, orders, inventory, events** | 3 | Full demo funnel on edge | Go `storefront`, Entra External ID OIDC, Redis cart, NATS JetStream (ADR-004), `order-svc`, `inventory-svc`, Stripe test checkout, read-only degradation | Go services, event-driven design, idempotency, OIDC/PKCE | LANG, K8S, SEC | P4 met on edge cluster; contract tests green |
| 4 | **Trend intelligence & curation** | 2 | PFW trends in shared schema, curated landing page | `trend-ingest` with source allow-list + politeness, `match-svc` scoring + explanations, landing page auto-rebuild, trend snapshots | Responsible data collection, LLM-structured extraction, caching | LANG, DOC | P2, P3 met; sources audit documented |
| 5 | **Core region on Azure + hybrid networking** | 3 | AKS via Terraform, WireGuard to homelab, private endpoints, Front Door path | Terraform modules (hub/spoke, AKS, Key Vault, Blob, identity), policy-as-code in CI, Cilium on AKS, ESO + Key Vault, WireGuard site-to-site, packet-path diagrams with Hubble evidence | Azure networking, routing/NSG/UDR, MTU, DNS across sites, workload identity | NET, IAC, HYB, SEC, CICD | Same Git commit deploys to both regions; P9 diagrams for 3 paths; spend ≤ $50 |
| 6 | **Observability, SLOs, progressive delivery, hardening** | 2 | SLO dashboards, canary rollouts, supply-chain gates | OTel everywhere, Prometheus/Loki/Tempo/Grafana, burn-rate alerts + runbooks, Argo Rollouts canaries, cosign/SBOM/Trivy, Kyverno, default-deny policies, threat model, OpenCost | SLO math, canary analysis, admission control, STRIDE | OBS, SEC, CICD, DOC | P8 met; a bad deploy is auto-rolled back in a recorded demo |
| 7 | **Black Friday game days & narrative** | 1–2 | Prove the platform; assemble the story | k6 suite, KEDA/HPA/autoscaler tuning, Chaos Mesh runs, ≥ 4 postmortems, cost report, interview narrative, final write-ups + CV bullets | Capacity planning, chaos engineering, incident communication | K8S, NET, OBS, LEAD, DOC | P6, P7, P11, P12 met |

Phase order guarantees demoability: after Phase 1 there is a live cluster; after Phase 3 a working store; after Phase 5 a hybrid platform; Phase 7 is the capstone.

### 10.3 Per-phase ritual

1. Design: diagram + ADR(s). 2. Implement in small PRs (≤ 400 lines) with tests. 3. Verify against exit criteria. 4. Document: README section, runbooks, "built / broke / learned" write-up (LinkedIn/YouTube-ready), one CV bullet tagged with §10.1 codes. 5. Update this SPEC (status table, decision log).

---

## 11. Risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | Pi 5 memory/I-O too tight for Cilium + ArgoCD + Postgres + NATS + monitoring | H | H | NVMe HAT; trim monitoring on edge (Prometheus agent mode, short retention); run Loki/Tempo only on core; document every trade-off (principle 4) |
| R2 | Azure spend exceeds $50 | M | H | Scale-to-zero user pool, budget alert at $40 with auto-teardown action, Front Door/Firewall only during game days, weekly cost report |
| R3 | Trend-source legal/ethical issues | M | H | Allow-list with ToS/robots audit, text-only storage, politeness limits, no imagery stored, provenance on every trend |
| R4 | VLM metadata quality poor or inconsistent | M | M | Schema-constrained outputs, colour cross-check, mandatory human review, golden test set of 10 pieces |
| R5 | Scope creep (Backstage, mesh, Kafka…) | H | M | Out-of-scope list §4.2; anything new needs an ADR and a removed item |
| R6 | Cilium BYO CNI on AKS friction | M | M | Spike in Phase 5 week 1; fallback to Azure CNI Powered by Cilium (documented difference) |
| R7 | WireGuard/NAT issues from home ISP (CGNAT) | M | M | Pi initiates outbound tunnel to Azure; Cloudflare Tunnel as fallback for ingress |
| R8 | Time: 15 h/week not sustained | M | M | Phases are independently valuable; re-plan at each phase gate, never mid-phase |
| R9 | Go learning curve slows Phase 3 | M | M | Start Go with `atelierctl` in Phase 1–2; pair-program patterns; keep storefront template-based |
| R10 | Load generator (k6) saturates before the system does | M | M | Run k6 from a separate Azure VM/container job; verify generator CPU |
| R11 | Secret, hostname, IP or topology of fuhro-network leaks into the public repo or git history | M | **H** | Public/private split (§6.5), gitleaks + fuhro-leak gate, pre-commit hooks, generic `edge` naming, history audit before going public, `SECURITY.md` disclosure process |
| R12 | A bad merge or compromised account on the public repo reaches the homelab via GitOps | L | **H** | PR creation restricted to collaborators and Actions approval required for all external contributors (§16.3); passkey/hardware 2FA on the owner account; homelab ApplicationSet pins signed tags/SHAs; AppProject denies cluster-scoped resources and non-`atelier-*` destinations; branch protection with required status checks + signed commits; no PR previews run on the homelab (ADR-014 Amendment 2) |
| R13 | Atelier workload becomes a pivot into fuhro's internal apps (shared node, shared CNI) | M | **H** | Default-deny both directions via `CiliumClusterwideNetworkPolicy`; separate Entra tenant; separate tunnel; restricted WireGuard `AllowedIPs`; Pod Security `restricted`; isolation tests in CI on every edge deploy (P15); dedicated node/cluster if Q8 allows |
| R14 | Chaos experiments or load tests on the homelab disturb fuhro's internal services | M | M | Chaos scoped to `atelier-*` namespaces only (Chaos Mesh namespace-scoped mode); node-level chaos and all load tests run on Azure only; ResourceQuotas + LimitRanges on the tenant |
| R15 | Brand photos or trend corpus redistributed under an OSS license by accident | M | M | Separate private `atelier-brand-data` repo; public repo ships synthetic `data/sample/` only; CI asserts no image > 50 KB outside `data/sample/` |

---

## 12. Budget & Cost Controls (C1 = US$50/month)

| Item | Mode | Est./month |
|---|---|---|
| AKS control plane | Free tier | $0 |
| System node pool (1× B2pls_v2 ARM) | On only during work sessions (~40 h) | ~$5 |
| User node pool | Scale-to-zero; game-day bursts (2–3 × D2 for ≤ 4 h) | ~$5 |
| Storage (disks, Blob, state) | Minimal | ~$5 |
| Key Vault, DNS, Log export | Low | ~$5 |
| Azure VPN Gateway | **Avoided** — WireGuard on a B1ls VM instead | ~$4 |
| Cloudflare (DNS, Tunnel, WAF free tier, CDN) | Default global edge | $0 |
| Azure Front Door Standard + WAF | One or two game-day windows (hourly-billed base fee, ≈$0.05/h) | ~$3–5 |
| Entra External ID (CIAM) | Free tier (≤ 50 k MAU) | $0 |
| Anthropic API (Claude vision for 59 photos + trend extraction) | Batch, cached, run once per schema version | ~$3–8 |
| **Total** | | **≈ $40–50** |

Controls: Azure Budget alert at 80 % → Action Group → Function/Automation that runs `atelierctl teardown core --keep-state`; `terraform destroy` for ephemeral stacks is a first-class, tested path; weekly OpenCost + Cost Management report committed to `docs/writeups/cost/`.

---

## 13. Data, Ethics & Compliance Policy

- Trend sources: allow-listed, ToS and robots.txt verified and dated; text-only; attribution preserved; `User-Agent: AtelierTrendBot/1.0 (+contact)`; honour `Retry-After`.
- Customer data: synthetic only until go-live decision; Stripe test mode; no card data in any system; logs scrub PII fields.
- Product photos: Giullia owns rights; EXIF location stripped on ingest.
- Non-production regions never hold real customer data (edge is always non-production for PII).
- Go-live checklist (future): LGPD data inventory, privacy notice, consent, retention, DPO contact, incident process; Cloudflare as a TLS-terminating processor of customer data (ADR-014 Amendment 1).

---

## 14. Decision Log (ADR index)

| ADR | Title | Status |
|---|---|---|
| 001 | Monorepo with per-service directories | Proposed |
| 002 | Two regions: homelab edge + Azure core, one GitOps repo | Proposed |
| 003 | Anthropic Claude (tool-use, schema-constrained) for metadata drafts; local open models (bge/e5 + SigLIP) for embeddings; `stub` provider so anyone can run without a key | Accepted (Giullia, 2026-10-09) |
| 004 | NATS JetStream over Kafka/Redpanda | Proposed |
| 005 | Go `html/template` + HTMX storefront | Accepted (Giullia, 2026-10-09) |
| 006 | Cilium as CNI in both regions; Gateway API over Ingress | Proposed |
| 007 | WireGuard VM instead of Azure VPN Gateway (cost) | Proposed |
| 008 | Stripe hosted Checkout for PCI SAQ-A posture | Proposed |
| 009 | Cloudflare as default global edge (DNS, Tunnel, WAF, CDN); Azure Front Door only as a documented game-day experiment | Accepted (Giullia, 2026-10-09) |
| 010 | SPIFFE/SPIRE: not adopted unless justified | Proposed |
| 011 | Open source under Apache-2.0 with public/private repo split; Atelier as guest tenant on fuhro-network | Accepted (Giullia, 2026-10-09) |
| 012 | Shared Pi 5 cluster with Cilium tenancy (quotas + clusterwide deny policies); dedicated node is a future upgrade path | Accepted (Giullia, 2026-10-09) |
| 013 | Microsoft Entra External ID for customers + Entra ID for admin; no Keycloak on the homelab | Accepted (Giullia, 2026-10-09) |
| 014 | **Separate Cloudflare Tunnel for Ebahn** (own tunnel ID, credentials and connector); no DNS automation on the shared zone; no private-network routes on the Ebahn tunnel — see §16.6. **Amendment 1:** TLS terminates at Cloudflare, no ACME on the tenant. **Amendment 2:** no PR previews on the homelab | Accepted; amendments Proposed (2026-10-09) |
| 015 | Atelier is the **first tenant** of fuhro-network's GitOps: AppProject-per-tenant convention defined in Phase 1 and contributed back to fuhro-network (private) | Proposed |
| 016 | Leak gate: public generic tier + private-pattern tier on every owner push/PR, redacted output; contributions closed | Proposed (2026-10-09, revised) |

Template: `docs/adr/0000-template.md` (Context · Decision · Consequences · Alternatives · Pi-vs-Azure note · Interview probe).

---

## 15. Discovery Questions & Answers (Q3 and Q10 block v1.0)

| # | Question | Needed by |
|---|---|---|
| Q1 | Brand name and domain? | **Answered:** Ebahn · `ebahn.fuhro.network` (C13) |
| Q2 | Photos: count, format, angles? | **Answered:** 59 PNG; angles per piece TBD at ingest (C12) |
| Q3 | Pi 5 RAM, NVMe HAT, second node? | **Open — Phase 1 week 1 inventory.** Assume 8 GB, no NVMe until checked; R1 stays HIGH |
| Q4 | Which fuhro services keep running? | **Answered:** all of them (C14) → hard tenant quota |
| Q5 | VLM provider? | **Answered:** Anthropic Claude (C15, ADR-003) |
| Q6 | Public URL always or showcases only? | **Answered:** showcases only (C13) → tunnel scaled to 0 by default |
| Q7 | Cloudflare or Azure DNS? | **Answered:** Cloudflare (C16, ADR-009) |
| Q8 | Dedicated node or shared Pi? | **Answered:** shared Pi 5 at first (C14, ADR-012) |
| Q9 | fuhro GitOps conventions? | **Answered:** not yet defined → Atelier defines the tenant convention (ADR-015) |
| Q10 | fuhro CIDRs / DNS zones / hostname patterns for deny-list and leak gate? | **Open — Phase 0.** Blocks the leak gate and the clusterwide policy; kept only in the private repo |
| Q11 | Keycloak on fuhro? | **Answered:** no; use Entra (C15, ADR-013) |
| Q12 | TLS on the edge | **Decided, pending approval:** Cloudflare edge certificate; no ACME or DNS token on the tenant (ADR-014 Amendment 1) |
| Q13 | Preview hostnames | **Decided, pending approval:** no previews on the homelab; PR previews on ephemeral `kind` in CI (ADR-014 Amendment 2) |
| Q14 | Leak gate vs fork PRs | **Dissolved:** contributions are closed, so there are no fork PRs; ADR-016 simplified (no label gating, no `pull_request_target`) |

---

## 16. Open Source & Isolation from fuhro-network

> Atelier is public; fuhro-network is not. The public repo describes a **generic edge region**; everything that makes that region *fuhro* lives in a private repo and in cluster-side policy that Atelier cannot change.

### 16.1 Principles

1. **Guest tenant, not co-owner.** On the homelab, Atelier never installs or configures cluster-scoped components (CNI, ArgoCD, cert-manager, ingress, monitoring, storage classes). It consumes them. Cluster-scoped work happens only on Azure and `kind`, where Atelier owns the cluster.
2. **Deny by default, both directions.** fuhro-network's policy denies Atelier → internal; Atelier's own policy denies internal → Atelier. Neither side relies on the other.
3. **Nothing fuhro in public** — except the one deliberately public hostname `ebahn.fuhro.network`. No *other* hostnames, IPs, CIDRs, DNS zones, tunnel IDs, node names, user names or topology diagrams of fuhro-network appear in the public repo, issues, docs, screenshots or write-ups. The edge region is called `edge`; diagrams show a `kind`-shaped reference edge.
4. **Public inputs are untrusted on the homelab.** The homelab only deploys *released* versions (signed tag/SHA), never a branch.
5. **Separate identities, separate secrets, separate paths in.** Own Entra External ID tenant, own secret store path, own Cloudflare tunnel, own WireGuard peer, no DNS write access to the shared zone.

### 16.2 Isolation controls (homelab)

| Layer | Control | Verified by |
|---|---|---|
| Namespaces | `atelier-edge`, `atelier-data`, `atelier-net` (no preview namespaces, ADR-014 Amendment 2); labels `tenant=atelier`; `ResourceQuota` + `LimitRange` on each | `kubectl get quota` in P15 suite |
| Network | `CiliumClusterwideNetworkPolicy` (owned by fuhro): deny `tenant=atelier` ↔ any non-Atelier namespace, LAN CIDRs and internal DNS; allow only kube-dns, egress to the internet allow-list, and the Atelier WireGuard peer. Atelier's own `CiliumNetworkPolicy` default-deny inside its namespaces. | Hubble flow assertions: `curl internal-app` → `DROPPED (policy denied)` |
| DNS | CoreDNS: no internal zone forwarding for Atelier pods (Cilium DNS policy FQDN allow-list) | P15 suite |
| Ingress | Dedicated `Gateway` + separate Cloudflare **tunnel** (own ID and token) in `atelier-edge`, routing only `ebahn.fuhro.network`; no Cloudflare *API* token on the tenant (ADR-014); fuhro's tunnel never routes to Atelier and vice versa; connector at 0 replicas outside showcases | Tunnel config review; external scan while "closed" |
| Identity | Entra External ID tenant used only by Ebahn (ADR-013); no identity brokering with any fuhro identity; no shared cookie domain | Config review |
| GitOps | ArgoCD `AppProject atelier`: `sourceRepos` = public repo + private env repo; `destinations` = `atelier-*` only; `clusterResourceWhitelist: []`; `namespaceResourceBlacklist` for NetworkPolicy/CiliumNetworkPolicy that could widen access; sync windows | `argocd proj get atelier` in P15 |
| RBAC | Atelier service accounts have no cluster roles; no `kubectl` for Atelier automation on the homelab — only ArgoCD | `kubectl auth can-i --list` checks |
| Pods | Pod Security `restricted`, non-root, read-only root FS, no hostNetwork/hostPath, seccomp `RuntimeDefault` | Kyverno (core) / PSA labels (edge) |
| Site-to-site | WireGuard peer with `AllowedIPs` = Atelier slice only; keys generated on-device, stored SOPS/age | `wg show`, route table review |
| Chaos/load | Chaos Mesh namespace-scoped mode on edge; node-level chaos and all k6 runs only on Azure | Chaos Mesh config; k6 runners in Azure |
| Observability | Atelier metrics/logs scraped into Atelier's own Prometheus agent/Loki tenant (or fuhro's stack with tenant label and no cross-tenant dashboards); public dashboards JSON contain no fuhro series | Dashboard lint in CI |

### 16.3 Public-repo hygiene

- **Contributions closed.** In the public repo set *Settings → General → Features → Pull requests → "Collaborators only"* (keep the box ticked; unticking disables PRs): the owner still uses PRs to run the required checks), and *Settings → Actions → General → Require approval for all external contributors*. `CONTRIBUTING.md` says outside contributions are not accepted. Verify both settings in the Phase 0 exit check. Fork workflows never receive secrets on public repos in any case.
- **Leak gates in two tiers plus a local hook (ADR-016).** Tier 1, no secrets: gitleaks, trufflehog and generic network regexes (RFC1918, CGNAT/Tailscale, link-local, `.local/.lan/.internal/.home.arpa/.ts.net`). Tier 2, private patterns from `atelier-env-fuhro/leak-patterns/`: required check on `main`, runs on every push and same-repo PR with a read-only token; workflows use only `push`, `pull_request`, `schedule` and `workflow_dispatch`, never `pull_request_target`. Local pre-commit via `$ATELIER_LEAK_PATTERNS`. CI output is redacted to category + file:line, because public Actions logs are public.
- Pre-commit hooks mirror the CI gates locally.
- Branch protection on `main`: required status checks (CI green including the leak gate), signed commits, no force-push. No required approving review while there is a single maintainer; passkey or hardware-key 2FA on the owner account instead. Releases are signed tags with release notes.
- `SECURITY.md` with a private disclosure channel; `CONTRIBUTING.md` states that outside contributions are not accepted.
- Issues are disabled or restricted; nothing from outside is required for the project to work. Write-ups and screenshots are reviewed for hostnames before publishing.
- **History audit** (`git filter-repo` ready) before the repo flips to public; repo starts private and flips at the end of Phase 0.
- Write-ups and videos: redact hostnames/IPs; reuse the `kind` reference diagrams, not homelab ones.

### 16.4 Reuse experience (what "open source" means here: read, clone, run; no outside contributions)

- `atelierctl bootstrap kind` brings up the whole stack with `data/sample/` (synthetic catalog with CC0/generated images, synthetic trend objects) — no VLM/LLM key required (deterministic stub provider).
- `make test` runs schema tests, service tests, k6 smoke, and policy tests (`kyverno test`, `conftest`) without any cloud account.
- Azure Terraform is runnable by anyone with their own subscription; no hard-coded tenant IDs (variables with `.tfvars.example`).
- No contribution workflow; ADRs double as learning material for readers.

### 16.5 What is *not* open

| Asset | Where | Why |
|---|---|---|
| Brand photos, reviewed metadata, descriptions | `atelier-brand-data` (private) | Commercial brand assets |
| Trend corpus (fetched text, extracted trend objects) | `atelier-brand-data` (private) | Derived from third-party editorial content; only the pipeline and schema are public, plus a synthetic sample |
| Homelab overlay, policies, tunnel, WireGuard, SOPS secrets | `atelier-env-fuhro` (private) | fuhro-network topology and Zero Trust posture |
| Cost reports with subscription IDs | `docs/writeups/cost/` redacted in public; raw in private | Account identifiers |

### 16.6 Tunnel isolation (ADR-014)

Ebahn gets its **own Cloudflare Tunnel**, created and operated independently from fuhro-network's tunnel, so that no path through Cloudflare can ever reach a fuhro internal service.

| Rule | How |
|---|---|
| Separate tunnel object | `cloudflared tunnel create ebahn` (or Zero Trust dashboard) → distinct tunnel UUID and credentials file. fuhro's tunnel is never edited for this project. |
| Credentials | `credentials.json` / connector token stored **only** as a SOPS/age-encrypted secret in the private env repo, mounted into `atelier-edge`. Never in the public repo, never on the fuhro connector. |
| Ingress rules | Locally-managed config in the private repo: exactly one rule `ebahn.fuhro.network → http://atelier-gw.atelier-edge.svc:80`, then `service: http_status:404` catch-all. No wildcard hostnames. |
| **No private network routes** | The Ebahn tunnel never gets `cloudflared tunnel route ip` / WARP private-network routes, so it can never become a WARP path into the LAN or pod network. Checked in P15. |
| Connector placement | `cloudflared` Deployment in `atelier-edge`, `replicas: 0` by default; scaled up by `atelierctl showcase start`, down by `showcase stop` (and by a CronJob safety net at 02:00). |
| Connector egress policy | `CiliumNetworkPolicy`: egress only to Cloudflare edge (TCP 443 / UDP 7844) and to `atelier-gw`; **deny** everything else — it cannot talk to any fuhro namespace, LAN CIDR or kube-apiserver. |
| fuhro side | fuhro's tunnel has **no** public-hostname route pointing at any `atelier-*` service; the clusterwide policy denies fuhro's connector → `tenant=atelier` as well. |
| Account boundary | Same Cloudflare account for now (shared zone). When a brand domain is bought, move Ebahn to its **own Cloudflare account** so even the zone is separate; the tunnel design above does not change. |
| Previews | None. No per-PR hostnames and no preview namespaces on the homelab; PR previews run on ephemeral `kind` in CI (ADR-014 Amendment 2). |
| Evidence | External scan of `ebahn.fuhro.network` while "closed" returns Cloudflare 530/1033; Hubble shows connector flows only to Cloudflare edge and `atelier-gw`; `cloudflared tunnel route ip list` is empty for the Ebahn tunnel. |

---

## 17. Working Agreement

- **"status"** → position in §10.2, open ADRs, budget to date, next exit criterion.
- **"continue"** → resume at the last unchecked item of the current phase.
- Every concept introduced gets: a 2–3 sentence mental model, the production failure it prevents, and one interviewer probe; each phase ends with a "should explain unaided" list.
- No pseudocode or placeholders unless labelled `TODO(spec)`.
- Over-engineering is challenged; tests, idempotency, rollback paths and runbooks are non-negotiable.
- Changes to this file go through PR with a one-line entry below.

### Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-09 | 0.1 | Initial draft from discovery answers (budget $50, 15 h/week, demo-first, Go templates). |
| 2026-10-09 | 0.2 | Open source (Apache-2.0) + isolation from fuhro-network: public/private repo split, guest-tenant model, §16, R11–R15, ADR-011–013, Q8–Q11, P13–P15. |
| 2026-10-09 | 0.3 | Discovery answers applied: brand Ebahn @ `ebahn.fuhro.network` (showcase-only), 59 PNGs, shared Pi 5, all fuhro services stay, Claude as VLM, Entra instead of Keycloak, Cloudflare default edge. C12–C16, ADR-003/009/012/013 accepted, ADR-014/015 proposed, trimmed edge footprint, no DNS automation on shared zone. |
| 2026-10-09 | 0.4 | Separate Cloudflare Tunnel for Ebahn made explicit (ADR-014 accepted, §16.6): own tunnel/credentials, single ingress rule, no private-network routes, connector egress locked down, replicas 0 outside showcases, Access-protected previews. |
| 2026-10-09 | 0.5 | Consistency pass before Phase 0: §16 sub-numbering and cross-refs fixed, Keycloak leftovers replaced by Entra, stale PNG/A1 references fixed, changelog ordered; new open items Q12 (TLS vs ADR-014), Q13 (preview hostnames), Q14 (leak gate vs fork PRs). |
| 2026-10-09 | 0.6 | Q12–Q14 decided (proposed): ADR-014 Amendments 1–2 (TLS at Cloudflare; no PR previews on the homelab), ADR-016 (three-tier leak gate). Added `leak-patterns/` and `tools/collect-patterns.py` to the private repo layout; ADR template and ADR files written. |
| 2026-10-09 | 0.7 | Contributions closed (only the owner opens PRs): PR creation restricted to collaborators, Actions approval for external contributors, no `pull_request_target`. ADR-016 simplified; Q14 dissolved; R12, P13, §16.3–16.4, branch protection and Phase 0 exit criteria updated. |
| 2026-10-09 | 0.8 | Phase 0 artefacts: `docs/runbooks/phase-0-walkthrough.md`, `tools/leakcheck/` (fail-closed, redacted, tested), `leak-gate` workflow, pre-commit config, starter files, ADRs 0001/0002/0011. Deviation from §16.3: trufflehog deferred to Phase 6 together with SHA-pinning of third-party Actions (only gitleaks in Phase 0). Collector zone suggestion now matches subdomains only (`[A-Za-z0-9-]+\.zone`). |
