"""Strict allowlist for public aggregate evidence; never publish free-form payloads."""
import datetime
import hashlib
import io
import json
import re
import zipfile

REPOSITORY = 'serevy/security-twin-adapter-lab'
SCHEMA = 'public-conformance-portal-v1'
SCENARIOS = {
    'baseline_availability': 'Baseline availability',
    'scoped_containment': 'Session-scoped containment',
    'unrelated_session_survival': 'Unrelated-session survival',
    'ttl_bound': 'TTL bound',
    'automatic_expiry': 'Automatic expiry',
    'explicit_rollback': 'Explicit rollback',
    'partial_failure_visibility': 'Partial-failure visibility',
    'verified_clean_recovery': 'Verified clean recovery',
    'provider_unavailable': 'Provider unavailable',
    'rollback_failure': 'Rollback failure',
    'recovery_verification_failure': 'Recovery verification failure',
    'technical_preflight': 'Technical preflight',
    'control_plane_unavailable': 'Control plane unavailable',
    'restart_clean_recovery': 'Restart clean recovery',
}
BOOTSTRAP = {
    'schema_version': 'public-conformance-status-v1', 'generated_by': 'repository-bootstrap',
    'status': 'BOOTSTRAP', 'contract': {'version': 'adapter-contract-v1-draft', 'validated': False},
    'reference_ranges': {'envoy_web_api': 'NOT_STARTED'},
    'claims': {'production_adapter_compatibility': False, 'private_runtime_validation': False},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read_json(data):
    require(len(data) <= 16384, 'Aggregate JSON exceeds 16 KB')
    return json.loads(data, object_pairs_hook=unique_object)


def checks(value):
    require(isinstance(value, dict) and set(value) == set(SCENARIOS), 'Unexpected scenario set')
    require(all(v in ('PASS', 'FAIL', 'NOT_RUN') for v in value.values()), 'Invalid check status')
    return {key: value[key] for key in SCENARIOS}


def source(value):
    fields = {'repository', 'run_id', 'head_sha', 'head_branch', 'event', 'conclusion',
              'updated_at', 'evidence_kind', 'evidence_id'}
    require(isinstance(value, dict) and set(value) == fields, 'Unexpected source fields')
    require(value['repository'] == REPOSITORY and value['head_branch'] == 'main', 'Non-public source')
    require(value['event'] in ('push', 'workflow_dispatch'), 'PR evidence cannot be published')
    require(value['conclusion'] in ('success', 'failure', 'cancelled', 'timed_out'), 'Incomplete run')
    for key in ('run_id', 'evidence_id'):
        require(type(value[key]) is int and value[key] > 0, 'Invalid source ID')
    require(isinstance(value['head_sha'], str) and re.fullmatch('[a-f0-9]{40}', value['head_sha']), 'Invalid commit')
    require(value['evidence_kind'] in ('workflow-artifact', 'workflow-job-summary'), 'Invalid evidence kind')
    stamp = value['updated_at']
    require(isinstance(stamp, str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', stamp), 'Invalid timestamp')
    datetime.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
    return dict(value)


def validate(snapshot):
    if snapshot == BOOTSTRAP:
        return {'schema_version': SCHEMA, 'contract_version': 'v1-draft', 'status': 'BOOTSTRAP',
                'checks': dict.fromkeys(SCENARIOS, 'NOT_RUN'), 'source': None, 'execution_failures': []}
    fields = {'schema_version', 'contract_version', 'status', 'checks', 'source', 'execution_failures'}
    require(isinstance(snapshot, dict) and set(snapshot) == fields, 'Unexpected snapshot fields')
    require(snapshot['schema_version'] == SCHEMA and snapshot['contract_version'] == 'v1-draft', 'Unknown version')
    aggregate = checks(snapshot['checks'])
    failures = snapshot['execution_failures']
    require(isinstance(failures, list) and all(x in ('harness', 'teardown') for x in failures)
            and len(failures) == len(set(failures)), 'Invalid execution failures')
    if snapshot['status'] == 'BOOTSTRAP':
        require(snapshot['source'] is None and not failures and
                all(v == 'NOT_RUN' for v in aggregate.values()), 'Invalid bootstrap claims')
        provenance = None
    else:
        provenance = source(snapshot['source'])
        require(snapshot['status'] in ('PASS', 'FAIL'), 'Invalid aggregate status')
        expected = 'PASS' if all(v == 'PASS' for v in aggregate.values()) and not failures else 'FAIL'
        require(snapshot['status'] == expected, 'Aggregate contradicts checks')
        require(snapshot['status'] != 'PASS' or provenance['conclusion'] == 'success', 'Failed workflow cannot claim PASS')
    return {'schema_version': SCHEMA, 'contract_version': 'v1-draft', 'status': snapshot['status'],
            'checks': aggregate, 'source': provenance, 'execution_failures': failures}


def from_artifact(archive, run, artifact):
    """Metadata comes from GitHub REST, not from the artifact. ZIP is never extracted."""
    repo = run['repository']
    require(repo['full_name'] == REPOSITORY and repo['private'] is False, 'Wrong repository')
    require(run['head_repository']['id'] == repo['id'] and run['head_repository']['private'] is False,
            'Fork/private run rejected')
    require(run['path'] == '.github/workflows/envoy-conformance.yml' and
            run['name'] == 'Envoy Conformance' and run['status'] == 'completed', 'Wrong workflow')
    require(artifact['name'] == 'envoy-web-api-conformance' and artifact['expired'] is False, 'Invalid artifact')
    origin = artifact['workflow_run']
    require(origin['id'] == run['id'] and origin['head_sha'] == run['head_sha'] and
            origin['head_branch'] == 'main' and origin['repository_id'] == repo['id'] and
            origin['head_repository_id'] == repo['id'], 'Artifact provenance mismatch')
    require(len(archive) <= 262144 and artifact['size_in_bytes'] <= 262144, 'Artifact exceeds 256 KB')
    require(artifact['digest'] == 'sha256:' + hashlib.sha256(archive).hexdigest(), 'Artifact digest mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        entries = [i for i in bundle.infolist() if i.filename == 'envoy-web-api.json']
        require(len(entries) == 1 and entries[0].file_size <= 16384, 'Missing/duplicate/oversized aggregate')
        raw = read_json(bundle.read(entries[0]))
    required = {'schema_version', 'contract_version', 'scenario', 'synthetic_only', 'status', 'checks'}
    require(isinstance(raw, dict) and required <= set(raw) and
            set(raw) <= required | {'harness', 'teardown'}, 'Unexpected aggregate fields')
    require(raw['schema_version'] == '1' and raw['contract_version'] == 'v1-draft' and
            raw['scenario'] == 'envoy-web-api' and raw['synthetic_only'] is True, 'Wrong evidence contract')
    failures = [key for key in ('harness', 'teardown') if key in raw]
    require(all(raw[key] == 'FAIL' for key in failures), 'Invalid execution flag')
    return validate({
        'schema_version': SCHEMA, 'contract_version': 'v1-draft', 'status': raw['status'],
        'checks': raw['checks'], 'execution_failures': failures,
        'source': {'repository': REPOSITORY, 'run_id': run['id'], 'head_sha': run['head_sha'],
                   'head_branch': run['head_branch'], 'event': run['event'], 'conclusion': run['conclusion'],
                   'updated_at': run['updated_at'], 'evidence_kind': 'workflow-artifact', 'evidence_id': artifact['id']},
    })
