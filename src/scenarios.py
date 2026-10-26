import pandas as pd

from src.scoring import classify_risk_band, validate_scored_inputs


SCENARIOS = {
    "Baseline": {
        "market_stress_risk": 1.00,
        "financial_crime_exposure_risk": 1.00,
        "governance_regulatory_risk": 1.00,
        "banking_macro_stress_risk": 1.00,
        "sanctions_geopolitical_risk": 1.00,
        "cyber_operational_risk": 1.00,
    },
    "Market Shock": {
        "market_stress_risk": 1.35,
        "financial_crime_exposure_risk": 1.05,
        "governance_regulatory_risk": 1.00,
        "banking_macro_stress_risk": 1.25,
        "sanctions_geopolitical_risk": 1.05,
        "cyber_operational_risk": 1.00,
    },
    "Banking Stress": {
        "market_stress_risk": 1.15,
        "financial_crime_exposure_risk": 1.05,
        "governance_regulatory_risk": 1.05,
        "banking_macro_stress_risk": 1.40,
        "sanctions_geopolitical_risk": 1.05,
        "cyber_operational_risk": 1.00,
    },
    "Financial Crime Pressure": {
        "market_stress_risk": 1.00,
        "financial_crime_exposure_risk": 1.40,
        "governance_regulatory_risk": 1.20,
        "banking_macro_stress_risk": 1.05,
        "sanctions_geopolitical_risk": 1.15,
        "cyber_operational_risk": 1.05,
    },
    "Sanctions Escalation": {
        "market_stress_risk": 1.10,
        "financial_crime_exposure_risk": 1.15,
        "governance_regulatory_risk": 1.05,
        "banking_macro_stress_risk": 1.10,
        "sanctions_geopolitical_risk": 1.45,
        "cyber_operational_risk": 1.10,
    },
    "Cyber Disruption": {
        "market_stress_risk": 1.05,
        "financial_crime_exposure_risk": 1.10,
        "governance_regulatory_risk": 1.00,
        "banking_macro_stress_risk": 1.15,
        "sanctions_geopolitical_risk": 1.05,
        "cyber_operational_risk": 1.50,
    },
    "Geopolitical Crisis": {
        "market_stress_risk": 1.20,
        "financial_crime_exposure_risk": 1.20,
        "governance_regulatory_risk": 1.15,
        "banking_macro_stress_risk": 1.20,
        "sanctions_geopolitical_risk": 1.50,
        "cyber_operational_risk": 1.20,
    },
}


LAYER_WEIGHTS = {
    "market_stress_risk": 0.20,
    "financial_crime_exposure_risk": 0.20,
    "governance_regulatory_risk": 0.20,
    "banking_macro_stress_risk": 0.15,
    "sanctions_geopolitical_risk": 0.15,
    "cyber_operational_risk": 0.10,
}


def calculate_scenario_score(row: pd.Series, scenario_multipliers: dict) -> float:
    """Calculate scenario-adjusted composite financial-sector risk score."""

    score = 0.0

    for layer, weight in LAYER_WEIGHTS.items():
        adjusted_layer_score = min(row[layer] * scenario_multipliers[layer], 100)
        score += adjusted_layer_score * weight

    return round(float(score), 2)


def run_scenario_analysis(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Run all scenario adjustments against the scored country dataset."""

    validate_scored_inputs(scored_df)
    scenario_records = []

    for scenario_name, multipliers in SCENARIOS.items():
        for _, row in scored_df.iterrows():
            scenario_score = calculate_scenario_score(row, multipliers)
            baseline_score = float(row["financial_sector_risk_score"])
            score_change = round(scenario_score - baseline_score, 2)

            scenario_records.append(
                {
                    "scenario": scenario_name,
                    "rank": row["rank"],
                    "country": row["country"],
                    "region": row["region"],
                    "baseline_financial_sector_risk_score": baseline_score,
                    "scenario_financial_sector_risk_score": scenario_score,
                    "score_change": score_change,
                    "scenario_risk_band": classify_risk_band(scenario_score),
                    "baseline_risk_band": row["risk_band"],
                    "primary_risk_driver": row["primary_risk_driver"],
                }
            )

    scenario_df = pd.DataFrame(scenario_records)

    scenario_df = scenario_df.sort_values(
        by=["scenario", "scenario_financial_sector_risk_score"],
        ascending=[True, False],
    ).reset_index(drop=True)

    scenario_df["scenario_rank"] = (
        scenario_df.groupby("scenario")[
            "scenario_financial_sector_risk_score"
        ]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    return scenario_df


def build_scenario_summary(scenario_df: pd.DataFrame) -> pd.DataFrame:
    """Build high-level scenario summary table."""

    summary = (
        scenario_df.groupby("scenario")
        .agg(
            average_scenario_score=(
                "scenario_financial_sector_risk_score",
                "mean",
            ),
            max_scenario_score=(
                "scenario_financial_sector_risk_score",
                "max",
            ),
            average_score_change=("score_change", "mean"),
            high_risk_count=(
                "scenario_risk_band",
                lambda x: int((x == "High").sum()),
            ),
            elevated_or_high_count=(
                "scenario_risk_band",
                lambda x: int(((x == "Elevated") | (x == "High")).sum()),
            ),
        )
        .round(2)
        .reset_index()
        .sort_values("average_scenario_score", ascending=False)
    )

    return summary
