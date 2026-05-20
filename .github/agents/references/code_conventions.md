# Code Conventions

Reference file for `@simulation-agent`. Loaded on demand — keeps the agent file lean.

---

## Standard analysis script skeleton

```python
import argparse
import datetime
import json

import astropy.units as u
import h5py
import matplotlib.pyplot as plt
import numpy as np

# Always use argparse — no hardcoded paths
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run",  required=True, help="Path to run directory")
parser.add_argument("--snap", type=int, default=-1, help="Snapshot index (-1 = last)")
parser.add_argument("--out",  required=True, help="Output path (.json or .h5)")
args = parser.parse_args()

# Explicit unit conversion — never magic numbers
sigma_cgs = sigma_code * (u.M_sun / u.au**2).to(u.g / u.cm**2)

# Figure style consistent with group standard
plt.rcParams.update({
    "figure.dpi": 300,
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
})
```

---

## HDF5 result saving

Save results with units as HDF5 attributes so any downstream reader knows
the physical meaning without consulting a separate readme:

```python
with h5py.File("results/gaps/disk_1Mjup_gap.h5", "w") as f:
    ds = f.create_dataset("sigma_gap", data=sigma_gap)
    ds.attrs["units"] = "g/cm^2"
    ds.attrs["snapshot"] = snap_index
    ds.attrs["code"] = "FARGO3D"
    ds.attrs["date"] = datetime.date.today().isoformat()
```

---

## Diagnostic figure naming

| Domain | Save path pattern | Example |
|---|---|---|
| Disk simulation | `plots/disk/<run>_<quantity>.pdf` | `plots/disk/disk_1Mjup_sigma.pdf` |
| Cosmological | `plots/cosmo/<snap>_<quantity>.pdf` | `plots/cosmo/z0_gas_temp.pdf` |
| Dust evolution | `plots/dust/<run>_<quantity>.pdf` | `plots/dust/run01_grainsize.pdf` |
