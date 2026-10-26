import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from src import scoring, data_sources
from src.publication import publishing_run


def publish_dashboard_fixture(tables, change=0):
    with publishing_run(tables, "demonstration") as publication:
        seed = data_sources.build_seed_financial_risk_dataset()
        seed["market_stress_proxy"] += change
        scored = scoring.add_driver_analysis(scoring.calculate_composite_score(scoring.calculate_layer_scores(seed)))
        scored.to_csv(tables / "financial_sector_risk_scores.csv", index=False)
        report = tables.parent / "financial_sector_risk_report.pdf"
        report.write_bytes(b"synthetic PDF fixture")
        publication.complete(report)
    return scored


def test_dashboard_refuses_incomplete_run_and_refreshes_completed_snapshot(monkeypatch, tmp_path):
    tables = tmp_path / "tables"
    monkeypatch.setattr(app, "TABLES_DIR", tables)
    monkeypatch.setattr(app, "REPORTS_DIR", tmp_path / "reports")
    first = publish_dashboard_fixture(tables)
    at = AppTest.from_string("import app\napp.main()", default_timeout=20).run()
    assert not at.exception
    assert at.metric[0].value == f"{first.financial_sector_risk_score.max():.2f}"
    assert any("DEMONSTRATION" in warning.value for warning in at.warning)
    second = publish_dashboard_fixture(tables, 20)
    at.run()
    assert not at.exception
    assert at.metric[0].value == f"{second.financial_sector_risk_score.max():.2f}"
    assert first.financial_sector_risk_score.max() != second.financial_sector_risk_score.max()
    with publishing_run(tables, "live"):
        at.run()
        assert not at.exception
        assert len(at.error) == 1
        assert len(at.metric) == 0
        assert len(at.get("download_button")) == 0


def test_table_and_download_use_the_same_bytes(monkeypatch):
    snapshot = {"tables/test.csv": b"value\n1\n"}
    pd.testing.assert_frame_equal(app.load_table("test.csv", snapshot), pd.DataFrame({"value": [1]}))
    calls = []
    monkeypatch.setattr(app.st, "download_button", lambda **kwargs: calls.append(kwargs))
    app.show_download_button(app.TABLES_DIR / "test.csv", "Download", "text/csv", snapshot)
    assert calls[0]["data"] == snapshot["tables/test.csv"]
