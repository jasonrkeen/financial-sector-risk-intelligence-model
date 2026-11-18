"""Configuration for the fictional offline demonstration only."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "data/sample/fictional_jurisdictions.csv"
SAMPLE_OUTPUT = ROOT / "outputs/sample"


@dataclass(frozen=True)
class SampleConfig:
    seed: int = 42
    simulations: int = 1000
    noise_std: float = 7.5

    def __post_init__(self) -> None:
        if self.seed < 0:
            raise ValueError("Seed must be nonnegative")
        if self.simulations < 2:
            raise ValueError("At least two simulations are required for sample statistics")
        if not 0 <= self.noise_std < float("inf"):
            raise ValueError("Noise must be finite and nonnegative")
