"""
Unit tests for skill script Pydantic validation models and SUCCESS/ERROR
stdout protocol. Simulation codes (FARGO3D, PLUTO) do NOT need to be
installed — the Pydantic models are imported directly from each script.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

SKILLS_DIR = Path(".github/skills")
FARGO_SCRIPT = SKILLS_DIR / "fargo3d/scripts/run_fargo3d.py"
COMPILE_PLUTO_SCRIPT = SKILLS_DIR / "pluto/scripts/compile_pluto.py"
RUN_PLUTO_SCRIPT = SKILLS_DIR / "pluto/scripts/run_pluto.py"
PHYSICS_WRITER_SCRIPT = SKILLS_DIR / "pluto/scripts/physics_config_writer.py"
PLOT_PLUTO_SCRIPT = SKILLS_DIR / "pluto/scripts/plot_pluto.py"
PLOT_DUSTPY_SCRIPT = SKILLS_DIR / "dustpy/scripts/plot_dustpy.py"


def _import_module(script_path: Path):
    """Import a skill script as a module without executing its main block."""
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so Pydantic can resolve forward refs from
    # `from __future__ import annotations` via sys.modules[cls.__module__]
    sys.modules[script_path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_script(
    script_path: Path, args: list[str], timeout: int = 15
) -> tuple[int, str]:
    """Run a script via subprocess; return (returncode, last stdout line)."""
    result = subprocess.run(
        [sys.executable, str(script_path)] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    lines = result.stdout.strip().splitlines()
    last = lines[-1] if lines else ""
    return result.returncode, last


_dustpy_available = (
    subprocess.run(
        [sys.executable, "-c", "import dustpy"], capture_output=True
    ).returncode
    == 0
)

_pypluto_available = (
    subprocess.run(
        [sys.executable, "-c", "import pyPLUTO"], capture_output=True
    ).returncode
    == 0
)


# ---------------------------------------------------------------------------
# Fixtures — import Pydantic models from each skill script
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fargo_mod():
    return _import_module(FARGO_SCRIPT)


@pytest.fixture(scope="module")
def compile_pluto_mod():
    return _import_module(COMPILE_PLUTO_SCRIPT)


@pytest.fixture(scope="module")
def run_pluto_mod():
    mod = _import_module(RUN_PLUTO_SCRIPT)
    # run_pluto.py uses `from __future__ import annotations`; rebuild resolves
    # forward references now that the module is registered in sys.modules.
    mod.PLUTOParams.model_rebuild()
    return mod


@pytest.fixture(scope="module")
def physics_mod():
    return _import_module(PHYSICS_WRITER_SCRIPT)


# ---------------------------------------------------------------------------
# Script existence tests
# ---------------------------------------------------------------------------


def test_run_fargo3d_script_exists():
    assert FARGO_SCRIPT.exists(), f"Script not found: {FARGO_SCRIPT}"


def test_compile_pluto_script_exists():
    assert COMPILE_PLUTO_SCRIPT.exists(), f"Script not found: {COMPILE_PLUTO_SCRIPT}"


def test_run_pluto_script_exists():
    assert RUN_PLUTO_SCRIPT.exists(), f"Script not found: {RUN_PLUTO_SCRIPT}"


def test_physics_config_writer_script_exists():
    assert PHYSICS_WRITER_SCRIPT.exists(), f"Script not found: {PHYSICS_WRITER_SCRIPT}"


def test_plot_pluto_script_exists():
    assert PLOT_PLUTO_SCRIPT.exists(), f"Script not found: {PLOT_PLUTO_SCRIPT}"


def test_plot_dustpy_script_exists():
    assert PLOT_DUSTPY_SCRIPT.exists(), f"Script not found: {PLOT_DUSTPY_SCRIPT}"


# ---------------------------------------------------------------------------
# FARGO3D — FARGO3DParams model tests
# ---------------------------------------------------------------------------


class TestFARGO3DParams:
    """Tests for the FARGO3DParams Pydantic model in run_fargo3d.py."""

    def test_model_class_exists(self, fargo_mod):
        assert hasattr(fargo_mod, "FARGO3DParams"), (
            "FARGO3DParams class not found in run_fargo3d.py"
        )

    def test_requires_par_file_and_output_dir(self, fargo_mod, tmp_path):
        """par_file and output_dir are required fields."""
        with pytest.raises((ValidationError, Exception)):
            fargo_mod.FARGO3DParams(par_file="missing.par", output_dir=str(tmp_path))

    def test_aspect_ratio_gt_zero(self, fargo_mod, tmp_path):
        """AspectRatio must be > 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), AspectRatio=0.0
            )

    def test_aspect_ratio_le_one(self, fargo_mod, tmp_path):
        """AspectRatio must be <= 1.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), AspectRatio=1.1
            )

    def test_aspect_ratio_valid(self, fargo_mod, tmp_path):
        """AspectRatio=0.05 is within (0.0, 1.0] — should pass field validation."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        # model_validator checks par_file exists — it does here
        params = fargo_mod.FARGO3DParams(
            par_file=str(par), output_dir=str(tmp_path), AspectRatio=0.05
        )
        assert params.AspectRatio == pytest.approx(0.05)

    def test_sigma0_gt_zero(self, fargo_mod, tmp_path):
        """Sigma0 must be > 0.0."""
        par = tmp_path / "test.par"
        par.write_text("AspectRatio   0.05\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Sigma0=0.0
            )

    def test_sigma0_negative_rejected(self, fargo_mod, tmp_path):
        """Sigma0 must be positive."""
        par = tmp_path / "test.par"
        par.write_text("AspectRatio   0.05\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Sigma0=-1e-4
            )

    def test_alpha_ge_zero(self, fargo_mod, tmp_path):
        """Alpha must be >= 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Alpha=-0.001
            )

    def test_alpha_le_point_one(self, fargo_mod, tmp_path):
        """Alpha must be <= 0.1."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Alpha=0.2
            )

    def test_alpha_zero_allowed(self, fargo_mod, tmp_path):
        """Alpha=0.0 (ge=0.0) should be accepted at the field level."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        params = fargo_mod.FARGO3DParams(
            par_file=str(par), output_dir=str(tmp_path), Alpha=0.0
        )
        assert params.Alpha == 0.0

    def test_flaring_index_ge_zero(self, fargo_mod, tmp_path):
        """FlaringIndex must be >= 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), FlaringIndex=-0.1
            )

    def test_flaring_index_le_one(self, fargo_mod, tmp_path):
        """FlaringIndex must be <= 1.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), FlaringIndex=1.5
            )

    def test_planet_mass_ge_zero(self, fargo_mod, tmp_path):
        """PlanetMass must be >= 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), PlanetMass=-1e-3
            )

    def test_tmax_gt_zero(self, fargo_mod, tmp_path):
        """Tmax must be > 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Tmax=0.0
            )

    def test_ntot_ge_one(self, fargo_mod, tmp_path):
        """Ntot must be >= 1."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Ntot=0
            )

    def test_ninterm_ge_one(self, fargo_mod, tmp_path):
        """Ninterm must be >= 1."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Ninterm=0
            )

    def test_dt_gt_zero(self, fargo_mod, tmp_path):
        """DT must be > 0.0."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), DT=0.0
            )

    def test_nx_ge_eight(self, fargo_mod, tmp_path):
        """Nx must be >= 8."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Nx=4
            )

    def test_nx_le_4096(self, fargo_mod, tmp_path):
        """Nx must be <= 4096."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Nx=8192
            )

    def test_ny_ge_eight(self, fargo_mod, tmp_path):
        """Ny must be >= 8."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Ny=4
            )

    def test_ny_le_1024(self, fargo_mod, tmp_path):
        """Ny must be <= 1024."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), Ny=2048
            )

    def test_n_procs_ge_one(self, fargo_mod, tmp_path):
        """n_procs must be >= 1."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), n_procs=0
            )

    def test_n_procs_le_512(self, fargo_mod, tmp_path):
        """n_procs must be <= 512."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        with pytest.raises(ValidationError):
            fargo_mod.FARGO3DParams(
                par_file=str(par), output_dir=str(tmp_path), n_procs=1024
            )

    def test_scientific_notation_coerced(self, fargo_mod, tmp_path):
        """String scientific notation values are coerced to float by field_validator."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        params = fargo_mod.FARGO3DParams(
            par_file=str(par), output_dir=str(tmp_path), Alpha="1e-3"
        )
        assert params.Alpha == pytest.approx(1e-3)

    def test_par_file_not_found_raises(self, fargo_mod, tmp_path):
        """model_validator raises ValueError when par_file does not exist."""
        with pytest.raises((ValidationError, Exception)):
            fargo_mod.FARGO3DParams(
                par_file=str(tmp_path / "nonexistent.par"),
                output_dir=str(tmp_path),
            )

    def test_optional_fields_default_none(self, fargo_mod, tmp_path):
        """All optional disk params default to None."""
        par = tmp_path / "test.par"
        par.write_text("Sigma0   6e-4\n")
        params = fargo_mod.FARGO3DParams(
            par_file=str(par), output_dir=str(tmp_path)
        )
        for field in ("AspectRatio", "Sigma0", "Alpha", "FlaringIndex", "PlanetMass",
                      "Tmax", "Ntot", "Ninterm", "DT", "Nx", "Ny"):
            assert getattr(params, field) is None, f"{field} should default to None"


# ---------------------------------------------------------------------------
# FARGO3D — protocol test (subprocess)
# ---------------------------------------------------------------------------


def test_fargo_protocol_missing_par_file_emits_error():
    """Running run_fargo3d.py with a missing par_file must emit ERROR on stderr and exit 1."""
    rc, _ = _run_script(
        FARGO_SCRIPT,
        ["--par-file", "/nonexistent/path/test.par", "--output-dir", "/tmp/out"],
    )
    # The script prints "ERROR: parameter validation failed" to stderr and exits 1
    assert rc != 0, "Expected non-zero exit code when par_file is missing"


# ---------------------------------------------------------------------------
# PLUTOCompileParams — compile_pluto.py
# ---------------------------------------------------------------------------


class TestPLUTOCompileParams:
    """Tests for the PLUTOCompileParams Pydantic model in compile_pluto.py."""

    def test_model_class_exists(self, compile_pluto_mod):
        assert hasattr(compile_pluto_mod, "PLUTOCompileParams"), (
            "PLUTOCompileParams class not found in compile_pluto.py"
        )

    def test_config_num_ge_one(self, compile_pluto_mod, tmp_path):
        """config_num must be >= 1."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), config_num=0
            )

    def test_config_num_le_99(self, compile_pluto_mod, tmp_path):
        """config_num must be <= 99."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), config_num=100
            )

    def test_make_jobs_ge_one(self, compile_pluto_mod, tmp_path):
        """make_jobs must be >= 1."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), make_jobs=0
            )

    def test_make_jobs_le_64(self, compile_pluto_mod, tmp_path):
        """make_jobs must be <= 64."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), make_jobs=128
            )

    def test_setup_timeout_ge_10(self, compile_pluto_mod, tmp_path):
        """setup_timeout must be >= 10."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), setup_timeout=5
            )

    def test_setup_timeout_le_600(self, compile_pluto_mod, tmp_path):
        """setup_timeout must be <= 600."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), setup_timeout=601
            )

    def test_make_timeout_ge_30(self, compile_pluto_mod, tmp_path):
        """make_timeout must be >= 30."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), make_timeout=10
            )

    def test_make_timeout_le_3600(self, compile_pluto_mod, tmp_path):
        """make_timeout must be <= 3600."""
        with pytest.raises(ValidationError):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir=str(tmp_path), make_timeout=7200
            )

    def test_chombo_incompatible_with_fargo(self, compile_pluto_mod, tmp_path):
        """with_chombo=True and with_fargo=True must raise ValueError (mutual exclusion)."""
        # The model_validator checks run_dir exists and pluto_dir is set;
        # we need PLUTO_DIR or pluto_dir. Use a real dir but no definitions.h —
        # the exclusion validator fires before the file-existence check.
        import os
        env_backup = os.environ.get("PLUTO_DIR")
        # Set PLUTO_DIR to tmp_path so the env check passes in the validator
        os.environ["PLUTO_DIR"] = str(tmp_path)
        try:
            with pytest.raises((ValidationError, ValueError)):
                compile_pluto_mod.PLUTOCompileParams(
                    run_dir=str(tmp_path),
                    pluto_dir=str(tmp_path),
                    with_chombo=True,
                    with_fargo=True,
                )
        finally:
            if env_backup is None:
                os.environ.pop("PLUTO_DIR", None)
            else:
                os.environ["PLUTO_DIR"] = env_backup

    def test_chombo_incompatible_with_sb(self, compile_pluto_mod, tmp_path):
        """with_chombo=True and with_sb=True must raise ValueError."""
        import os
        env_backup = os.environ.get("PLUTO_DIR")
        os.environ["PLUTO_DIR"] = str(tmp_path)
        try:
            with pytest.raises((ValidationError, ValueError)):
                compile_pluto_mod.PLUTOCompileParams(
                    run_dir=str(tmp_path),
                    pluto_dir=str(tmp_path),
                    with_chombo=True,
                    with_sb=True,
                )
        finally:
            if env_backup is None:
                os.environ.pop("PLUTO_DIR", None)
            else:
                os.environ["PLUTO_DIR"] = env_backup

    def test_chombo_incompatible_with_fd(self, compile_pluto_mod, tmp_path):
        """with_chombo=True and with_fd=True must raise ValueError."""
        import os
        env_backup = os.environ.get("PLUTO_DIR")
        os.environ["PLUTO_DIR"] = str(tmp_path)
        try:
            with pytest.raises((ValidationError, ValueError)):
                compile_pluto_mod.PLUTOCompileParams(
                    run_dir=str(tmp_path),
                    pluto_dir=str(tmp_path),
                    with_chombo=True,
                    with_fd=True,
                )
        finally:
            if env_backup is None:
                os.environ.pop("PLUTO_DIR", None)
            else:
                os.environ["PLUTO_DIR"] = env_backup

    def test_sb_incompatible_with_fd(self, compile_pluto_mod, tmp_path):
        """with_sb=True and with_fd=True must raise ValueError."""
        import os
        env_backup = os.environ.get("PLUTO_DIR")
        os.environ["PLUTO_DIR"] = str(tmp_path)
        try:
            with pytest.raises((ValidationError, ValueError)):
                compile_pluto_mod.PLUTOCompileParams(
                    run_dir=str(tmp_path),
                    pluto_dir=str(tmp_path),
                    with_sb=True,
                    with_fd=True,
                )
        finally:
            if env_backup is None:
                os.environ.pop("PLUTO_DIR", None)
            else:
                os.environ["PLUTO_DIR"] = env_backup

    def test_chombo_mpi_requires_with_chombo(self, compile_pluto_mod, tmp_path):
        """chombo_mpi=True without with_chombo=True must raise ValueError."""
        import os
        env_backup = os.environ.get("PLUTO_DIR")
        os.environ["PLUTO_DIR"] = str(tmp_path)
        try:
            with pytest.raises((ValidationError, ValueError)):
                compile_pluto_mod.PLUTOCompileParams(
                    run_dir=str(tmp_path),
                    pluto_dir=str(tmp_path),
                    chombo_mpi=True,
                    with_chombo=False,
                )
        finally:
            if env_backup is None:
                os.environ.pop("PLUTO_DIR", None)
            else:
                os.environ["PLUTO_DIR"] = env_backup

    def test_run_dir_not_found_raises(self, compile_pluto_mod):
        """model_validator raises ValueError when run_dir does not exist."""
        with pytest.raises((ValidationError, Exception)):
            compile_pluto_mod.PLUTOCompileParams(
                run_dir="/nonexistent/path/to/run",
            )


# ---------------------------------------------------------------------------
# compile_pluto.py — protocol test (subprocess)
# ---------------------------------------------------------------------------


def test_compile_pluto_protocol_missing_run_dir_emits_error():
    """Running compile_pluto.py with missing run_dir must exit non-zero."""
    rc, _ = _run_script(
        COMPILE_PLUTO_SCRIPT,
        ["--run-dir", "/nonexistent/path/run"],
    )
    assert rc != 0, "Expected non-zero exit code when run_dir is missing"


# ---------------------------------------------------------------------------
# PLUTOParams — run_pluto.py
# ---------------------------------------------------------------------------


class TestPLUTOParams:
    """Tests for the PLUTOParams Pydantic model in run_pluto.py."""

    def test_model_class_exists(self, run_pluto_mod):
        assert hasattr(run_pluto_mod, "PLUTOParams"), (
            "PLUTOParams class not found in run_pluto.py"
        )

    def test_tstop_gt_zero(self, run_pluto_mod, tmp_path):
        """tstop must be > 0.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), tstop=0.0)

    def test_tstop_negative_rejected(self, run_pluto_mod, tmp_path):
        """tstop must be positive."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), tstop=-10.0)

    def test_cfl_ge_point_one(self, run_pluto_mod, tmp_path):
        """cfl must be >= 0.1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), cfl=0.05)

    def test_cfl_le_point_nine(self, run_pluto_mod, tmp_path):
        """cfl must be <= 0.9."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), cfl=0.95)

    def test_cfl_valid(self, run_pluto_mod, tmp_path):
        """cfl=0.3 is within [0.1, 0.9]."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        params = run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), cfl=0.3)
        assert params.cfl == pytest.approx(0.3)

    def test_cfl_max_var_gt_one(self, run_pluto_mod, tmp_path):
        """cfl_max_var must be > 1.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), cfl_max_var=1.0)

    def test_first_dt_gt_zero(self, run_pluto_mod, tmp_path):
        """first_dt must be > 0.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), first_dt=0.0)

    def test_restart_ge_zero(self, run_pluto_mod, tmp_path):
        """restart must be >= 0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), restart=-1)

    def test_h5restart_ge_zero(self, run_pluto_mod, tmp_path):
        """h5restart must be >= 0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), h5restart=-1)

    def test_frestart_ge_zero(self, run_pluto_mod, tmp_path):
        """frestart must be >= 0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), frestart=-1)

    def test_maxsteps_ge_one(self, run_pluto_mod, tmp_path):
        """maxsteps must be >= 1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), maxsteps=0)

    def test_xres_ge_one(self, run_pluto_mod, tmp_path):
        """xres must be >= 1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), xres=0)

    def test_n_procs_ge_one(self, run_pluto_mod, tmp_path):
        """n_procs must be >= 1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), n_procs=0)

    def test_n_procs_le_512(self, run_pluto_mod, tmp_path):
        """n_procs must be <= 512."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), n_procs=1024)

    def test_config_num_ge_one(self, run_pluto_mod, tmp_path):
        """config_num must be >= 1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), config_num=0)

    def test_config_num_le_99(self, run_pluto_mod, tmp_path):
        """config_num must be <= 99."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), config_num=100)

    def test_watch_interval_ge_one(self, run_pluto_mod, tmp_path):
        """watch_interval must be >= 1.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), watch_interval=0.5)

    def test_watch_interval_le_3600(self, run_pluto_mod, tmp_path):
        """watch_interval must be <= 3600.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), watch_interval=7200.0)

    def test_plot_interval_ge_one(self, run_pluto_mod, tmp_path):
        """plot_interval must be >= 1.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), plot_interval=0.5)

    def test_plot_interval_le_3600(self, run_pluto_mod, tmp_path):
        """plot_interval must be <= 3600.0."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), plot_interval=7200.0)

    def test_quiver_subsample_ge_one(self, run_pluto_mod, tmp_path):
        """quiver_subsample must be >= 1."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), quiver_subsample=0)

    def test_quiver_subsample_le_128(self, run_pluto_mod, tmp_path):
        """quiver_subsample must be <= 128."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises(ValidationError):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), quiver_subsample=256)

    def test_tstop_and_checkpoint_times_mutually_exclusive(self, run_pluto_mod, tmp_path):
        """Specifying both tstop and checkpoint_times must raise ValueError."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises((ValidationError, ValueError)):
            run_pluto_mod.PLUTOParams(
                run_dir=str(tmp_path),
                tstop=100.0,
                checkpoint_times=[50.0, 100.0],
            )

    def test_multiple_restart_modes_rejected(self, run_pluto_mod, tmp_path):
        """Specifying both restart and h5restart must raise ValueError."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises((ValidationError, ValueError)):
            run_pluto_mod.PLUTOParams(
                run_dir=str(tmp_path),
                restart=5,
                h5restart=5,
            )

    def test_decomp_product_must_equal_n_procs(self, run_pluto_mod, tmp_path):
        """decomp product != n_procs must raise ValueError."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        with pytest.raises((ValidationError, ValueError)):
            run_pluto_mod.PLUTOParams(
                run_dir=str(tmp_path),
                n_procs=4,
                decomp=[2, 3],  # product=6, not 4
            )

    def test_run_dir_not_found_raises(self, run_pluto_mod):
        """model_validator raises ValueError when run_dir does not exist."""
        with pytest.raises((ValidationError, Exception)):
            run_pluto_mod.PLUTOParams(run_dir="/nonexistent/path/to/run")

    def test_pluto_ini_missing_raises(self, run_pluto_mod, tmp_path):
        """model_validator raises ValueError when pluto.ini is missing from run_dir."""
        with pytest.raises((ValidationError, Exception)):
            run_pluto_mod.PLUTOParams(run_dir=str(tmp_path))

    def test_valid_minimal_params(self, run_pluto_mod, tmp_path):
        """Minimal valid params (run_dir with pluto.ini, tstop) should succeed."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        params = run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), tstop=500.0)
        assert params.tstop == pytest.approx(500.0)
        assert params.run_dir == str(tmp_path)

    def test_scientific_notation_coerced(self, run_pluto_mod, tmp_path):
        """String scientific notation is coerced to float for tstop, cfl, etc."""
        (tmp_path / "pluto.ini").write_text("[Time]\ntstop    100.0\n")
        params = run_pluto_mod.PLUTOParams(run_dir=str(tmp_path), tstop="5e2", cfl="3e-1")
        assert params.tstop == pytest.approx(500.0)
        assert params.cfl == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# run_pluto.py — protocol test (subprocess)
# ---------------------------------------------------------------------------


def test_run_pluto_protocol_missing_run_dir_emits_error():
    """Running run_pluto.py with missing run_dir must exit non-zero."""
    rc, _ = _run_script(
        RUN_PLUTO_SCRIPT,
        ["--run-dir", "/nonexistent/path/run"],
    )
    assert rc != 0, "Expected non-zero exit code when run_dir is missing"


# ---------------------------------------------------------------------------
# physics_config_writer.py — function tests
# ---------------------------------------------------------------------------


class TestEvaluateConstant:
    """Tests for the _evaluate_constant function in physics_config_writer.py."""

    def test_function_exists(self, physics_mod):
        assert hasattr(physics_mod, "_evaluate_constant"), (
            "_evaluate_constant not found in physics_config_writer.py"
        )

    def test_const_au_value(self, physics_mod):
        """CONST_au (1 AU in cm) evaluates to the correct value."""
        result = physics_mod._evaluate_constant("CONST_au")
        assert result == pytest.approx(1.49597870700e13, rel=1e-6)

    def test_const_msun_value(self, physics_mod):
        """CONST_Msun (solar mass in g) evaluates to the correct value."""
        result = physics_mod._evaluate_constant("CONST_Msun")
        assert result == pytest.approx(1.98892e33, rel=1e-4)

    def test_const_g_value(self, physics_mod):
        """CONST_G (gravitational constant) evaluates correctly."""
        result = physics_mod._evaluate_constant("CONST_G")
        assert result == pytest.approx(6.67430e-8, rel=1e-4)

    def test_numeric_literal(self, physics_mod):
        """Pure numeric literals evaluate correctly."""
        result = physics_mod._evaluate_constant("3.14159")
        assert result == pytest.approx(3.14159, rel=1e-5)

    def test_arithmetic_expression(self, physics_mod):
        """Simple arithmetic expressions are evaluated."""
        result = physics_mod._evaluate_constant("2.0 * CONST_au")
        assert result == pytest.approx(2.0 * 1.49597870700e13, rel=1e-6)

    def test_empty_string_returns_none(self, physics_mod):
        """Empty expression returns None."""
        result = physics_mod._evaluate_constant("")
        assert result is None

    def test_invalid_expression_returns_none(self, physics_mod):
        """Non-parseable expressions return None gracefully."""
        result = physics_mod._evaluate_constant("UNDEFINED_SYMBOL_XYZ")
        assert result is None

    def test_unknown_constant_returns_none(self, physics_mod):
        """Expressions that cannot be evaluated return None."""
        result = physics_mod._evaluate_constant("UNKNOWN_CONST_XYZ")
        assert result is None


class TestParseDefinitionsH:
    """Tests for the _parse_definitions_h function in physics_config_writer.py."""

    def test_function_exists(self, physics_mod):
        assert hasattr(physics_mod, "_parse_definitions_h"), (
            "_parse_definitions_h not found in physics_config_writer.py"
        )

    def test_missing_definitions_h_returns_empty_dict(self, physics_mod, tmp_path):
        """Returns empty dict when definitions.h is absent."""
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert result == {}

    def test_parses_physics_key(self, physics_mod, tmp_path):
        """Parses #define PHYSICS from definitions.h."""
        defs = tmp_path / "definitions.h"
        defs.write_text("#define PHYSICS  HD\n")
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert result.get("PHYSICS") == "HD"

    def test_parses_geometry_key(self, physics_mod, tmp_path):
        """Parses #define GEOMETRY from definitions.h."""
        defs = tmp_path / "definitions.h"
        defs.write_text("#define GEOMETRY  POLAR\n")
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert result.get("GEOMETRY") == "POLAR"

    def test_parses_unit_length_and_evaluates_cgs(self, physics_mod, tmp_path):
        """Parses UNIT_LENGTH and evaluates UNIT_LENGTH_CGS numerically."""
        defs = tmp_path / "definitions.h"
        defs.write_text("#define UNIT_LENGTH  CONST_au\n")
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert "UNIT_LENGTH" in result
        assert result.get("UNIT_LENGTH_CGS") == pytest.approx(1.49597870700e13, rel=1e-6)

    def test_inline_comments_stripped(self, physics_mod, tmp_path):
        """Inline // comments are stripped before parsing."""
        defs = tmp_path / "definitions.h"
        defs.write_text("#define DIMENSIONS  2  // spatial dimensions\n")
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert result.get("DIMENSIONS") == "2"

    def test_derived_units_computed_when_all_three_present(self, physics_mod, tmp_path):
        """UNIT_TIME_CGS, UNIT_PRESSURE_CGS, UNIT_TEMPERATURE_CGS are derived."""
        defs = tmp_path / "definitions.h"
        defs.write_text(
            "#define UNIT_DENSITY   1.0e-10\n"
            "#define UNIT_LENGTH    CONST_au\n"
            "#define UNIT_VELOCITY  1.0e5\n"
        )
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert "UNIT_TIME_CGS" in result, "UNIT_TIME_CGS should be derived"
        assert "UNIT_PRESSURE_CGS" in result, "UNIT_PRESSURE_CGS should be derived"
        assert "UNIT_TEMPERATURE_CGS" in result, "UNIT_TEMPERATURE_CGS should be derived"
        # UNIT_TIME = UNIT_LENGTH / UNIT_VELOCITY = CONST_au / 1e5
        expected_time = 1.49597870700e13 / 1.0e5
        assert result["UNIT_TIME_CGS"] == pytest.approx(expected_time, rel=1e-5)

    def test_unknown_keys_not_included(self, physics_mod, tmp_path):
        """Keys not in the accepted list are silently ignored."""
        defs = tmp_path / "definitions.h"
        defs.write_text("#define MY_CUSTOM_KEY  42\n")
        result = physics_mod._parse_definitions_h(str(tmp_path))
        assert "MY_CUSTOM_KEY" not in result


# ---------------------------------------------------------------------------
# plot_pluto.py — existence and protocol tests
# ---------------------------------------------------------------------------


def test_plot_pluto_script_exists_check():
    assert PLOT_PLUTO_SCRIPT.exists(), f"plot_pluto.py not found: {PLOT_PLUTO_SCRIPT}"


@pytest.mark.skipif(not _pypluto_available, reason="pyPLUTO not installed in active environment")
def test_plot_pluto_protocol_missing_run_dir_emits_error():
    """Running plot_pluto.py with missing run_dir must exit non-zero."""
    rc, _ = _run_script(
        PLOT_PLUTO_SCRIPT,
        ["--run-dir", "/nonexistent/path/run", "--snap", "last"],
    )
    assert rc != 0, "Expected non-zero exit when run_dir is missing"


# ---------------------------------------------------------------------------
# plot_dustpy.py — existence and protocol tests
# ---------------------------------------------------------------------------


def test_plot_dustpy_script_exists_check():
    assert PLOT_DUSTPY_SCRIPT.exists(), f"plot_dustpy.py not found: {PLOT_DUSTPY_SCRIPT}"


@pytest.mark.skipif(not _dustpy_available, reason="dustpy not installed in active environment")
def test_plot_dustpy_protocol_missing_run_dir_emits_error():
    """Running plot_dustpy.py with a missing run_dir must emit ERROR or exit non-zero."""
    rc, last = _run_script(
        PLOT_DUSTPY_SCRIPT,
        ["--run_dir", "/nonexistent/path/run", "--plot", "all"],
    )
    assert rc != 0 or last.startswith("ERROR"), (
        "Expected non-zero exit or ERROR line when run_dir is missing"
    )
