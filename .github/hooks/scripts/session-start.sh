#!/usr/bin/env bash
# sessionStart / SessionStart hook — LMU Astrophysics template
#
# Validates AGENTS.md for unfilled <PLACEHOLDER> fields and surfaces the
# current science goal at the start of every agent session.
#
# VS Code compatibility notes:
#   - Writes to stderr (shown as context in CLI and VS Code).
#   - Also outputs hookSpecificOutput.additionalContext JSON to stdout for
#     VS Code, which injects the string directly into the agent's conversation
#     (more reliable than stderr-only context injection).
set -euo pipefail

WARNINGS=""
GOAL=""
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

echo "=== Copilot session start — LMU Astrophysics ===" >&2

if [ -f "AGENTS.md" ]; then
    COUNT=$(grep -cE '<[A-Z_]{2,}>' AGENTS.md 2>/dev/null || echo 0)
    if [ "$COUNT" -gt 0 ]; then
        echo "  WARNING: AGENTS.md has ${COUNT} unfilled <PLACEHOLDER> field(s)." >&2
        echo "  Fill in project-specific context before running science tasks:" >&2
        grep -nE '<[A-Z_]{2,}>' AGENTS.md | head -5 >&2
        WARNINGS="WARNING: ${COUNT} unfilled AGENTS.md placeholder(s) — fill in project context before running science tasks."
    else
        echo "  AGENTS.md: no unfilled placeholders." >&2
    fi

    GOAL=$(awk '/One-sentence science goal:/{found=1;next} found{gsub(/^[> ]+/,""); if(NF){print; exit}}' \
               AGENTS.md 2>/dev/null || echo "")
    if [ -n "$GOAL" ] && ! echo "$GOAL" | grep -qE '<[A-Z_]{2,}>'; then
        echo "  Science goal: ${GOAL}" >&2
    else
        GOAL=""
    fi
fi

echo "  Branch: ${BRANCH}" >&2

# Build additionalContext string for VS Code injection into the conversation
CONTEXT="LMU Astrophysics session | Branch: ${BRANCH}"
[ -n "$WARNINGS" ] && CONTEXT="${CONTEXT} | ${WARNINGS}"
[ -n "$GOAL" ]     && CONTEXT="${CONTEXT} | Science goal: ${GOAL}"

# Output JSON for VS Code's SessionStart hookSpecificOutput.
# VS Code injects additionalContext into the agent's conversation;
# CLI ignores this JSON output (sessionStart is informational in both).
python3 -c "
import json, sys
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': sys.argv[1]
    }
}))
" "$CONTEXT"

exit 0
