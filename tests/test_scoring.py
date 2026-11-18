"""Hand-calculated examples and invariants of the preserved model."""
import numpy as np
import pandas as pd
import pytest

from src.sample_config import SAMPLE_INPUT
from src.scoring import (calculate_layer_scores, calculate_composite_score,
                         add_driver_analysis, classify_risk_band)
from src.scenarios import run_scenario_analysis, SCENARIOS
from src.monte_carlo import run_monte_carlo_simulation, build_monte_carlo_summary


def scored_sample():
    return add_driver_analysis(calculate_composite_score(
        calculate_layer_scores(pd.read_csv(SAMPLE_INPUT))))


@pytest.mark.parametrize("score,band", [(0,"Low"),(24.99,"Low"),(25,"Moderate"),
    (49.99,"Moderate"),(50,"Elevated"),(74.99,"Elevated"),(75,"High"),(100,"High")])
def test_band_boundaries(score, band):
    assert classify_risk_band(score) == band


def test_hand_calculated_nonuniform_layers_and_composite():
    data = pd.DataFrame([dict(country="Synthetic Example", region="Fictional",
        market_stress_proxy=10, inflation_pressure=20, currency_pressure=30,
        financial_crime_exposure=30, corruption_risk=60, aml_cft_weakness=90,
        governance_weakness=30, regulatory_quality_weakness=0,
        banking_stress_proxy=40, sovereign_debt_pressure=70,
        sanctions_exposure=60, geopolitical_instability=90, cyber_operational_pressure=80)])
    before = data.copy(deep=True)
    result = add_driver_analysis(calculate_composite_score(calculate_layer_scores(data)))
    row = result.iloc[0]
    # Hand calculation: layer means 20,60,30,40,60,80; weighted total 45.
    assert row["financial_sector_risk_score"] == 45
    assert row["risk_band"] == "Moderate"
    assert row["primary_risk_driver"] == "Cyber / Operational"
    assert row["rank"] == 1
    pd.testing.assert_frame_equal(data, before)


def test_fixture_rank_and_bands():
    df = scored_sample()
    assert df.country.tolist() == ["Synthetic Delta", "Synthetic Gamma", "Synthetic Beta", "Synthetic Alpha"]
    assert df.financial_sector_risk_score.tolist() == [90,65,40,10]
    assert df.risk_band.tolist() == ["High","Elevated","Moderate","Low"]
    assert df["rank"].tolist() == [1,2,3,4]


def test_layer_clipping():
    df = pd.read_csv(SAMPLE_INPUT)
    numeric = df.select_dtypes("number").columns
    df.loc[0,numeric] = -10
    df.loc[1,numeric] = 150
    result = calculate_composite_score(calculate_layer_scores(df))
    assert result.financial_sector_risk_score.iloc[:2].tolist() == [0,100]


def test_scenarios_baseline_and_hand_calculated_shock():
    scored = scored_sample()
    before = scored.copy(deep=True)
    result = run_scenario_analysis(scored)
    assert len(result) == 4 * len(SCENARIOS)
    assert (result.query("scenario == 'Baseline'").score_change == 0).all()
    alpha_shock = result.query("scenario == 'Market Shock' and country == 'Synthetic Alpha'").iloc[0]
    # 2.7 + 2.1 + 2 + 1.875 + 1.575 + 1 = 11.25.
    assert alpha_shock.scenario_financial_sector_risk_score == 11.25
    assert result.scenario_financial_sector_risk_score.between(0,100).all()
    assert (result.score_change >= 0).all()
    pd.testing.assert_frame_equal(scored, before)


def test_monte_carlo_seed_bounds_and_summary():
    scored = scored_sample()
    before = scored.copy(deep=True)
    first = run_monte_carlo_simulation(scored, n_simulations=20, random_seed=42)
    same = run_monte_carlo_simulation(scored, n_simulations=20, random_seed=42)
    changed = run_monte_carlo_simulation(scored, n_simulations=20, random_seed=43)
    pd.testing.assert_frame_equal(first, same)
    assert not first.equals(changed)
    assert first.simulated_financial_sector_risk_score.between(0,100).all()
    assert np.isfinite(first.select_dtypes("number")).all().all()
    assert first.groupby("simulation_id").simulated_rank.apply(lambda x: sorted(x)==[1,2,3,4]).all()
    summary = build_monte_carlo_summary(first)
    assert summary.high_risk_probability.between(0,1).all()
    assert summary.elevated_or_high_probability.between(0,1).all()
    pd.testing.assert_frame_equal(scored, before)


def test_zero_noise_preserves_scores():
    result = run_monte_carlo_simulation(scored_sample(), n_simulations=3, noise_std=0)
    assert (result.simulated_financial_sector_risk_score == result.financial_sector_risk_score).all()
