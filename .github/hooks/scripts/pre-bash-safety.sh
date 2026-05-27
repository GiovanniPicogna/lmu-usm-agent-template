#!/usr/bin/env bash
# preToolUse hook — bash tool safety guard
#
# Blocks shell operations that are explicitly prohibited by §10 of
# copilot-instructions.md:
#   - git push --force / git reset --hard / git clean -f
#   - rm -rf on data/ or results/
#   - HPC job submission (sbatch / qsub / bsub) without user review
#
# Input:  JSON payload from stdin — toolName + toolArgs (camelCase CLI format)
#         or tool_name + tool_input (snake_case VS Code format).
# Output: {"permissionDecision":"deny","permissionDecisionReason":"..."} to block,
#         or empty stdout to allow.
set -euo pipefail

INPUT=$(cat)

# Parse the shell command from the JSON payload — handle both payload formats
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
args = d.get('toolArgs') or d.get('tool_input') or {}
print(args.get('command', '') if isinstance(args, dict) else '')
" 2>/dev/null || echo "")

deny() {
    python3 -c "import json, sys; print(json.dumps({'permissionDecision':'deny','permissionDecisionReason':sys.argv[1]}))" "$1"
    exit 0
}

# --- Block destructive git operations ---
if echo "$COMMAND" | grep -qE 'git\s+(push\s+(--force|-f\b)|reset\s+--hard|clean\s+-[fdxX]+)'; then
    deny "Blocked: destructive git operation (push --force / reset --hard / clean -f). Request explicit user confirmation first (§10 copilot-instructions.md)."
fi

# --- Block recursive deletes on protected directories ---
if echo "$COMMAND" | grep -qE '\brm\b[^|&;]*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*[^|&;]*(data|results)/'; then
    deny "Blocked: recursive delete on data/ or results/ is prohibited (§10 copilot-instructions.md). Write to a new path or obtain explicit user confirmation."
fi

# --- Block direct HPC job submission ---
if echo "$COMMAND" | grep -qE '\b(sbatch|qsub|bsub)\b'; then
    deny "Blocked: HPC job submission requires the user to review the generated script first (§10 copilot-instructions.md). Show the script and ask the user to submit manually."
fi

exit 0
