# Phase 0: publishing a platform repo without publishing my homelab

*Atelier, Phase 0 (foundation). Written 2026-10-10.*

## What I built

A public repository for my platform project, Atelier (a fashion e-commerce platform that doubles as a Kubernetes platform-engineering portfolio), with a private twin that holds everything that identifies my homelab and a second private repo for the brand's photos and data. Anyone can read and run the public code; outside contributions are closed, so nobody but me can open a pull request.

## How

A leak checker I wrote runs before every commit on my laptop and again in GitHub Actions, next to gitleaks. It has three tiers: generic checks that need no secrets (private IP ranges, internal hostnames), a private pattern list that CI fetches with a read-only token, and the same list locally. It only ever reports a category, a file and a line, because the logs of a public repository are public. If its configuration is missing, empty or invalid, it fails closed instead of quietly passing.

## What broke or surprised me

- My first scan of the finished repo reported five findings in the README and the Apache license text. The cause was a pattern the collector had generated that matched any full stop after a closing bracket, plus a bare word from a default Kubernetes context name. The gate was right to be strict and the pattern list was too loose, so I now review every generated pattern before it is committed.
- When I proved the gate in CI, a red run was not enough. A broken token would also turn the job red. I checked that the failing step was the private-pattern scan, reporting exactly the canary's location and nothing else, and not the step that fetches the patterns.
- A budget in Azure is an alarm, not a brake, and on a free account even the alarm and its test email did not work for me. The free account has a spending limit instead, which is a real brake. The budget alert moves to the start of Phase 5, before anything paid exists.

## What I learned

Public CI logs are public, so a guard must never print what it finds. A gate that quietly loads nothing is worse than no gate, which is why mine fails closed. And a control is only proven when it fails for the reason I expect, so I test the canary, not just the red cross.

I also settled three design decisions as ADRs: Atelier is a guest tenant on a shared cluster with its own Cloudflare tunnel, TLS reaches the cluster with a Cloudflare Origin CA certificate whose key never left my machine, and pull request previews run in throwaway `kind` clusters in CI instead of on the homelab.

## Next

Phase 1: running the platform as an isolated guest on my Raspberry Pi, with its own namespaces, quotas and network policy, and a first page served at ebahn.fuhro.network through its own tunnel.
