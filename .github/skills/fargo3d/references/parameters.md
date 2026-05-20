# FARGO3D Skill — Full Parameter Reference

Called by `scripts/run_fargo3d.py`. Parameters marked **required** have no
default; all others fall back to the existing `.par` file value when omitted.

| Name | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `par_file` | str | **required** | must exist | Path to `.par` setup file |
| `output_dir` | str | **required** | — | Where FARGO3D writes `gasdens*.dat` etc. |
| `AspectRatio` | float | (from par) | (0, 1] | Disk scale-height ratio h/r |
| `Sigma0` | float | (from par) | > 0 | Surface density at 1 au (code units) |
| `Alpha` | float | (from par) | [0, 0.1] | Alpha-viscosity |
| `FlaringIndex` | float | (from par) | [0, 1] | Disk flaring index |
| `PlanetMass` | float | (from par) | ≥ 0 | Planet mass in stellar masses |
| `Tmax` | float | (from par) | > 0 | Max time in orbital periods |
| `Ninterm` | int | (from par) | ≥ 1 | Output cadence (steps between outputs) |
| `DT` | float | (from par) | > 0 | Time-step per orbit fraction |
| `Nx` | int | (from par) | [8, 4096] | Azimuthal resolution |
| `Ny` | int | (from par) | [8, 1024] | Radial resolution |
| `extra_params` | dict | `{}` | — | Any other `.par` key-value pairs not listed above |
| `fargo3d_bin` | str | `"./fargo3d"` | — | Path to FARGO3D executable |
| `n_procs` | int | 1 | [1, 512] | MPI rank count (CPU runs) |
| `gpu` | bool | False | — | Use GPU flag (`-m` instead of `-0`) |
