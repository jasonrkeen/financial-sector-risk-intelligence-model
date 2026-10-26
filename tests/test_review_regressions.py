import numpy as np
import pandas as pd
import pytest

from src import scoring, scenarios, monte_carlo, data_sources, acled_live
from test_p0 import fetch_pages, event


@pytest.mark.parametrize("fatalities", [None, "unknown", -1, np.inf])
def test_acled_invalid_fatalities_cannot_be_scored_as_observed(monkeypatch, fatalities):
    record = {**event(), "fatalities": fatalities}
    fetch_pages(monkeypatch, [dict(data=[record], next_cursor=None, total_count=1)])
    with pytest.raises(RuntimeError, match="fatalities"):
        acled_live.fetch_acled_events(["Test"])


@pytest.mark.parametrize("operation", [scoring.add_driver_analysis, scenarios.run_scenario_analysis,
                                        monte_carlo.run_monte_carlo_simulation])
def test_invalid_scores_are_rejected_before_ranking_or_simulation(operation):
    scored = scoring.add_driver_analysis(scoring.calculate_composite_score(
        scoring.calculate_layer_scores(data_sources.build_seed_financial_risk_dataset())))
    scored.loc[0, "market_stress_risk"] = np.nan
    scored.loc[0, "financial_sector_risk_score"] = np.nan
    if operation is scoring.add_driver_analysis:
        scored = scored.drop(columns="rank")
    with pytest.raises(ValueError, match="^Ranking and simulation require finite"):
        operation(scored)
