# PLUTO Skill — Run Examples

All examples use `$PLUTO_DIR/Test_Problems/HD/Disk_Planet/` as the reference
run directory. It contains `definitions.h`, `init.c`, `eos.c`, `makefile`,
and two `pluto.ini` variants — a fully self-contained, ready-to-run test case.

---

## `$PLUTO_DIR/Test_Problems/HD/Disk_Planet/` — 2-D polar disk with planet

2-D isothermal HD disk in polar geometry (r ∈ [0.4, 2.5] in code units,
256 × 768 cells). Planet mass, disk mass, stellar mass, and viscosity are
all runtime-patchable `[Parameters]`.

**Compile** (from inside the test directory):
```bash
cd $PLUTO_DIR/Test_Problems/HD/Disk_Planet
python $PLUTO_DIR/setup.py          # select modules interactively, or:
make                                 # if Makefile already exists
```

**Run with defaults** (`pluto_01.ini`, `tstop = 2.0` code units):
```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir $PLUTO_DIR/Test_Problems/HD/Disk_Planet
```

**Override planet mass and extend run** to 10 code-unit orbits:
```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "$PLUTO_DIR/Test_Problems/HD/Disk_Planet",
             "tstop": 10.0,
             "parameters": {"Mplanet": 100.0, "Viscosity": 1e14}}'
```

**Staged run** with restarts at t = 2, 5, 10:
```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --json '{"run_dir": "$PLUTO_DIR/Test_Problems/HD/Disk_Planet",
             "checkpoint_times": [2.0, 5.0, 10.0]}'
```

**Resume** from snapshot 5:
```bash
python ~/.agents/skills/pluto/scripts/run_pluto.py \
    --run-dir $PLUTO_DIR/Test_Problems/HD/Disk_Planet --tstop 10 --restart 5
```

---

## Other useful test problems in `$PLUTO_DIR/Test_Problems/`

| Path | Physics | Notes |
|---|---|---|
| `HD/Disk_Vortex/` | HD polar | Rossby wave instability |
| `HD/Jet/` | HD cylindrical | Jet propagation |
| `MHD/Disk_Wind/` | MHD polar | Magnetically driven disk wind |
| `Particles/Dust/` | HD + dust particles | Dust-gas drag coupling |
