import pytest


@pytest.fixture
def hypothesis_valid_data():
    return {
        "schema": "HypothesisHandoff/v1",
        "science_goal": "How does planet mass affect gap depth?",
        "domain": "disk",
        "hypotheses": [
            {
                "id": 1,
                "description": "A Jupiter-mass planet opens a gap via tidal torques.",
                "predicted_observables": ["gap depth: 0.1 [normalized]"],
                "parameters": {"Mplanet": {"value_or_range": "1.0", "unit": "Mjup"}},
                "novelty_score": 0.7,
                "feasibility_score": 0.9,
                "literature_refs": ["2016A&A...594A.116H"],
            }
        ],
        "priority_rank": [1],
        "top_hypothesis_id": 1,
        "debate_rounds": 3,
        "human_gate_1_confirmed": False,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def analytical_valid_data():
    return {
        "schema": "AnalyticalHandoff/v1",
        "domain": "disk",
        "science_goal": "How does planet mass affect gap depth?",
        "hypothesis_ref": 1,
        "characteristic_scales": {
            "hill_radius": {
                "value": 0.69,
                "unit": "AU",
                "formula": "r_H = a*(q/3)^(1/3)",
                "ref_bibcode": "2016A&A...594A.116H",
            },
            "pressure_scale_height": {
                "value": 2.0,
                "unit": "AU",
                "formula": "H = h * r",
                "ref_bibcode": None,
            },
        },
        "stability_criteria": [
            {
                "name": "gap_opening",
                "criterion": "q > (h/r)^3",
                "satisfied": True,
                "margin": 2.5,
                "ref_bibcode": "2001A&A...365L...1J",
            }
        ],
        "predicted_observables": [
            {
                "name": "gap_depth",
                "value": 0.1,
                "unit": "normalized",
                "uncertainty": 0.02,
                "formula_ref": "Eq. 14",
            }
        ],
        "linear_regime": True,
        "nonlinear_trigger": None,
        "parameter_recommendations": {"Sigma0": "6e-4 in code units"},
        "benchmark_script": None,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def simconfig_valid_data():
    return {
        "schema": "SimConfigHandoff/v1",
        "domain": "disk",
        "task_id": "disk_gap_depth_1mjup",
        "hypothesis_ref": 1,
        "analytical_ref": "results/analytical/disk_gap_depth_1mjup_20260601.json",
        "code": "FARGO3D",
        "code_version": "v2.0-rc1",
        "config_path": "data/runs/disk_gap_depth_1mjup/fargo.par",
        "physics_params": {"Sigma0": 6e-4, "AspectRatio": 0.05},
        "skill_invoked": ".github/skills/fargo3d/scripts/run_fargo3d.py",
        "hpc_mode": False,
        "slurm_script_path": None,
        "scheduler": None,
        "n_cores": 4,
        "walltime_h": 2.0,
        "run_cmd": "python run_fargo3d.py --par fargo.par",
        "validated": True,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def simulation_valid_data():
    return {
        "schema": "SimulationHandoff/v1",
        "task_id": "disk_gap_depth_1mjup",
        "run_dir": "/tmp/runs/disk_gap_depth_1mjup",
        "run_manifest": "/tmp/runs/disk_gap_depth_1mjup/run_manifest.json",
        "code": "FARGO3D",
        "code_version": "v2.0-rc1",
        "skill_script": ".github/skills/fargo3d/scripts/run_fargo3d.py",
        "skill_script_version": "1.0.0",
        "param_file": "/tmp/runs/disk_gap_depth_1mjup/fargo.par",
        "param_file_md5": "abc123def456abc123def456abc123de",
        "output_dir": "/tmp/runs/disk_gap_depth_1mjup/out",
        "output_files": [],
        "diagnostics": {
            "n_snapshots": 100,
            "last_snap": 99,
            "t_end_code": 100.0,
            "rho_field": "gasdens",
            "rho_units": "M_sun/AU^2",
            "rho_max": 6e-4,
            "rho_min": 1e-8,
            "wall_clock_s": 3600.0,
        },
        "units": {
            "length": "AU",
            "mass": "M_sun",
            "time": "yr",
            "density": "M_sun/AU^2",
        },
        "sanity_passed": True,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def analysis_valid_data():
    return {
        "schema": "AnalysisHandoff/v1",
        "domain": "disk",
        "task_id": "disk_gap_depth_1mjup",
        "output_dir": "/tmp/runs/disk_gap_depth_1mjup/out",
        "sim_config_ref": "results/analytical/disk_gap_depth_1mjup_20260601.json",
        "simulation_ref": None,
        "diagnostics": {"gap_depth": {"value": 0.08, "unit": "normalized", "snapshot": 99}},
        "plot_paths": ["/tmp/plots/gap_depth.pdf"],
        "data_hash": "a" * 64,
        "analytical_comparison": {},
        "sanity_passed": True,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def interpretation_valid_data():
    return {
        "schema": "InterpretationHandoff/v1",
        "domain": "disk",
        "task_id": "disk_gap_depth_1mjup",
        "science_goal": "How does planet mass affect gap depth?",
        "findings": [
            {
                "statement": "A 1 MJup planet opens a gap with depth ~0.08.",
                "evidence": "gap_depth",
                "confidence": "high",
                "literature_refs": ["2016A&A...594A.116H"],
            }
        ],
        "hypothesis_match": "confirmed",
        "analytical_agreement_summary": "Numerical gap depth agrees with prediction within 20%.",
        "plausibility_flags": [],
        "caveats": [],
        "followup_suggestions": [],
        "next_action": "write",
        "abort_reason": None,
        "human_gate_2_confirmed": False,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def spectralfit_valid_data():
    return {
        "schema": "SpectralFitHandoff/v1",
        "spectrum_file": "data/spectra/obs/core.pha",
        "background_file": "data/spectra/obs/core_bkg.pha",
        "energy_range_keV": [0.5, 7.0],
        "model": "TBabs*apec",
        "best_fit": {
            "nH": {"value": 4.6e-2, "unit": "10^22 cm^-2", "frozen": True},
            "kT": {"value": 3.5, "unit": "keV", "frozen": False},
        },
        "fit_statistic": {"stat": "cstat", "value": 245.3, "dof": 230},
        "fit_passed_sanity": True,
        "parameter_grid": "results/fits/core_grid.json",
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def mcmc_valid_data():
    return {
        "schema": "MCMCHandoff/v1",
        "chain_file": "results/fits/core_emcee.h5",
        "sampler": "emcee",
        "n_walkers": 64,
        "n_steps": 5000,
        "burn_in": 500,
        "converged": True,
        "gelman_rubin_max": 1.01,
        "medians": {"kT": 3.5, "nH": 0.046},
        "uncertainties_68": {"kT": [-0.2, 0.3], "nH": [-0.005, 0.005]},
        "corner_plot": "plots/corner_nH_kT.pdf",
        "seed": 42,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }


@pytest.fixture
def paper_valid_data():
    return {
        "schema": "PaperHandoff/v1",
        "task_id": "disk_gap_depth_1mjup",
        "domain": "disk",
        "paper_dir": "paper/disk_gap_depth_1mjup_20260601/",
        "manuscript_tex": "paper/disk_gap_depth_1mjup_20260601/manuscript.tex",
        "manuscript_pdf": "paper/disk_gap_depth_1mjup_20260601/manuscript.pdf",
        "bibliography_bib": "paper/bibliography.bib",
        "new_bibtex_keys": ["2016A&A...594A.116H"],
        "sections_written": [
            "abstract",
            "introduction",
            "methods",
            "results",
            "discussion",
            "conclusions",
        ],
        "n_figures": 3,
        "n_citations": 12,
        "compilation_status": "ok",
        "latex_errors": [],
        "todo_count": 0,
        "referee_report": "paper/disk_gap_depth_1mjup_20260601/referee_notes.md",
        "referee_score": 7.5,
        "timestamp": "2026-06-01T12:00:00Z",
        "warnings": [],
    }
