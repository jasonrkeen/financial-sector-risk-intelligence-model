"""
FATF and sanctions reference layer for the Financial Sector Risk Intelligence Model.

This module adds jurisdiction-level AML/CFT and sanctions risk adjustments using
public FATF list status and high-level sanctions exposure categories.

Responsible-use note:
This is a jurisdiction-level strategic risk layer. It does not identify suspects,
predict crimes, or replace legal, compliance, sanctions, or AML/CFT judgment.

Maintenance note:
This is a manually maintained public-reference layer. FATF lists and sanctions
conditions can change over time, so the reference values should be reviewed
before publication, operational use, or any decision-support use.
"""

from __future__ import annotations

import pandas as pd


FATF_REFERENCE_LAST_REVIEWED = "2026-06-15"
FATF_REFERENCE_SOURCE_NOTE = (
    "Manual reference layer based on FATF / FinCEN public statements. "
    "FATF lists are updated periodically and should be reviewed before use."
)


FATF_HIGH_RISK_CALL_FOR_ACTION = {
    "Iran",
    "North Korea",
    "Democratic People's Republic of Korea",
    "Myanmar",
    "Burma",
}


FATF_INCREASED_MONITORING = {
    "Algeria",
    "Angola",
    "Bulgaria",
    "Burkina Faso",
    "Cameroon",
    "Côte d'Ivoire",
    "Cote d'Ivoire",
    "Croatia",
    "Democratic Republic of the Congo",
    "DR Congo",
    "Haiti",
    "Kenya",
    "Kuwait",
    "Laos",
    "Lao PDR",
    "Lebanon",
    "Mali",
    "Monaco",
    "Mozambique",
    "Namibia",
    "Nepal",
    "Nigeria",
    "Papua New Guinea",
    "South Africa",
    "South Sudan",
    "Syria",
    "Tanzania",
    "Venezuela",
    "Vietnam",
    "Yemen",
}


SANCTIONS_EXPOSURE_OVERRIDES = {
    "Iran": 98,
    "Russia": 95,
    "North Korea": 100,
    "Democratic People's Republic of Korea": 100,
    "Myanmar": 88,
    "Burma": 88,
    "Syria": 86,
    "Venezuela": 76,
    "China": 52,
    "Turkey": 38,
    "United Arab Emirates": 34,
}


COUNTRY_ALIASES = {
    "Russian Federation": "Russia",
    "Iran, Islamic Rep.": "Iran",
    "Egypt, Arab Rep.": "Egypt",
    "Korea, Dem. People's Rep.": "North Korea",
    "Myanmar": "Myanmar",
    "Viet Nam": "Vietnam",
    "Lao PDR": "Laos",
    "Congo, Dem. Rep.": "Democratic Republic of the Congo",
    "Cote d'Ivoire": "Côte d'Ivoire",
}


def normalize_country_name(country: str) -> str:
    """Normalize country names for FATF and sanctions matching."""

    if not isinstance(country, str):
        return ""

    cleaned = country.strip()
    return COUNTRY_ALIASES.get(cleaned, cleaned)


def classify_fatf_status(country: str) -> str:
    """Classify jurisdiction FATF status."""

    normalized = normalize_country_name(country)

    if normalized in FATF_HIGH_RISK_CALL_FOR_ACTION:
        return "High-Risk Call for Action"

    if normalized in FATF_INCREASED_MONITORING:
        return "Increased Monitoring"

    return "Not Listed"


def fatf_status_to_aml_cft_adjustment(status: str) -> float:
    """Map FATF status to AML/CFT weakness adjustment."""

    if status == "High-Risk Call for Action":
        return 35.0

    if status == "Increased Monitoring":
        return 20.0

    return 0.0


def fatf_status_to_financial_crime_adjustment(status: str) -> float:
    """Map FATF status to financial crime exposure adjustment."""

    if status == "High-Risk Call for Action":
        return 25.0

    if status == "Increased Monitoring":
        return 15.0

    return 0.0


def fatf_status_to_sanctions_floor(status: str) -> float:
    """Set a minimum sanctions/geopolitical exposure floor based on FATF status."""

    if status == "High-Risk Call for Action":
        return 80.0

    if status == "Increased Monitoring":
        return 45.0

    return 0.0


def apply_fatf_sanctions_layer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply FATF and sanctions reference adjustments to the model input dataset.

    This function expects the pre-scoring input dataframe, not the already-scored
    output dataframe.
    """

    adjusted = df.copy()

    adjusted["normalized_country"] = adjusted["country"].apply(normalize_country_name)
    adjusted["fatf_status"] = adjusted["normalized_country"].apply(classify_fatf_status)

    adjusted["fatf_aml_cft_adjustment"] = adjusted["fatf_status"].apply(
        fatf_status_to_aml_cft_adjustment
    )

    adjusted["fatf_financial_crime_adjustment"] = adjusted["fatf_status"].apply(
        fatf_status_to_financial_crime_adjustment
    )

    adjusted["fatf_sanctions_floor"] = adjusted["fatf_status"].apply(
        fatf_status_to_sanctions_floor
    )

    adjusted["aml_cft_weakness"] = (
        adjusted["aml_cft_weakness"] + adjusted["fatf_aml_cft_adjustment"]
    ).clip(0, 100)

    adjusted["financial_crime_exposure"] = (
        adjusted["financial_crime_exposure"]
        + adjusted["fatf_financial_crime_adjustment"]
    ).clip(0, 100)

    adjusted["sanctions_exposure"] = adjusted.apply(
        lambda row: max(
            row["sanctions_exposure"],
            row["fatf_sanctions_floor"],
            SANCTIONS_EXPOSURE_OVERRIDES.get(row["normalized_country"], 0),
        ),
        axis=1,
    )

    adjusted["geopolitical_instability"] = adjusted.apply(
        lambda row: max(
            row["geopolitical_instability"],
            70 if row["fatf_status"] == "High-Risk Call for Action" else 0,
            50 if row["fatf_status"] == "Increased Monitoring" else 0,
        ),
        axis=1,
    )

    adjusted = adjusted.drop(
        columns=[
            "normalized_country",
            "fatf_aml_cft_adjustment",
            "fatf_financial_crime_adjustment",
            "fatf_sanctions_floor",
        ],
        errors="ignore",
    )

    return adjusted


def build_fatf_reference_table() -> pd.DataFrame:
    """Build an auditable FATF reference table for model outputs."""

    records = []

    for country in sorted(FATF_HIGH_RISK_CALL_FOR_ACTION):
        records.append(
            {
                "country": country,
                "fatf_status": "High-Risk Call for Action",
                "aml_cft_adjustment": 35.0,
                "financial_crime_adjustment": 25.0,
                "sanctions_floor": 80.0,
                "source": FATF_REFERENCE_SOURCE_NOTE,
                "last_reviewed": FATF_REFERENCE_LAST_REVIEWED,
            }
        )

    for country in sorted(FATF_INCREASED_MONITORING):
        records.append(
            {
                "country": country,
                "fatf_status": "Increased Monitoring",
                "aml_cft_adjustment": 20.0,
                "financial_crime_adjustment": 15.0,
                "sanctions_floor": 45.0,
                "source": FATF_REFERENCE_SOURCE_NOTE,
                "last_reviewed": FATF_REFERENCE_LAST_REVIEWED,
            }
        )

    return pd.DataFrame(records)