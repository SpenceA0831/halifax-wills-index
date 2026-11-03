#!/bin/bash
# rebuild site from src (run from repo root)
set -e
cd "$(dirname "$0")/src"; rm -rf /tmp/o; python3 -I gen.py /tmp/o | grep -E "unmatched|wills;"
cp /tmp/o/index.html /tmp/o/*.csv ../site/
