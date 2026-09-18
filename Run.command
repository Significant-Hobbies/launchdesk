#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.10+ is required. Install Python, then run python3 server.py.'
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ is required"'
exec python3 server.py
