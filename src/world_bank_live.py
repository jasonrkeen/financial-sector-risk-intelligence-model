"""
World Bank live-data connector for the Financial Sector Risk Intelligence Model.

This module pulls selected public World Bank indicators and converts them into
directional 0-100 risk proxy scores.

Responsible-use note:
These are jurisdiction-level public-source indicators for strategic risk analysis.
They are not investment advice, legal conclusions, compliance determinations,
or predictions of criminal activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import requests


WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class WorldBankIndicator:
    """Configuration for a World Bank indicator used by the model."""

    code: str
    output_column: str
    risk_direction: str
    description: str


INDICATORS: list[WorldBankIndicator] = [
    WorldBankIndicator(
        code="FP.CPI.TOTL.ZG",
        output_column="inflation_annual_pct",
        risk_direction="higher_is_riskier",
        description="Inflation, consumer prices annual %",
    ),
    WorldBankIndicator(
        code="GC.DOD.TOTL.GD.ZS",
        output_column="central_government_debt_pct_gdp",
        risk_direction="higher_is_riskier",
        description="Central government debt, total % of GDP",
    ),
    WorldBankIndicator(
        code="NY.GDP.MKTP.CD",
        output_column="gdp_current_usd",
        risk_direction="context_only",
        description="GDP current US$",
    ),
    WorldBankIndicator(
        code="NY.GDP.MKTP.KD.ZG",
        output_column="gdp_growth_annual_pct",
        risk_direction="lower_is_riskier",
        description="GDP growth annual %",
    ),
    WorldBankIndicator(
        code="CC.EST",
        output_column="control_of_corruption_estimate",
        risk_direction="lower_is_riskier",
        description="Worldwide Governance Indicator: Control of Corruption",
    ),
    WorldBankIndicator(
        code="RL.EST",
        output_column="rule_of_law_estimate",
        risk_direction="lower_is_riskier",
        description="Worldwide Governance Indicator: Rule of Law",
    ),
    WorldBankIndicator(
        code="RQ.EST",
        output_column="regulatory_quality_estimate",
        risk_direction="lower_is_riskier",
        description="Worldwide Governance Indicator: Regulatory Quality",
    ),
    WorldBankIndicator(
        code="PV.EST",
        output_column="political_stability_estimate",
        risk_direction="lower_is_riskier",
        description="Worldwide Governance Indicator: Political Stability and Absence of Violence",
    ),
]


DEFAULT_COUNTRIES = {
    "United States": "USA",
    "United Kingdom": "GBR",
    "Germany": "DEU",
    "France": "FRA",
    "Japan": "JPN",
    "Canada": "CAN",
    "Brazil": "BRA",
    "Mexico": "MEX",
    "South Africa": "ZAF",
    "Turkey": "TUR",
    "Russia": "RUS",
    "China": "CHN",
    "Iran": "IRN",
    "United Arab Emirates": "ARE",
    "Singapore": "SGP",
    "Switzerland": "CHE",
}


COUNTRY_REGIONS = {
    "United States": "North America",
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Japan": "East Asia",
    "Canada": "North America",
    "Brazil": "Latin America",
    "Mexico": "Latin America",
    "South Africa": "Africa",
    "Turkey": "Middle East / Europe",
    "Russia": "Eurasia",
    "China": "East Asia",
    "Iran": "Middle East",
    "United Arab Emirates": "Middle East",
    "Singapore": "Southeast Asia",
    "Switzerland": "Europe",
}


def fetch_world_bank_indicator(
    country_codes: list[str],
    indicator_code: str,
    start_year: int = 2018,
    end_year: int = 2026,
) -> pd.DataFrame:
    """Fetch one World Bank indicator for selected country codes."""

    countries = ";".join(country_codes)
    url = (
        f"{WORLD_BANK_BASE_URL}/country/{countries}/indicator/{indicator_code}"
        f"?format=json&per_page=20000&date={start_year}:{end_year}"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    payload: list[Any] = response.json()

    if len(payload) < 2 or payload[1] is None:
        return pd.DataFrame()

    records = []

    for item in payload[1]:
        value = item.get("value")

        if value is None:
            continue

        country = item.get("country", {})
        countryiso3code = item.get("countryiso3code")
        date = item.get("date")

        records.append(
            {
                "country": country.get("value"),
                "iso3": countryiso3code,
                "year": int(date),
                "indicator_code": indicator_code,
                "value": float(value),
            }
        )

    return pd.DataFrame(records)


def fetch_latest_world_bank_data(
    countries: dict[str, str] | None = None,
    start_year: int = 2018,
    end_year: int = 2026,
) -> pd.DataFrame:
    """Fetch the latest available value for each configured indicator."""

    if countries is None:
        countries = DEFAULT_COUNTRIES

    country_codes = list(countries.values())
    all_indicator_frames = []
    year_columns = []

    for indicator in INDICATORS:
        frame = fetch_world_bank_indicator(
            country_codes=country_codes,
            indicator_code=indicator.code,
            start_year=start_year,
            end_year=end_year,
        )

        if frame.empty:
            continue

        indicator_year_column = f"{indicator.output_column}_year"

        frame = frame.sort_values(["iso3", "year"], ascending=[True, False])
        latest = frame.groupby("iso3").head(1).copy()

        latest = latest.rename(
            columns={
                "value": indicator.output_column,
                "year": indicator_year_column,
            }
        )

        latest = latest[["iso3", indicator_year_column, indicator.output_column]]

        all_indicator_frames.append(latest)
        year_columns.append(indicator_year_column)

    if not all_indicator_frames:
        return pd.DataFrame()

    merged = all_indicator_frames[0]

    for frame in all_indicator_frames[1:]:
        merged = merged.merge(frame, on="iso3", how="outer")

    existing_year_columns = [col for col in year_columns if col in merged.columns]

    if existing_year_columns:
        merged["latest_data_year"] = merged[existing_year_columns].max(axis=1)
    else:
        merged["latest_data_year"] = np.nan

    reverse_country_lookup = {iso3: country for country, iso3 in countries.items()}
    merged["country"] = merged["iso3"].map(reverse_country_lookup)
    merged["region"] = merged["country"].map(COUNTRY_REGIONS)

    output_columns = ["country", "iso3", "region", "latest_data_year"] + [
        indicator.output_column
        for indicator in INDICATORS
        if indicator.output_column in merged.columns
    ]

    return merged[output_columns + existing_year_columns].copy()


def get_column_or_fallback(
    df: pd.DataFrame,
    column_name: str,
    fallback_value: float = np.nan,
) -> pd.Series:
    """Return a dataframe column or a same-length fallback Series."""

    if column_name in df.columns:
        return pd.to_numeric(df[column_name], errors="coerce")

    return pd.Series([fallback_value] * len(df), index=df.index)


def minmax_risk_score(
    values,
    higher_is_riskier: bool = True,
    fallback_score: float = 50.0,
) -> pd.Series:
    """Convert numeric values to a 0-100 risk score using min-max scaling."""

    if isinstance(values, pd.Series):
        numeric = pd.to_numeric(values, errors="coerce")
    else:
        numeric = pd.Series([values])

    if numeric.notna().sum() < 2:
        return pd.Series([fallback_score] * len(numeric), index=numeric.index)

    min_value = numeric.min()
    max_value = numeric.max()

    if np.isclose(min_value, max_value):
        return pd.Series([fallback_score] * len(numeric), index=numeric.index)

    scaled = (numeric - min_value) / (max_value - min_value) * 100

    if not higher_is_riskier:
        scaled = 100 - scaled

    return scaled.fillna(fallback_score).clip(0, 100).round(2)


def governance_estimate_to_risk(
    values,
    fallback_score: float = 50.0,
) -> pd.Series:
    """
    Convert WGI estimate values to 0-100 risk scores.

    WGI estimates usually range roughly from -2.5 to +2.5, where higher is better.
    This converts lower governance estimates into higher risk.
    """

    if isinstance(values, pd.Series):
        numeric = pd.to_numeric(values, errors="coerce")
    else:
        numeric = pd.Series([values])

    risk = ((2.5 - numeric) / 5.0) * 100

    return risk.fillna(fallback_score).clip(0, 100).round(2)


def build_live_world_bank_financial_risk_dataset() -> pd.DataFrame:
    """
    Build a live World Bank-based financial risk dataset.

    The output columns intentionally match the seed dataset expected by the
    existing scoring pipeline.
    """

    live_df = fetch_latest_world_bank_data()

    if live_df.empty:
        raise RuntimeError("World Bank live data pull returned no records.")

    inflation = get_column_or_fallback(live_df, "inflation_annual_pct")
    debt = get_column_or_fallback(live_df, "central_government_debt_pct_gdp")
    growth = get_column_or_fallback(live_df, "gdp_growth_annual_pct")
    corruption = get_column_or_fallback(live_df, "control_of_corruption_estimate")
    rule_of_law = get_column_or_fallback(live_df, "rule_of_law_estimate")
    political_stability = get_column_or_fallback(live_df, "political_stability_estimate")
    regulatory_quality = get_column_or_fallback(live_df, "regulatory_quality_estimate")

    live_df["inflation_pressure"] = minmax_risk_score(
        inflation,
        higher_is_riskier=True,
    )

    live_df["sovereign_debt_pressure"] = minmax_risk_score(
        debt,
        higher_is_riskier=True,
    )

    growth_risk = minmax_risk_score(
        growth,
        higher_is_riskier=False,
    )

    live_df["market_stress_proxy"] = (
        0.60 * live_df["inflation_pressure"]
        + 0.40 * growth_risk
    ).round(2)

    live_df["currency_pressure"] = (
        0.65 * live_df["inflation_pressure"] + 20
    ).clip(0, 100).round(2)

    live_df["corruption_risk"] = governance_estimate_to_risk(corruption)

    live_df["governance_weakness"] = (
        governance_estimate_to_risk(rule_of_law)
        + governance_estimate_to_risk(political_stability)
    ) / 2

    live_df["governance_weakness"] = live_df["governance_weakness"].round(2)

    live_df["regulatory_quality_weakness"] = governance_estimate_to_risk(
        regulatory_quality
    )

    live_df["aml_cft_weakness"] = (
        0.50 * live_df["corruption_risk"]
        + 0.30 * live_df["regulatory_quality_weakness"]
        + 0.20 * live_df["governance_weakness"]
    ).round(2)

    live_df["financial_crime_exposure"] = (
        0.45 * live_df["corruption_risk"]
        + 0.35 * live_df["aml_cft_weakness"]
        + 0.20 * live_df["regulatory_quality_weakness"]
    ).round(2)

    live_df["banking_stress_proxy"] = (
        0.45 * live_df["sovereign_debt_pressure"]
        + 0.35 * live_df["market_stress_proxy"]
        + 0.20 * live_df["regulatory_quality_weakness"]
    ).round(2)

    live_df["sanctions_exposure"] = 25.0

    sanctions_overrides = {
        "Russia": 95,
        "Iran": 98,
        "China": 52,
        "Turkey": 38,
        "United Arab Emirates": 34,
    }

    live_df["sanctions_exposure"] = live_df.apply(
        lambda row: sanctions_overrides.get(row["country"], row["sanctions_exposure"]),
        axis=1,
    )

    live_df["geopolitical_instability"] = governance_estimate_to_risk(
        political_stability
    )

    live_df["cyber_operational_pressure"] = (
        35
        + 0.25 * live_df["market_stress_proxy"]
        + 0.25 * live_df["governance_weakness"]
    ).clip(0, 100).round(2)

    live_df["world_bank_status"] = "Active"

    if "latest_data_year" in live_df.columns:
        live_df["world_bank_latest_data_year"] = pd.to_numeric(
            live_df["latest_data_year"],
            errors="coerce",
        )
    else:
        live_df["world_bank_latest_data_year"] = np.nan

    model_columns = [
        "country",
        "region",
        "world_bank_status",
        "world_bank_latest_data_year",
        "market_stress_proxy",
        "inflation_pressure",
        "currency_pressure",
        "financial_crime_exposure",
        "corruption_risk",
        "aml_cft_weakness",
        "governance_weakness",
        "regulatory_quality_weakness",
        "banking_stress_proxy",
        "sovereign_debt_pressure",
        "sanctions_exposure",
        "geopolitical_instability",
        "cyber_operational_pressure",
    ]

    provenance_columns = [col for col in live_df.columns if col not in model_columns]
    return live_df[model_columns + provenance_columns].copy()


def build_world_bank_source_metadata() -> pd.DataFrame:
    """Build source metadata for the source register."""

    records = []

    for indicator in INDICATORS:
        records.append(
            {
                "source_name": "World Bank API",
                "source_type": "Live public API",
                "status": "Active",
                "indicator_code": indicator.code,
                "output_column": indicator.output_column,
                "use_case": indicator.description,
                "notes": "Pulled through the World Bank Indicators API.",
            }
        )

    return pd.DataFrame(records)