from __future__ import annotations

from pathlib import Path
from typing import Iterable

import openpyxl
import pandas as pd

from .repositories import FileMarketDataRepository


SCREENER_COLUMNS = [
    "Name", "CMP", "ATH%", "PE", "EPS", "PB", "MCap", "ROCE%",
    "ROE%", "Sales_Grwth%", "Profit_Grwth%", "MedPE", "ROCE_5Yr%",
    "ROE_5Yr%", "Debt2EqR", "PAT_12M", "CFO_2_EBITDA%", "CapType",
    "Symbol", "Latest",
]


def _get_link_if_exists(cell) -> str | None:
    try:
        return cell.hyperlink.target
    except AttributeError:
        return None


def extract_hyperlinks_from_xlsx(
    file_name,
    sheet_name: str = "data",
    columns_to_parse: Iterable[str] = ("Name",),
    row_header: int = 1,
) -> pd.DataFrame:
    """
    Read Screener XLSX data while extracting hyperlinks from selected cells.

    This is the notebook logic moved into the product/data-ingestion layer.
    ``row_header=1`` preserves the original Colab behaviour.
    """
    file_name = Path(file_name)
    df = pd.read_excel(file_name, sheet_name=sheet_name)

    workbook = openpyxl.load_workbook(
        file_name,
        read_only=False,
        data_only=False,
    )
    try:
        ws = workbook[sheet_name]

        for column in columns_to_parse:
            if column not in df.columns:
                raise ValueError(
                    f"Column '{column}' was not found in sheet '{sheet_name}'."
                )

            row_offset = row_header + 1
            column_index = list(df.columns).index(column) + 1

            df[column] = [
                _get_link_if_exists(
                    ws.cell(
                        row=row_offset + i,
                        column=column_index,
                    )
                )
                for i in range(len(df[column]))
            ]
    finally:
        workbook.close()

    return df


def _normalise_screener_symbols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the Screener workbook's positional columns into Quantvesting's
    canonical schema and derive Symbol from the hyperlink stored in ``Name``.

    This intentionally preserves the supplied notebook's positional mapping:
    the workbook's 18 columns are renamed to the first 18 canonical fields,
    then Symbol and Latest are added.
    """
    result = df.copy()

    if "Name" not in result.columns:
        raise ValueError("Screener data must contain a 'Name' column.")

    source_column_count = len(result.columns)
    if source_column_count != 18:
        raise ValueError(
            "Unexpected Screener XLSX schema. "
            f"Expected 18 source columns, found {source_column_count}."
        )

    # ``extract_hyperlinks_from_xlsx`` replaces Name with the URL, so the
    # symbol can be derived exactly as in the original notebook.
    result["Symbol"] = (
        result["Name"]
        .astype("string")
        .str.split("company/")
        .str[1]
        .str.split("/")
        .str[0]
    )
    result["Latest"] = 1

    # Preserve the original notebook's positional rename. In particular,
    # the workbook's ROE/PE column is historically carried into
    # ``ROCE_5Yr%`` in the CSV schema; changing that would alter existing
    # outputs.
    result.columns = SCREENER_COLUMNS

    return result.copy()


def update_cap_type_by_mcap(
    df: pd.DataFrame,
    large_cap_count: int = 100,
    mid_cap_count: int = 150,
) -> pd.DataFrame:
    """
    Reproduce the current Quantvesting cap classification.

    Highest MCap rows become LC, next MC, remaining SC.
    """
    result = df.copy()

    if "MCap" not in result.columns:
        raise ValueError("Screener data must contain 'MCap'.")

    result = result.sort_values(
        by="MCap",
        ascending=False,
        kind="stable",
    ).reset_index(drop=True)

    result["CapType"] = "SC"

    if large_cap_count > 0:
        result.loc[
            : large_cap_count - 1,
            "CapType",
        ] = "LC"

    if mid_cap_count > 0:
        result.loc[
            large_cap_count : large_cap_count + mid_cap_count - 1,
            "CapType",
        ] = "MC"

    return result


def ingest_screener_xlsx(
    xlsx_path,
    csv_path=None,
    *,
    sheet_name: str = "data",
    columns_to_parse: Iterable[str] = ("Name",),
    row_header: int = 1,
    large_cap_count: int = 100,
    mid_cap_count: int = 150,
    repository=None,
) -> pd.DataFrame:
    """
    Convert/merge Screener XLSX into the canonical myScreenerDB.csv.

    Behaviour intentionally matches the supplied notebook:
      1. Extract the latest XLSX rows and hyperlink-derived symbols.
      2. Keep existing CSV rows whose Symbol is not in the XLSX extract.
      3. Sort by MCap.
      4. Recalculate LC/MC/SC classification.
      5. Persist to CSV.

    The function returns the final DataFrame so the notebook can inspect it.
    """
    xlsx_path = Path(xlsx_path)

    if csv_path is None:
        csv_path = xlsx_path.with_suffix(".csv")
    csv_path = Path(csv_path)

    latest = extract_hyperlinks_from_xlsx(
        xlsx_path,
        sheet_name=sheet_name,
        columns_to_parse=columns_to_parse,
        row_header=row_header,
    )
    latest = _normalise_screener_symbols(latest)

    # The XLSX extract is authoritative for symbols present in the workbook.
    # If a workbook ever contains the same symbol more than once, keep the
    # last occurrence so one security cannot leak into the security-level
    # market dataset twice.
    latest = (
        latest.dropna(subset=["Symbol"])
        .drop_duplicates(subset=["Symbol"], keep="last")
        .reset_index(drop=True)
    )

    if repository is not None:
        existing = repository.load().get("screener", pd.DataFrame()).copy()
    elif csv_path.exists():
        existing = pd.read_csv(csv_path)
    else:
        existing = pd.DataFrame()

    if not existing.empty:
        # De-duplicate the persisted source first. Latest XLSX rows then
        # replace those symbols, while untouched historical securities remain.
        if "Symbol" in existing.columns:
            existing = (
                existing.dropna(subset=["Symbol"])
                .drop_duplicates(subset=["Symbol"], keep="last")
                .copy()
            )
        latest_symbols = latest["Symbol"].dropna().astype(str)
        existing = existing[
            ~existing["Symbol"].astype(str).isin(latest_symbols)
        ].copy()
        combined = pd.concat(
            [latest, existing],
            ignore_index=True,
            sort=False,
        )
    else:
        combined = latest.copy()

    # Make sure the canonical columns exist before classification.
    for column in SCREENER_COLUMNS:
        if column not in combined.columns:
            combined[column] = pd.NA

    combined = combined[SCREENER_COLUMNS].copy()
    combined = update_cap_type_by_mcap(
        combined,
        large_cap_count=large_cap_count,
        mid_cap_count=mid_cap_count,
    )

    if repository is not None:
        repository.save_screener(combined)
    else:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(csv_path, index=False)

    return combined


def ingest_screener_from_config(
    market_dir,
    config,
) -> pd.DataFrame:
    """Run Screener ingestion using the Phase A YAML configuration."""
    market_dir = Path(market_dir)
    cfg = config.get("ingestion", {}).get("screener", {})

    repository = FileMarketDataRepository(market_dir)

    return ingest_screener_xlsx(
        market_dir / cfg.get("xlsx_file", "myScreenerDB.xlsx"),
        market_dir / cfg.get("csv_file", "myScreenerDB.csv"),
        sheet_name=cfg.get("sheet_name", "data"),
        columns_to_parse=cfg.get("hyperlink_columns", ["Name"]),
        row_header=cfg.get("row_header", 1),
        large_cap_count=cfg.get("large_cap_count", 100),
        mid_cap_count=cfg.get("mid_cap_count", 150),
        repository=repository,
    )
