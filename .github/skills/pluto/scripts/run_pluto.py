#!/usr/bin/env python3
"""
PLUTO ini patcher and runner with optional compile-check, background mode,
and on-the-fly monitor/plot support.

Usage (agent / JSON form):
    python run_pluto.py --json '{"run_dir": "runs/disk", "tstop": 500, '
    '"parameters": {"ALPHA": 1e-3}}'

Usage (CLI form):
    python run_pluto.py --run-dir runs/disk --tstop 500 --n-procs 4
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import typing as ty
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator
from scientific_pydantic.numpy import NDArrayAdapter


class PLUTOParams(BaseModel):
    run_dir: str
    output_dir: Optional[str] = None
    tstop: Optional[float] = Field(default=None, gt=0.0)
    cfl: Optional[float] = Field(default=None, ge=0.1, le=0.9)
    first_dt: Optional[float] = Field(default=None, gt=0.0)
    solver: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    n_procs: int = Field(default=1, ge=1, le=512)
    pluto_bin: str = "./pluto"
    restart: Optional[int] = Field(default=None, ge=0)
    checkpoint_times: ty.Optional[
        ty.Annotated[np.ndarray, NDArrayAdapter(ndim=1, dtype="float64", gt=0.0)]
    ] = None
    config_num: Optional[int] = Field(default=None, ge=1, le=99)
    auto_compile: bool = True
    force_compile: bool = False
    background: bool = False
    monitor: bool = False
    watch_interval: float = Field(default=20.0, ge=1.0, le=3600.0)
    plot_on_the_fly: bool = False
    plot_interval: float = Field(default=30.0, ge=1.0, le=3600.0)
    plot_output_dir: Optional[str] = None
    quiver_subsample: int = Field(default=8, ge=1, le=128)

    @field_validator("tstop", "cfl", "first_dt", mode="before")
    @classmethod
    def coerce_scientific_notation(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
        return v

    @field_validator("parameters", mode="before")
    @classmethod
    def coerce_parameters(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def run_dir_exists(self):
        if not os.path.isdir(self.run_dir):
            raise ValueError(f"run_dir does not exist: {self.run_dir!r}")
        ini = os.path.join(self.run_dir, "pluto.ini")
        if not os.path.isfile(ini):
            raise ValueError(f"pluto.ini not found in run_dir: {self.run_dir!r}")
        if self.tstop is not None and self.checkpoint_times is not None:
            raise ValueError("Specify either 'tstop' or 'checkpoint_times', not both.")
        return self


class PLUTOIniPatcher:
    _SECTION_RE = re.compile(r"^\[(.+)\]\s*$")
    _KEY_RE = re.compile(r"^(\s*)(\S+)(\s+)(.*?)(\s*)$")

    def __init__(self, ini_path: str):
        with open(ini_path) as fh:
            self.lines = fh.readlines()

    def _set_value(self, section: str, key: str, value: str) -> bool:
        in_section = False
        for i, line in enumerate(self.lines):
            sm = self._SECTION_RE.match(line)
            if sm:
                in_section = sm.group(1).strip().lower() == section.lower()
                continue
            if not in_section:
                continue
            km = self._KEY_RE.match(line)
            if km and km.group(2).lower() == key.lower():
                self.lines[i] = f"{km.group(1)}{km.group(2)}{km.group(3)}{value}\n"
                return True
        return False

    def _append_to_section(self, section: str, key: str, value: str) -> None:
        in_section = False
        insert_at = None
        for i, line in enumerate(self.lines):
            sm = self._SECTION_RE.match(line)
            if sm:
                if in_section:
                    insert_at = i
                    break
                in_section = sm.group(1).strip().lower() == section.lower()
        if in_section and insert_at is None:
            insert_at = len(self.lines)
        if insert_at is None:
            self.lines.append(f"\n[{section}]\n")
            insert_at = len(self.lines)
        self.lines.insert(insert_at, f"  {key}    {value}\n")

    def apply(
        self,
        tstop: Optional[float] = None,
        cfl: Optional[float] = None,
        first_dt: Optional[float] = None,
        solver: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        if tstop is not None:
            if not self._set_value("Time", "tstop", str(tstop)):
                self._append_to_section("Time", "tstop", str(tstop))
        if cfl is not None:
            if not self._set_value("Time", "CFL", str(cfl)):
                self._append_to_section("Time", "CFL", str(cfl))
        if first_dt is not None:
            if not self._set_value("Time", "first_dt", str(first_dt)):
                self._append_to_section("Time", "first_dt", str(first_dt))
        if solver is not None:
            if not self._set_value("Solver", "Solver", solver):
                self._append_to_section("Solver", "Solver", solver)
        if output_dir is not None:
            if not self._set_value("Output", "output_dir", output_dir):
                self._append_to_section("Output", "output_dir", output_dir)
        if parameters:
            for k, v in parameters.items():
                if not self._set_value("Parameters", k, str(v)):
                    self._append_to_section("Parameters", k, str(v))

    def write(self, path: str) -> None:
        with open(path, "w") as fh:
            fh.writelines(self.lines)


def _parse_last_snapshot(run_dir: str) -> dict:
    result = {"n": -1, "t": float("nan"), "rho_max": float("nan"), "rho_min": float("nan")}
    try:
        import h5py

        hdf_files = sorted(Path(run_dir).glob("data.*.hdf5"))
        if hdf_files:
            last = hdf_files[-1]
            result["n"] = int(last.stem.split(".")[1])
            with h5py.File(last) as hf:
                result["t"] = float(hf.attrs.get("t", float("nan")))
                rho = hf.get("rho") or hf.get("Density")
                if rho is not None:
                    arr = rho[()]
                    result["rho_max"] = float(arr.max())
                    result["rho_min"] = float(arr.min())
            return result
    except Exception:
        pass

    dbl_out = os.path.join(run_dir, "dbl.out")
    if os.path.isfile(dbl_out):
        with open(dbl_out) as fh:
            lines = [line for line in fh.readlines() if line.strip()]
        if lines:
            last_line = lines[-1].split()
            try:
                result["n"] = int(last_line[0])
                result["t"] = float(last_line[1])
            except (IndexError, ValueError):
                pass
    return result


def _find_latest_snapshot_index(run_dir: str) -> int:
    hdf_files = sorted(Path(run_dir).glob("data.*.hdf5"))
    if hdf_files:
        try:
            return int(hdf_files[-1].stem.split(".")[1])
        except Exception:
            pass
    dbl_out = os.path.join(run_dir, "dbl.out")
    if os.path.isfile(dbl_out):
        with open(dbl_out) as fh:
            lines = [line for line in fh.readlines() if line.strip()]
        if lines:
            try:
                return int(lines[-1].split()[0])
            except Exception:
                pass
    return -1


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _load_snapshot_arrays(output_dir: str, snap_n: int):
    try:
        import h5py

        for h5 in sorted(Path(output_dir).glob("data.*.hdf5")):
            try:
                idx = int(h5.stem.split(".")[1])
            except Exception:
                continue
            if idx != snap_n:
                continue
            with h5py.File(h5) as hf:
                rho = hf.get("rho") or hf.get("Density")
                vx1 = hf.get("vx1") or hf.get("Velocity1")
                vx2 = hf.get("vx2") or hf.get("Velocity2")
                if rho is None or vx1 is None or vx2 is None:
                    return None
                return rho[()], vx1[()], vx2[()]
    except Exception:
        pass

    try:
        import pyPLUTO as pp  # type: ignore

        data = pp.pload(snap_n, w_dir=output_dir)
        return np.array(data.rho), np.array(data.vx1), np.array(data.vx2)
    except Exception:
        return None


def _render_snapshot_plots(
    output_dir: str, plot_dir: str, snap_n: int, quiver_subsample: int
) -> Optional[str]:
    arrays = _load_snapshot_arrays(output_dir, snap_n)
    if arrays is None:
        return None

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    rho, vx1, vx2 = arrays
    speed = np.sqrt(vx1 * vx1 + vx2 * vx2)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=140)
    im0 = axes[0].imshow(rho, origin="lower", cmap="viridis", aspect="auto")
    axes[0].set_title(f"Density n={snap_n}")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(speed, origin="lower", cmap="cividis", aspect="auto")
    axes[1].set_title(f"|v| n={snap_n}")
    ny, nx = speed.shape
    ys = np.arange(0, ny, quiver_subsample)
    xs = np.arange(0, nx, quiver_subsample)
    xx, yy = np.meshgrid(xs, ys)
    axes[1].quiver(xx, yy, vx1[np.ix_(ys, xs)], vx2[np.ix_(ys, xs)], color="white", alpha=0.6)
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    for ax in axes:
        ax.set_xlabel("i")
        ax.set_ylabel("j")

    os.makedirs(plot_dir, exist_ok=True)
    out_path = os.path.join(plot_dir, f"snapshot_{snap_n:05d}.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def _monitor_process(
    *,
    pid: int,
    output_dir: str,
    watch_interval: float,
    plot_on_the_fly: bool,
    plot_interval: float,
    plot_output_dir: str,
    quiver_subsample: int,
    monitor_log: str,
) -> None:
    last_snap = -1
    last_plot_t = 0.0
    with open(monitor_log, "a") as log:
        log.write(f"[monitor] started pid={pid}\n")
        log.flush()
        while _process_is_alive(pid):
            snap_n = _find_latest_snapshot_index(output_dir)
            if snap_n >= 0 and snap_n != last_snap:
                stats = _parse_last_snapshot(output_dir)
                log.write(
                    f"[monitor] snapshot={stats['n']} t={stats['t']:.6g} "
                    f"rho_max={stats['rho_max']:.3e} rho_min={stats['rho_min']:.3e}\n"
                )
                log.flush()
                last_snap = snap_n

            now = time.time()
            if plot_on_the_fly and snap_n >= 0 and (now - last_plot_t) >= plot_interval:
                out = _render_snapshot_plots(output_dir, plot_output_dir, snap_n, quiver_subsample)
                if out:
                    log.write(f"[monitor] plot={out}\n")
                    log.flush()
                    last_plot_t = now

            time.sleep(watch_interval)
        log.write("[monitor] process finished\n")
        log.flush()


def _spawn_monitor_sidecar(params: PLUTOParams, output_dir: str, pid: int) -> str:
    plot_dir = params.plot_output_dir or os.path.join(output_dir, "live_plots")
    monitor_log = os.path.join(output_dir, "pluto_monitor.log")
    payload = {
        "pid": pid,
        "output_dir": output_dir,
        "watch_interval": params.watch_interval,
        "plot_on_the_fly": params.plot_on_the_fly,
        "plot_interval": params.plot_interval,
        "plot_output_dir": plot_dir,
        "quiver_subsample": params.quiver_subsample,
        "monitor_log": monitor_log,
    }
    subprocess.Popen(
        [sys.executable, __file__, "--monitor-json", json.dumps(payload)],
        cwd=params.run_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return monitor_log


def _compile_if_needed(params: PLUTOParams, pluto_exe: str) -> None:
    needs_compile = params.force_compile or not os.path.isfile(pluto_exe)
    if not needs_compile:
        return
    if not params.auto_compile and not params.force_compile:
        return

    compile_script = os.path.expanduser("~/.agents/skills/pluto/scripts/compile_pluto.py")
    cmd = [sys.executable, compile_script, "--run-dir", params.run_dir]
    if params.config_num is not None:
        cmd += ["--config-num", str(params.config_num)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=params.run_dir)
    if proc.returncode != 0:
        stderr_tail = "\n".join(proc.stderr.splitlines()[-20:])
        raise RuntimeError(f"Auto-compile failed.\n{stderr_tail}")


def _monitor_from_payload(payload_json: str) -> int:
    payload = json.loads(payload_json)
    _monitor_process(
        pid=int(payload["pid"]),
        output_dir=str(payload["output_dir"]),
        watch_interval=float(payload["watch_interval"]),
        plot_on_the_fly=bool(payload["plot_on_the_fly"]),
        plot_interval=float(payload["plot_interval"]),
        plot_output_dir=str(payload["plot_output_dir"]),
        quiver_subsample=int(payload["quiver_subsample"]),
        monitor_log=str(payload["monitor_log"]),
    )
    return 0


def run_pluto_simulation(params: PLUTOParams) -> str:
    ini_path = os.path.join(params.run_dir, "pluto.ini")
    backup_path = ini_path + ".bak_skill"
    output_dir = params.output_dir or params.run_dir
    os.makedirs(output_dir, exist_ok=True)

    shutil.copy2(ini_path, backup_path)
    proc = None
    try:
        patcher = PLUTOIniPatcher(ini_path)
        patcher.apply(
            tstop=params.tstop,
            cfl=params.cfl,
            first_dt=params.first_dt,
            solver=params.solver,
            parameters=params.parameters,
            output_dir=output_dir if output_dir != params.run_dir else None,
        )
        patcher.write(ini_path)

        pluto_exe = params.pluto_bin
        if not os.path.isabs(pluto_exe):
            pluto_exe = os.path.join(params.run_dir, pluto_exe.lstrip("./"))

        _compile_if_needed(params, pluto_exe)

        if not os.path.isfile(pluto_exe):
            pluto_exe = shutil.which("pluto") or ""
        if not pluto_exe or not os.path.isfile(pluto_exe):
            return (
                f"ERROR: PLUTO binary not found in '{params.run_dir}' and not on PATH.\n"
                "Compile first with:\n"
                "  python ~/.agents/skills/pluto/scripts/compile_pluto.py "
                f"--run-dir {params.run_dir}"
            )

        cmd: list[str] = []
        if params.n_procs > 1:
            cmd += ["mpirun", "-n", str(params.n_procs)]
        cmd += [pluto_exe]
        if params.restart is not None:
            cmd += ["-restart", str(params.restart)]

        t0 = time.time()
        run_log = os.path.join(output_dir, "pluto_run.log")
        pid_file = os.path.join(output_dir, "pluto_run.pid")

        if params.background:
            log_fh = open(run_log, "a")
            proc = subprocess.Popen(
                cmd,
                cwd=params.run_dir,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
            )
            with open(pid_file, "w") as fh:
                fh.write(str(proc.pid))
            monitor_log = "none"
            if params.monitor or params.plot_on_the_fly:
                monitor_log = _spawn_monitor_sidecar(params, output_dir, proc.pid)
            return (
                f"STARTED: pid={proc.pid} run_dir={params.run_dir}\n"
                f"  log={run_log}\n"
                f"  pid_file={pid_file}\n"
                f"  monitor_log={monitor_log}"
            )

        proc = subprocess.Popen(
            cmd,
            cwd=params.run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        last_plot_t = 0.0
        while proc.poll() is None:
            snap_n = _find_latest_snapshot_index(output_dir)
            now = time.time()
            if (
                params.plot_on_the_fly
                and snap_n >= 0
                and (now - last_plot_t) >= params.plot_interval
            ):
                plot_dir = params.plot_output_dir or os.path.join(output_dir, "live_plots")
                _render_snapshot_plots(output_dir, plot_dir, snap_n, params.quiver_subsample)
                last_plot_t = now
            if params.monitor:
                time.sleep(params.watch_interval)
            else:
                time.sleep(0.2)

        stdout, stderr = proc.communicate()
        t_wall = time.time() - t0

    except Exception as exc:
        return f"ERROR: {exc}"
    finally:
        if os.path.exists(backup_path):
            shutil.move(backup_path, ini_path)

    if proc is None:
        return "ERROR: internal error (process did not start)"

    if proc.returncode != 0:
        stderr_tail = "\n".join((stderr or "").splitlines()[-15:])
        return (
            f"ERROR: PLUTO exited with code {proc.returncode}\n"
            f"Last 15 lines of stderr:\n{stderr_tail}"
        )

    snap = _parse_last_snapshot(output_dir)
    warnings = [line for line in (stderr or "").splitlines() if "warn" in line.lower()]
    warn_str = "; ".join(warnings[:5]) if warnings else "none"
    _ = stdout
    return (
        f"SUCCESS: run_dir={params.run_dir}  stages=1  wall_clock={t_wall:.1f}s\n"
        f"  last_snapshot={snap['n']}  t={snap['t']:.4g} (code units)\n"
        f"  rho_max={snap['rho_max']:.3e}  rho_min={snap['rho_min']:.3e}\n"
        f"  warnings: {warn_str}"
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Patch pluto.ini and run PLUTO.")
    p.add_argument("--json", metavar="JSON", help="JSON string or file with all parameters")
    p.add_argument("--monitor-json", dest="monitor_json", help=argparse.SUPPRESS)
    p.add_argument("--run-dir", dest="run_dir")
    p.add_argument("--output-dir", dest="output_dir")
    p.add_argument("--tstop", type=float)
    p.add_argument("--cfl", type=float)
    p.add_argument("--first-dt", type=float, dest="first_dt")
    p.add_argument("--solver")
    p.add_argument("--n-procs", type=int, dest="n_procs")
    p.add_argument("--pluto-bin", dest="pluto_bin")
    p.add_argument("--restart", type=int)
    p.add_argument("--config-num", type=int, dest="config_num")
    p.add_argument("--auto-compile", dest="auto_compile", action="store_true", default=None)
    p.add_argument("--no-auto-compile", dest="auto_compile", action="store_false")
    p.add_argument("--force-compile", action="store_true")
    p.add_argument("--background", action="store_true")
    p.add_argument("--monitor", action="store_true")
    p.add_argument("--watch-interval", type=float, dest="watch_interval")
    p.add_argument("--plot-on-the-fly", action="store_true", dest="plot_on_the_fly")
    p.add_argument("--plot-interval", type=float, dest="plot_interval")
    p.add_argument("--plot-output-dir", dest="plot_output_dir")
    p.add_argument("--quiver-subsample", type=int, dest="quiver_subsample")
    p.add_argument(
        "--checkpoint-times",
        dest="checkpoint_times",
        help="JSON array of staged tstop values, e.g. '[100,200,500]'",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.monitor_json:
        sys.exit(_monitor_from_payload(args.monitor_json))

    raw: dict = {
        k: v for k, v in vars(args).items() if v is not None and k not in {"json", "monitor_json"}
    }

    if args.json:
        src = args.json.strip()
        if os.path.isfile(src):
            with open(src) as fh:
                raw = json.load(fh)
        else:
            raw = json.loads(src)

    try:
        params = PLUTOParams(**raw)
    except Exception as exc:
        print(f"ERROR: parameter validation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    result = run_pluto_simulation(params)
    print(result)
    if result.startswith("ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
