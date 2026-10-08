#!/usr/bin/env python3
"""Select an explicit public main-branch run; import aggregate JSON only."""
import argparse
import json
from pathlib import Path
import subprocess

from evidence import REPOSITORY, from_artifact


def gh(path):
    return subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/{path}'],
                          check=True, capture_output=True, timeout=60).stdout


def import_run(run_id):
    run = json.loads(gh(f'actions/runs/{run_id}'))
    artifacts = json.loads(gh(f'actions/runs/{run_id}/artifacts?name=envoy-web-api-conformance&per_page=100'))
    matches = [a for a in artifacts['artifacts'] if a['name'] == 'envoy-web-api-conformance']
    if len(matches) != 1 or artifacts['total_count'] != 1:
        raise ValueError('Expected exactly one public conformance artifact')
    artifact = matches[0]
    if artifact['size_in_bytes'] > 262144 or artifact['expired']:
        raise ValueError('Artifact unavailable or too large')
    archive = gh(f"actions/artifacts/{int(artifact['id'])}/zip")
    return from_artifact(archive, run, artifact)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--output', type=Path, default=Path('results/latest.json'))
    args = parser.parse_args()
    if args.run_id <= 0:
        parser.error('run-id must be positive')
    snapshot = import_run(args.run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + '\n')
    print(f"Imported public aggregate for run {args.run_id}: {snapshot['status']}")


if __name__ == '__main__':
    main()
