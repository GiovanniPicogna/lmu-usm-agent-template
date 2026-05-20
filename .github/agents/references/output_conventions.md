# Simulation Output Conventions

Reference file for `@simulation-agent`. Loaded on demand — keeps the agent file lean.

---

## FARGO3D / PLUTO output conventions

```python
import numpy as np
import h5py

# FARGO3D binary outputs (version >= 3.0 with HDF5 enabled)
# Each field is a 2-D array: shape (N_r, N_phi)
def read_fargo_field(run_dir: str, field: str, snap: int) -> np.ndarray:
    """Read a FARGO3D HDF5 output field at a given snapshot index."""
    path = f"{run_dir}/gasdens{snap}.h5"  # or .dat for binary
    with h5py.File(path, "r") as f:
        return f[field][...]

# FARGO3D binary (legacy .dat format)
def read_fargo_dat(run_dir: str, field: str, snap: int,
                   nr: int, nphi: int) -> np.ndarray:
    """Read a legacy FARGO3D .dat binary field."""
    path = f"{run_dir}/{field}{snap}.dat"
    return np.fromfile(path, dtype=np.float64).reshape(nr, nphi)

# PLUTO outputs: use pyPLUTO (pip install pyPLUTO) or pload()
# import pyPLUTO as pp
# d = pp.pload(snap, w_dir=run_dir)
# sigma = d.rho  # in code units — convert explicitly
```

**FARGO3D code units** (check `units.dat` in run directory):

| Quantity | Code unit |
|---|---|
| Length | 1 AU |
| Mass | 1 M★ |
| Time | orbital period at R = 1 AU / (2π) |
| Velocity | (G M★ / 1 AU)^0.5 |

Always convert to CGS or SI before saving results.

---

## Magneticum / GADGET snapshot conventions

```python
import h5py
import numpy as np

# Magneticum uses GADGET HDF5 format (SnapFormat=3)
GADGET_UNITS = {
    "length":   3.085678e21,   # cm per code unit (1 kpc/h at h=0.704)
    "mass":     1.989e43,      # g per code unit (10^10 M_sun/h)
    "velocity": 1.0e5,         # cm/s per code unit (1 km/s)
    "time":     3.085678e16,   # s per code unit
}

def read_gadget_snap(path: str, ptype: int = 0) -> dict:
    """
    Read particle positions and masses from a GADGET HDF5 snapshot.

    Parameters
    ----------
    path : str
        Path to snapshot HDF5 file.
    ptype : int
        Particle type (0=gas, 1=DM, 4=stars, 5=BH).

    Returns
    -------
    dict with keys 'pos' [kpc], 'mass' [M_sun], 'vel' [km/s],
    and for gas: 'temp' [K], 'sfr' [M_sun/yr], 'metallicity' [Z_sun].
    """
    with h5py.File(path, "r") as f:
        header = dict(f["Header"].attrs)
        h = header["HubbleParam"]
        a = header["Time"]  # scale factor
        group = f[f"PartType{ptype}"]
        pos  = group["Coordinates"][...] * GADGET_UNITS["length"] / (h * 3.086e18)  # -> kpc
        mass = group["Masses"][...]      * GADGET_UNITS["mass"]   / (h * 1.989e33)  # -> M_sun
        vel  = group["Velocities"][...] * np.sqrt(a)              # peculiar -> physical km/s
        result = {"pos": pos, "mass": mass, "vel": vel, "redshift": 1 / a - 1}
        if ptype == 0 and "InternalEnergy" in group:
            u    = group["InternalEnergy"][...]   # (km/s)^2
            xe   = group["ElectronAbundance"][...]
            mu   = 4.0 / (3 + 4 * xe)            # mean molecular weight
            temp = (5 / 3 - 1) * u * mu * 1.67e-24 * 1e10 / 1.38e-16  # K
            result["temp"] = temp
        return result
```

**GadgetIO.jl** (Julia): preferred for large snapshot batches on LRZ.
Call from Python via:

```python
import subprocess
import json

result = subprocess.run(
    ["julia", "scripts/read_snap.jl", snap_path],
    capture_output=True, text=True, check=True,
)
data = json.loads(result.stdout)
```
