from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from src import acled_live as acled
from src import data_sources as sources
from src import scoring, scenarios, monte_carlo, world_bank_live as wb
from src import market_data


def fail(*args, **kwargs):
    raise RuntimeError("fixture source unavailable")


def test_optional_failure_preserves_live_data(monkeypatch):
    live = sources.build_seed_financial_risk_dataset()
    live["world_bank_status"] = "Active"
    live["inflation_pressure"] = 99
    monkeypatch.setattr(sources, "build_live_world_bank_financial_risk_dataset", lambda: live)
    monkeypatch.setattr(sources, "build_market_data_outputs", lambda: (pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    monkeypatch.setattr(sources, "build_acled_live_outputs", fail)
    bundle = sources.build_input_bundle()
    assert bundle.dataset.inflation_pressure.eq(99).all()
    assert bundle.dataset.world_bank_status.eq("Active").all()
    assert bundle.dataset.acled_status.str.startswith("Unavailable").all()
    assert bundle.acled_signals.acled_status.equals(bundle.dataset.acled_status)


def test_world_bank_failure_does_not_substitute_seed(monkeypatch):
    monkeypatch.setattr(sources, "build_live_world_bank_financial_risk_dataset", fail)
    with pytest.raises(RuntimeError):
        sources.build_input_bundle()


def test_demo_is_offline_and_labeled(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Demo attempted a live source")
    for name in ["build_live_world_bank_financial_risk_dataset", "build_market_data_outputs", "build_acled_live_outputs"]:
        monkeypatch.setattr(sources, name, forbidden)
    bundle = sources.build_input_bundle(False)
    assert len(bundle.dataset) == 16
    assert bundle.dataset.data_mode.eq("demonstration").all()
    assert bundle.market_history.empty and bundle.acled_events.empty


def signal(country="Other", value=50., status="Active"):
    return dict(country=country, acled_geopolitical_instability_signal=value,
                acled_market_disruption_signal=value, acled_banking_pressure_signal=value,
                acled_status=status)


@pytest.mark.parametrize("signals", [pd.DataFrame(), pd.DataFrame([signal()]),
    pd.DataFrame([signal("Missing", np.nan)]), pd.DataFrame([signal("Missing", 0., "Unavailable")])])
def test_missing_acled_does_not_lower_scores(signals):
    base = pd.DataFrame([dict(country="Missing", geopolitical_instability=80.,
                             market_stress_proxy=80., banking_stress_proxy=80.)])
    result = acled.apply_acled_layer(base, signals)
    pd.testing.assert_frame_equal(result[base.columns], base)


def test_observed_zero_signal_retains_original_formula():
    base = pd.DataFrame([dict(country="Observed", geopolitical_instability=80.,
                             market_stress_proxy=80., banking_stress_proxy=80.)])
    result = acled.apply_acled_layer(base, pd.DataFrame([signal("Observed", 0.)]))
    assert result.iloc[0][["geopolitical_instability", "market_stress_proxy", "banking_stress_proxy"]].tolist() == [56., 68., 68.]


def event(event_id="A", **kwargs):
    return dict(event_id_cnty=event_id, event_date="2026-01-05", country="Test",
                event_type="Protests", fatalities=0, **kwargs)


def fetch_pages(monkeypatch, pages):
    monkeypatch.setattr(acled, "load_acled_credentials", lambda: ("fixture", "fixture"))
    monkeypatch.setattr(acled, "request_acled_token", lambda **kwargs: "fixture-token")
    monkeypatch.setattr(acled, "build_date_range", lambda **kwargs: ("2026-01-01", "2026-01-31"))
    responses = []
    for payload in pages:
        response = Mock()
        response.json.return_value = payload
        responses.append(response)
    request = Mock(side_effect=responses)
    monkeypatch.setattr(acled.requests, "get", request)
    return request


def test_cursor_pagination_deduplicates_and_verifies_total(monkeypatch):
    request = fetch_pages(monkeypatch, [
        dict(data=[event()], next_cursor=123, total_count=2),
        dict(data=[event(), event("B")], next_cursor=None, total_count=2),
    ])
    result = acled.fetch_acled_events(["Test"], limit=2)
    assert result.event_id_cnty.tolist() == ["A", "B"]
    assert [call.kwargs["params"]["cursor"] for call in request.call_args_list] == [0, 123]


@pytest.mark.parametrize("pages", [
    [dict(data=[event()], next_cursor=None, total_count=2)],
    [dict(data=[event()])],
    [dict(data=[event()], next_cursor=1), dict(data=[event()], next_cursor=1)],
    [dict(data=[event()], next_cursor=1, total_count=2), dict(data=[event("B")], next_cursor=None, total_count=3)],
    [dict(data=[{**event(), "event_date": "2025-01-01"}], next_cursor=None)],
    [dict(data=[{**event(), "country": "Unexpected"}], next_cursor=None)],
    [dict(data=[{**event(), "event_id_cnty": None}], next_cursor=None)],
    [dict(data=[event(), {**event(), "fatalities": 10}], next_cursor=None)],
    [dict(success=False, data=[], next_cursor=None)],
])
def test_reject_incomplete_or_invalid_acled(monkeypatch, pages):
    fetch_pages(monkeypatch, pages)
    with pytest.raises(RuntimeError):
        acled.fetch_acled_events(["Test"])


def test_page_safety_limit(monkeypatch):
    fetch_pages(monkeypatch, [dict(data=[event()], next_cursor=1)])
    monkeypatch.setattr(acled, "ACLED_MAX_PAGES", 1)
    with pytest.raises(RuntimeError, match="safety limit"):
        acled.fetch_acled_events(["Test"])


def test_empty_response_is_not_assumed_country_coverage(monkeypatch):
    fetch_pages(monkeypatch, [dict(data=[], next_cursor=None, total_count=0)])
    events = acled.fetch_acled_events(["Test"])
    assert events.empty
    assert acled.build_acled_country_signals(events).empty


def test_driver_uses_weighted_contributions():
    row = pd.Series({name: 10. for name in monte_carlo.LAYER_COLUMNS})
    row["cyber_operational_risk"] = 90.
    row["market_stress_risk"] = 60.
    assert scoring.identify_primary_driver(row) == "Market Stress"


def test_partial_market_source_is_not_labeled_active():
    metrics = pd.DataFrame([dict(ticker="^VIX", latest_close=20.)])
    result = market_data.build_market_stress_signal(metrics)
    assert result.iloc[0].market_data_status.startswith("Partial")
    assert "XLF" in result.iloc[0].market_data_status


def test_nonfinite_layer_does_not_become_high_risk():
    seed = sources.build_seed_financial_risk_dataset()
    seed["cyber_operational_pressure"] = seed["cyber_operational_pressure"].astype(float)
    seed.loc[0, "cyber_operational_pressure"] = np.inf
    result = scoring.calculate_composite_score(scoring.calculate_layer_scores(seed))
    assert result.loc[0, "risk_band"] == "Unknown"


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, None])
def test_missing_or_nonfinite_score_is_unknown(value):
    assert scoring.classify_risk_band(value) == "Unknown"


@pytest.mark.parametrize("value,expected", [(0,"Low"),(24.99,"Low"),(25,"Moderate"),(50,"Elevated"),(75,"High"),(100,"High")])
def test_band_thresholds_unchanged(value, expected):
    assert scoring.classify_risk_band(value) == expected


def test_missing_input_does_not_silently_reweight_layer():
    seed = sources.build_seed_financial_risk_dataset()
    seed.loc[0, "inflation_pressure"] = np.nan
    result = scoring.calculate_composite_score(scoring.calculate_layer_scores(seed))
    assert pd.isna(result.loc[0, "market_stress_risk"])
    assert result.loc[0, "risk_band"] == "Unknown"


def test_world_bank_indicator_years_survive(monkeypatch):
    def fetch(country_codes, indicator_code, **kwargs):
        return pd.DataFrame([dict(iso3="USA", year=2018 if indicator_code == "GC.DOD.TOTL.GD.ZS" else 2025, value=3.)])
    monkeypatch.setattr(wb, "fetch_world_bank_indicator", fetch)
    result = wb.build_live_world_bank_financial_risk_dataset()
    assert result.loc[0, "central_government_debt_pct_gdp_year"] == 2018
    assert result.loc[0, "inflation_annual_pct_year"] == 2025
    assert result.loc[0, "central_government_debt_pct_gdp"] == 3.


def test_baseline_equivalence_and_seed_reproducibility():
    scored = scoring.add_driver_analysis(scoring.calculate_composite_score(
        scoring.calculate_layer_scores(sources.build_seed_financial_risk_dataset())))
    results = scenarios.run_scenario_analysis(scored)
    assert results.loc[results.scenario.eq("Baseline"), "score_change"].eq(0).all()
    a = monte_carlo.run_monte_carlo_simulation(scored, n_simulations=5)
    b = monte_carlo.run_monte_carlo_simulation(scored, n_simulations=5)
    pd.testing.assert_frame_equal(a, b)
