# ADR-0002: Two regions, one GitOps flow: homelab edge and Azure core

- **Status:** Accepted (Giullia, 2026-10-10)
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** K8S, NET, HYB, CICD

## Context

The goal is a platform that can survive a Black Friday peak and that proves hybrid-cloud skills. A single Raspberry Pi cannot absorb a simulated peak, and Azure alone costs money and teaches nothing about running at the edge. The Pi is shared with other homelab apps, so Atelier is only a guest there (ADR-0011).

## Decision

Run two regions from the same release tags.

- **Edge:** a guest tenant on the homelab cluster. It runs the always-on demo and the cheap checks, within a hard memory quota.
- **Core:** Azure AKS, built with Terraform, scaled to zero when idle. It runs the load tests and chaos experiments.
- Both reconcile through Argo CD. The differences live only in overlays. The public repo has `kind` and `core` overlays. The edge overlay lives in the private environment repo.

## Consequences

- Real practice with hybrid networking (WireGuard, routing, DNS across sites) and with the difference between a constrained edge and an elastic cloud.
- More moving parts than a single cluster, and a budget ceiling of about US$50 per month to defend.
- Node-level chaos and all load tests run only on Azure, so the homelab's other apps are never at risk.

## Alternatives considered

- Azure only: simpler, but loses the edge and hybrid story and the homelab investment.
- Homelab only: cannot demonstrate scale.

## Pi-vs-Azure note

This ADR is the contrast: ARM64, tight memory and slow disk at the edge, elastic x86 or ARM nodes with managed services in Azure.

## Interview probe

"Why two regions for a demo store?" Answer: to show the same artefact running under very different constraints, and to practise the network between them.
