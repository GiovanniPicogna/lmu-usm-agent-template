---
applyTo: "**/*.py"
---
# Python conventions — LMU Astrophysics group

These rules apply to all Python files and supplement the broader guidelines in
`.github/copilot-instructions.md` (§2 environment, §4 coding standards).

## Type annotations & documentation

- Use type hints on **all public function signatures**
- Write a **NumPy-format docstring** for every function and class:
  `Parameters`, `Returns`, `Raises`, and `Examples` sections as needed
- Do not add docstrings to private helpers (`_name`) unless the logic is non-obvious

## Units & constants

- `import astropy.units as u` — always; use `Quantity` for physical values
- `from astropy import constants as const` — use `const.M_sun`, `const.G`, `const.c`, etc.
- **Never hardcode unit conversions** as bare floats (e.g. `* 1.496e13` is wrong;
  use `(1 * u.au).to(u.cm).value` or a named constant in `src/utils/`)

## File and path handling

- Use `pathlib.Path` everywhere; avoid `os.path` string manipulation
- Accept all input/output paths as CLI arguments (`argparse` or `click`)
- Never hardcode absolute paths; use relative paths anchored to the repo root

## Error handling

- Catch **specific** exceptions — never bare `except:`
- Log the full traceback before re-raising or calling `sys.exit(1)`
- Validate user-supplied inputs at the script entry point only

## Reproducibility

- Set and log a random seed for all stochastic operations (`seed = 42` default)
- Write the seed as an attribute to any HDF5 output: `f.attrs["seed"] = seed`
- Show progress with `tqdm` or `print(..., flush=True)` for loops > ~10 s
- Provide a `--dry-run` / `--test` flag in analysis scripts where feasible
