#!/usr/bin/env bash
# agentStop hook — prompt log enforcer
#
# If src/ was modified during this agent turn but no corresponding prompt log
# was created in prompts/, force another turn to create it.
# Enforces §7 of copilot-instructions.md: "every analysis script must be
# accompanied by a corresponding prompt log in prompts/".
#
# Input:  agentStop JSON payload from stdin (sessionId, cwd, transcriptPath, stopReason).
# Output: {"decision":"block","reason":"..."} to force another turn,
#         or empty stdout to allow the session to end normally.
set -euo pipefail

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
    python3 -c "import json, sys; print(json.dumps({'decision':'block','reason':sys.argv[1]}))" "$MSG"
    exit 0
fi

exit 0
