"""
physics_config_writer.py — shared module
Reads UNIT_* constants and compile-time settings from definitions.h,
writes physics_config.md in run_dir.

Imported by compile_pluto.py after a successful build.
Can also be called standalone:
    python physics_config_writer.py --run-dir /path/to/problem
"""

from __future__ import annotations
import re
import argparse
from pathlib import Path
from typing import Optional

# ── Physical constants (CGS) — mirrors PLUTO's definitions ──────────────────
CONST = {
    "CONST_mp": 1.67262192e-24,  # proton mass [g]
    "CONST_me": 9.10938370e-28,  # electron mass [g]
    "CONST_kB": 1.38064852e-16,  # Boltzmann [erg/K]
    "CONST_eV": 1.60217662e-12,  # electron volt [erg]
    "CONST_hPlanck": 6.62607015e-27,  # Planck [erg s]
    "CONST_c": 2.99792458e10,  # speed of light [cm/s]
    "CONST_G": 6.67430000e-8,  # gravitational [cm³/g/s²]
    "CONST_au": 1.49597870700e13,  # astronomical unit [cm]
    "CONST_pc": 3.08567758149e18,  # parsec [cm]
    "CONST_ly": 9.46073047258e17,  # light-year [cm]
    "CONST_Rsun": 6.96000000e10,  # solar radius [cm]
    "CONST_Msun": 1.98892000e33,  # solar mass [g]
    "CONST_Lsun": 3.84600000e33,  # solar luminosity [erg/s]
    "CONST_mH": 1.67352000e-24,  # hydrogen mass [g]
    "CONST_kms": 1.00000000e5,  # 1 km in cm (so kms = cm/s per km/s)
    "CONST_sigma": 5.67051000e-5,  # Stefan-Boltzmann [erg/cm²/s/K⁴]
    "CONST_amu": 1.66053906e-24,  # atomic mass unit [g]
}


def _evaluate_constant(expr: str) -> Optional[float]:
    """
    Evaluate a C-preprocessor constant expression to a float.
    Handles: numeric literals, CONST_* names, basic arithmetic.
    """
    if not expr:
        return None
    # Replace CONST_* names with values
    for name, val in sorted(CONST.items(), key=lambda x: -len(x[0])):
        expr = expr.replace(name, str(val))
    # Strip C suffixes and cast operators
    expr = re.sub(r"\(double\)|\(float\)|\bL\b|\bf\b|\bd\b", "", expr)
    expr = expr.replace("^", "**")  # some users write ^ for power
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:
        return None


_KEY_RE = re.compile(r"#define\s+(\w+)\s+(.+)")


def _parse_definitions_h(run_dir: str) -> dict:
    """
    Extract compile-time settings from definitions.h.
    Returns a flat dict of the relevant keys.
    """
    path = Path(run_dir) / "definitions.h"
    if not path.is_file():
        return {}

    raw: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        # Strip inline comments
        if "//" in line:
            line = line[: line.index("//")]
        if "/*" in line:
            line = line[: line.index("/*")]
        m = _KEY_RE.match(line)
        if m:
            raw[m.group(1).strip()] = m.group(2).strip()

    result = {}

    # Compile-time physics settings
    for key in [
        "PHYSICS",
        "DIMENSIONS",
        "GEOMETRY",
        "COMPONENTS",
        "EQUATION_OF_STATE",
        "TIME_STEPPING",
        "RECONSTRUCTION",
        "DIVB_CONTROL",
        "RESISTIVITY",
        "VISCOSITY",
        "THERMAL_CONDUCTION",
        "BODY_FORCE",
        "COOLING",
        "ROTATING_FRAME",
        "PARTICLES",
        "USER_DEF_PARAMETERS",
        "UNIT_DENSITY",
        "UNIT_LENGTH",
        "UNIT_VELOCITY",
        "GAMMA",
        "UNIT_DENSITY_LABEL",
        "UNIT_LENGTH_LABEL",
        "UNIT_VELOCITY_LABEL",
    ]:
        if key in raw:
            result[key] = raw[key]

    # Evaluate UNIT_* numerically
    for ukey in ("UNIT_DENSITY", "UNIT_LENGTH", "UNIT_VELOCITY"):
        if ukey in raw:
            val = _evaluate_constant(raw[ukey])
            if val is not None:
                result[ukey + "_CGS"] = val

    # Derived units (if all three are known)
    ud = result.get("UNIT_DENSITY_CGS")
    ul = result.get("UNIT_LENGTH_CGS")
    uv = result.get("UNIT_VELOCITY_CGS")
    if ud and ul and uv:
        result["UNIT_TIME_CGS"] = ul / uv
        result["UNIT_PRESSURE_CGS"] = ud * uv**2
        kB = CONST["CONST_kB"]
        mH = CONST["CONST_mH"]
        result["UNIT_TEMPERATURE_CGS"] = uv**2 * mH / kB

    return result


def write_physics_config(run_dir: str, extra: Optional[dict] = None) -> str:
    """
    Parse definitions.h in run_dir, merge any extra key/values,
    and write physics_config.md.  Returns the path written.
    """
    cfg = _parse_definitions_h(run_dir)
    if extra:
        cfg.update(extra)

    lines = [
        "# physics_config.md",
        "# Written by compile_pluto.py after successful compile.",
        "# Read by run_pluto.py, plot_pluto.py to set axis labels and unit conversions.",
        "# Do not edit manually — re-run compile_pluto.py to regenerate.",
        "",
    ]

    # ── Compile-time physics ────────────────────────────────────────────────
    physics_keys = [
        "PHYSICS",
        "DIMENSIONS",
        "GEOMETRY",
        "COMPONENTS",
        "EQUATION_OF_STATE",
        "TIME_STEPPING",
        "RECONSTRUCTION",
        "DIVB_CONTROL",
        "RESISTIVITY",
        "VISCOSITY",
        "THERMAL_CONDUCTION",
        "BODY_FORCE",
        "COOLING",
        "ROTATING_FRAME",
        "PARTICLES",
        "USER_DEF_PARAMETERS",
        "GAMMA",
    ]
    lines.append("## Compile-time physics (from definitions.h)")
    for k in physics_keys:
        if k in cfg:
            lines.append(f"{k} = {cfg[k]}")

    lines.append("")
    lines.append("## Unit normalisation (from definitions.h)")

    unit_expr_keys = [
        ("UNIT_DENSITY", "expression"),
        ("UNIT_LENGTH", "expression"),
        ("UNIT_VELOCITY", "expression"),
    ]
    for k, _ in unit_expr_keys:
        if k in cfg:
            lines.append(f"{k} = {cfg[k]}")

    lines.append("")
    lines.append("## Evaluated unit values (CGS)")
    cgs_map = {
        "UNIT_DENSITY_CGS": "g/cm³",
        "UNIT_LENGTH_CGS": "cm",
        "UNIT_VELOCITY_CGS": "cm/s",
        "UNIT_TIME_CGS": "s",
        "UNIT_PRESSURE_CGS": "Ba (erg/cm³)",
        "UNIT_TEMPERATURE_CGS": "K",
    }
    for k, unit in cgs_map.items():
        if k in cfg:
            lines.append(f"{k} = {cfg[k]:.6e}    # {unit}")

    # ── Sysconf extras ──────────────────────────────────────────────────────
    if extra:
        lines.append("")
        lines.append("## Compile run metadata")
        for k, v in extra.items():
            if k not in cfg or k in (
                "arch",
                "config_num",
                "binary",
                "parallel",
                "modules",
                "compiled_at",
                "skill_version",
            ):
                lines.append(f"{k} = {v}")

    out_path = Path(run_dir) / "physics_config.md"
    out_path.write_text("\n".join(lines) + "\n")
    return str(out_path)


def read_physics_config(run_dir: str) -> dict:
    """
    Read physics_config.md back into a dict.
    Values are returned as strings; CGS floats are cast to float.
    """
    path = Path(run_dir) / "physics_config.md"
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.split("#")[0].strip()  # strip inline comment
            if k.endswith("_CGS"):
                try:
                    result[k] = float(v)
                    continue
                except ValueError:
                    pass
            result[k] = v
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    p = argparse.ArgumentParser(description="Parse definitions.h and write physics_config.md.")
    p.add_argument("--run-dir", dest="run_dir", required=True)
    args = p.parse_args()
    out = write_physics_config(args.run_dir)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
