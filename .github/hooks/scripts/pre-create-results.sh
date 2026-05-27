#!/usr/bin/env bash
# preToolUse hook — create tool: prevent overwriting existing results/ files.
#
# Enforces §10 of copilot-instructions.md: "never overwrite existing results
# files — always write to a new path or prompt for confirmation."
#
# Input:  JSON payload from stdin — toolName + toolArgs (or tool_name + tool_input).
# Output: {"permissionDecision":"deny","permissionDecisionReason":"..."} to block,
#         or empty stdout to allow.
set -euo pipefail

INPUT=$(cat)

# Extract the target file path from the create-tool arguments
FILEPATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
args = d.get('toolArgs') or d.get('tool_input') or {}
if not isinstance(args, dict):
    print('')
    sys.exit(0)
# Try common field names used by different Copilot surfaces
for key in ('path', 'file_path', 'filename', 'filepath'):
    if key in args:
        print(args[key])
        sys.exit(0)
print('')
" 2>/dev/null || echo "")

# Only guard the results/ directory; allow everywhere else
if echo "$FILEPATH" | grep -qE '^results/' && [ -f "$FILEPATH" ]; then
    NAME="${FILEPATH%.*}"
    EXT="${FILEPATH##*.}"
    DATE=$(date +%Y%m%d)
    SUGGESTED="${NAME}_${DATE}.${EXT}"
    MSG="Blocked: ${FILEPATH} already exists. Per §10 of copilot-instructions.md, never overwrite results files. Use a timestamped name instead: ${SUGGESTED}"
    python3 -c "import json, sys; print(json.dumps({'permissionDecision':'deny','permissionDecisionReason':sys.argv[1]}))" "$MSG"
    exit 0
fi

exit 0
