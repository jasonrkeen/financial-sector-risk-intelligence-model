"""
Financial Sector Risk Intelligence Dashboard

Interactive Streamlit dashboard for the Financial Sector Risk Intelligence Model.
"""

from pathlib import Path
from io import BytesIO

from src.publication import read_snapshot, SnapshotUnavailable

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
TABLES_DIR = BASE_DIR / "outputs" / "tables"
CHARTS_DIR = BASE_DIR / "outputs" / "charts"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"


st.set_page_config(
    page_title="Financial Sector Risk Intelligence Model",
    page_icon="📊",
    layout="wide",
)


def load_table(filename: str, snapshot: dict[str, bytes]) -> pd.DataFrame:
    """Load from a single completed snapshot, never from mutable working files."""
    content = snapshot.get(f"tables/{filename}")
    return pd.read_csv(BytesIO(content)) if content is not None else pd.DataFrame()


def risk_band_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters to the main scored dataset."""

    filtered = df.copy()

    regions = sorted(filtered["region"].dropna().unique().tolist())
    selected_regions = st.sidebar.multiselect(
        "Region",
        options=regions,
        default=regions,
    )

    risk_bands = sorted(filtered["risk_band"].dropna().unique().tolist())
    selected_bands = st.sidebar.multiselect(
        "Risk Band",
        options=risk_bands,
        default=risk_bands,
    )

    filtered = filtered[
        (filtered["region"].isin(selected_regions))
        & (filtered["risk_band"].isin(selected_bands))
    ]

    return filtered


def show_download_button(file_path: Path, label: str, mime: str, snapshot: dict[str, bytes]) -> None:
    """Downloads use the same snapshot bytes as the displayed results."""
    key = f"{file_path.parent.name}/{file_path.name}"
    content = snapshot.get(key)
    if content is None:
        st.info(f"File not found in completed run: {file_path.name}")
        return
    st.download_button(label=label, data=content, file_name=file_path.name, mime=mime)


def show_empty_state(message: str) -> None:
    """Show a simple warning when an expected output table is missing."""

    st.warning(message)


def main() -> None:
    st.title("Financial Sector Risk Intelligence Model")
    st.caption(
        "Public-source framework for market stress, financial crime exposure, "
        "governance/regulatory risk, banking and macro-financial stress, "
        "sanctions/geopolitical pressure, cyber/operational risk, scenario analysis, "
        "and Monte Carlo robustness testing."
    )

    try:
        run, snapshot = read_snapshot(TABLES_DIR)
    except SnapshotUnavailable as exc:
        st.error(str(exc))
        return
    st.caption(f"Completed run: {run['run_id']}")
    if run["mode"] == "demonstration":
        st.warning("DEMONSTRATION: manually assigned seed inputs; not live evidence.")

    scored_df = load_table("financial_sector_risk_scores.csv", snapshot)
    profile_df = load_table("country_financial_risk_profiles.csv", snapshot)
    layer_summary_df = load_table("risk_layer_summary.csv", snapshot)
    scenario_df = load_table("scenario_results.csv", snapshot)
    scenario_summary_df = load_table("scenario_summary.csv", snapshot)
    monte_carlo_summary_df = load_table("monte_carlo_summary.csv", snapshot)
    source_register_df = load_table("source_register.csv", snapshot)
    live_source_status_df = load_table("live_source_status.csv", snapshot)
    market_signal_df = load_table("market_stress_signal.csv", snapshot)
    acled_signals_df = load_table("acled_country_signals.csv", snapshot)
    fatf_reference_df = load_table("fatf_sanctions_reference.csv", snapshot)

    if scored_df.empty:
        st.error(
            "No model output found. Run `python main.py` first to generate the output tables."
        )
        return

    st.sidebar.header("Filters")
    filtered_df = risk_band_filter(scored_df)

    st.sidebar.divider()
    st.sidebar.markdown("### Downloads")

    show_download_button(
        REPORTS_DIR / "financial_sector_risk_report.pdf",
        "Download PDF Report",
        "application/pdf", snapshot,
    )

    show_download_button(
        TABLES_DIR / "financial_sector_risk_scores.csv",
        "Download Risk Scores CSV",
        "text/csv", snapshot,
    )

    show_download_button(
        TABLES_DIR / "country_financial_risk_profiles.csv",
        "Download Country Profiles CSV",
        "text/csv", snapshot,
    )

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    top_score = filtered_df["financial_sector_risk_score"].max()
    avg_score = filtered_df["financial_sector_risk_score"].mean()
    high_count = int((filtered_df["risk_band"] == "High").sum())
    elevated_or_high = int(
        (
            (filtered_df["risk_band"] == "Elevated")
            | (filtered_df["risk_band"] == "High")
        ).sum()
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Highest Score", f"{top_score:.2f}")
    col2.metric("Average Score", f"{avg_score:.2f}")
    col3.metric("High Risk Count", high_count)
    col4.metric("Elevated / High Count", elevated_or_high)

    tabs = st.tabs(
        [
            "Overview",
            "Risk Layers",
            "Scenario Analysis",
            "Monte Carlo",
            "Country Profiles",
            "Sources & Methodology",
        ]
    )

    with tabs[0]:
        st.subheader("Top Jurisdictions by Financial Sector Risk Score")
        st.caption(
            "Use this as a triage view. Higher scores indicate stronger relative "
            "financial-sector pressure across the model layers, not a prediction."
        )

        top_df = filtered_df.sort_values(
            "financial_sector_risk_score",
            ascending=False,
        ).head(15)

        fig = px.bar(
            top_df.sort_values("financial_sector_risk_score"),
            x="financial_sector_risk_score",
            y="country",
            orientation="h",
            hover_data=[
                "region",
                "risk_band",
                "primary_risk_driver",
            ],
            title="Top Financial Sector Risk Jurisdictions",
            labels={
                "financial_sector_risk_score": "Financial Sector Risk Score",
                "country": "Country",
            },
        )
        fig.update_layout(
            height=650,
            margin=dict(l=120, r=40, t=70, b=70),
        )
        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            top_df[
                [
                    "rank",
                    "country",
                    "region",
                    "financial_sector_risk_score",
                    "risk_band",
                    "primary_risk_driver",
                ]
            ],
            width="stretch",
        )

    with tabs[1]:
        st.subheader("Risk Layer Comparison")
        st.caption(
            "Risk layers show what is driving the composite score. A country can rank "
            "higher because of broad pressure across several layers or because one layer "
            "is unusually elevated."
        )

        layer_cols = [
            "market_stress_risk",
            "financial_crime_exposure_risk",
            "governance_regulatory_risk",
            "banking_macro_stress_risk",
            "sanctions_geopolitical_risk",
            "cyber_operational_risk",
        ]

        heatmap_df = filtered_df.sort_values(
            "financial_sector_risk_score",
            ascending=False,
        ).head(15)

        fig = px.imshow(
            heatmap_df[layer_cols].to_numpy(),
            x=[
                "Market",
                "Financial Crime",
                "Governance",
                "Banking/Macro",
                "Sanctions/Geo",
                "Cyber/Ops",
            ],
            y=heatmap_df["country"],
            labels=dict(x="Risk Layer", y="Country", color="Risk Score"),
            title="Risk Layer Heatmap",
            aspect="auto",
            zmin=0,
            zmax=100,
        )

        fig.update_layout(
            height=750,
            margin=dict(l=130, r=50, t=80, b=130),
        )

        fig.update_xaxes(
            tickangle=-35,
            side="bottom",
            automargin=True,
        )

        fig.update_yaxes(
            automargin=True,
        )

        st.plotly_chart(fig, width="stretch")

        scatter = px.scatter(
            filtered_df,
            x="market_stress_risk",
            y="financial_crime_exposure_risk",
            size="financial_sector_risk_score",
            hover_name="country",
            hover_data=["region", "risk_band", "primary_risk_driver"],
            title="Market Stress vs Financial Crime Exposure",
            labels={
                "market_stress_risk": "Market Stress Risk",
                "financial_crime_exposure_risk": "Financial Crime Exposure Risk",
            },
        )
        scatter.update_layout(
            height=650,
            margin=dict(l=90, r=40, t=70, b=70),
        )
        st.plotly_chart(scatter, width="stretch")

        sanctions_fig = px.bar(
            filtered_df.sort_values("sanctions_geopolitical_risk", ascending=False)
            .head(10)
            .sort_values("sanctions_geopolitical_risk"),
            x="sanctions_geopolitical_risk",
            y="country",
            orientation="h",
            title="Top Sanctions / Geopolitical Risk Jurisdictions",
            labels={
                "sanctions_geopolitical_risk": "Sanctions / Geopolitical Risk Score",
                "country": "Country",
            },
        )
        sanctions_fig.update_layout(
            height=650,
            margin=dict(l=130, r=40, t=70, b=70),
        )
        st.plotly_chart(sanctions_fig, width="stretch")

        if not layer_summary_df.empty:
            st.subheader("Average Risk by Region")
            st.dataframe(layer_summary_df, width="stretch")

    with tabs[2]:
        st.subheader("Scenario Analysis")
        st.caption(
            "Scenario analysis applies stress assumptions to model layers. These "
            "scenarios are not forecasts; they show how the model reacts under different "
            "pressure conditions."
        )

        if scenario_df.empty or scenario_summary_df.empty:
            show_empty_state("Scenario output not found. Run `python main.py` again.")
        else:
            st.dataframe(scenario_summary_df, width="stretch")

            selected_scenario = st.selectbox(
                "Select scenario",
                options=sorted(scenario_df["scenario"].unique().tolist()),
            )

            scenario_view = scenario_df[
                scenario_df["scenario"] == selected_scenario
            ].sort_values(
                "scenario_financial_sector_risk_score",
                ascending=False,
            )

            fig = px.bar(
                scenario_view.head(15).sort_values(
                    "scenario_financial_sector_risk_score"
                ),
                x="scenario_financial_sector_risk_score",
                y="country",
                orientation="h",
                hover_data=[
                    "baseline_financial_sector_risk_score",
                    "score_change",
                    "scenario_risk_band",
                    "primary_risk_driver",
                ],
                title=f"{selected_scenario}: Scenario-Adjusted Risk Scores",
                labels={
                    "scenario_financial_sector_risk_score": "Scenario Score",
                    "country": "Country",
                },
            )
            fig.update_layout(
                height=650,
                margin=dict(l=130, r=40, t=70, b=70),
            )
            st.plotly_chart(fig, width="stretch")

            st.dataframe(
                scenario_view[
                    [
                        "scenario_rank",
                        "country",
                        "region",
                        "baseline_financial_sector_risk_score",
                        "scenario_financial_sector_risk_score",
                        "score_change",
                        "scenario_risk_band",
                        "primary_risk_driver",
                    ]
                ],
                width="stretch",
            )

    with tabs[3]:
        st.subheader("Monte Carlo Robustness Testing")

        if monte_carlo_summary_df.empty:
            show_empty_state("Monte Carlo output not found. Run `python main.py` again.")
        else:
            st.caption(
                "Monte Carlo testing perturbs the model's layer scores to test whether "
                "rankings remain stable under input uncertainty. It is a robustness test, "
                "not a forecast."
            )

            mean_score_hover = [
                "baseline_score",
                "std_simulated_score",
                "mean_simulated_rank",
                "elevated_or_high_probability",
            ]

            if "rank_volatility" in monte_carlo_summary_df.columns:
                mean_score_hover.insert(3, "rank_volatility")

            fig = px.bar(
                monte_carlo_summary_df.head(15).sort_values("mean_simulated_score"),
                x="mean_simulated_score",
                y="country",
                orientation="h",
                hover_data=mean_score_hover,
                title="Monte Carlo Mean Simulated Scores",
                labels={
                    "mean_simulated_score": "Mean Simulated Score",
                    "country": "Country",
                },
            )
            fig.update_layout(
                height=650,
                margin=dict(l=130, r=40, t=70, b=70),
            )
            st.plotly_chart(fig, width="stretch")

            rank_hover = [
                "mean_simulated_score",
                "best_simulated_rank",
                "worst_simulated_rank",
                "high_risk_probability",
                "elevated_or_high_probability",
            ]

            if "rank_volatility" in monte_carlo_summary_df.columns:
                rank_hover.append("rank_volatility")

            rank_stability_view = (
                monte_carlo_summary_df.sort_values(
                    "mean_simulated_rank",
                    ascending=True,
                )
                .head(15)
                .sort_values("mean_simulated_rank", ascending=False)
            )

            rank_fig = px.bar(
                rank_stability_view,
                x="mean_simulated_rank",
                y="country",
                orientation="h",
                hover_data=rank_hover,
                title="Monte Carlo Rank Stability - Lower Average Rank Is More Stable Near the Top",
                labels={
                    "mean_simulated_rank": "Average Simulated Rank",
                    "country": "Country",
                },
            )

            rank_fig.update_layout(
                height=650,
                margin=dict(l=130, r=40, t=70, b=70),
            )

            st.plotly_chart(rank_fig, width="stretch")

            if "rank_volatility" in monte_carlo_summary_df.columns:
                volatility_fig = px.bar(
                    monte_carlo_summary_df.sort_values(
                        "rank_volatility",
                        ascending=False,
                    )
                    .head(10)
                    .sort_values("rank_volatility"),
                    x="rank_volatility",
                    y="country",
                    orientation="h",
                    title="Monte Carlo Rank Volatility - Highest Movement",
                    labels={
                        "rank_volatility": "Rank Volatility",
                        "country": "Country",
                    },
                )
                volatility_fig.update_layout(
                    height=650,
                    margin=dict(l=130, r=40, t=70, b=70),
                )
                st.plotly_chart(volatility_fig, width="stretch")

            st.dataframe(monte_carlo_summary_df, width="stretch")

    with tabs[4]:
        st.subheader("Country Financial Risk Profiles")

        if profile_df.empty:
            st.dataframe(filtered_df, width="stretch")
        else:
            selected_country = st.selectbox(
                "Select country",
                options=profile_df["country"].tolist(),
            )

            country_row = profile_df[profile_df["country"] == selected_country]

            st.dataframe(country_row, width="stretch")

            layer_cols = [
                "market_stress_risk",
                "financial_crime_exposure_risk",
                "governance_regulatory_risk",
                "banking_macro_stress_risk",
                "sanctions_geopolitical_risk",
                "cyber_operational_risk",
            ]

            profile_long = country_row.melt(
                id_vars=["country"],
                value_vars=layer_cols,
                var_name="risk_layer",
                value_name="risk_score",
            )

            fig = px.bar(
                profile_long,
                x="risk_layer",
                y="risk_score",
                title=f"{selected_country}: Risk Layer Profile",
                labels={
                    "risk_layer": "Risk Layer",
                    "risk_score": "Risk Score",
                },
            )
            fig.update_layout(
                height=600,
                xaxis_tickangle=-30,
                margin=dict(l=60, r=40, t=70, b=120),
            )
            st.plotly_chart(fig, width="stretch")

    with tabs[5]:
        st.subheader("Sources and Methodology")

        st.markdown(
            """
            This dashboard summarizes a standalone financial-sector risk intelligence model.

            The model scores jurisdictions across six layers:

            1. Market stress risk  
            2. Financial crime exposure risk  
            3. Governance and regulatory risk  
            4. Banking and macro-financial stress risk  
            5. Sanctions and geopolitical finance risk  
            6. Cyber and operational risk  

            Current version: live/reference public-source model.

            The current pipeline integrates live World Bank macro/governance indicators,
            FATF/sanctions reference adjustments, public market-data stress signals,
            and aggregated country-level ACLED event-data signals. Seed values remain
            as a fallback for pipeline testing if live pulls fail.
            """
        )

        st.warning(
            "Responsible-use note: This project is for research, education, and strategic "
            "risk analysis. It does not provide investment advice, identify criminal suspects, "
            "predict criminal acts, or replace legal, compliance, regulatory, intelligence, "
            "security, or professional judgment."
        )

        if not live_source_status_df.empty:
            st.subheader("Live Source Status")
            st.dataframe(live_source_status_df, width="stretch")

        if not source_register_df.empty:
            st.subheader("Source Register")
            st.dataframe(source_register_df, width="stretch")

        if not market_signal_df.empty:
            st.subheader("Market Data Signal")
            st.dataframe(market_signal_df, width="stretch")

        if not acled_signals_df.empty:
            st.subheader("ACLED Country Signals")
            st.dataframe(acled_signals_df, width="stretch")

        if not fatf_reference_df.empty:
            st.subheader("FATF / Sanctions Reference")
            st.dataframe(fatf_reference_df, width="stretch")


if __name__ == "__main__":
    main()