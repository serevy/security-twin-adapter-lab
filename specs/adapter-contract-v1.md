# Public Adapter Contract v1 — Draft

Status: **pre-v1 / draft**

This document defines public **observable conformance behavior**. It is not a private runtime ABI, binary layout, internal policy schema, or detection specification.

## 1. Adapter identity and capability profile

A conforming adapter exposes a stable profile containing at least:

- `adapter_id`;
- observation capability set;
- action capability set;
- whether rollback is supported;
- maximum safe TTL for bounded actions.

Capability advertisement means **technically supported**, not **authorized**.

## 2. Observation contract

An observation adapter must:

- produce project-neutral typed observations/evidence;
- identify its source;
- reject unsupported observation classes visibly;
- preserve unknown/missing data as unknown rather than inventing a clean state;
- avoid embedding platform-native handles or objects into the public contract.

Synthetic reference fixtures use synthetic data only.

## 3. Bounded actuation contract

An actuator receives an already-authorized bounded request.

The adapter may **narrow** the request because of platform constraints. It must never widen:

- target;
- scope;
- action class;
- TTL;
- capability;
- rollback expectations.

Before mutation, the adapter performs a technical preflight for:

- supported capability;
- target validity;
- TTL within adapter maximum;
- rollback compatibility where required.

## 4. Outcome classes

A public conformance result distinguishes at least:

- `APPLIED` — requested bounded operation completed;
- `REJECTED` — no provider mutation occurred;
- `PARTIAL_FAILURE` — provider/external state may have changed but the operation did not complete cleanly;
- `RECOVERED` — recovery completed and the fixture verified the expected clean condition.

A partial failure must never be reported as success.

## 5. Recovery

Where rollback is advertised:

- rollback must be explicit and idempotent where practical;
- recovery verification must be separate from the request to recover;
- a successful API response alone is not sufficient proof of restored state when the provider is asynchronous/eventually consistent.

## 6. Failure visibility

Conformance tests must keep these cases visible:

- unsupported capability;
- TTL exceeded;
- rollback unsupported;
- provider/control-plane unavailable;
- partial mutation;
- rollback failure;
- recovery verification failure.

## 7. Security boundary

This public contract intentionally does **not** specify:

- how a private system decides that an action should be requested;
- detection thresholds or scoring;
- model/provider routing;
- private authority state internals beyond externally necessary outcome categories;
- private adversarial fixtures.

See [Public Disclosure Boundary](../PUBLIC_DISCLOSURE_BOUNDARY.md).
