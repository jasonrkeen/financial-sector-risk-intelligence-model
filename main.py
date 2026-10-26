"""
Financial Sector Risk Intelligence Model

Standalone public-source framework for financial-sector risk scoring.

Responsible-use note:
This project is for research, education, and strategic risk analysis.
It does not provide investment advice, identify criminal suspects, predict
criminal acts, or replace legal, compliance, regulatory, or professional judgment.
"""

import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR, TABLES_DIR, ensure_directories
from src.data_sources import build_input_bundle, InputBundle
from src.scoring import (
    calculate_layer_scores,
    calculate_composite_score,
    add_driver_analysis,
)
from src.outputs import (
    save_outputs,
    save_scenario_outputs,
    save_monte_carlo_outputs,
)
from src.visualization import (
    generate_visualizations,
    generate_monte_carlo_visualizations,
)
from src.scenarios import run_scenario_analysis, build_scenario_summary
from src.monte_carlo import (
    run_monte_carlo_simulation,
    build_monte_carlo_summary,
)
from src.report_generator import generate_pdf_report
from src.publication import publishing_run, Publication


def print_summary(scored_df: pd.DataFrame) -> None:
    """Print a concise terminal summary."""

    top_10 = scored_df[
        [
            "rank",
            "country",
            "region",
            "financial_sector_risk_score",
            "risk_band",
            "primary_risk_driver",
        ]
    ].head(10)

    print("=" * 72)
    print("Financial Sector Risk Intelligence Model")
    print("=" * 72)
    print()
    print("Top 10 jurisdictions by Financial Sector Risk Score:")
    print(top_10.to_string(index=False))
    print()
    print("Output tables saved:")
    print(f"- {TABLES_DIR / 'financial_sector_risk_scores.csv'}")
    print(f"- {TABLES_DIR / 'country_financial_risk_profiles.csv'}")
    print(f"- {TABLES_DIR / 'risk_layer_summary.csv'}")
    print(f"- {TABLES_DIR / 'source_register.csv'}")
    print(f"- {TABLES_DIR / 'live_source_status.csv'}")
    print(f"- {TABLES_DIR / 'fatf_sanctions_reference.csv'}")
    print(f"- {TABLES_DIR / 'market_metrics.csv'}")
    print(f"- {TABLES_DIR / 'market_stress_signal.csv'}")
    print(f"- {TABLES_DIR / 'acled_country_signals.csv'}")
    print(f"- {TABLES_DIR / 'scenario_results.csv'}")
    print(f"- {TABLES_DIR / 'scenario_summary.csv'}")
    print(f"- {TABLES_DIR / 'monte_carlo_results.csv'}")
    print(f"- {TABLES_DIR / 'monte_carlo_summary.csv'}")
    print()
    print("Raw and processed data saved:")
    print("- data/raw/live_financial_risk_dataset.csv")
    print("- data/raw/market_history.csv")
    print("- data/raw/acled_events_90d.csv")
    print("- data/processed/processed_financial_sector_risk_data.csv")
    print()
    print("Charts saved:")
    print("- outputs/charts/top_10_financial_sector_risk_countries.png")
    print("- outputs/charts/risk_layer_heatmap.png")
    print("- outputs/charts/market_vs_financial_crime_risk.png")
    print("- outputs/charts/governance_vs_sanctions_risk.png")
    print("- outputs/charts/monte_carlo_score_distribution.png")
    print("- outputs/charts/monte_carlo_rank_stability.png")
    print("- outputs/charts/monte_carlo_rank_volatility.png")
    print()
    print("Report saved:")
    print("- outputs/reports/financial_sector_risk_report.pdf")
    print()
    print("Next recommended build steps:")
    print("1. Run final pipeline validation after all file updates.")
    print("2. Review Streamlit dashboard for live-source diagnostics.")
    print("3. Run final GitHub cleanup checklist before publishing.")
    print("=" * 72)


def save_input_evidence(bundle: InputBundle) -> None:
    """Export exactly the evidence used to build this run's model inputs."""
    for frame, path in [
        (bundle.market_history, RAW_DIR / "market_history.csv"),
        (bundle.market_metrics, TABLES_DIR / "market_metrics.csv"),
        (bundle.market_signal, TABLES_DIR / "market_stress_signal.csv"),
        (bundle.acled_events, RAW_DIR / "acled_events_90d.csv"),
        (bundle.acled_signals, TABLES_DIR / "acled_country_signals.csv"),
    ]:
        # A failed connector may return a columnless dataframe: keep CSV readable.
        if not len(frame.columns):
            frame = pd.DataFrame(columns=["status"])
        frame.to_csv(path, index=False)


def run_pipeline(use_live_data: bool = True) -> pd.DataFrame:
    """Run the complete financial-sector risk model pipeline."""

    ensure_directories()
    with publishing_run(TABLES_DIR, "live" if use_live_data else "demonstration") as publication:
        return _run_pipeline(use_live_data, publication)


def _run_pipeline(use_live_data: bool, publication: Publication) -> pd.DataFrame:
    bundle = build_input_bundle(use_live_data=use_live_data)
    input_df = bundle.dataset
    input_df.to_csv(RAW_DIR / "live_financial_risk_dataset.csv", index=False)

    save_input_evidence(bundle)

    scored_df = calculate_layer_scores(input_df)
    scored_df = calculate_composite_score(scored_df)
    scored_df = add_driver_analysis(scored_df)

    processed_path = PROCESSED_DIR / "processed_financial_sector_risk_data.csv"
    scored_df.to_csv(processed_path, index=False)

    save_outputs(scored_df, source_status=bundle.source_status)

    scenario_df = run_scenario_analysis(scored_df)
    scenario_summary = build_scenario_summary(scenario_df)
    save_scenario_outputs(scenario_df, scenario_summary)

    monte_carlo_df = run_monte_carlo_simulation(
        scored_df=scored_df,
        n_simulations=1000,
        noise_std=7.5,
        random_seed=42,
    )
    monte_carlo_summary = build_monte_carlo_summary(monte_carlo_df)
    save_monte_carlo_outputs(monte_carlo_df, monte_carlo_summary)

    generate_visualizations(scored_df)
    generate_monte_carlo_visualizations(monte_carlo_df, monte_carlo_summary)

    report_path = generate_pdf_report(
        scored_df=scored_df,
        scenario_summary=scenario_summary,
        monte_carlo_summary=monte_carlo_summary,
    )

    from src.source_status import build_live_source_status_table
    build_live_source_status_table(bundle.source_status).to_csv(
        TABLES_DIR / "live_source_status.csv", index=False,
    )
    publication.complete(report_path)
    print_summary(scored_df)

    return scored_df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Offline seed demonstration; no live requests")
    args = parser.parse_args()
    run_pipeline(use_live_data=not args.demo)
