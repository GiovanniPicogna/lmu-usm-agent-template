#!/usr/bin/env bash
# preToolUse hook — create/write tool: prevent overwriting existing results/ files.
#
# Enforces §10 of copilot-instructions.md: "never overwrite existing results
# files — always write to a new path or prompt for confirmation."
#
# VS Code compatibility notes:
#   - VS Code reads .github/hooks/*.json by default.
#   - VS Code IGNORES hook matchers — script self-checks tool_name and exits
#     immediately for any non-create tool invocation.
#   - VS Code uses camelCase for tool input fields (filePath vs path).
#   - Known create tool names: "create" (CLI), "create_file" (VS Code).
#   - Output uses dual-format JSON (CLI top-level + VS Code hookSpecificOutput).
#
# Input:  JSON via stdin — tool_name + tool_input (VS Code) or toolName + toolArgs (CLI).
# Output: dual-format JSON to stdout to block; empty stdout to allow.
set -euo pipefail

INPUT=$(cat)

# Parse tool name and file path; handle both payload formats
PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tool_name = d.get('tool_name', d.get('toolName', ''))
args = d.get('tool_input', d.get('toolArgs')) or {}
filepath = ''
if isinstance(args, dict):
    # VS Code uses camelCase (filePath); CLI uses snake_case (path, file_path)
    for key in ('filePath', 'path', 'file_path', 'filename', 'filepath'):
        if key in args:
            filepath = args[key]
            break
print(tool_name + '\t' + filepath)
" 2>/dev/null || printf '\t')

TOOL_NAME=$(printf '%s' "$PARSED" | cut -f1)
FILEPATH=$(printf '%s' "$PARSED" | cut -f2-)

# VS Code ignores matchers — skip non-create tools immediately.
case "$TOOL_NAME" in
    create|create_file|createFile|write_file|writeFile) ;;
    "") ;;       # Unknown — still evaluate
    *) exit 0 ;; # Not a create tool — allow
esac

# Only guard the results/ directory; allow everywhere else
if echo "$FILEPATH" | grep -qE '^results/' && [ -f "$FILEPATH" ]; then
    NAME="${FILEPATH%.*}"
    EXT="${FILEPATH##*.}"
    DATE=$(date +%Y%m%d)
    SUGGESTED="${NAME}_${DATE}.${EXT}"
    MSG="Blocked: ${FILEPATH} already exists. Per §10 of copilot-instructions.md, never overwrite results files. Use a timestamped name instead: ${SUGGESTED}"
    python3 -c "
import json, sys
msg = sys.argv[1]
print(json.dumps({
    'permissionDecision': 'deny',
    'permissionDecisionReason': msg,
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': msg,
    }
}))
" "$MSG"
    exit 0
fi

exit 0
