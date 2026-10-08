---
layout: default
title: Security Twin Adapter Lab
---

# Security Twin Adapter Lab

**Public adapter conformance. Private decision logic.**

This site is the public specification and evidence surface for bounded security adapters.

## Current status

| Item | Status |
| --- | --- |
| Public disclosure boundary | Defined |
| PDDR-0001 | Accepted / delivery in progress |
| Adapter Contract v1 | Draft |
| Public CI | Bootstrap |
| Envoy / Web API reference range | Not started |
| Production adapter compatibility | Not claimed |

## Conformance principles

A conforming adapter:

1. advertises technical capability without acquiring policy authority;
2. accepts only a bounded, already-authorized request;
3. may narrow a request but never widen it;
4. rejects unsupported capability or unsafe TTL before mutation;
5. distinguishes rejection from partial failure;
6. exposes rollback/recovery behavior;
7. provides enough evidence to verify recovery without exposing private detection internals.

## Latest machine-readable status

See [results/latest.json](../results/latest.json).

## Public disclosure boundary

Read [PUBLIC_DISCLOSURE_BOUNDARY.md](../PUBLIC_DISCLOSURE_BOUNDARY.md).

## Contract

Read [Adapter Contract v1 — Draft](../specs/adapter-contract-v1.md).

---

This public lab does not expose the private Enterprise Security Twin implementation or detection/evasion-sensitive decision semantics.
