from unittest.mock import Mock

import pandas as pd

import main
from src import config, data_sources, outputs, source_status


def test_pipeline_fetches_once_exports_used_evidence_and_refreshes_status(monkeypatch, tmp_path):
    raw, tables, processed = (tmp_path / name for name in ["raw", "tables", "processed"])
    for directory in [raw, tables, processed]:
        directory.mkdir()
    for module in [main, config, outputs, source_status]:
        for name, path in [("RAW_DIR", raw), ("TABLES_DIR", tables), ("PROCESSED_DIR", processed)]:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, path)
    monkeypatch.setattr(main, "ensure_directories", lambda: None)
    monkeypatch.setattr(main, "generate_visualizations", lambda *args: None)
    monkeypatch.setattr(main, "generate_monte_carlo_visualizations", lambda *args: None)
    report = tmp_path / "financial_sector_risk_report.pdf"
    def make_report(**kwargs):
        report.write_bytes(b"synthetic report fixture")
        return report
    monkeypatch.setattr(main, "generate_pdf_report", make_report)
    monkeypatch.setattr(main, "print_summary", lambda *args: None)
    simulation = main.run_monte_carlo_simulation
    monkeypatch.setattr(main, "run_monte_carlo_simulation", lambda scored_df, **kwargs:
                        simulation(scored_df, n_simulations=2))
    live = data_sources.build_seed_financial_risk_dataset()
    live["world_bank_status"] = "Active"
    wb = Mock(return_value=live)
    market = Mock(return_value=(pd.DataFrame({"close": [123.]}), pd.DataFrame({"ticker": ["TEST"]}),
        pd.DataFrame([dict(market_data_stress_signal=10., market_data_banking_signal=20.,
                          market_data_volatility_signal=30., market_data_status="Active") ])))
    signals = pd.DataFrame([dict(country="United States", acled_geopolitical_instability_signal=15.,
        acled_market_disruption_signal=25., acled_banking_pressure_signal=35., acled_status="Active")])
    events = pd.DataFrame({"event_id_cnty": ["fixture"]})
    acled = Mock(return_value=(events, signals))
    monkeypatch.setattr(data_sources, "build_live_world_bank_financial_risk_dataset", wb)
    monkeypatch.setattr(data_sources, "build_market_data_outputs", market)
    monkeypatch.setattr(data_sources, "build_acled_live_outputs", acled)
    result = main.run_pipeline()
    assert (wb.call_count, market.call_count, acled.call_count) == (1, 1, 1)
    pd.testing.assert_frame_equal(pd.read_csv(raw / "acled_events_90d.csv"), events)
    assert pd.read_csv(tables / "market_stress_signal.csv").iloc[0].market_data_stress_signal == 10.
    assert result.market_data_stress_signal.eq(10.).all()
    status = pd.read_csv(tables / "live_source_status.csv").set_index("source_layer")
    for layer in ["FATF / sanctions reference", "Scenario analysis", "Monte Carlo robustness"]:
        assert status.loc[layer, "file_status"] == "Available"
        assert status.loc[layer, "row_count"] > 0
    assert "Unavailable" in status.loc["ACLED country signals", "source_status"]
    # A second demo run must replace previous live evidence and status, not reuse it.
    main.run_pipeline(False)
    assert (wb.call_count, market.call_count, acled.call_count) == (1, 1, 1)
    assert pd.read_csv(raw / "acled_events_90d.csv").empty
    assert pd.read_csv(tables / "market_stress_signal.csv").empty
    status = pd.read_csv(tables / "live_source_status.csv").set_index("source_layer")
    assert status.loc["World Bank API", "source_status"].startswith("Disabled")
    register = pd.read_csv(tables / "source_register.csv").set_index("source_name")
    assert register.loc["ACLED", "status"].startswith("Disabled")


def test_source_register_does_not_claim_active_without_run_status():
    register = outputs.build_source_register().set_index("source_name")
    for name in ["World Bank API", "ACLED", "Market data connector"]:
        assert register.loc[name, "status"].startswith("Unknown")
