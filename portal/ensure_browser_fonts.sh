#!/usr/bin/env bash
set -euo pipefail
# Runner-only glyph support, never a published font asset.
if [ -z "$(fc-list :lang=ja)" ]; then
  sudo apt-get -o Acquire::Retries=1 -o Acquire::http::Timeout=30 update -qq
  sudo apt-get -o Acquire::Retries=1 -o Acquire::http::Timeout=30 install -y --no-install-recommends fonts-ipafont-gothic
fi
test -n "$(fc-list :lang=ja)"
