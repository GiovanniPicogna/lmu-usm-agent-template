---
applyTo: "**/*.py"
---
# Python conventions — LMU Astrophysics group

These rules apply to all Python files and supplement the broader guidelines in
`.github/copilot-instructions.md` (§2 environment, §4 coding standards).

References: [Clean Code for Data Scientists](https://datasciencecampus.github.io/coffee-and-coding/20190611_clean_code/Best_Practice_in_Programming_for_Data_Scientists_python_and_R.html) ·
[clean-code-ml](https://github.com/davified/clean-code-ml) ·
[Programming for Astronomy](https://philuttley.github.io/prog4aa_lesson2/aio/index.html) ·
[Clean Code in Python](https://testdriven.io/blog/clean-code-python/) ·
[IBM: Clean, Testable Python](https://developer.ibm.com/articles/au-cleancode/)

---

## 1. Naming conventions

### Variables & constants
- Use **descriptive, intention-revealing names** — another developer must
  understand the stored value from the name alone, without reading comments.
- Variables → `snake_case` nouns (`stellar_mass`, `dust_opacity`).
- Constants → `UPPER_SNAKE_CASE` (`AU_TO_CM = 1.496e13`).
- Global scope constants must be defined at the top of the module, never
  inline as magic numbers.
- No cryptic abbreviations: `flux_density` not `fd`; `number_of_particles` not `n`.
- No redundant context: inside class `Disk`, write `self.mass`, not `self.disk_mass`.
- **Never** use `df`, `data`, `tmp`, `res`, `x`, `l` as lone variable names —
  these reveal no intent. Use `galaxy_dataframe`, `spectral_data`, etc.
- Use solution-domain suffixes for clarity when the type is not obvious:
  `mass_list`, `position_array`, `coord_dict`.
- Use the **same term** for the same concept throughout a file; avoid mixing
  synonyms (`star`/`stellar_object`/`source`).

### Functions & methods
- Use **`snake_case` verbs** that describe the action: `compute_gap_depth`,
  `load_snapshot`, `plot_surface_density`.
- Use the same verb for equivalent operations (`get_mass`, `get_luminosity`,
  not `get_mass` and `fetch_luminosity`).
- Boolean-returning functions should read as questions: `is_converged`,
  `has_planet`, `exceeds_threshold`.

### Classes
- Use `CamelCase` nouns: `ProtoplanetaryDisk`, `SpectrumFitter`.

---

## 2. Functions

### Single responsibility
Each function must do exactly **one thing** and do it well.
If the function name contains "and", split it into two functions.

```python
# Bad — two responsibilities
def load_and_plot_spectrum(path):
    ...

# Good
def load_spectrum(path: Path) -> np.ndarray:
    ...

def plot_spectrum(flux: np.ndarray, wavelength: np.ndarray) -> None:
    ...
```

### Size
- Preferred: ≤ 30 lines. Hard limit: 50 lines.
- If a function grows beyond that, extract a clearly named helper.

### Arguments
- Aim for ≤ 2 arguments. Use a dataclass or `argparse.Namespace` when you
  need more.
- **Never use boolean flag arguments** — they mean the function does two
  things. Split into separate functions instead.

```python
# Bad
def transform(text: str, uppercase: bool) -> str:
    ...

# Good
def to_uppercase(text: str) -> str: ...
def to_lowercase(text: str) -> str: ...
```

### No side effects
A function should not modify its inputs or global state silently.
Return new values; do not mutate arguments in place unless it is the
explicit, documented purpose.

### Code order — "story-book" layout
Arrange functions so the file reads **top-to-bottom**: the high-level caller
appears before the helpers it calls. (The newspaper metaphor: headline first,
details further down.)

```python
# Top of file — entry point / high-level logic
def analyse_disk(run_dir: Path) -> DiskSummary:
    surface_density = load_surface_density(run_dir)
    gap_depth = compute_gap_depth(surface_density)
    return DiskSummary(gap_depth=gap_depth)

# Below — helper functions
def load_surface_density(run_dir: Path) -> np.ndarray:
    ...

def compute_gap_depth(sigma: np.ndarray) -> float:
    ...
```

### Avoid deep nesting
Replace nested conditions with **early returns** (guard clauses) or
extract the inner body into a named function.

```python
# Bad — three levels deep
def process(data):
    if data is not None:
        if len(data) > 0:
            if data[0] > 0:
                return compute(data)

# Good
def process(data):
    if data is None or len(data) == 0:
        return None
    if data[0] <= 0:
        return None
    return compute(data)
```

---

## 3. Type annotations & documentation

- Use type hints on **all public function signatures**:
  ```python
  def compute_stokes_number(
      grain_size: u.Quantity,
      gas_surface_density: u.Quantity,
  ) -> u.Quantity:
  ```
- Write a **NumPy-format docstring** for every public function and class.
  Include `Parameters`, `Returns`, and `Raises`; add `Examples` for
  non-obvious usage.
- Private helpers (`_name`) need a docstring only when the logic is
  non-obvious.
- **Self-documenting code first**: if the code is clear, a comment adds
  noise. Write the comment only when it explains *why*, never *what*.

```python
# Bad — restates the code
total_mass = np.sum(masses)  # sum all masses

# Good — explains why
# Use log-space sum to avoid float overflow for >10^4 particles
total_mass = np.exp(np.log(masses).sum())
```

- **Never leave commented-out code** in committed files. Use `git stash`
  or a feature branch instead.
- Do not add noise comments: `# constructor`, `# end for loop`, etc.

---

## 4. Code principles

### DRY — Don't Repeat Yourself
Extract any logic that appears more than once into a named function.
Avoid DRY-ing too eagerly: wait until you see a second real duplicate.

### KISS — Keep It Simple
Prefer the simplest solution that satisfies the requirements.
Avoid clever one-liners that sacrifice readability for brevity.

```python
# Bad — clever but unreadable
result = sum(x for x in data if x % 2 == 0)

# Good — readable
even_numbers = [x for x in data if x % 2 == 0]
result = sum(even_numbers)
```

### SoC — Separation of Concerns
Separate data loading, processing, and output into distinct functions.
Do not mix I/O with numerical computation in a single function.

### Ubiquitous language
Use the same term in code, comments, and discussions with collaborators.
Do not reuse the same name for different objects (e.g., `spectrum` for
both the raw array and the fitted model).

---

## 5. Testing & defensive programming

- Adopt a **test-driven mindset**: write at least a sketch of the test
  before writing the function it exercises.
- Use `pytest` for all tests. Target **≥ 80 % branch coverage** for
  analysis scripts.
- Keep **cyclomatic complexity < 10** per function; measure with
  `radon cc -s src/`.
- Add `assert` statements for preconditions and postconditions at
  validation boundaries (not inside tight loops).
- **Fail early and loudly**: validate inputs at script entry points;
  raise a descriptive exception rather than silently returning `None`.
- After fixing a bug, write a regression test to prevent recurrence.
- Test with simplified data first (single row, zero-mass planet, flat
  disk) before running on full datasets.

---

## 6. Pythonic idioms

- Use **context managers** for any resource acquisition:
  ```python
  with h5py.File(path, "r") as f:
      data = f["density"][:]
  ```
- Prefer **vectorised `numpy` operations** over Python loops on arrays
  (orders of magnitude faster for large grids).
- Use **list comprehensions** for simple transformations; prefer
  `for`-loops when the body is complex or has side effects.
- Avoid `print()` debug statements in committed code; use the `logging`
  module with appropriate levels (`DEBUG`, `INFO`, `WARNING`).
- Remove all `df.head()`, `df.describe()`, and exploratory
  `print()` calls before committing.

---

## 7. Units & constants

- `import astropy.units as u` — always; use `Quantity` for physical values.
- `from astropy import constants as const` — use `const.M_sun`, `const.G`, etc.
- **Never hardcode unit conversions** as bare floats (e.g. `* 1.496e13` is
  wrong; use `(1 * u.au).to(u.cm).value` or a named constant in `src/utils/`).

---

## 8. File and path handling

- Use `pathlib.Path` everywhere; avoid `os.path` string manipulation.
- Accept all input/output paths as CLI arguments (`argparse` or `click`).
- Never hardcode absolute paths; use relative paths anchored to the repo root.

---

## 9. Error handling

- Catch **specific** exceptions — never bare `except:`.
- Log the full traceback before re-raising or calling `sys.exit(1)`.
- Validate user-supplied inputs at the script entry point only.

---

## 10. Reproducibility

- Set and log a random seed for all stochastic operations (`seed = 42` default).
- Write the seed as an attribute to any HDF5 output: `f.attrs["seed"] = seed`.
- Show progress with `tqdm` or `print(..., flush=True)` for loops > ~10 s.
- Provide a `--dry-run` / `--test` flag in analysis scripts where feasible.

---

## 11. Tooling

| Tool | Purpose |
|------|---------|
| `ruff` | Fast linting (replaces flake8, isort, pyupgrade) |
| `black` | Deterministic, non-configurable code formatting |
| `radon` | Cyclomatic complexity measurement (`radon cc -s src/`) |
| `pytest` | Unit and regression tests |
| `pre-commit` | Enforces all the above on every commit |

Run the full suite before pushing:
```bash
pre-commit run --all-files
pytest --tb=short
```
