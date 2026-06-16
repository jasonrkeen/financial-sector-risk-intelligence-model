from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import CHARTS_DIR, REPORTS_DIR


REPORT_PATH = REPORTS_DIR / "financial_sector_risk_report.pdf"


def _build_title_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )


def _build_heading_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="HeadingStyle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
    )


def _build_body_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="BodyStyle",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=6,
    )


def _build_small_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="SmallStyle",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=4,
    )


def _build_table_cell_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="TableCellStyle",
        parent=styles["BodyText"],
        fontSize=7,
        leading=8,
        spaceAfter=0,
    )


def _build_table_header_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="TableHeaderStyle",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        alignment=TA_CENTER,
        spaceAfter=0,
    )


def _format_table_data(data: list[list]) -> list[list]:
    """Convert table strings to Paragraph objects so long text wraps cleanly."""

    header_style = _build_table_header_style()
    cell_style = _build_table_cell_style()

    formatted_rows = []

    for row_index, row in enumerate(data):
        formatted_row = []

        for value in row:
            if isinstance(value, str):
                style = header_style if row_index == 0 else cell_style
                formatted_row.append(Paragraph(value, style))
            else:
                formatted_row.append(value)

        formatted_rows.append(formatted_row)

    return formatted_rows


def _add_table(data: list[list], col_widths: list[float] | None = None) -> Table:
    table = Table(_format_table_data(data), colWidths=col_widths, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ]
        )
    )

    return table


def _add_how_to_read(
    story: list,
    text: str,
    body_style: ParagraphStyle,
) -> None:
    """Add a reusable plain-English how-to-read note."""

    story.append(
        Paragraph(
            f"<b>How to read this section:</b> {text}",
            body_style,
        )
    )


def _add_chart_if_exists(
    story: list,
    chart_path: Path,
    heading: str,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
    how_to_read: str | None = None,
    width: float = 6.6 * inch,
) -> None:
    if not chart_path.exists():
        story.append(Paragraph(f"Chart missing: {chart_path.name}", body_style))
        return

    story.append(Paragraph(heading, heading_style))

    if how_to_read:
        _add_how_to_read(story, how_to_read, body_style)

    story.append(Image(str(chart_path), width=width, height=3.8 * inch))
    story.append(Spacer(1, 0.15 * inch))


def build_top_risk_table(scored_df: pd.DataFrame, top_n: int = 10) -> list[list]:
    table_df = scored_df[
        [
            "rank",
            "country",
            "region",
            "financial_sector_risk_score",
            "risk_band",
            "primary_risk_driver",
        ]
    ].head(top_n)

    rows = [
        [
            "Rank",
            "Country",
            "Region",
            "Score",
            "Band",
            "Primary Driver",
        ]
    ]

    for _, row in table_df.iterrows():
        rows.append(
            [
                int(row["rank"]),
                row["country"],
                row["region"],
                row["financial_sector_risk_score"],
                row["risk_band"],
                row["primary_risk_driver"],
            ]
        )

    return rows


def build_scoring_criteria_table() -> list[list]:
    """Build plain-English scoring criteria for the report."""

    return [
        [
            "Score / Layer",
            "What it captures",
            "Why it matters",
            "Higher score generally means",
        ],
        [
            "Composite Financial Sector Risk Score",
            "Weighted 0-100 summary of the six model layers.",
            "Provides one directional comparison point across jurisdictions.",
            "More combined financial-sector pressure relative to other jurisdictions in the model.",
        ],
        [
            "Market Stress Risk",
            "Market pressure, inflation pressure, currency pressure, and broad financial stress proxies.",
            "Financial systems can become more fragile when prices, rates, volatility, or currency conditions deteriorate.",
            "Greater market or macro-financial strain.",
        ],
        [
            "Financial Crime Exposure Risk",
            "Financial crime exposure, corruption risk, and AML/CFT weakness proxies.",
            "Weaknesses in this area can raise concerns around illicit finance, monitoring burden, and institutional risk.",
            "Greater exposure to financial crime or AML/CFT pressure.",
        ],
        [
            "Governance / Regulatory Risk",
            "Governance weakness, regulatory quality weakness, and corruption-risk proxies.",
            "Governance and regulatory quality influence financial-sector resilience, enforcement capacity, and rule consistency.",
            "Weaker governance or regulatory environment.",
        ],
        [
            "Banking / Macro Stress Risk",
            "Banking stress, sovereign-debt pressure, and market-stress proxies.",
            "Banking and sovereign stress can affect credit conditions, capital stability, and financial-sector confidence.",
            "Greater banking or macroeconomic pressure.",
        ],
        [
            "Sanctions / Geopolitical Risk",
            "Sanctions exposure, geopolitical instability, and governance weakness.",
            "Geopolitical and sanctions pressure can affect cross-border finance, compliance workload, and market access.",
            "Greater geopolitical, sanctions, or strategic-risk pressure.",
        ],
        [
            "Cyber / Operational Risk",
            "Cyber and operational pressure proxy adjusted by broader volatility and governance conditions.",
            "Operational disruption can affect financial institutions, payments, data integrity, and continuity planning.",
            "Greater cyber, technology, or operational disruption pressure.",
        ],
    ]


def build_scenario_table(scenario_summary: pd.DataFrame) -> list[list]:
    rows = [
        [
            "Scenario",
            "Avg Score",
            "Max Score",
            "Avg Change",
            "High Count",
            "Elevated/High",
        ]
    ]

    for _, row in scenario_summary.iterrows():
        rows.append(
            [
                row["scenario"],
                row["average_scenario_score"],
                row["max_scenario_score"],
                row["average_score_change"],
                int(row["high_risk_count"]),
                int(row["elevated_or_high_count"]),
            ]
        )

    return rows


def build_monte_carlo_table(
    monte_carlo_summary: pd.DataFrame,
    top_n: int = 10,
) -> list[list]:
    summary = monte_carlo_summary.copy()

    if "rank_volatility" not in summary.columns:
        summary["rank_volatility"] = 0.0

    table_df = summary[
        [
            "monte_carlo_rank",
            "country",
            "mean_simulated_score",
            "std_simulated_score",
            "mean_simulated_rank",
            "rank_volatility",
            "elevated_or_high_probability",
        ]
    ].head(top_n)

    rows = [
        [
            "MC Rank",
            "Country",
            "Mean Score",
            "Std Dev",
            "Mean Rank",
            "Rank Vol",
            "Elev/High Prob",
        ]
    ]

    for _, row in table_df.iterrows():
        rows.append(
            [
                int(row["monte_carlo_rank"]),
                row["country"],
                row["mean_simulated_score"],
                row["std_simulated_score"],
                row["mean_simulated_rank"],
                row["rank_volatility"],
                row["elevated_or_high_probability"],
            ]
        )

    return rows


def generate_pdf_report(
    scored_df: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    monte_carlo_summary: pd.DataFrame,
    output_path: Path = REPORT_PATH,
) -> Path:
    """Generate the financial-sector risk PDF report."""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    title_style = _build_title_style()
    heading_style = _build_heading_style()
    body_style = _build_body_style()
    small_style = _build_small_style()

    story = []

    story.append(Paragraph("Financial Sector Risk Intelligence Model", title_style))
    story.append(
        Paragraph(
            "A public-source framework for market stress, financial crime exposure, "
            "governance risk, sanctions/geopolitical pressure, cyber/operational risk, "
            "scenario analysis, and Monte Carlo robustness testing.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Responsible Use", heading_style))
    story.append(
        Paragraph(
            "This report is for research, education, and strategic risk analysis. "
            "It does not provide investment advice, identify criminal suspects, predict "
            "criminal acts, or replace legal, compliance, regulatory, intelligence, "
            "security, or professional judgment. Scores are analytical indicators based "
            "on public-source and reference risk layers and should be interpreted as "
            "decision-support inputs, not definitive conclusions.",
            body_style,
        )
    )

    story.append(Paragraph("How to Read This Report", heading_style))
    story.append(
        Paragraph(
            "Read the report as a structured comparison of relative jurisdiction-level "
            "financial-sector pressure. A higher score does not mean a specific event "
            "will occur. It means the model observed stronger directional risk signals "
            "across the selected public-source and reference layers. The most useful "
            "question is not only which jurisdiction ranks highest, but which risk layer "
            "is driving the score and whether the ranking remains stable under scenarios "
            "and Monte Carlo uncertainty testing.",
            body_style,
        )
    )

    story.append(Paragraph("Total Scoring Criteria and Why It Matters", heading_style))
    story.append(
        Paragraph(
            "The total score is a weighted 0-100 composite built from six risk layers. "
            "The purpose is to make different types of financial-sector pressure easier "
            "to compare in one framework while still preserving the underlying layer "
            "signals for analyst review.",
            body_style,
        )
    )
    story.append(
        _add_table(
            build_scoring_criteria_table(),
            col_widths=[
                1.35 * inch,
                1.55 * inch,
                1.65 * inch,
                1.55 * inch,
            ],
        )
    )

    story.append(PageBreak())

    story.append(Paragraph("Top Jurisdictions by Financial Sector Risk Score", heading_style))
    _add_how_to_read(
        story,
        "This table ranks jurisdictions by the composite score. The score is a "
        "directional 0-100 indicator, the band provides a plain-language grouping, "
        "and the primary driver identifies the highest contributing risk layer. "
        "Use this as a triage view, not a final judgment.",
        body_style,
    )
    story.append(
        _add_table(
            build_top_risk_table(scored_df),
            col_widths=[
                0.45 * inch,
                1.1 * inch,
                1.15 * inch,
                0.65 * inch,
                0.75 * inch,
                1.75 * inch,
            ],
        )
    )

    story.append(Spacer(1, 0.2 * inch))

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "top_10_financial_sector_risk_countries.png",
        heading="Top 10 Risk Chart",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "The bars show the same composite scores visually. Longer bars indicate "
            "higher relative model scores. Small differences between bars should not "
            "be overinterpreted without reviewing the layer scores and robustness tests."
        ),
    )

    story.append(PageBreak())

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "risk_layer_heatmap.png",
        heading="Risk Layer Heatmap",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "Each row is a jurisdiction and each column is a risk layer. Darker or "
            "higher-intensity cells generally indicate stronger risk signals. This is "
            "useful for seeing whether a jurisdiction's score is broad-based or driven "
            "by one or two specific layers."
        ),
    )

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "market_vs_financial_crime_risk.png",
        heading="Market Stress vs Financial Crime Exposure",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "Each point compares two different risk dimensions. Jurisdictions farther "
            "to the right show higher market stress, while jurisdictions higher on the "
            "chart show higher financial crime exposure. Outliers help identify where "
            "different risk pressures may overlap."
        ),
    )

    story.append(PageBreak())

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "governance_vs_sanctions_risk.png",
        heading="Top Sanctions / Geopolitical Risk Jurisdictions",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "This chart ranks jurisdictions by the sanctions/geopolitical risk layer. "
            "Longer bars indicate stronger geopolitical or sanctions-related pressure "
            "within the model. Use this chart to understand which jurisdictions are "
            "driving that specific layer rather than reading it as a full composite ranking."
        ),
    )

    story.append(PageBreak())

    story.append(Paragraph("Scenario Analysis Summary", heading_style))
    _add_how_to_read(
        story,
        "Scenario analysis does not forecast the future. It applies stress assumptions "
        "to the model layers to show which scenarios place the most pressure on the "
        "overall model. Average score shows broad model impact, max score shows the "
        "highest jurisdiction score under that scenario, and elevated/high counts show "
        "how many jurisdictions cross higher risk bands.",
        body_style,
    )
    story.append(
        Paragraph(
            "Scenario analysis applies stress multipliers to the baseline risk layers. "
            "These scenarios are not forecasts. They help compare how the model behaves "
            "under different financial-sector pressure conditions.",
            body_style,
        )
    )
    story.append(
        _add_table(
            build_scenario_table(scenario_summary),
            col_widths=[
                1.5 * inch,
                0.8 * inch,
                0.8 * inch,
                0.8 * inch,
                0.8 * inch,
                0.9 * inch,
            ],
        )
    )

    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Monte Carlo Robustness Summary", heading_style))
    _add_how_to_read(
        story,
        "Monte Carlo testing asks whether the results are stable when model inputs "
        "are slightly perturbed. Mean score shows the average simulated score, standard "
        "deviation shows score uncertainty, mean rank shows the average simulated "
        "position, and rank volatility shows how much ranking movement occurred.",
        body_style,
    )
    story.append(
        Paragraph(
            "Monte Carlo testing perturbs risk-layer scores with random noise to test "
            "whether rankings and risk bands remain stable under uncertainty. It is a "
            "robustness test, not a prediction model. Rank volatility shows how much "
            "a jurisdiction's simulated rank moves across repeated runs.",
            body_style,
        )
    )
    story.append(
        _add_table(
            build_monte_carlo_table(monte_carlo_summary),
            col_widths=[
                0.55 * inch,
                1.0 * inch,
                0.75 * inch,
                0.65 * inch,
                0.65 * inch,
                0.65 * inch,
                0.85 * inch,
            ],
        )
    )

    story.append(PageBreak())

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "monte_carlo_score_distribution.png",
        heading="Monte Carlo Score Distribution",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "This chart shows the spread of simulated scores across repeated model runs. "
            "A tighter distribution suggests more stable scoring assumptions, while a "
            "wider or multi-peaked distribution suggests more uncertainty across the "
            "jurisdictions and layers."
        ),
    )

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "monte_carlo_rank_stability.png",
        heading="Monte Carlo Rank Stability",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "Lower average simulated rank means a jurisdiction stayed closer to the top "
            "of the ranking across repeated simulations. This chart helps distinguish "
            "jurisdictions that consistently rank high from those that move more under "
            "uncertainty."
        ),
    )

    story.append(PageBreak())

    _add_chart_if_exists(
        story=story,
        chart_path=CHARTS_DIR / "monte_carlo_rank_volatility.png",
        heading="Monte Carlo Rank Volatility",
        heading_style=heading_style,
        body_style=body_style,
        how_to_read=(
            "Rank volatility measures movement in simulated rank. Higher volatility "
            "means the jurisdiction's rank moved more across repeated simulations. "
            "That does not necessarily mean higher risk; it means the ranking is less "
            "stable under uncertainty."
        ),
    )

    story.append(Paragraph("Methodology", heading_style))
    story.append(
        Paragraph(
            "The model scores jurisdictions across six core layers: market stress, "
            "financial crime exposure, governance/regulatory risk, banking/macro stress, "
            "sanctions/geopolitical risk, and cyber/operational risk. The baseline composite "
            "uses weighted 0-100 scores. The current version integrates live World Bank "
            "macro/governance data, FATF/sanctions reference adjustments, public market-data "
            "stress signals, and country-level ACLED event-data signals. Monte Carlo testing "
            "and scenario analysis are used to assess robustness and stress sensitivity. "
            "Outputs should be interpreted as directional public-source indicators, not "
            "definitive legal, compliance, investment, or operational conclusions.",
            small_style,
        )
    )

    doc.build(story)

    return output_path