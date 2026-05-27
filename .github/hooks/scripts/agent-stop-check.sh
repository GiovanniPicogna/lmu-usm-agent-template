#!/usr/bin/env bash
# agentStop / Stop hook — prompt log enforcer
#
# If src/ was modified during this agent turn but no corresponding prompt log
# was created in prompts/, force another turn to create it.
# Enforces §7 of copilot-instructions.md: "every analysis script must be
# accompanied by a corresponding prompt log in prompts/".
#
# VS Code compatibility notes:
#   - Registered under both "agentStop" (CLI) and "Stop" (VS Code) events.
#   - VS Code Stop hook sends stop_hook_active=true when agent is already
#     continuing from a previous Stop block — must check this to prevent
#     infinite loops.
#   - Output uses dual-format JSON: top-level decision (CLI) +
#     hookSpecificOutput wrapper (VS Code).
#
# Input:  JSON via stdin — includes stop_hook_active field (VS Code).
# Output: dual-format JSON to force another turn; empty stdout to allow.
set -euo pipefail

INPUT=$(cat)

# Guard against infinite loops: VS Code sets stop_hook_active=true when the
# agent is already continuing due to a previous Stop hook invocation.
STOP_HOOK_ACTIVE=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if d.get('stop_hook_active', False) else 'false')
" 2>/dev/null || echo "false")

[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

# Detect modified or newly untracked files under src/
STAGED_SRC=$(git diff --name-only HEAD 2>/dev/null | grep '^src/' || true)
UNTRACKED_SRC=$(git ls-files --others --exclude-standard 'src/' 2>/dev/null || true)
ALL_SRC=$(printf '%s\n%s\n' "$STAGED_SRC" "$UNTRACKED_SRC" | grep -v '^[[:space:]]*$' || true)

# Nothing modified in src/ — nothing to enforce
[ -z "$ALL_SRC" ] && exit 0

# Check whether a prompt log was created or modified this session
STAGED_PROMPTS=$(git diff --name-only HEAD 2>/dev/null | grep '^prompts/' || true)
UNTRACKED_PROMPTS=$(git ls-files --others --exclude-standard 'prompts/' 2>/dev/null \
    | grep -v 'TEMPLATE' || true)
ALL_PROMPTS=$(printf '%s\n%s\n' "$STAGED_PROMPTS" "$UNTRACKED_PROMPTS" \
    | grep -v '^[[:space:]]*$' || true)

if [ -z "$ALL_PROMPTS" ]; then
    DATE=$(date +%Y%m%d)
    MSG="Prompt log missing. Files in src/ were modified but no log was created in prompts/. Per §7 of copilot-instructions.md: run 'cp prompts/TEMPLATE.md prompts/<task_id>_${DATE}.md', fill in the Metadata block (date, model, task ID, exact prompt), the Output files table, and the Validation checklist — then reply done."
    python3 -c "
import json, sys
msg = sys.argv[1]
print(json.dumps({
    'decision': 'block',
    'reason': msg,
    'hookSpecificOutput': {
        'hookEventName': 'Stop',
        'decision': 'block',
        'reason': msg,
    }
}))
" "$MSG"
    exit 0
fi

exit 0
