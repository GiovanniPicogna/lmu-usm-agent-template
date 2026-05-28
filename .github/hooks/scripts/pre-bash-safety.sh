#!/usr/bin/env bash
# preToolUse hook — bash/terminal tool safety guard
#
# Blocks shell operations that are explicitly prohibited by §10 of
# copilot-instructions.md:
#   - git push --force / git reset --hard / git clean -f
#   - rm -rf on data/ or results/
#   - HPC job submission (sbatch / qsub / bsub) without user review
#
# VS Code compatibility notes:
#   - VS Code reads .github/hooks/*.json by default.
#   - VS Code IGNORES hook matchers — this script runs for ALL PreToolUse
#     events; it self-checks tool_name and exits 0 immediately for non-bash tools.
#   - Output uses dual-format JSON: top-level permissionDecision (CLI) +
#     hookSpecificOutput wrapper (VS Code).
#   - Known bash/terminal tool names: "bash" (CLI), "runInTerminal" (VS Code).
#
# Input:  JSON via stdin — tool_name + tool_input (VS Code) or toolName + toolArgs (CLI).
# Output: dual-format JSON to stdout to block; empty stdout to allow.
set -euo pipefail

INPUT=$(cat)

# Parse tool name and shell command from the JSON payload (handle both formats)
PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tool_name = d.get('tool_name', d.get('toolName', ''))
args = d.get('tool_input', d.get('toolArgs')) or {}
command = args.get('command', '') if isinstance(args, dict) else ''
print(tool_name + '\t' + command)
" 2>/dev/null || printf '\t')

TOOL_NAME=$(printf '%s' "$PARSED" | cut -f1)
COMMAND=$(printf '%s' "$PARSED" | cut -f2-)

# VS Code ignores matchers — skip non-bash tools immediately.
# Known bash/terminal tool names across Copilot and Claude Code surfaces:
case "$TOOL_NAME" in
    bash|Bash|runInTerminal|run_in_terminal|executeTerminalCommand) ;;
    "") ;;       # Unknown — still evaluate (fail-safe)
    *) exit 0 ;; # Not a shell tool — allow
esac

# Output dual-format deny JSON: CLI reads top-level; VS Code reads hookSpecificOutput
deny() {
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
" "$1"
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
