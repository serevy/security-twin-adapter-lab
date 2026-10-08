#!/usr/bin/env python3
"""One local/CI command; always remove the isolated, synthetic Compose range."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from conformance import fresh_result  # noqa: E402


def main():
    os.chdir(ROOT)
    result = ROOT / 'results/envoy-web-api.json'
    result.parent.mkdir(exist_ok=True)
    (result.parent / 'envoy-compose.log').unlink(missing_ok=True)
    result.write_text(json.dumps(fresh_result(), indent=2) + '\n')
    env = dict(os.environ, LOCAL_UID=str(os.getuid()), LOCAL_GID=str(os.getgid()))
    compose = ['docker', 'compose', '-p', 'security-twin-envoy-lab', '-f', 'docker/envoy/compose.yml']

    def run(*args):
        subprocess.run([*compose, *args], env=env, check=True, timeout=240)

    code = 0
    try:
        run('up', '-d', '--build', '--wait', '--wait-timeout', '60')
        run('run', '--rm', '--no-deps', 'runner', 'main')
        run('stop', '-t', '2', 'adapter')
        run('run', '--rm', '--no-deps', 'runner', 'outage')
        run('start', 'adapter')
        run('run', '--rm', '--no-deps', 'runner', 'restart')
        if json.loads(result.read_text())['status'] != 'PASS':
            raise subprocess.SubprocessError('incomplete conformance result')
    except (OSError, subprocess.SubprocessError) as error:
        code = 1
        print(f'Range failed ({type(error).__name__}); see the bounded result/log.', file=sys.stderr)
        data = json.loads(result.read_text())
        data['status'] = 'FAIL'
        data['harness'] = 'FAIL'
        result.write_text(json.dumps(data, indent=2) + '\n')
        try:
            logs = subprocess.run([*compose, 'logs', '--no-color', '--tail', '30'], env=env,
                                  capture_output=True, text=True, timeout=15)
            (result.parent / 'envoy-compose.log').write_text(logs.stdout[-12000:])
        except (OSError, subprocess.SubprocessError):
            pass
    finally:
        try:
            run('down', '-v', '--remove-orphans')
        except (OSError, subprocess.SubprocessError):
            code = 1
            print('Range teardown failed.', file=sys.stderr)
            data = json.loads(result.read_text())
            data['status'] = 'FAIL'
            data['teardown'] = 'FAIL'
            result.write_text(json.dumps(data, indent=2) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
