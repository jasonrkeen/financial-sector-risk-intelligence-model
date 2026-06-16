import pandas as pd

from src.config import TABLES_DIR
from src.fatf_sanctions import build_fatf_reference_table
from src.source_status import build_live_source_status_table


def build_country_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a clean country profile table for analyst review."""

    columns = [
        "rank",
        "country",
        "region",
        "financial_sector_risk_score",
        "risk_band",
        "primary_risk_driver",
        "market_stress_risk",
        "financial_crime_exposure_risk",
        "governance_regulatory_risk",
        "banking_macro_stress_risk",
        "sanctions_geopolitical_risk",
        "cyber_operational_risk",
    ]

    return df[columns].copy()


def build_risk_layer_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize average risk by region and layer."""

    layer_columns = [
        "market_stress_risk",
        "financial_crime_exposure_risk",
        "governance_regulatory_risk",
        "banking_macro_stress_risk",
        "sanctions_geopolitical_risk",
        "cyber_operational_risk",
        "financial_sector_risk_score",
    ]

    summary = (
        df.groupby("region")[layer_columns]
        .mean()
        .round(2)
        .reset_index()
        .sort_values("financial_sector_risk_score", ascending=False)
    )

    return summary


def build_source_register() -> pd.DataFrame:
    """Build a source register for active, reference, fallback, and planned sources."""

    records = [
        {
            "source_name": "Manual seed dataset",
            "source_type": "Internal baseline",
            "status": "Fallback",
            "use_case": "Offline scoring pipeline validation",
            "notes": "Values are directional 0-100 proxy scores for model testing if live sources fail.",
        },
        {
            "source_name": "World Bank API",
            "source_type": "Live public API",
            "status": "Active",
            "use_case": "Governance, macroeconomic, inflation, debt, and GDP growth indicators",
            "notes": "Used for live macro/governance proxy inputs.",
        },
        {
            "source_name": "FATF public lists",
            "source_type": "Public reference source",
            "status": "Active reference layer",
            "use_case": "AML/CFT jurisdictional risk indicators",
            "notes": "Used for high-risk call-for-action and increased-monitoring jurisdiction adjustments.",
        },
        {
            "source_name": "Market data connector",
            "source_type": "Live public market data",
            "status": "Active",
            "use_case": "Market stress, banking pressure, volatility, and dollar-pressure proxy signals",
            "notes": "Uses market ETF/index proxies to add broad financial stress context.",
        },
        {
            "source_name": "ACLED",
            "source_type": "Live authenticated API",
            "status": "Active",
            "use_case": "Country-level political violence, protest, fatalities, and geographic spread indicators",
            "notes": "Uses aggregated 90-day country-level event signals only.",
        },
        {
            "source_name": "OpenSanctions / OFAC",
            "source_type": "Planned public data source",
            "status": "Planned",
            "use_case": "Sanctions exposure and restricted-party environment",
            "notes": "Future lawful research/compliance-style jurisdictional aggregation layer.",
        },
        {
            "source_name": "GDELT",
            "source_type": "Optional public data source",
            "status": "Optional",
            "use_case": "News-pressure and geopolitical narrative monitoring",
            "notes": "Optional backup or comparison layer if ACLED is unavailable.",
        },
    ]

    return pd.DataFrame(records)


def save_outputs(scored_df: pd.DataFrame) -> None:
    """Save model output tables."""

    full_output = scored_df.copy()
    country_profiles = build_country_profile_table(scored_df)
    layer_summary = build_risk_layer_summary(scored_df)
    source_register = build_source_register()
    fatf_reference = build_fatf_reference_table()
    live_source_status = build_live_source_status_table()

    full_output.to_csv(
        TABLES_DIR / "financial_sector_risk_scores.csv",
        index=False,
    )

    country_profiles.to_csv(
        TABLES_DIR / "country_financial_risk_profiles.csv",
        index=False,
    )

    layer_summary.to_csv(
        TABLES_DIR / "risk_layer_summary.csv",
        index=False,
    )

    source_register.to_csv(
        TABLES_DIR / "source_register.csv",
        index=False,
    )

    fatf_reference.to_csv(
        TABLES_DIR / "fatf_sanctions_reference.csv",
        index=False,
    )

    live_source_status.to_csv(
        TABLES_DIR / "live_source_status.csv",
        index=False,
    )


def save_scenario_outputs(
    scenario_df: pd.DataFrame,
    scenario_summary: pd.DataFrame,
) -> None:
    """Save scenario analysis output tables."""

    scenario_df.to_csv(
        TABLES_DIR / "scenario_results.csv",
        index=False,
    )

    scenario_summary.to_csv(
        TABLES_DIR / "scenario_summary.csv",
        index=False,
    )


def save_monte_carlo_outputs(
    monte_carlo_df: pd.DataFrame,
    monte_carlo_summary: pd.DataFrame,
) -> None:
    """Save Monte Carlo output tables."""

    monte_carlo_df.to_csv(
        TABLES_DIR / "monte_carlo_results.csv",
        index=False,
    )

    monte_carlo_summary.to_csv(
        TABLES_DIR / "monte_carlo_summary.csv",
        index=False,
    )