"""Quantvesting presentation helpers.

The engine returns structured pandas DataFrames/dicts. This module is only a
presentation adapter, allowing the same engine to feed Jupyter/Colab today and
an API/Web UI later.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import math

from IPython.display import Markdown, display


IST = ZoneInfo("Asia/Kolkata")


# -----------------------------------------------------------------------------
# Notebook presentation contracts
# -----------------------------------------------------------------------------
# These are deliberately presentation-only. The engine continues to return its
# complete structured output, while notebooks can choose the concise views
# that are useful for interactive analysis.
PROSPECT_DISPLAY_COLUMNS = [
    "Symbol", "FTT", "Dev%_200", "Dev%_PE", "Spread%", "Conviction",
    "Cyclical", "RSI_14", "RSP", "FTT%", "ATH%", "Gained%", "CumlRnk",
    "ROE%/PE", "Criteria", "Strategy", "Category", "InFolio",
]

PORTFOLIO_DISPLAY_COLUMNS = [
    "Symbol", "Today P/L%", "Current P/L%", "FTT%", "OTT%", "FTT Amt",
    "Current P/L", "Current", "FTT", "Dev%_PE", "RSI_14", "Conviction",
    "Spread%", "CumlRnk", "RRR Ind", "CurrAlloc%", "Gained%", "Criteria",
    "Strategy", "Category",
]


def get_run_datetime():
    return datetime.now(IST)


def get_run_datetime_string():
    return get_run_datetime().strftime("%Y-%m-%d %H:%M:%S")


def format_amount(number):
    """Format Indian currency values into readable K/L/C notation."""
    if number is None:
        return "0.00"

    try:
        value = float(number)
    except (TypeError, ValueError):
        return "0.00"

    if value != value:  # NaN
        return "N/A"

    abs_number = abs(value)
    if abs_number >= 1_00_00_000:
        return f"{value / 1_00_00_000:.2f} C"
    if abs_number >= 1_00_000:
        return f"{value / 1_00_000:.2f} L"
    if abs_number >= 1_000:
        return f"{value / 1_000:.2f} K"
    return f"{value:.2f}"


def format_run_summary(summary):
    """Return the compact portfolio run summary as Markdown.

    Example
    -------
    ## Run date time (IST): 2026-08-08 15:13:55

    Deployed:  1.46 C
    Current:  1.62 C
    CAGR/XIRR %: 4.66%
    """
    run_datetime = summary.get("run_datetime", get_run_datetime_string())

    # ``initial_investment`` is the canonical engine field. ``deployed`` and
    # ``invested`` remain supported for compatibility with earlier snapshots.
    deployed = summary.get(
        "deployed",
        summary.get("initial_investment", summary.get("invested", 0)),
    )
    current = summary.get("current", 0)
    cagr_xirr = summary.get("cagr_xirr")

    try:
        cagr_value = float(cagr_xirr)
        cagr_text = (
            "N/A"
            if not math.isfinite(cagr_value)
            else f"{cagr_value:.2f}%"
        )
    except (TypeError, ValueError):
        cagr_text = "N/A"

    return (
        f"## Run date time (IST): {run_datetime}\n\n"
        f"Deployed:  {format_amount(deployed)}  \n"
        f"Current:  {format_amount(current)}  \n"
        f"CAGR/XIRR %: {cagr_text}"
    )


def display_run_summary(summary):
    """Display the compact portfolio run summary in Jupyter/Colab."""
    display(Markdown(format_run_summary(summary)))


def _select_display_columns(df, columns):
    """Return requested columns that exist, preserving requested order."""
    if columns is None:
        return df.copy()

    missing = [column for column in columns if column not in df.columns]
    if missing:
        # Do not silently hide a broken presentation contract. This catches
        # engine/schema changes early while still allowing optional columns in
        # future versions if the caller chooses to pass a filtered list.
        raise KeyError(
            "Requested display columns are missing from DataFrame: "
            f"{missing}"
        )

    return df.loc[:, columns].copy()


def display_dataframe(
    df,
    columns=None,
    sort_by=None,
    ascending=True,
):
    """Display a DataFrame interactively in Jupyter/Colab.

    Parameters
    ----------
    df : pandas.DataFrame
        Source dataframe returned by the engine.
    columns : list[str], optional
        Presentation columns and their exact display order.
    sort_by : str, optional
        Column used for interactive-view sorting.
    ascending : bool, default=True
        Sort direction.

    Outside Colab, this falls back to normal IPython display.
    """
    display_df = _select_display_columns(df, columns)

    if sort_by is not None and sort_by in display_df.columns:
        display_df = display_df.sort_values(
            by=sort_by,
            ascending=ascending,
        )

    try:
        from google.colab import data_table
        display(data_table.DataTable(display_df, include_index=False))
    except ImportError:
        display(display_df)


def display_portfolio_category_chart(
    df_portfolio,
    category_column="Category",
    value_column="Current",
    title="Category Current Distribution",
):
    """Display a donut chart of current portfolio value by category.

    This is a Jupyter presentation helper only. It uses the already-calculated
    ``Current`` portfolio values from the engine and performs no investment
    calculations beyond grouping them for display.
    """
    import matplotlib.pyplot as plt

    required = {category_column, value_column}
    missing = required.difference(df_portfolio.columns)
    if missing:
        raise KeyError(
            "Portfolio category chart is missing columns: "
            f"{sorted(missing)}"
        )

    chart_df = (
        df_portfolio[[category_column, value_column]]
        .copy()
    )
    chart_df[category_column] = (
        chart_df[category_column]
        .fillna("Unclassified")
        .astype(str)
    )
    chart_df[value_column] = chart_df[value_column].fillna(0)

    distribution = (
        chart_df.groupby(category_column, sort=False)[value_column]
        .sum()
        .sort_values(ascending=False)
    )

    distribution = distribution[distribution > 0]

    if distribution.empty:
        raise ValueError("No positive portfolio values available for chart.")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        distribution.values,
        labels=distribution.index,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"width": 0.42},
    )
    ax.set_title(title)
    ax.axis("equal")
    plt.tight_layout()
    display(fig)
    plt.close(fig)

    return distribution


def summary_to_dict(summary):
    """Return a plain dictionary suitable for a future API response."""
    return dict(summary)


def format_validation_report(report):
    """Return a compact, presentation-neutral Markdown quality summary."""
    report = report or {}
    status = report.get("status", "SUCCESS")
    warnings = report.get("warnings", [])
    errors = report.get("errors", [])
    info = report.get("info", [])

    lines = [
        "### Data Quality",
        "",
        f"- Status: **{status}**",
        f"- Critical errors: **{len(errors)}**",
        f"- Warnings: **{len(warnings)}**",
        f"- Informational: **{len(info)}**",
    ]
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- ⚠ {message}" for message in warnings)
    if errors:
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"- ❌ {message}" for message in errors)
    return "\n".join(lines)
