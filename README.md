# Security Twin Adapter Lab

[English] | [日本語](README.ja.md)

> **Public conformance lab for bounded security adapters, failure handling, and recovery.**

**Verify continuously. Intervene minimally. Recover deliberately.**

Security Twin Adapter Lab is a public, reproducible test surface for security-adapter interoperability.

It is intentionally **not** a public mirror of the private Enterprise Security Twin implementation.

The lab focuses on what an adapter may claim, what it must refuse, how failures become visible, and how recovery is demonstrated without publishing detection- or evasion-sensitive internals.

## What belongs here

- public adapter contracts;
- synthetic fixtures and scenarios;
- bounded reference adapters;
- Docker / Envoy test ranges;
- conformance workflows;
- machine-readable public results;
- GitHub Pages documentation and compatibility status.

## What does not belong here

- private decision thresholds, weights, heuristics, or model prompts;
- evasion-sensitive detection boundaries;
- private adversarial corpora;
- production credentials or private-repository tokens;
- private source-code checkout from public CI;
- unrestricted privileged control paths.

Read [PUBLIC_DISCLOSURE_BOUNDARY.md](PUBLIC_DISCLOSURE_BOUNDARY.md) before contributing any fixture, trace, result, or implementation detail.

## Initial roadmap

1. establish the disclosure/conformance boundary;
2. publish Adapter Contract v1;
3. validate the repository with secret-free public CI;
4. publish a small GitHub Pages conformance portal;
5. add an Envoy / Web API reference range;
6. exercise scoped containment, TTL rollback, partial failure, and verified recovery;
7. expand to additional adapter families without moving policy authority into adapters.

## Public contract principle

Adapters may advertise **technical capability**. They do not gain policy authority by doing so.

A conforming actuator consumes an already-authorized bounded request, may narrow it further for platform constraints, and must fail visibly when it cannot apply or recover the requested control.

The public contract describes observable behavior and conformance expectations. It is **not** a dump of any private runtime ABI, scoring logic, or detection implementation.

## Status

**Pre-v1 / synthetic reference fixture.**

No production adapter compatibility claim is made yet.

## Run the Envoy reference range

A synthetic Docker Compose fixture covers scoped session restriction, bounded TTL,
explicit rollback, partial failure and separately verified recovery through real Envoy.

```bash
python3 scripts/run_envoy_conformance.py
```

Requires Docker Compose v2 and Python 3.10+ on Linux/macOS. The command starts and
always tears down the isolated range and writes `results/envoy-web-api.json`.
See [topology, scenarios, public limits and manual commands](docs/envoy-range.md).

## Conformance portal

The [Pages portal](https://serevy.github.io/security-twin-adapter-lab/) (available after
manual deployment) shows the latest published aggregate snapshot, scenario results,
synthetic adapter maturity and recovery evidence with source-run provenance.
See the [portal build and publication guide](docs/portal.md) and
[reviewed aggregate JSON](results/latest.json). Portal-only changes use lightweight CI;
they do not rerun the Docker range.

## Public language and evidence rule

Public-facing human-readable content should use English as the primary language and
Japanese as the maintained secondary language where practical. Machine-readable evidence,
identifiers, contract versions, schema versions and provenance remain language-neutral
and must not diverge between locales. Translate presentation only; do not duplicate result
JSON or widen disclosure. Pages uses `/` (English) and `/ja/` (日本語) with one shared
`result.json`. Update both presentations and their checks when changing portal explanations.

[PDDR-0002](docs/records/PDDR-0002-public-localization-and-language-neutral-evidence.md)
records the rationale and scope; this short contributor rule is explicit rather than
inferred from treating a PDDR as unconditional Policy.

## PDDR

Durable public-surface decisions are recorded under [docs/records](docs/records/) using [PDDR Kit](https://github.com/serevy/pddr-kit).

Validate locally with:

```bash
python .pddr/pddr.py validate
```

## License

License selection is intentionally deferred until the public/commercial boundary review is complete.
