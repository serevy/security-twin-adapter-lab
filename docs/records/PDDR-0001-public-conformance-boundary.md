---
id: PDDR-0001
title: Public Conformance Boundary and Disclosure Policy
decision_date: 2026-10-08
recorded_date: 2026-10-08
decision_status: accepted
delivery_status: in-progress
scope:
  - project
  - product
  - process
owners: []
evidence:
  - "Project owner created the public security-twin-adapter-lab repository on 2026-10-08"
  - "Issue #1"
  - PUBLIC_DISCLOSURE_BOUNDARY.md
  - README.md
related:
  - "Issue #2"
  - "Issue #3"
supersedes: []
superseded_by: null
---

# PDDR-0001: Public Conformance Boundary and Disclosure Policy

## Summary

Use this public repository as an intentionally limited conformance and interoperability surface for security adapters.

Publish reproducible contracts, synthetic fixtures, bounded reference adapters, failure/recovery expectations and aggregate conformance evidence.

Do not publish the private Enterprise Security Twin implementation, detection/evasion-sensitive semantics, private adversarial corpora, production topology, credentials or private CI dependencies.

## Context and observations

The private Enterprise Security Twin project needs a public surface for adapter interoperability and reproducible testing without turning its internal decision system into public documentation.

A public test lab also enables heavy Docker/Envoy-style conformance work to run independently from private repository CI, but cost reduction is a secondary benefit rather than the architectural purpose of this repository.

Publishing an exact internal ABI or detailed private traces would create unnecessary coupling and could reveal implementation details useful for evasion.

A deliberately lossy public contract can still demonstrate useful guarantees:

- capability advertisement is not policy authority;
- actuation is bounded;
- unsupported operations fail visibly;
- partial failure is distinct from success;
- rollback and recovery are explicit.

## Options considered

### Option A — Publish the private implementation or a close mirror

- Description: expose the private repository or copy substantial internal Core code into the public lab.
- Benefits: simplest path to identical tests.
- Costs / constraints: exposes private research and evasion-sensitive details; tightly couples public compatibility to internal implementation.
- Status: rejected.

### Option B — Public CI that checks out private source

- Description: keep a public test repository but fetch/build private Enterprise Security Twin code with credentials.
- Benefits: one implementation under test.
- Costs / constraints: introduces secret/private-source handling into a forkable public workflow and makes the public lab depend on private availability.
- Status: rejected.

### Option C — Intentionally lossy public conformance boundary

- Description: define a minimal public behavioral contract, synthetic fixtures and reference adapters that do not require private source.
- Benefits: reproducible interoperability; independent public CI; lower disclosure risk; third-party adapter participation remains possible.
- Costs / constraints: public tests cannot prove every private implementation property; a compatibility mapping must be maintained deliberately.
- Status: selected.

## Decision

Approved on 2026-10-08:

1. Keep Enterprise Security Twin implementation and detection-sensitive research private.
2. Treat this repository as a public **behavioral conformance surface**, not a mirror or ABI dump.
3. Publish only the minimum adapter semantics needed for interoperability and independent verification.
4. Keep detection thresholds, weights, feature combinations, model prompts/routing, private adversarial corpora and evasion-sensitive internal state private.
5. Use synthetic data and synthetic credentials only.
6. Public CI must not require a private repository checkout, private PAT, production credential or private package-registry credential.
7. Adapters may advertise technical capability but never gain policy authority from the public contract.
8. Reference actuator tests must preserve bounded scope, TTL, rollback and visible partial-failure/recovery semantics.
9. GitHub Pages may publish public contract versions and aggregate conformance evidence, but not private traces or decision internals.
10. A later proposal to expose additional detail requires an explicit disclosure review and, when durable, a new or superseding PDDR.

## Delivery and validation

Initial delivery includes:

- public repository bootstrap;
- this PDDR;
- PUBLIC_DISCLOSURE_BOUNDARY.md;
- PDDR validation CI;
- public-boundary lint CI;
- initial Adapter Contract v1 draft;
- GitHub Pages skeleton.

The first substantive runtime fixture will be an Envoy / Web API synthetic range. It must run without private source code and must demonstrate only public adapter behavior.

The decision is not considered fully validated until the first public conformance workflow and Pages deployment complete successfully.

## Consequences

- Public interoperability is decoupled from the private implementation language and ABI.
- Some private/public compatibility mapping must be maintained deliberately.
- Public examples may be less detailed than internal regression fixtures by design.
- Contributors can reason about adapter safety behavior without receiving enough detail to reproduce private detection logic.
- CI cost reduction is possible for public synthetic tests without making private CI dependent on a public runner.

## Revisit when

Revisit if:

- third-party adapter development requires semantics not expressible by the public contract;
- public/private compatibility drift becomes difficult to detect;
- a published fixture materially improves evasion capability;
- Pages/CI artifacts reveal more internal detail than intended;
- licensing/commercial boundaries require a different publication model.

## Evidence

- Public repository creation by the project owner on 2026-10-08.
- Issue #1 tracks the bootstrap boundary and CI.
- README.md defines the public lab purpose.
- PUBLIC_DISCLOSURE_BOUNDARY.md defines publish/keep-private and CI/Pages rules.
- Issue #2 tracks the first Envoy / Web API reference range.
- Issue #3 tracks the GitHub Pages conformance portal.

## Related records

None yet. Future contract, Envoy reference-range, Pages or licensing decisions may add related PDDR records.
