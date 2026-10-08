#!/usr/bin/env python3
"""Fail closed on public-workflow patterns that would cross the disclosure boundary."""

from __future__ import annotations

from pathlib import Path
import sys


WORKFLOW_DIR = Path(".github/workflows")
FORBIDDEN = {
    "pull_request_target": "public contribution code must not run with pull_request_target privileges",
    "secrets.": "public workflows must not depend on repository/environment secrets",
    "serevy/enterprise-security-twin": "public CI must not check out or fetch the private Twin repository",
    "repository: serevy/enterprise-security-twin": "public CI must not target the private Twin repository",
}

diagnostics: list[str] = []

for path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
    text = path.read_text(encoding="utf-8")
    for token, reason in FORBIDDEN.items():
        if token in text:
            diagnostics.append(f"{path}: forbidden '{token}': {reason}")

if diagnostics:
    print("\n".join(diagnostics), file=sys.stderr)
    raise SystemExit(1)

print("OK: public workflow boundary checks passed")
