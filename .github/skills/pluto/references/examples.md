# PLUTO Skill — Run Examples
# Based on PLUTO v4.4-patch3  •  See SKILL.md for routing and physics context

Resolve `$PLUTO_DIR` to the actual path before using in JSON strings.

---

## 1. HD Disk–Planet  *(polar, isothermal, 2-D)*

`Test_Problems/HD/Disk_Planet/` — 8 numbered configs, 256×768 cells, r ∈ [0.4, 2.5].

```bash
# Compile config 1
python compile_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet" --config-num 1

# Run default (tstop from pluto_01.ini)
python run_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/HD/Disk_Planet"

# Override planet mass + extend to 10 orbital periods
python run_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "tstop": 10.0,
  "parameters": {"Mplanet": 100.0, "Viscosity": 1e14}}'

# Staged run: stop at t=2, 5, 10 and restart automatically
python run_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "checkpoint_times": [2.0, 5.0, 10.0]}'

# Resume from snapshot 5
python run_pluto.py --run-dir "/path/to/Disk_Planet" --restart 5 --tstop 10.0

# HDF5 restart (requires binary compiled with hdf5=true)
python run_pluto.py --run-dir "/path/to/Disk_Planet" --h5restart 5 --tstop 10.0

# Plot last snapshot
python plot_pluto.py --run-dir "/path/to/Disk_Planet" --snap last \
  --variables rho vx1 vx2 --velocity-overlay

# Plot all snapshots as PDF sequence
python plot_pluto.py --run-dir "/path/to/Disk_Planet" --snap all \
  --variables rho prs --format pdf
```

---

## 2. HD Disk–Planet + FARGO orbital advection

```bash
python compile_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "config_num": 1,
  "with_fargo": true}'

python run_pluto.py --run-dir "/path/to/Disk_Planet" --tstop 10.0
```

FARGO is activated entirely at compile time. No ini change needed.

---

## 3. HD Disk–Planet + shearing box  *(sb XOR fd)*

```bash
python compile_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "config_num": 1,
  "with_sb": true}'
```

---

## 4. MHD Disk Wind  *(axisymmetric polar, MHD)*

```bash
python compile_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/MHD/Disk_Wind" --config-num 1

# Switch to more robust solver for magnetically dominated flows
python run_pluto.py --json '{
  "run_dir": "/path/to/MHD/Disk_Wind",
  "tstop": 5.0,
  "solver": "hlld"}'

python plot_pluto.py --run-dir "/path/to/MHD/Disk_Wind" --snap last \
  --variables rho Bx1 Bx2 --velocity-overlay
```

---

## 5. Parallel run with explicit domain decomposition

```bash
# Compile with MPI support (binary still named ./pluto)
python compile_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "config_num": 1,
  "parallel": true}'

# Run: mpirun -np 4 ./pluto -dec 2 2
python run_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "tstop": 10.0,
  "n_procs": 4,
  "decomp": [2, 2],
  "parameters": {"Mplanet": 100.0}}'
```

---

## 6. AMR with Chombo  *(requires g++ and gfortran)*

Chombo is incompatible with `--with-fd`, `--with-sb`, `--with-fargo`.

```bash
# Serial AMR compile
python compile_pluto.py --json '{"run_dir": "/path/to/amr_problem", "with_chombo": true}'

# Parallel AMR compile (implies parallel=true)
python compile_pluto.py --json '{
  "run_dir": "/path/to/amr_problem",
  "with_chombo": true,
  "chombo_mpi": true}'

# Run (Chombo output: data.nnnn.hdf5 plots, chk.nnnn.hdf5 checkpoints)
python run_pluto.py --json '{"run_dir": "/path/to/amr_problem", "tstop": 1.0, "n_procs": 4}'

# Restart from Chombo checkpoint chk.0005.hdf5 (uses -restart 5 internally)
python run_pluto.py --json '{"run_dir": "/path/to/amr_problem", "restart": 5, "tstop": 3.0}'

# Plot Chombo AMR output (plot_pluto reads data.nnnn.hdf5 via pyPLUTO)
python plot_pluto.py --run-dir "/path/to/amr_problem" --snap last \
  --variables rho Bx1 --datatype dbl.h5
```

---

## 7. Background run with live monitoring

```bash
python run_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "tstop": 20.0,
  "background": true,
  "monitor": true,
  "plot_on_the_fly": true,
  "watch_interval": 30.0}'
```

While running, check:
```bash
tail -f /path/to/Disk_Planet/pluto_monitor.log
tail -5 /path/to/Disk_Planet/dbl.out
```

---

## 8. Timing test — no disk output, limited steps

```bash
python run_pluto.py --json '{
  "run_dir": "/path/to/Disk_Planet",
  "maxsteps": 100,
  "no_write": true}'
```

---

## 9. Units and physical scale workflow

When working in code units you must define three normalisation constants in
`definitions.h` (in the user-defined constants block) before compiling:

```c
/* [Beg] user-defined constants (do not change this line) */
#define UNIT_DENSITY   (CONST_mp)         /* code unit of density = proton mass in g/cm³ */
#define UNIT_LENGTH    (CONST_au)         /* code unit of length  = 1 AU in cm          */
#define UNIT_VELOCITY  (CONST_kms*1.e3)   /* code unit of velocity = 1 km/s in cm/s     */
/* [End] user-defined constants (do not change this line) */
```

`compile_pluto.py` reads these and writes them to `physics_config.md`.
`plot_pluto.py` reads `physics_config.md` to label axes in physical units.

To convert simulation output:
```
t_physical [s]      = t_code * UNIT_LENGTH / UNIT_VELOCITY
rho_physical [g/cc] = rho_code * UNIT_DENSITY
P_physical [Ba]     = P_code  * UNIT_DENSITY * UNIT_VELOCITY²
T_physical [K]      = T_code  * UNIT_VELOCITY² * CONST_mH / CONST_kB
```

---

## 10. EOS and viscosity compile examples

```bash
# Isothermal HD disc (EOS must be set in definitions.h before compile)
# definitions.h: EOS ISOTHERMAL, PHYSICS HD, GEOMETRY POLAR
python compile_pluto.py --run-dir "/path/to/isothermal_disc" --config-num 2

# MHD with explicit viscosity and thermal conduction
# definitions.h: VISCOSITY EXPLICIT, THERMAL_CONDUCTION SUPER_TIME_STEPPING
python compile_pluto.py --run-dir "/path/to/viscous_disc"

# Relativistic resistive MHD (ResRMHD)
# definitions.h: PHYSICS ResRMHD, EOS IDEAL
python compile_pluto.py --run-dir "/path/to/resistive_jet" --parallel
```

---

## 11. Other useful test problems

| Path | PHYSICS | Geometry | Notable feature |
|------|---------|----------|-----------------|
| `HD/Sod/` | HD | Cartesian | Shock-tube; quickest sanity check |
| `HD/Disk_Vortex/` | HD | Polar | Rossby wave instability |
| `HD/Jet/` | HD | Cylindrical | Jet propagation; test `roe` vs `hll` |
| `MHD/Disk_Wind/` | MHD | Polar | Magnetically-driven wind |
| `MHD/Orszag_Tang/` | MHD | Cartesian | Classic vortex; tests `hlld` |
| `RHD/Blast/` | RHD | Cartesian | Relativistic blast wave |
| `RMHD/Rotor/` | RMHD | Cartesian | Relativistic MHD rotor |
| `Particles/Dust/` | HD+dust | Polar | Dust-gas drag; use `-frestart` |

---

## 12. pyPLUTO v4.4 analysis workflows  *(post-run, no recompile)*

All examples use the bundled pyPLUTO installed from `$PLUTO_DIR/Tools/pyPLUTO/`.
Install once: `pip install -e $PLUTO_DIR/Tools/pyPLUTO`

```python
import numpy as np
import pyPLUTO as pp
import pyPLUTO.pload as ppl
import matplotlib.pyplot as plt

WDIR = "runs/disk/"    # adjust to your run_dir

# ── 1. Load last snapshot ──────────────────────────────────────────────────
info = pp.nlast_info(w_dir=WDIR)
N    = info['nlast']
t    = info['time']
D    = ppl.pload(N, w_dir=WDIR, datatype='dbl')

# ── 2. Array layout: D.rho.shape == (nx2, nx1) == (nphi, nr) for POLAR ──
nr, nphi = D.rho.shape[1], D.rho.shape[0]
r   = D.x1      # 1-D radial cell centres
phi = D.x2      # 1-D azimuthal cell centres

# ── 3. Azimuthal average (axis=0 = phi axis for POLAR) ────────────────────
rho_mean = D.rho.mean(axis=0)   # shape (nr,) — radial density profile
vr_mean  = D.vx1.mean(axis=0)

# ── 4. Disc surface density (Σ ≈ ρ * Δz for 2-D; requires unit conversion)
# Σ [g/cm²] = rho_code * UNIT_DENSITY * Δr * UNIT_LENGTH
UNIT_DENSITY = 1.67e-24   # read from physics_config.md
UNIT_LENGTH  = 1.496e13   # 1 AU in cm
sigma = D.rho.mean(axis=0) * UNIT_DENSITY * np.diff(np.concatenate([[0], D.x1])) * UNIT_LENGTH

# ── 5. Gap depth: min density between r=0.8 and r=1.2 code units ──────────
mask     = (r >= 0.8) & (r <= 1.2)
gap_rho  = rho_mean[mask]
gap_min  = gap_rho.min()
print(f"Gap min density (code): {gap_min:.3e}  at t={t:.2f}")

# ── 6. Spiral arm detection: azimuthal density fluctuation at r=1.0 ───────
ir  = np.argmin(np.abs(r - 1.0))
phi_rho = D.rho[:, ir]   # shape (nphi,) — phi slice at r=1 AU

# ── 7. Quick 2-D disc plot (r-phi → Cartesian) ────────────────────────────
R, PHI = np.meshgrid(r, phi, indexing='ij')  # (nr, nphi)
X = R * np.cos(PHI)
Y = R * np.sin(PHI)
# D.rho is (nphi, nr) — transpose to (nr, nphi) for meshgrid
fig, ax = plt.subplots(figsize=(7, 6))
pcm = ax.pcolormesh(X, Y, D.rho.T, cmap='viridis',
                    norm=plt.matplotlib.colors.LogNorm(), shading='auto')
fig.colorbar(pcm, ax=ax, label=r'$\rho$ [code]')
ax.set_aspect('equal')
ax.set_xlabel('x [AU]'); ax.set_ylabel('y [AU]')
ax.set_title(f'Density  t={t:.2f}  n={N}')
fig.savefig('plots/rho_disc.pdf', bbox_inches='tight')
plt.close(fig)

# ── 8. Time series: load all snapshots and track gap depth ────────────────
from pathlib import Path
import re

# Parse dbl.out for all (n, t) pairs
times, gap_depths = [], []
for line in Path(WDIR + "dbl.out").read_text().splitlines():
    parts = line.split()
    if parts:
        n_snap, t_snap = int(parts[0]), float(parts[1])
        Ds = ppl.pload(n_snap, w_dir=WDIR, datatype='dbl')
        rho_r = Ds.rho.mean(axis=0)
        m = (Ds.x1 >= 0.8) & (Ds.x1 <= 1.2)
        times.append(t_snap)
        gap_depths.append(rho_r[m].min())

fig, ax = plt.subplots()
ax.semilogy(times, gap_depths)
ax.set_xlabel('t [code]'); ax.set_ylabel(r'$\rho_{\rm gap,min}$')
fig.savefig('plots/gap_depth_timeseries.pdf', bbox_inches='tight')
plt.close(fig)
```

---

## 13. Spherical disc + FARGO  *(MHD, VTK output)*

Based on `Test_Problems/MHD/FARGO/Spherical_Disk/`.

```bash
python compile_pluto.py --json '{
  "run_dir": "$PLUTO_DIR/Test_Problems/MHD/FARGO/Spherical_Disk",
  "with_fargo": true}'

python run_pluto.py --json '{
  "run_dir": "$PLUTO_DIR/Test_Problems/MHD/FARGO/Spherical_Disk",
  "tstop": 10.0}'

python plot_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/MHD/FARGO/Spherical_Disk" \
  --snap last --variables rho Bx1 --datatype vtk
```

Python analysis (r-phi midplane slice at θ = π/2):
```python
import pyPLUTO.pload as ppl, pyPLUTO.Image as img
D = ppl.pload(N, w_dir=wdir, datatype='vtk')
I = img.Image()
# r-phi midplane: rphi=True, x2cut = index of equatorial plane
I.pltSphData(D, w_dir=wdir, datatype='vtk', plvar='Bx1',
             logvar=False, rphi=True, x2cut=D.n2//2)
```

---

## 14. Cosmic-ray particle tracking  *(Particles module)*

```bash
python compile_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/Particles/CR_Transport" \
  --with-cr-transport

python run_pluto.py --run-dir "$PLUTO_DIR/Test_Problems/Particles/CR_Transport" --tstop 1.0
```

Load particle data:
```python
import pyPLUTO.ploadparticles as plp
P = plp.ploadparticles(N, w_dir=wdir, datatype='dbl', ptype='CR')
# P.x1, P.x2, P.x3  — particle positions
# P.vx1, P.vx2, P.vx3 — velocities
# P.identity — particle IDs
```

---

## Common errors and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERROR: PLUTO binary not found` | Not compiled | Run compile script or set `auto_compile=true` |
| `make failed` on Chombo | Missing g++ or gfortran | Install C++ and Fortran compilers |
| `PLUTO exited 1` immediately | `[Parameters]` count wrong | Count `USER_DEF_PARAMETERS` in `definitions.h`; must match `pluto.ini` exactly |
| `NaN` / `rho_min < 0` | Numerical instability | Reduce `cfl` (try 0.2); switch to `tvdlf`; check `first_dt` |
| `dt` shrinks every step | CFL violation | Reduce `cfl`; check boundary conditions for supersonic inflow |
| `output_dir` patches silently ignored | Wrong section name | Must be `[Static Grid Output]` not `[Output]` — handled by `run_pluto.py` |
| `-decomp` flag not recognised | Wrong flag name | Use `-dec` (userguide Table 1.3); `run_pluto.py` handles this |
| Snapshots not found after run | Wrong `datatype` in plot | Check `dbl.out` for actual format; pass `--datatype dbl.h5` if HDF5 |
| Plot axes show array indices | No units file | Ensure `physics_config.md` exists; run `compile_pluto.py` first |
