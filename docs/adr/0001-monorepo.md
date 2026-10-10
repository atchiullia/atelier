# ADR-0001: One public monorepo with per-service directories

- **Status:** Proposed
- **Date:** 2026-10-09
- **Deciders:** Giullia Lazaro
- **Requirement codes:** CICD, DOC

## Context

The platform has about six small services, a shared metadata schema library, a CLI, Terraform and Kubernetes manifests, all written and operated by one person. The schema is the contract between most services, so changes often touch several of them at once.

## Decision

Keep everything that is safe to publish in one public repository, `atelier`, with one directory per service (`services/`), shared code in `libs/`, infrastructure in `infra/` and `platform/`, and documentation in `docs/`. Anything that identifies the homelab or is commercial lives in separate private repositories (ADR-0011).

## Consequences

- A schema change and the services that use it land in one commit and one CI run.
- One place to search, one set of conventions, one place for the leak gate.
- CI must run only what a change touches (path filters), or it will slow down as the repo grows.
- The private repositories are intentionally outside the monorepo, so deploying to the homelab always needs two sources (ADR-0002).

## Alternatives considered

- One repository per service: version skew against the shared schema and a lot of overhead for one maintainer.
- Including the homelab overlay in the monorepo: leaks topology (rejected by ADR-0011).

## Pi-vs-Azure note

Not applicable.

## Interview probe

"Monorepo or polyrepo for a small platform team, and how do you stop a monorepo's CI from getting slow?" Answer: monorepo while a shared contract changes often, with path-filtered pipelines and cached builds.
