# Synthetic Envoy / Web API range

This fixture implements Issue #5 under [PDDR-0001](records/PDDR-0001-public-conformance-boundary.md)
and the existing [public contract](../specs/adapter-contract-v1.md). It neither accesses
nor models private Enterprise Security Twin code, detection, scoring or authority.
No public contract fields or outcome definitions are changed.

## Run

Requirements: Docker Engine with Compose v2 supporting `up --wait`, and Python 3.10+
on a Linux/macOS host. Images are fixed to Envoy 1.35.0 and Python 3.12.11
(`slim-bookworm`); no Python packages are installed. These are reproducibility pins,
not production deployment recommendations.

From the repository root:

```bash
python3 scripts/run_envoy_conformance.py
```

The script builds and starts the range, waits for readiness, tests real Envoy traffic,
stops the adapter to test actual control-plane unavailability, restarts it, verifies
clean availability, and always runs `down -v --remove-orphans`. It exits nonzero on
failure. The range uses a fixed Compose project name: run only one instance at a time.
The script owns and tears down that project, so do not put unrelated resources in it.

For manual inspection (POSIX shell):

```bash
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
docker compose -p security-twin-envoy-lab -f docker/envoy/compose.yml up -d --build --wait
docker compose -p security-twin-envoy-lab -f docker/envoy/compose.yml run --rm runner main
# The all-in-one script additionally runs the outage/restart phases.
docker compose -p security-twin-envoy-lab -f docker/envoy/compose.yml down -v --remove-orphans
```

The main phase alone leaves the overall result `FAIL` with outage/restart `NOT_RUN`;
only the complete script can produce the full conformance PASS.
Run stdlib unit tests separately with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_public_boundary.py
python3 .pddr/pddr.py validate
```

## Topology and isolation

The runner sends HTTP to Envoy (`8080`). Envoy asks the adapter's HTTP `ext_authz`
listener (`8081`) before routing `/public` to `normal-api` and `/sensitive/export`
to `sensitive-api`. The runner directly calls the adapter control listener (`8080`);
Envoy does not route client traffic to that control surface.

All services use an internal Compose bridge without host-published ports. Containers
run as non-root with read-only roots, dropped capabilities, no-new-privileges and
resource limits. Only the runner's `results/` mount is writable. No host networking,
privileged mode, Docker socket mounts, private checkouts or credentials are used.

The `x-lab-session` header is a **synthetic label, not authentication**. Only the two
fixed fixture labels are accepted. Do not expose this range to real users: its control
and fault-injection endpoints are deliberately unauthenticated on the isolated network.
The APIs return only their fixed service names and a synthetic-data flag.

## Fixture-local wire format

These endpoints and JSON field names are a test harness encoding of public behavior,
not a new public ABI or a production control plane.

| Endpoint | Behavior |
| --- | --- |
| `GET /profile` | Identity, empty observation set, `restrict_route` action, rollback support, max TTL, automatic expiry |
| `POST /restrict` | Technical preflight followed by exact bounded mutation |
| `GET /state` | Active synthetic restrictions; unknown on injected provider failure |
| `POST /rollback` | Explicit, idempotent rollback acknowledgement; never claims verified recovery |
| `GET /verify/{request_id}` | Separate state verification; only known operations in a clean fixture yield `RECOVERED` |
| `POST /test/fault` | Deterministic test-only provider, partial mutation, rollback and verification faults |

A bounded request contains exactly:

```json
{
  "request_id": "example",
  "target": "synthetic-session",
  "scope": "/sensitive/export",
  "action": "restrict_route",
  "ttl_seconds": 60,
  "rollback_required": true
}
```

Maximum TTL is a synthetic technical limit of 60 seconds, not a detection threshold.
Preflight accepts only the fixed sessions, exact route and action, integer TTL 1–60,
and required rollback. Unknown fields, unsupported inputs, duplicate request IDs and
overlapping restrictions on the same target are rejected before mutation. In particular,
retrying cannot refresh or extend an existing TTL. No adapter-selected target or policy
exists. Applying a restriction echoes the exact accepted bounds.

Expiry uses a monotonic deadline, enforced during authorization/state reads at the
boundary (no background timer needed). Explicit rollback remains available after expiry.
State is deliberately in-memory: restarting loses history and is **not** advertised as
production recovery. Unknown operation verification stays unknown after restart.

## Scenarios and evidence

| Check | Evidence |
| --- | --- |
| Baseline | Both APIs and both required sessions succeed through Envoy; upstream bodies identify correct routing |
| Scoped containment | Only the targeted session's exact sensitive route returns 403 |
| Unrelated-session survival | Other session retains sensitive and public access; targeted session keeps public access |
| TTL bound | Over-limit and malformed TTL rejected with unchanged state; exact maximum accepted with unchanged bounds |
| Automatic expiry | Short restriction blocks first, then state and real access return clean |
| Explicit rollback | Repeated rollback acknowledgements plus independent state and traffic verification |
| Partial failure visibility | Fault mutates first, returns `PARTIAL_FAILURE`, stays observable/blocked and fails clean verification |
| Verified clean recovery | Explicit rollback after partial failure, separate `RECOVERED` state evidence, restored traffic |
| Provider unavailable | Deterministic 503 and `REJECTED` before mutation, unknown state, Envoy fails closed |
| Rollback failure | `PARTIAL_FAILURE`, still blocked, recovery denied until fault cleared and rollback retried |
| Verification failure | Successful rollback cannot turn an unavailable verification result into clean evidence |
| Technical preflight | Unsupported action, target, scope, rollback and fields rejected without mutation |
| Control plane unavailable | Actual stopped adapter container: control request fails and Envoy returns 503 |
| Restart clean recovery | Fresh state and both upstreams healthy; lost operation history remains unknown |

Failure of the authorization provider returns **503**, distinct from a scoped denial's
403. Fail-closed provider outages affect all traffic and are not successful containment
or an unrelated-traffic survival claim. Survival is asserted under healthy scoped
containment. Failure injection and state are synthetic; no attack corpus is involved.

`results/envoy-web-api.json` contains schema/contract version and named PASS/FAIL/NOT_RUN
checks. A failed run cannot be an overall PASS; tests stop on first failure, retaining
completed checks and leaving the rest NOT_RUN. No raw request bodies, private-like
scores, thresholds or decision traces are emitted. Results are generated and gitignored;
`results/latest.json` (the existing portal placeholder) is intentionally unchanged.

## CI

`Envoy Conformance` runs the same command on `ubuntu-latest`, with read-only repository
permissions, no credentials persisted by checkout, pinned action revisions and an always
teardown step. It uploads only the small JSON result and, on failure, a capped 12 KB
Compose log (last 30 lines per service) for three days. Request logging is disabled.

Runtime/spec/workflow changes trigger the range on PRs and `main`; documentation-only
and PDDR-only changes do not spend Docker CI minutes. Manual dispatch also runs it.
Existing PDDR and Public Boundary workflows continue to validate every PR.

## Limits

This proves only the described synthetic fixture behavior, not production Envoy control-plane
compatibility, durable crash recovery, authentication, performance or private-system behavior.
The public contract and PDDR boundary remain unchanged. Rollback-disabled adapter preflight
is additionally covered by a unit test; the runnable reference fixture advertises rollback.
