import numpy as np
import pandas as pd


def clip_score(series: pd.Series) -> pd.Series:
    """Keep score values within a 0-100 range."""
    return series.clip(lower=0, upper=100)


def classify_risk_band(score: float) -> str:
    """Convert numeric score to a simple risk band."""
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "Elevated"
    return "High"


def calculate_layer_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate financial-sector risk layer scores."""

    scored = df.copy()

    scored["market_stress_risk"] = clip_score(
        scored[
            [
                "market_stress_proxy",
                "inflation_pressure",
                "currency_pressure",
            ]
        ].mean(axis=1)
    )

    scored["financial_crime_exposure_risk"] = clip_score(
        scored[
            [
                "financial_crime_exposure",
                "corruption_risk",
                "aml_cft_weakness",
            ]
        ].mean(axis=1)
    )

    scored["governance_regulatory_risk"] = clip_score(
        scored[
            [
                "governance_weakness",
                "regulatory_quality_weakness",
                "corruption_risk",
            ]
        ].mean(axis=1)
    )

    scored["banking_macro_stress_risk"] = clip_score(
        scored[
            [
                "banking_stress_proxy",
                "sovereign_debt_pressure",
                "market_stress_proxy",
            ]
        ].mean(axis=1)
    )

    scored["sanctions_geopolitical_risk"] = clip_score(
        scored[
            [
                "sanctions_exposure",
                "geopolitical_instability",
                "governance_weakness",
            ]
        ].mean(axis=1)
    )

    scored["cyber_operational_risk"] = clip_score(
        scored["cyber_operational_pressure"]
    )

    return scored


def calculate_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate final Financial Sector Risk Score.

    Starting weights:
    - 20% Market Stress Risk
    - 20% Financial Crime Exposure Risk
    - 20% Governance / Regulatory Risk
    - 15% Banking / Macro Stress Risk
    - 15% Sanctions / Geopolitical Risk
    - 10% Cyber / Operational Risk
    """

    scored = df.copy()

    scored["financial_sector_risk_score"] = clip_score(
        0.20 * scored["market_stress_risk"]
        + 0.20 * scored["financial_crime_exposure_risk"]
        + 0.20 * scored["governance_regulatory_risk"]
        + 0.15 * scored["banking_macro_stress_risk"]
        + 0.15 * scored["sanctions_geopolitical_risk"]
        + 0.10 * scored["cyber_operational_risk"]
    )

    scored["financial_sector_risk_score"] = scored[
        "financial_sector_risk_score"
    ].round(2)

    scored["risk_band"] = scored["financial_sector_risk_score"].apply(
        classify_risk_band
    )

    return scored


def identify_primary_driver(row: pd.Series) -> str:
    """Identify the highest contributing risk layer for each country."""

    layer_columns = {
        "market_stress_risk": "Market Stress",
        "financial_crime_exposure_risk": "Financial Crime Exposure",
        "governance_regulatory_risk": "Governance / Regulatory",
        "banking_macro_stress_risk": "Banking / Macro Stress",
        "sanctions_geopolitical_risk": "Sanctions / Geopolitical",
        "cyber_operational_risk": "Cyber / Operational",
    }

    highest_column = max(layer_columns.keys(), key=lambda col: row[col])
    return layer_columns[highest_column]


def add_driver_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Add primary driver and ranked output fields."""

    scored = df.copy()

    scored["primary_risk_driver"] = scored.apply(identify_primary_driver, axis=1)

    scored = scored.sort_values(
        by="financial_sector_risk_score",
        ascending=False,
    ).reset_index(drop=True)

    scored.insert(0, "rank", np.arange(1, len(scored) + 1))

    return scored