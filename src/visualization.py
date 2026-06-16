from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.config import CHARTS_DIR


def save_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    top_n: int = 10,
) -> None:
    """Save a simple horizontal bar chart."""

    chart_df = df.sort_values(y_col, ascending=True).tail(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(chart_df[x_col], chart_df[y_col])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_ranked_layer_bar_chart(
    df: pd.DataFrame,
    layer_col: str,
    title: str,
    xlabel: str,
    output_path: Path,
    top_n: int = 10,
) -> None:
    """Save a ranked horizontal bar chart for a selected risk layer."""

    chart_df = df.sort_values(layer_col, ascending=True).tail(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(chart_df["country"], chart_df[layer_col])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Country")
    plt.grid(axis="x", alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_layer_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """Save a heatmap-style chart of risk layers by country."""

    layer_columns = [
        "market_stress_risk",
        "financial_crime_exposure_risk",
        "governance_regulatory_risk",
        "banking_macro_stress_risk",
        "sanctions_geopolitical_risk",
        "cyber_operational_risk",
    ]

    top_df = df.sort_values(
        "financial_sector_risk_score",
        ascending=False,
    ).head(12)

    heatmap_data = top_df[layer_columns].to_numpy()

    plt.figure(figsize=(12, 7))
    plt.imshow(heatmap_data, aspect="auto")

    plt.xticks(
        ticks=range(len(layer_columns)),
        labels=[
            "Market",
            "Financial Crime",
            "Governance",
            "Banking/Macro",
            "Sanctions/Geo",
            "Cyber/Ops",
        ],
        rotation=45,
        ha="right",
    )

    plt.yticks(
        ticks=range(len(top_df)),
        labels=top_df["country"],
    )

    plt.colorbar(label="Risk Score")
    plt.title("Financial Sector Risk Layer Heatmap - Top Jurisdictions")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def _select_scatter_labels(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    top_n: int = 3,
    exclude_labels: set[str] | None = None,
) -> set[str]:
    """
    Select a limited set of labels for scatter charts.

    This keeps crowded charts readable by labeling:
    - highest composite-risk jurisdictions
    - strongest x-axis outliers
    - strongest y-axis outliers

    Some crowded labels can be excluded manually.
    """

    if exclude_labels is None:
        exclude_labels = set()

    label_countries: set[str] = set()

    if "financial_sector_risk_score" in df.columns:
        top_risk = df.sort_values(
            "financial_sector_risk_score",
            ascending=False,
        ).head(top_n)
        label_countries.update(top_risk["country"].tolist())

    x_outliers = df.sort_values(x_col, ascending=False).head(2)
    y_outliers = df.sort_values(y_col, ascending=False).head(2)

    label_countries.update(x_outliers["country"].tolist())
    label_countries.update(y_outliers["country"].tolist())

    label_countries = label_countries - exclude_labels

    return label_countries


def save_scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    label_top_n: int = 3,
    exclude_labels: set[str] | None = None,
) -> None:
    """
    Save a scatter chart with selective country labels.

    Labels are intentionally limited to avoid overlapping text when many
    jurisdictions cluster near the same score range.
    """

    chart_df = df.copy()

    if exclude_labels is None:
        exclude_labels = set()

    label_countries = _select_scatter_labels(
        chart_df,
        x_col=x_col,
        y_col=y_col,
        top_n=label_top_n,
        exclude_labels=exclude_labels,
    )

    plt.figure(figsize=(10, 6))
    plt.scatter(chart_df[x_col], chart_df[y_col], alpha=0.70)

    for _, row in chart_df.iterrows():
        country = row["country"]

        if country not in label_countries:
            continue

        plt.annotate(
            country,
            (row[x_col], row[y_col]),
            textcoords="offset points",
            xytext=(8, 8),
            fontsize=8,
            alpha=0.9,
        )

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_monte_carlo_distribution_chart(
    monte_carlo_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save a distribution chart of simulated financial-sector risk scores."""

    plt.figure(figsize=(10, 6))
    plt.hist(
        monte_carlo_df["simulated_financial_sector_risk_score"],
        bins=30,
    )
    plt.title("Monte Carlo Distribution of Simulated Financial Sector Risk Scores")
    plt.xlabel("Simulated Financial Sector Risk Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_monte_carlo_rank_stability_chart(
    monte_carlo_summary: pd.DataFrame,
    output_path: Path,
    top_n: int = 10,
) -> None:
    """Save a chart showing average simulated rank stability."""

    chart_df = monte_carlo_summary.sort_values(
        "mean_simulated_rank",
        ascending=False,
    ).tail(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(chart_df["country"], chart_df["mean_simulated_rank"])
    plt.title("Monte Carlo Rank Stability - Top Jurisdictions")
    plt.xlabel("Average Simulated Rank")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def save_monte_carlo_rank_volatility_chart(
    monte_carlo_summary: pd.DataFrame,
    output_path: Path,
    top_n: int = 10,
) -> None:
    """Save a chart showing rank volatility under Monte Carlo simulation."""

    if "rank_volatility" not in monte_carlo_summary.columns:
        return

    chart_df = monte_carlo_summary.sort_values(
        "rank_volatility",
        ascending=True,
    ).tail(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(chart_df["country"], chart_df["rank_volatility"])
    plt.title("Monte Carlo Rank Volatility - Highest Movement")
    plt.xlabel("Rank Volatility")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_visualizations(scored_df: pd.DataFrame) -> None:
    """Generate all baseline model charts."""

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    save_bar_chart(
        df=scored_df,
        x_col="country",
        y_col="financial_sector_risk_score",
        title="Top 10 Financial Sector Risk Jurisdictions",
        xlabel="Financial Sector Risk Score",
        ylabel="Country",
        output_path=CHARTS_DIR / "top_10_financial_sector_risk_countries.png",
        top_n=10,
    )

    save_layer_heatmap(
        df=scored_df,
        output_path=CHARTS_DIR / "risk_layer_heatmap.png",
    )

    save_scatter_chart(
        df=scored_df,
        x_col="market_stress_risk",
        y_col="financial_crime_exposure_risk",
        title="Market Stress vs Financial Crime Exposure",
        xlabel="Market Stress Risk",
        ylabel="Financial Crime Exposure Risk",
        output_path=CHARTS_DIR / "market_vs_financial_crime_risk.png",
        label_top_n=3,
        exclude_labels={"United Kingdom"},
    )

    save_ranked_layer_bar_chart(
        df=scored_df,
        layer_col="sanctions_geopolitical_risk",
        title="Top Sanctions / Geopolitical Risk Jurisdictions",
        xlabel="Sanctions / Geopolitical Risk Score",
        output_path=CHARTS_DIR / "governance_vs_sanctions_risk.png",
        top_n=10,
    )


def generate_monte_carlo_visualizations(
    monte_carlo_df: pd.DataFrame,
    monte_carlo_summary: pd.DataFrame,
) -> None:
    """Generate Monte Carlo robustness charts."""

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    save_monte_carlo_distribution_chart(
        monte_carlo_df=monte_carlo_df,
        output_path=CHARTS_DIR / "monte_carlo_score_distribution.png",
    )

    save_monte_carlo_rank_stability_chart(
        monte_carlo_summary=monte_carlo_summary,
        output_path=CHARTS_DIR / "monte_carlo_rank_stability.png",
    )

    save_monte_carlo_rank_volatility_chart(
        monte_carlo_summary=monte_carlo_summary,
        output_path=CHARTS_DIR / "monte_carlo_rank_volatility.png",
    )