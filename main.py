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
from src.data_sources import build_financial_risk_dataset
from src.market_data import build_market_data_outputs
from src.acled_live import build_acled_live_outputs
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


def save_market_outputs() -> None:
    """Fetch and save market data outputs."""

    market_history, market_metrics, market_signal = build_market_data_outputs()

    market_history.to_csv(
        RAW_DIR / "market_history.csv",
        index=False,
    )

    market_metrics.to_csv(
        TABLES_DIR / "market_metrics.csv",
        index=False,
    )

    market_signal.to_csv(
        TABLES_DIR / "market_stress_signal.csv",
        index=False,
    )


def save_acled_outputs(countries: list[str]) -> None:
    """Fetch and save ACLED raw events and country-level signals."""

    try:
        acled_events, acled_signals = build_acled_live_outputs(
            countries=countries,
            days_back=90,
        )

        acled_events.to_csv(
            RAW_DIR / "acled_events_90d.csv",
            index=False,
        )

        acled_signals.to_csv(
            TABLES_DIR / "acled_country_signals.csv",
            index=False,
        )

    except Exception as exc:
        print(f"[WARN] ACLED output save failed: {exc}")

        fallback_signals = pd.DataFrame(
            [
                {
                    "country": country,
                    "acled_events_90d": 0,
                    "acled_fatalities_90d": 0,
                    "acled_political_violence_events_90d": 0,
                    "acled_demonstration_events_90d": 0,
                    "acled_civilian_targeting_events_90d": 0,
                    "acled_admin1_spread_90d": 0,
                    "acled_geopolitical_instability_signal": 0,
                    "acled_market_disruption_signal": 0,
                    "acled_banking_pressure_signal": 0,
                    "acled_status": f"Fallback: {exc}",
                }
                for country in countries
            ]
        )

        fallback_events = pd.DataFrame()

        fallback_events.to_csv(
            RAW_DIR / "acled_events_90d.csv",
            index=False,
        )

        fallback_signals.to_csv(
            TABLES_DIR / "acled_country_signals.csv",
            index=False,
        )


def run_pipeline() -> pd.DataFrame:
    """Run the complete financial-sector risk model pipeline."""

    ensure_directories()

    input_df = build_financial_risk_dataset(use_live_data=True)
    input_df.to_csv(RAW_DIR / "live_financial_risk_dataset.csv", index=False)

    save_market_outputs()
    save_acled_outputs(countries=input_df["country"].tolist())

    scored_df = calculate_layer_scores(input_df)
    scored_df = calculate_composite_score(scored_df)
    scored_df = add_driver_analysis(scored_df)

    processed_path = PROCESSED_DIR / "processed_financial_sector_risk_data.csv"
    scored_df.to_csv(processed_path, index=False)

    save_outputs(scored_df)

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

    generate_pdf_report(
        scored_df=scored_df,
        scenario_summary=scenario_summary,
        monte_carlo_summary=monte_carlo_summary,
    )

    print_summary(scored_df)

    return scored_df


if __name__ == "__main__":
    run_pipeline()