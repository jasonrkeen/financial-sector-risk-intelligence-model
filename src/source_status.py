"""
Live source status register for the Financial Sector Risk Intelligence Model.

This module creates an auditable source-status table so users can quickly see
which data layers are live, reference-based, fallback, or planned.

Responsible-use note:
This table documents source availability and model-data provenance. It does not
validate legal, compliance, investment, or regulatory conclusions.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_DIR, TABLES_DIR


def file_status(path: Path) -> str:
    """Return a simple file availability status."""

    if path.exists() and path.stat().st_size > 0:
        return "Available"

    if path.exists() and path.stat().st_size == 0:
        return "Empty file"

    return "Missing"


def row_count(path: Path) -> int | None:
    """Return CSV row count if readable."""

    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        return int(len(pd.read_csv(path)))
    except Exception:
        return None


def build_live_source_status_table(source_status: dict[str, str] | None = None) -> pd.DataFrame:
    """Build a source-status table from current pipeline outputs."""

    sources = [
        {
            "source_layer": "World Bank API",
            "source_type": "Live public API",
            "output_file": RAW_DIR / "live_financial_risk_dataset.csv",
            "model_use": "Macro, governance, inflation, debt, GDP growth proxies",
            "status_note": "Run status identifies live inputs or explicitly selected demonstration seeds.",
        },
        {
            "source_layer": "FATF / sanctions reference",
            "source_type": "Public reference layer",
            "output_file": TABLES_DIR / "fatf_sanctions_reference.csv",
            "model_use": "AML/CFT and sanctions jurisdictional adjustment layer",
            "status_note": "Reference table; should be reviewed before publication or operational use.",
        },
        {
            "source_layer": "Market data",
            "source_type": "Live public market data connector",
            "output_file": TABLES_DIR / "market_stress_signal.csv",
            "model_use": "Market stress, banking pressure, volatility signal",
            "status_note": "Read source_status for active, partial, fallback, or disabled connector state.",
        },
        {
            "source_layer": "Market history",
            "source_type": "Live public market data connector",
            "output_file": RAW_DIR / "market_history.csv",
            "model_use": "Raw market history for audit and diagnostics",
            "status_note": "Supports market_metrics.csv and market_stress_signal.csv.",
        },
        {
            "source_layer": "ACLED live event data",
            "source_type": "Live authenticated API",
            "output_file": RAW_DIR / "acled_events_90d.csv",
            "model_use": "Country-level geopolitical instability and event pressure",
            "status_note": "Requires ACLED_USERNAME and ACLED_PASSWORD in .env.",
        },
        {
            "source_layer": "ACLED country signals",
            "source_type": "Derived live-data signal",
            "output_file": TABLES_DIR / "acled_country_signals.csv",
            "model_use": "Aggregated 90-day country-level conflict/protest/instability signals",
            "status_note": "Derived from ACLED raw event data.",
        },
        {
            "source_layer": "Monte Carlo robustness",
            "source_type": "Model diagnostic output",
            "output_file": TABLES_DIR / "monte_carlo_summary.csv",
            "model_use": "Rank stability and uncertainty testing",
            "status_note": "Generated from model scores, not an external source.",
        },
        {
            "source_layer": "Scenario analysis",
            "source_type": "Model diagnostic output",
            "output_file": TABLES_DIR / "scenario_summary.csv",
            "model_use": "Stress-test comparison across scenario assumptions",
            "status_note": "Generated from model scores, not an external source.",
        },
    ]

    records = []

    for source in sources:
        path = source["output_file"]

        records.append(
            {
                "source_layer": source["source_layer"],
                "source_type": source["source_type"],
                "output_file": str(path),
                "source_status": (source_status or {}).get(
                    {"Market history": "Market data", "ACLED country signals": "ACLED live event data"}.get(
                        source["source_layer"], source["source_layer"]),
                    "Generated this run" if source_status is not None and source["source_layer"] in
                    {"Monte Carlo robustness", "Scenario analysis"} else "Unknown: no run status supplied",
                ),
                "file_status": file_status(path),
                "row_count": row_count(path),
                "model_use": source["model_use"],
                "status_note": source["status_note"],
            }
        )

    return pd.DataFrame(records)