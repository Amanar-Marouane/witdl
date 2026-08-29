#!/bin/bash
# WitDL wrapper script — run from anywhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$SCRIPT_DIR" python3 -m witdl "$@"
