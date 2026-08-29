#!/bin/bash
# WitDL wrapper script (fallback if pip install not used)
# After `pip install -e .`, just use: witdl <command>
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$SCRIPT_DIR" python3 -m witdl "$@"
