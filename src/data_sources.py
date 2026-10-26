from dataclasses import dataclass

import pandas as pd

from src.world_bank_live import build_live_world_bank_financial_risk_dataset
from src.fatf_sanctions import apply_fatf_sanctions_layer, FATF_REFERENCE_LAST_REVIEWED
from src.market_data import build_market_data_outputs, apply_market_data_layer
from src.acled_live import build_acled_live_outputs, apply_acled_layer


def build_seed_financial_risk_dataset() -> pd.DataFrame:
    """
    Build a starter dataset using manually defined public-source-style proxies.

    All values are 0-100 directional risk proxy scores:
    - 0 means lower observed/proxy risk
    - 100 means higher observed/proxy risk
    """

    records = [
        {
            "country": "United States",
            "region": "North America",
            "market_stress_proxy": 42,
            "inflation_pressure": 38,
            "currency_pressure": 20,
            "financial_crime_exposure": 36,
            "corruption_risk": 22,
            "aml_cft_weakness": 25,
            "governance_weakness": 18,
            "regulatory_quality_weakness": 15,
            "banking_stress_proxy": 34,
            "sovereign_debt_pressure": 48,
            "sanctions_exposure": 18,
            "geopolitical_instability": 28,
            "cyber_operational_pressure": 62,
        },
        {
            "country": "United Kingdom",
            "region": "Europe",
            "market_stress_proxy": 40,
            "inflation_pressure": 35,
            "currency_pressure": 28,
            "financial_crime_exposure": 42,
            "corruption_risk": 24,
            "aml_cft_weakness": 26,
            "governance_weakness": 20,
            "regulatory_quality_weakness": 18,
            "banking_stress_proxy": 32,
            "sovereign_debt_pressure": 42,
            "sanctions_exposure": 20,
            "geopolitical_instability": 30,
            "cyber_operational_pressure": 58,
        },
        {
            "country": "Germany",
            "region": "Europe",
            "market_stress_proxy": 36,
            "inflation_pressure": 32,
            "currency_pressure": 22,
            "financial_crime_exposure": 32,
            "corruption_risk": 20,
            "aml_cft_weakness": 24,
            "governance_weakness": 16,
            "regulatory_quality_weakness": 14,
            "banking_stress_proxy": 30,
            "sovereign_debt_pressure": 32,
            "sanctions_exposure": 24,
            "geopolitical_instability": 32,
            "cyber_operational_pressure": 54,
        },
        {
            "country": "France",
            "region": "Europe",
            "market_stress_proxy": 38,
            "inflation_pressure": 34,
            "currency_pressure": 24,
            "financial_crime_exposure": 34,
            "corruption_risk": 24,
            "aml_cft_weakness": 26,
            "governance_weakness": 22,
            "regulatory_quality_weakness": 20,
            "banking_stress_proxy": 34,
            "sovereign_debt_pressure": 44,
            "sanctions_exposure": 22,
            "geopolitical_instability": 35,
            "cyber_operational_pressure": 55,
        },
        {
            "country": "Japan",
            "region": "East Asia",
            "market_stress_proxy": 35,
            "inflation_pressure": 28,
            "currency_pressure": 36,
            "financial_crime_exposure": 28,
            "corruption_risk": 18,
            "aml_cft_weakness": 22,
            "governance_weakness": 16,
            "regulatory_quality_weakness": 15,
            "banking_stress_proxy": 30,
            "sovereign_debt_pressure": 60,
            "sanctions_exposure": 18,
            "geopolitical_instability": 34,
            "cyber_operational_pressure": 50,
        },
        {
            "country": "Canada",
            "region": "North America",
            "market_stress_proxy": 32,
            "inflation_pressure": 30,
            "currency_pressure": 24,
            "financial_crime_exposure": 30,
            "corruption_risk": 18,
            "aml_cft_weakness": 22,
            "governance_weakness": 14,
            "regulatory_quality_weakness": 14,
            "banking_stress_proxy": 28,
            "sovereign_debt_pressure": 36,
            "sanctions_exposure": 16,
            "geopolitical_instability": 22,
            "cyber_operational_pressure": 48,
        },
        {
            "country": "Brazil",
            "region": "Latin America",
            "market_stress_proxy": 58,
            "inflation_pressure": 54,
            "currency_pressure": 56,
            "financial_crime_exposure": 62,
            "corruption_risk": 60,
            "aml_cft_weakness": 52,
            "governance_weakness": 55,
            "regulatory_quality_weakness": 50,
            "banking_stress_proxy": 46,
            "sovereign_debt_pressure": 58,
            "sanctions_exposure": 20,
            "geopolitical_instability": 50,
            "cyber_operational_pressure": 52,
        },
        {
            "country": "Mexico",
            "region": "Latin America",
            "market_stress_proxy": 52,
            "inflation_pressure": 48,
            "currency_pressure": 45,
            "financial_crime_exposure": 68,
            "corruption_risk": 66,
            "aml_cft_weakness": 58,
            "governance_weakness": 60,
            "regulatory_quality_weakness": 54,
            "banking_stress_proxy": 40,
            "sovereign_debt_pressure": 42,
            "sanctions_exposure": 24,
            "geopolitical_instability": 58,
            "cyber_operational_pressure": 50,
        },
        {
            "country": "South Africa",
            "region": "Africa",
            "market_stress_proxy": 64,
            "inflation_pressure": 52,
            "currency_pressure": 65,
            "financial_crime_exposure": 66,
            "corruption_risk": 64,
            "aml_cft_weakness": 68,
            "governance_weakness": 62,
            "regulatory_quality_weakness": 58,
            "banking_stress_proxy": 52,
            "sovereign_debt_pressure": 62,
            "sanctions_exposure": 24,
            "geopolitical_instability": 54,
            "cyber_operational_pressure": 54,
        },
        {
            "country": "Turkey",
            "region": "Middle East / Europe",
            "market_stress_proxy": 74,
            "inflation_pressure": 82,
            "currency_pressure": 84,
            "financial_crime_exposure": 58,
            "corruption_risk": 58,
            "aml_cft_weakness": 55,
            "governance_weakness": 66,
            "regulatory_quality_weakness": 62,
            "banking_stress_proxy": 64,
            "sovereign_debt_pressure": 70,
            "sanctions_exposure": 38,
            "geopolitical_instability": 70,
            "cyber_operational_pressure": 58,
        },
        {
            "country": "Russia",
            "region": "Eurasia",
            "market_stress_proxy": 78,
            "inflation_pressure": 66,
            "currency_pressure": 76,
            "financial_crime_exposure": 78,
            "corruption_risk": 82,
            "aml_cft_weakness": 66,
            "governance_weakness": 82,
            "regulatory_quality_weakness": 76,
            "banking_stress_proxy": 72,
            "sovereign_debt_pressure": 62,
            "sanctions_exposure": 95,
            "geopolitical_instability": 90,
            "cyber_operational_pressure": 72,
        },
        {
            "country": "China",
            "region": "East Asia",
            "market_stress_proxy": 58,
            "inflation_pressure": 34,
            "currency_pressure": 42,
            "financial_crime_exposure": 56,
            "corruption_risk": 55,
            "aml_cft_weakness": 48,
            "governance_weakness": 62,
            "regulatory_quality_weakness": 56,
            "banking_stress_proxy": 66,
            "sovereign_debt_pressure": 54,
            "sanctions_exposure": 52,
            "geopolitical_instability": 66,
            "cyber_operational_pressure": 68,
        },
        {
            "country": "Iran",
            "region": "Middle East",
            "market_stress_proxy": 86,
            "inflation_pressure": 88,
            "currency_pressure": 90,
            "financial_crime_exposure": 82,
            "corruption_risk": 80,
            "aml_cft_weakness": 84,
            "governance_weakness": 86,
            "regulatory_quality_weakness": 82,
            "banking_stress_proxy": 78,
            "sovereign_debt_pressure": 72,
            "sanctions_exposure": 98,
            "geopolitical_instability": 92,
            "cyber_operational_pressure": 70,
        },
        {
            "country": "United Arab Emirates",
            "region": "Middle East",
            "market_stress_proxy": 36,
            "inflation_pressure": 28,
            "currency_pressure": 18,
            "financial_crime_exposure": 58,
            "corruption_risk": 34,
            "aml_cft_weakness": 48,
            "governance_weakness": 30,
            "regulatory_quality_weakness": 28,
            "banking_stress_proxy": 30,
            "sovereign_debt_pressure": 22,
            "sanctions_exposure": 34,
            "geopolitical_instability": 38,
            "cyber_operational_pressure": 54,
        },
        {
            "country": "Singapore",
            "region": "Southeast Asia",
            "market_stress_proxy": 28,
            "inflation_pressure": 24,
            "currency_pressure": 18,
            "financial_crime_exposure": 34,
            "corruption_risk": 10,
            "aml_cft_weakness": 18,
            "governance_weakness": 8,
            "regulatory_quality_weakness": 8,
            "banking_stress_proxy": 22,
            "sovereign_debt_pressure": 18,
            "sanctions_exposure": 18,
            "geopolitical_instability": 24,
            "cyber_operational_pressure": 48,
        },
        {
            "country": "Switzerland",
            "region": "Europe",
            "market_stress_proxy": 24,
            "inflation_pressure": 16,
            "currency_pressure": 18,
            "financial_crime_exposure": 36,
            "corruption_risk": 10,
            "aml_cft_weakness": 18,
            "governance_weakness": 8,
            "regulatory_quality_weakness": 8,
            "banking_stress_proxy": 24,
            "sovereign_debt_pressure": 16,
            "sanctions_exposure": 16,
            "geopolitical_instability": 18,
            "cyber_operational_pressure": 46,
        },
    ]

    return pd.DataFrame(records)


@dataclass
class InputBundle:
    """Inputs and the exact supporting evidence fetched for one run."""

    dataset: pd.DataFrame
    market_history: pd.DataFrame
    market_metrics: pd.DataFrame
    market_signal: pd.DataFrame
    acled_events: pd.DataFrame
    acled_signals: pd.DataFrame
    source_status: dict[str, str]


def build_input_bundle(use_live_data: bool = True) -> InputBundle:
    """Live mode requires World Bank data; demo mode makes no network requests."""
    if use_live_data:
        # Do not substitute manually assigned seed values for failed live data.
        dataset = build_live_world_bank_financial_risk_dataset()
        if dataset.empty:
            raise RuntimeError("World Bank returned no model inputs; use --demo for offline examples.")
        mode = "live"
    else:
        dataset = build_seed_financial_risk_dataset()
        dataset["world_bank_status"] = "Disabled: demonstration seed data"
        mode = "demonstration"
    dataset = apply_fatf_sanctions_layer(dataset)
    dataset["data_mode"] = mode
    market_history = pd.DataFrame(columns=["date", "ticker", "close"])
    market_metrics = pd.DataFrame(columns=["ticker", "observations"])
    market_signal = pd.DataFrame(columns=["market_data_status"])
    acled_events = pd.DataFrame(columns=["event_id_cnty", "event_date", "country"])
    acled_signals = pd.DataFrame(columns=["country", "acled_status"])
    dataset["market_data_status"] = "Disabled: demonstration mode"
    dataset["acled_status"] = "Disabled: demonstration mode"
    if use_live_data:
        market_history, market_metrics, market_signal = build_market_data_outputs()
        dataset = apply_market_data_layer(dataset, market_signal)
        # Optional event-source failures must not discard valid macro inputs.
        try:
            acled_events, acled_signals = build_acled_live_outputs(
                countries=dataset["country"].tolist(), days_back=90,
            )
            dataset = apply_acled_layer(dataset.drop(columns="acled_status"), acled_signals)
        except Exception as exc:
            dataset["acled_status"] = f"Unavailable: {type(exc).__name__}; no adjustment"
            acled_events = pd.DataFrame(columns=["event_id_cnty", "event_date", "country"])
            acled_signals = pd.DataFrame(columns=["country", "acled_status"])
    # Coverage rows include countries absent from the event response, with unknown values.
    acled_signals = pd.DataFrame({"country": dataset["country"]}).merge(
        acled_signals.drop(columns="acled_status", errors="ignore"),
        on="country", how="left", validate="one_to_one",
    )
    acled_signals["acled_status"] = dataset["acled_status"].to_numpy()
    statuses = {
        "World Bank API": "; ".join(sorted(dataset["world_bank_status"].unique())),
        "Market data": "; ".join(sorted(dataset["market_data_status"].unique())),
        "ACLED live event data": "; ".join(sorted(dataset["acled_status"].unique())),
        "FATF / sanctions reference": f"Manual reference: last reviewed {FATF_REFERENCE_LAST_REVIEWED}",
    }
    return InputBundle(dataset, market_history, market_metrics, market_signal,
                       acled_events, acled_signals, statuses)


def build_financial_risk_dataset(use_live_data: bool = True) -> pd.DataFrame:
    """Compatibility wrapper; False is a strictly offline demonstration."""
    return build_input_bundle(use_live_data=use_live_data).dataset
