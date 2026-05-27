#!/usr/bin/env bash
# sessionStart hook — LMU Astrophysics template
#
# Validates AGENTS.md for unfilled <PLACEHOLDER> fields and surfaces the
# current science goal at the start of every agent session.
#
# Writes to stderr (shown to the agent as context); no JSON output needed
# because sessionStart is informational only and does not block execution.
set -euo pipefail

echo "=== Copilot session start — LMU Astrophysics ===" >&2

if [ -f "AGENTS.md" ]; then
    COUNT=$(grep -cE '<[A-Z_]{2,}>' AGENTS.md 2>/dev/null || echo 0)
    if [ "$COUNT" -gt 0 ]; then
        echo "  WARNING: AGENTS.md has ${COUNT} unfilled <PLACEHOLDER> field(s)." >&2
        echo "  Fill in project-specific context before running science tasks:" >&2
        grep -nE '<[A-Z_]{2,}>' AGENTS.md | head -5 >&2
    else
        echo "  AGENTS.md: no unfilled placeholders." >&2
    fi

    # Display the science goal if it has been filled in
    GOAL=$(awk '/One-sentence science goal:/{found=1;next} found{gsub(/^[> ]+/,""); if(NF){print; exit}}' \
               AGENTS.md 2>/dev/null || echo "")
    if [ -n "$GOAL" ] && ! echo "$GOAL" | grep -qE '<[A-Z_]{2,}>'; then
        echo "  Science goal: ${GOAL}" >&2
    fi
fi

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "  Branch: ${BRANCH}" >&2

exit 0
