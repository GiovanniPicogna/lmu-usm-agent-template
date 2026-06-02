"""Unit tests for file discovery and per-target zip bundling."""

from __future__ import annotations

import zipfile

from src.zenodo.archive import bundle_target, collect_files
from src.zenodo.config import TargetConfig


# ── collect_files ─────────────────────────────────────────────────────────────


def test_collect_files_returns_all_files_recursively(tmp_path):
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "fit.json").write_text("{}")
    (tmp_path / "results" / "sub").mkdir()
    (tmp_path / "results" / "sub" / "chain.h5").write_bytes(b"hdf5")

    target = TargetConfig(name="results", path=tmp_path / "results", description="t")
    files = collect_files(target)

    assert len(files) == 2
    assert all(f.is_file() for f in files)


def test_collect_files_returns_empty_for_missing_path(tmp_path):
    target = TargetConfig(name="data", path=tmp_path / "nope", description="t")
    assert collect_files(target) == []


def test_collect_files_skips_directories(tmp_path):
    root = tmp_path / "plots"
    root.mkdir()
    (root / "fig1.pdf").write_bytes(b"%PDF")
    (root / "subdir").mkdir()

    target = TargetConfig(name="plots", path=root, description="t")
    files = collect_files(target)
    assert len(files) == 1
    assert files[0].name == "fig1.pdf"


def test_collect_files_skips_gitkeep(tmp_path):
    root = tmp_path / "results"
    root.mkdir()
    (root / ".gitkeep").write_text("")
    (root / "real.json").write_text("{}")

    files = collect_files(TargetConfig(name="results", path=root, description="t"))
    assert [f.name for f in files] == ["real.json"]


# ── bundle_target ─────────────────────────────────────────────────────────────


def test_bundle_target_creates_zip_with_relative_paths(tmp_path):
    root = tmp_path / "results"
    (root / "sub").mkdir(parents=True)
    (root / "fit.json").write_text("{}")
    (root / "sub" / "chain.h5").write_bytes(b"hdf5")
    staging = tmp_path / "staging"
    staging.mkdir()

    target = TargetConfig(name="results", path=root, description="t")
    zip_path = bundle_target(target, staging)

    assert zip_path is not None
    assert zip_path.name == "results.zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
    # arcnames are relative to the target's parent, so they keep the 'results/' prefix
    assert names == ["results/fit.json", "results/sub/chain.h5"]


def test_bundle_target_returns_none_for_empty_target(tmp_path):
    root = tmp_path / "plots"
    root.mkdir()
    staging = tmp_path / "staging"
    staging.mkdir()

    target = TargetConfig(name="plots", path=root, description="t")
    assert bundle_target(target, staging) is None


def test_bundle_target_is_deterministic(tmp_path):
    root = tmp_path / "results"
    root.mkdir()
    (root / "b.json").write_text("b")
    (root / "a.json").write_text("a")
    staging = tmp_path / "staging"
    staging.mkdir()

    target = TargetConfig(name="results", path=root, description="t")
    zip_path = bundle_target(target, staging)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    # entries are written in sorted order regardless of filesystem iteration
    assert names == ["results/a.json", "results/b.json"]
