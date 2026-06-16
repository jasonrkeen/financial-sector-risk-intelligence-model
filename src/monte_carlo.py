import numpy as np
import pandas as pd

from src.scoring import classify_risk_band


LAYER_COLUMNS = [
    "market_stress_risk",
    "financial_crime_exposure_risk",
    "governance_regulatory_risk",
    "banking_macro_stress_risk",
    "sanctions_geopolitical_risk",
    "cyber_operational_risk",
]


LAYER_WEIGHTS = {
    "market_stress_risk": 0.20,
    "financial_crime_exposure_risk": 0.20,
    "governance_regulatory_risk": 0.20,
    "banking_macro_stress_risk": 0.15,
    "sanctions_geopolitical_risk": 0.15,
    "cyber_operational_risk": 0.10,
}


def calculate_weighted_score(row: pd.Series) -> float:
    """Calculate a weighted composite score from simulated layer values."""

    score = 0.0

    for layer, weight in LAYER_WEIGHTS.items():
        score += row[layer] * weight

    return round(float(np.clip(score, 0, 100)), 2)


def run_monte_carlo_simulation(
    scored_df: pd.DataFrame,
    n_simulations: int = 1000,
    noise_std: float = 7.5,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Run Monte Carlo robustness testing.

    Each simulation perturbs the existing risk-layer scores with normally
    distributed noise. This does not forecast real-world outcomes. It tests
    whether rankings and scores are stable when input assumptions vary.
    """

    rng = np.random.default_rng(random_seed)
    simulation_records = []

    base_columns = [
        "country",
        "region",
        "financial_sector_risk_score",
        "risk_band",
        "primary_risk_driver",
    ]

    for simulation_id in range(1, n_simulations + 1):
        simulated = scored_df[base_columns + LAYER_COLUMNS].copy()

        for layer in LAYER_COLUMNS:
            noise = rng.normal(loc=0, scale=noise_std, size=len(simulated))
            simulated[layer] = np.clip(simulated[layer] + noise, 0, 100)

        simulated["simulated_financial_sector_risk_score"] = simulated.apply(
            calculate_weighted_score,
            axis=1,
        )

        simulated["simulated_risk_band"] = simulated[
            "simulated_financial_sector_risk_score"
        ].apply(classify_risk_band)

        simulated = simulated.sort_values(
            "simulated_financial_sector_risk_score",
            ascending=False,
        ).reset_index(drop=True)

        simulated["simulated_rank"] = np.arange(1, len(simulated) + 1)
        simulated["simulation_id"] = simulation_id

        simulation_records.append(
            simulated[
                [
                    "simulation_id",
                    "country",
                    "region",
                    "financial_sector_risk_score",
                    "simulated_financial_sector_risk_score",
                    "simulated_rank",
                    "risk_band",
                    "simulated_risk_band",
                    "primary_risk_driver",
                ]
            ]
        )

    results = pd.concat(simulation_records, ignore_index=True)

    return results


def build_monte_carlo_summary(monte_carlo_df: pd.DataFrame) -> pd.DataFrame:
    """Build summary statistics for Monte Carlo results."""

    summary = (
        monte_carlo_df.groupby(["country", "region"])
        .agg(
            baseline_score=("financial_sector_risk_score", "first"),
            mean_simulated_score=(
                "simulated_financial_sector_risk_score",
                "mean",
            ),
            median_simulated_score=(
                "simulated_financial_sector_risk_score",
                "median",
            ),
            std_simulated_score=(
                "simulated_financial_sector_risk_score",
                "std",
            ),
            min_simulated_score=(
                "simulated_financial_sector_risk_score",
                "min",
            ),
            max_simulated_score=(
                "simulated_financial_sector_risk_score",
                "max",
            ),
            mean_simulated_rank=("simulated_rank", "mean"),
            rank_volatility=("simulated_rank", "std"),
            best_simulated_rank=("simulated_rank", "min"),
            worst_simulated_rank=("simulated_rank", "max"),
            high_risk_probability=(
                "simulated_risk_band",
                lambda x: round(float((x == "High").mean()), 3),
            ),
            elevated_or_high_probability=(
                "simulated_risk_band",
                lambda x: round(float(((x == "Elevated") | (x == "High")).mean()), 3),
            ),
        )
        .round(2)
        .reset_index()
        .sort_values("mean_simulated_score", ascending=False)
    )

    summary.insert(0, "monte_carlo_rank", np.arange(1, len(summary) + 1))

    return summary