# AGENTS.override.md — Machine-Local Overrides
#
# File:    AGENTS.override.md  (repo root, same directory as AGENTS.md)
# Purpose: Machine-specific overrides that must NOT be committed to git.
#          Loaded by Codex CLI alongside AGENTS.md; nearer directory wins.
#          This file is listed in .gitignore — keep it that way.
#
# Use this file for:
# - Local HPC cluster scratch paths (e.g. /hpc/scratch/<username>/runs/)
# - Personal conda env name if it differs from the team default (py312)
# - Machine-specific library paths (DYLD_LIBRARY_PATH, LD_LIBRARY_PATH)
# - Temporary debugging instructions or hypothesis flags
# - Personal style preferences that should not override team conventions
#
# Do NOT put here:
# - Rules that apply to all team members → put them in AGENTS.md instead
# - Secrets, tokens, or passwords → use .env files for those
# ─────────────────────────────────────────────────────────────────────────────

## Local overrides

# Uncomment and fill in as needed:

# ── HPC paths ────────────────────────────────────────────────────────────────
# **Run directory**: /hpc/scratch/<username>/runs/<project>/
# **Module load**:  module load hdf5/1.14 fftw/3.3

# ── Local conda environment (if different from 'py312') ──────────────────────
# conda activate <my_local_env>

# ── Machine-specific library path (macOS HDF5 example) ───────────────────────
# DYLD_LIBRARY_PATH=/usr/local/hdf5/lib

# ── Local PLUTO / FARGO3D binary paths ──────────────────────────────────────
# PLUTO_DIR=/Users/<username>/Codes/pluto-code
# FARGO3D_DIR=/Users/<username>/Codes/fargo3d
