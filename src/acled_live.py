"""
ACLED live-data connector for the Financial Sector Risk Intelligence Model.

This module pulls ACLED event data and converts it into country-level strategic
risk signals for geopolitical instability and related financial-sector pressure.

Responsible-use note:
This connector uses aggregated jurisdiction-level indicators only. It does not
forecast attacks, identify targets, recommend tactical action, or replace legal,
security, compliance, intelligence, or professional judgment.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv


ACLED_API_BASE_URL = "https://acleddata.com/api/acled/read"
ACLED_OAUTH_URL = "https://acleddata.com/oauth/token"

DEFAULT_COUNTRIES = [
    "United States",
    "United Kingdom",
    "Germany",
    "France",
    "Japan",
    "Canada",
    "Brazil",
    "Mexico",
    "South Africa",
    "Turkey",
    "Russia",
    "China",
    "Iran",
    "United Arab Emirates",
    "Singapore",
    "Switzerland",
]


POLITICAL_VIOLENCE_EVENT_TYPES = {
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Riots",
}

DEMONSTRATION_EVENT_TYPES = {
    "Protests",
    "Riots",
}

CIVILIAN_TARGETING_EVENT_TYPES = {
    "Violence against civilians",
}


def load_acled_credentials() -> tuple[str, str]:
    """Load ACLED credentials from .env or environment variables."""

    load_dotenv()

    username = os.getenv("ACLED_USERNAME", "").strip()
    password = os.getenv("ACLED_PASSWORD", "").strip()

    if not username or not password:
        raise RuntimeError(
            "Missing ACLED credentials. Add ACLED_USERNAME and ACLED_PASSWORD to .env."
        )

    return username, password


def request_acled_token(username: str, password: str) -> str:
    """Request an OAuth bearer token from ACLED."""

    payload = {
        "username": username,
        "password": password,
        "grant_type": "password",
        "client_id": "acled",
        "scope": "authenticated",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(
        ACLED_OAUTH_URL,
        data=payload,
        headers=headers,
        timeout=45,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "ACLED authentication failed.\n"
            f"Status code: {response.status_code}\n"
            f"Response: {response.text[:800]}"
        )

    token_payload = response.json()
    access_token = token_payload.get("access_token")

    if not access_token:
        raise RuntimeError(
            "ACLED authentication response did not include an access_token.\n"
            f"Response keys: {list(token_payload.keys())}"
        )

    return access_token


def build_date_range(days_back: int = 90) -> tuple[str, str]:
    """Build ACLED date range strings."""

    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    return start_date.isoformat(), end_date.isoformat()


def fetch_acled_events(
    countries: list[str] | None = None,
    days_back: int = 90,
    limit: int = 5000,
) -> pd.DataFrame:
    """
    Fetch ACLED events for selected countries and date range.

    The query uses country-level filters and returns a bounded number of records.
    Credentials are exchanged for an OAuth bearer token and are not sent in the URL.
    """

    if countries is None:
        countries = DEFAULT_COUNTRIES

    username, password = load_acled_credentials()
    access_token = request_acled_token(username=username, password=password)

    start_date, end_date = build_date_range(days_back=days_back)
    country_filter = "|".join(countries)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    params = {
        "country": country_filter,
        "country_where": "IN",
        "event_date": f"{start_date}|{end_date}",
        "event_date_where": "BETWEEN",
        "limit": limit,
        "_format": "json",
        "fields": (
            "event_id_cnty|event_date|country|region|admin1|event_type|"
            "sub_event_type|disorder_type|fatalities|latitude|longitude"
        ),
    }

    response = requests.get(
        ACLED_API_BASE_URL,
        headers=headers,
        params=params,
        timeout=45,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "ACLED data request failed.\n"
            f"Status code: {response.status_code}\n"
            f"Response: {response.text[:800]}"
        )

    payload: dict[str, Any] = response.json()

    if payload.get("success") is False:
        raise RuntimeError(f"ACLED API returned unsuccessful response: {payload}")

    data = payload.get("data", [])

    if not data:
        return pd.DataFrame()

    events = pd.DataFrame(data)

    if events.empty:
        return events

    events["event_date"] = pd.to_datetime(
        events.get("event_date"),
        errors="coerce",
    )

    events["fatalities"] = pd.to_numeric(
        events.get("fatalities", 0),
        errors="coerce",
    ).fillna(0)

    events["latitude"] = pd.to_numeric(
        events.get("latitude", np.nan),
        errors="coerce",
    )

    events["longitude"] = pd.to_numeric(
        events.get("longitude", np.nan),
        errors="coerce",
    )

    return events


def _score_higher_is_riskier(
    value: float,
    low: float,
    high: float,
    fallback: float = 50.0,
) -> float:
    """Convert a numeric value to 0-100 risk where higher values are riskier."""

    if pd.isna(value):
        return fallback

    if high == low:
        return fallback

    score = (value - low) / (high - low) * 100
    return round(float(np.clip(score, 0, 100)), 2)


def _safe_nunique(series: pd.Series) -> int:
    """Safely count unique non-null values."""

    if series is None or series.empty:
        return 0

    return int(series.dropna().nunique())


def build_acled_country_signals(events: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate ACLED events into country-level strategic risk signals.

    Output is intentionally country-level only.
    """

    if events.empty:
        return pd.DataFrame(
            columns=[
                "country",
                "acled_events_90d",
                "acled_fatalities_90d",
                "acled_political_violence_events_90d",
                "acled_demonstration_events_90d",
                "acled_civilian_targeting_events_90d",
                "acled_admin1_spread_90d",
                "acled_geopolitical_instability_signal",
                "acled_market_disruption_signal",
                "acled_banking_pressure_signal",
                "acled_status",
            ]
        )

    records = []

    for country, group in events.groupby("country"):
        event_count = int(len(group))
        fatalities = float(group["fatalities"].sum())

        event_type = group["event_type"].fillna("")

        political_violence_events = int(
            event_type.isin(POLITICAL_VIOLENCE_EVENT_TYPES).sum()
        )

        demonstration_events = int(
            event_type.isin(DEMONSTRATION_EVENT_TYPES).sum()
        )

        civilian_targeting_events = int(
            event_type.isin(CIVILIAN_TARGETING_EVENT_TYPES).sum()
        )

        admin1_spread = _safe_nunique(group.get("admin1", pd.Series(dtype=str)))

        event_volume_score = _score_higher_is_riskier(
            event_count,
            low=0,
            high=750,
        )

        fatality_score = _score_higher_is_riskier(
            fatalities,
            low=0,
            high=1000,
        )

        political_violence_score = _score_higher_is_riskier(
            political_violence_events,
            low=0,
            high=300,
        )

        demonstration_score = _score_higher_is_riskier(
            demonstration_events,
            low=0,
            high=500,
        )

        civilian_targeting_score = _score_higher_is_riskier(
            civilian_targeting_events,
            low=0,
            high=150,
        )

        spread_score = _score_higher_is_riskier(
            admin1_spread,
            low=0,
            high=25,
        )

        geopolitical_instability_signal = round(
            0.25 * event_volume_score
            + 0.20 * fatality_score
            + 0.25 * political_violence_score
            + 0.15 * civilian_targeting_score
            + 0.15 * spread_score,
            2,
        )

        market_disruption_signal = round(
            0.35 * geopolitical_instability_signal
            + 0.30 * demonstration_score
            + 0.20 * spread_score
            + 0.15 * fatality_score,
            2,
        )

        banking_pressure_signal = round(
            0.45 * geopolitical_instability_signal
            + 0.25 * market_disruption_signal
            + 0.15 * demonstration_score
            + 0.15 * spread_score,
            2,
        )

        records.append(
            {
                "country": country,
                "acled_events_90d": event_count,
                "acled_fatalities_90d": round(fatalities, 2),
                "acled_political_violence_events_90d": political_violence_events,
                "acled_demonstration_events_90d": demonstration_events,
                "acled_civilian_targeting_events_90d": civilian_targeting_events,
                "acled_admin1_spread_90d": admin1_spread,
                "acled_geopolitical_instability_signal": geopolitical_instability_signal,
                "acled_market_disruption_signal": market_disruption_signal,
                "acled_banking_pressure_signal": banking_pressure_signal,
                "acled_status": "Active",
            }
        )

    return pd.DataFrame(records)


def build_acled_live_outputs(
    countries: list[str] | None = None,
    days_back: int = 90,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch ACLED events and build country-level ACLED signals.

    Returns:
    - raw ACLED events
    - country-level ACLED signals
    """

    events = fetch_acled_events(
        countries=countries,
        days_back=days_back,
    )

    signals = build_acled_country_signals(events)

    return events, signals


def apply_acled_layer(
    df: pd.DataFrame,
    acled_signals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply ACLED country-level signals to the model input dataset.

    The weighting is conservative because ACLED is a conflict/event signal, not
    a direct financial-sector loss estimate.
    """

    adjusted = df.copy()

    if acled_signals.empty:
        adjusted["acled_status"] = "Fallback: no ACLED signals"
        return adjusted

    merged = adjusted.merge(
        acled_signals,
        on="country",
        how="left",
    )

    signal_columns = [
        "acled_geopolitical_instability_signal",
        "acled_market_disruption_signal",
        "acled_banking_pressure_signal",
    ]

    for column in signal_columns:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)

    merged["acled_status"] = merged["acled_status"].fillna("Fallback: country missing")

    merged["geopolitical_instability"] = (
        0.70 * merged["geopolitical_instability"]
        + 0.30 * merged["acled_geopolitical_instability_signal"]
    ).clip(0, 100).round(2)

    merged["market_stress_proxy"] = (
        0.85 * merged["market_stress_proxy"]
        + 0.15 * merged["acled_market_disruption_signal"]
    ).clip(0, 100).round(2)

    merged["banking_stress_proxy"] = (
        0.85 * merged["banking_stress_proxy"]
        + 0.15 * merged["acled_banking_pressure_signal"]
    ).clip(0, 100).round(2)

    return merged