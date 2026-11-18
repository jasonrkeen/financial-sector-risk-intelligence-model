"""Offline synthetic demonstration; never invokes the live-data pipeline."""

import argparse
from dataclasses import asdict
import hashlib
from io import BytesIO
from importlib.metadata import version
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from src.sample_config import ROOT, SAMPLE_INPUT, SAMPLE_OUTPUT, SampleConfig
from src.scoring import calculate_layer_scores, calculate_composite_score, add_driver_analysis
from src.scenarios import run_scenario_analysis, build_scenario_summary
from src.monte_carlo import run_monte_carlo_simulation, build_monte_carlo_summary


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_path(path: Path) -> Path:
    """Resolve paths from repo root and protect existing and non-sample files."""
    destination = (ROOT / path).resolve()
    if destination == ROOT or destination in ROOT.parents:
        raise ValueError("Output cannot be the repository or its parent")
    if ROOT in destination.parents and not destination.is_relative_to(SAMPLE_OUTPUT.resolve()):
        raise ValueError("Within the repository, output must be under outputs/sample")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {destination}")
    return destination


def write_visuals(scored: pd.DataFrame, destination: Path) -> None:
    """Create a plainly labeled sample chart and brief, not a live-data report."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(scored["country"], scored["financial_sector_risk_score"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Constructed score (not an event probability)")
    ax.set_title("SYNTHETIC DEMO — fictional jurisdictions")
    fig.tight_layout()
    fig.savefig(destination / "synthetic_scores.png", dpi=120)
    plt.close(fig)

    canvas = Canvas(str(destination / "synthetic_brief.pdf"), pagesize=letter,
                    invariant=1, pageCompression=1)
    canvas.setTitle("Synthetic financial-sector demonstration")
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40, 745, "SYNTHETIC DEMO - fictional jurisdictions")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(40, 720, "Software demonstration only. No observed country data or live sources.")
    canvas.drawString(40, 705, "Scores and simulation shares are not real-world event probabilities.")
    for index, row in scored.iterrows():
        canvas.drawString(40, 675 - index * 18,
                          f"{row['country']}: {row['financial_sector_risk_score']:.2f} ({row['risk_band']})")
    canvas.drawImage(ImageReader(BytesIO((destination / "synthetic_scores.png").read_bytes())),
                     40, 325, width=530, height=265)
    canvas.drawString(40, 295, "See run_manifest.json for input/code hashes, settings and environment.")
    canvas.drawString(40, 280, "This does not validate the live-data pipeline or predictive accuracy.")
    canvas.save()


def run_sample(destination: Path = SAMPLE_OUTPUT, config: SampleConfig = SampleConfig()) -> dict:
    destination = output_path(destination)
    inputs = pd.read_csv(SAMPLE_INPUT)
    scored = add_driver_analysis(calculate_composite_score(calculate_layer_scores(inputs)))
    scenarios = run_scenario_analysis(scored)
    draws = run_monte_carlo_simulation(scored, n_simulations=config.simulations,
                                     noise_std=config.noise_std, random_seed=config.seed)
    tables = {
        "synthetic_inputs.csv": inputs,
        "synthetic_scores.csv": scored,
        "synthetic_scenarios.csv": scenarios,
        "synthetic_scenario_summary.csv": build_scenario_summary(scenarios),
        "synthetic_monte_carlo.csv": draws,
        "synthetic_monte_carlo_summary.csv": build_monte_carlo_summary(draws),
    }
    destination.mkdir(parents=True, exist_ok=False)
    for name, frame in tables.items():
        frame.to_csv(destination / name, index=False, lineterminator="\n", float_format="%.8f")
    write_visuals(scored, destination)
    source_paths = ["src/scoring.py", "src/scenarios.py", "src/monte_carlo.py",
                    "src/sample_run.py", "src/sample_config.py"]
    manifest = {
        "status": "SYNTHETIC_DEMONSTRATION_NOT_EMPIRICALLY_VALIDATED",
        "source": "Bundled fictional fixture; no real-world observation date",
        "input_sha256": sha256(SAMPLE_INPUT),
        "config": asdict(config),
        "environment": {"python": platform.python_version(), "system": platform.system(),
                        "packages": {name: version(name) for name in
                                     ("numpy", "pandas", "matplotlib", "reportlab")}},
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                          for name in source_paths},
        "requirements_sha256": hashlib.sha256((ROOT / "requirements.txt").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "artifact_sha256": {path.name: sha256(path) for path in sorted(destination.iterdir())},
        "limits": "Repeatability within a recorded environment; no live-source or predictive validation.",
    }
    (destination / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SAMPLE_OUTPUT)
    parser.add_argument("--seed", type=int, default=SampleConfig.seed)
    parser.add_argument("--simulations", type=int, default=SampleConfig.simulations)
    args = parser.parse_args()
    try:
        manifest = run_sample(args.output_dir, SampleConfig(seed=args.seed, simulations=args.simulations))
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print("SYNTHETIC DEMO complete; expected scores: Delta 90, Gamma 65, Beta 40, Alpha 10.")
    print(json.dumps(manifest["config"], sort_keys=True))


if __name__ == "__main__":
    main()
