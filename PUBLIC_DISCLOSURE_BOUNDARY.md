# Public Disclosure Boundary

## Purpose

This repository exists to make **adapter interoperability, conformance behavior, and recovery evidence** publicly reproducible without publishing the private decision implementation behind Enterprise Security Twin.

The public surface should answer:

- what an adapter is allowed to claim;
- what it must reject;
- how bounded actuation is represented;
- how partial failure becomes visible;
- how rollback and verified recovery are demonstrated.

It should **not** answer how to evade private detection or how internal decision thresholds are chosen.

## Publish

The following are appropriate for this repository:

- public adapter capability and outcome contracts;
- synthetic-only example traffic and evidence;
- bounded reference adapters;
- Docker / Envoy fixtures;
- deterministic conformance scenarios;
- aggregate PASS / FAIL results;
- documented rollback and recovery expectations;
- adapter maturity/status;
- public CI configuration that requires no private source or credential.

## Keep private

Do not publish:

- private R0/R1/R2/R3 thresholds, weights, scores, feature selection, prompts, or model-routing rules;
- detailed trigger combinations that materially help an attacker evade detection;
- private adversarial or red-team corpora;
- private production topology, tenant information, credentials, endpoints, or secrets;
- private Safety/Authority implementation details beyond the behavior necessary for the public contract;
- private repository source code or build artifacts;
- unpublished vulnerabilities or provider-specific weaknesses;
- traces that expose evasion-sensitive timing or internal decision state.

## Public contract is intentionally lossy

The public contract is a **conformance boundary**, not a binary-compatible copy of any private ABI.

A public adapter may describe:

- adapter identity;
- technical observation/action capabilities;
- maximum safe TTL;
- rollback support;
- bounded requested action;
- applied / rejected / partial-failure outcomes;
- recovery evidence.

The private implementation may use additional internal fields and state that are neither required nor exposed here.

## CI boundary

Public workflows must be designed as though arbitrary contributors can read and fork them.

Default rules:

- no private repository checkout;
- no private PAT;
- no production credentials;
- no private package-registry credential;
- synthetic data only;
- least-privilege `GITHUB_TOKEN`;
- no `pull_request_target` workflow for untrusted contribution code;
- no privileged container, host network, or Docker socket exposure unless a later reviewed PDDR explicitly permits a bounded use;
- artifacts and traces are reviewed for disclosure risk before becoming long-lived public evidence.

## Pages boundary

GitHub Pages may publish:

- public contract/version;
- conformance scenario names;
- adapter maturity;
- aggregate results;
- bounded failure/recovery evidence.

Pages must not publish:

- detection thresholds;
- private model or decision internals;
- evasion-sensitive traces;
- private failure-injection corpus details;
- secrets or private source-derived artifacts.

## Review checklist

Before merging a public change, ask:

1. Does this reveal a private decision threshold, feature combination, or trigger?
2. Does this make an evasion strategy materially easier?
3. Does this copy private implementation rather than describe the public behavior?
4. Does a workflow require a secret, private checkout, privileged container, host network, or Docker socket?
5. Does a result contain more trace detail than the public claim requires?
6. Can the same conformance claim be demonstrated with a smaller, more synthetic fixture?

If yes to any item, narrow or redesign the change before publishing.
