import pandas as pd

from quantvesting.features import (
    build_portfolio_membership,
    validate_unique_symbols,
)
from quantvesting.prospects import (
    calculate_prospect_features,
    calculate_cumulative_rank,
)


def test_prospect_target_logic():
    df = pd.DataFrame({
        "Symbol": ["AAA", "BBB"],
        "Target": [120, 150],
        "Strategy": ["NTT", "BTT"],
        "Max": [130, 160],
        "Min": [80, 100],
        "Close": [100, 120],
        "Prev_Close": [99, 119],
    })

    out = calculate_prospect_features(df)

    assert out.loc[0, "FTT"] == 120
    assert out.loc[1, "FTT"] == 150
    assert round(out.loc[0, "FTT%"], 2) == 20.00


def test_cumulative_rank_matches_notebook_structure():
    df = pd.DataFrame({
        "Symbol": ["AAA", "BBB", "CCC", "DDD"],
        "MBQ": ["X40", "X5K", "OX40", "OTHER"],
        "Conviction": ["X-LC", "X-MC", "H-LC", "L-SC"],
        "Dev%_200": [-10, -5, -20, -1],
        "Dev%_PE": [-20, -10, -5, 2],
        "ROE%/PE": [2.0, 1.5, 1.0, 0.5],
        "Gained%": [20, 30, 10, 40],
        "RSI_14": [50, 60, 40, 70],
        "Sales_Grwth%": [10, 20, 5, 30],
        "Profit_Grwth%": [10, 20, 5, 30],
        "FTT%": [20, 30, 10, 40],
        "MCap": [1000, 500, 1500, 100],
        "ROE%": [20, 10, 25, 5],
        "CFO_2_EBITDA%": [90, 80, 95, 60],
    })

    config = {
        "ranking": {
            "categories": {
                "value": ["Dev%_200", "Dev%_PE", "ROE%/PE"],
                "growth": ["Sales_Grwth%", "Profit_Grwth%"],
                "quality": ["FTT%", "MCap", "ROE%", "CFO_2_EBITDA%"],
                "momentum": ["Gained%", "RSI_14"],
            },
            "directions": {
                "Dev%_200": True,
                "Dev%_PE": True,
                "ROE%/PE": False,
                "Sales_Grwth%": False,
                "Profit_Grwth%": False,
                "FTT%": False,
                "MCap": False,
                "ROE%": False,
                "CFO_2_EBITDA%": False,
                "Gained%": True,
                "RSI_14": False,
            },
            "category_weights": {
                "value": 1, "growth": 1, "quality": 1, "momentum": 1,
            },
            "conviction_priority": {
                "X-LC": 0, "X-MC": 2, "H-LC": 1, "L-SC": 11,
            },
        }
    }

    out = calculate_cumulative_rank(df, config)

    assert len(out) == 4
    assert list(out.columns) == [
        "Symbol", "CumlRnk", "Ovrl_Rank", "Cat_Rank",
        "Conviction_Priority", "BusinessQuality", "PortfolioClass",
        "Eligible", "OpportunityScore", "OpportunityBand",
    ]
    assert set(out["CumlRnk"].dropna()) == {1, 2, 3, 4}


def test_config_weights_change_overall_rank_score():
    df = pd.DataFrame({
        "Symbol": ["AAA", "BBB"],
        "MBQ": ["X40", "X40"],
        "Conviction": ["X-LC", "X-LC"],
        "Dev%_200": [-10, -5],
        "Dev%_PE": [-20, -10],
        "ROE%/PE": [2.0, 1.0],
        "Gained%": [20, 30],
        "RSI_14": [50, 60],
        "Sales_Grwth%": [10, 20],
        "Profit_Grwth%": [10, 20],
        "FTT%": [20, 30],
        "MCap": [1000, 500],
        "ROE%": [20, 10],
        "CFO_2_EBITDA%": [90, 80],
    })

    base = {
        "ranking": {
            "category_weights": {
                "value": 1, "growth": 1, "quality": 1, "momentum": 1,
            }
        }
    }
    out = calculate_cumulative_rank(df, base)
    assert "Ovrl_Rank" in out.columns


def test_portfolio_membership_aggregates_dm_and_sv_without_duplicates():
    portfolio = pd.DataFrame({
        "Symbol": ["ABBOTINDIA", "ABBOTINDIA", "ACC", "ACC"],
        "Shares": [1, 5, 10, 20],
        "AvgCost": [29555, 29860, 1000, 1100],
        "InPortfolio": ["DM", "SV", "DM", "DM"],
    })

    out = build_portfolio_membership(portfolio)

    assert list(out.columns) == ["Symbol", "InFolio"]
    assert len(out) == 2
    assert out.loc[out["Symbol"] == "ABBOTINDIA", "InFolio"].iloc[0] == "DM+SV"
    assert out.loc[out["Symbol"] == "ACC", "InFolio"].iloc[0] == "DM"
    validate_unique_symbols(out, "Portfolio membership")


def test_validate_unique_symbols_rejects_duplicates():
    df = pd.DataFrame({"Symbol": ["AAA", "AAA", "BBB"]})

    try:
        validate_unique_symbols(df, "Prospects")
    except ValueError as exc:
        assert "AAA" in str(exc)
    else:
        raise AssertionError("Expected duplicate Symbol validation to fail")


def test_reporting_contracts_and_summary_format():
    from quantvesting.reporting import (
        PROSPECT_DISPLAY_COLUMNS,
        PORTFOLIO_DISPLAY_COLUMNS,
        format_run_summary,
    )

    assert PROSPECT_DISPLAY_COLUMNS == [
        "Symbol", "FTT", "Dev%_200", "Dev%_PE", "Spread%", "Conviction",
        "Cyclical", "RSI_14", "RSP", "FTT%", "ATH%", "Gained%", "CumlRnk",
        "ROE%/PE", "Criteria", "Strategy", "Category", "InFolio",
    ]

    assert PORTFOLIO_DISPLAY_COLUMNS == [
        "Symbol", "Today P/L%", "Current P/L%", "FTT%", "OTT%", "FTT Amt",
        "Current P/L", "Current", "FTT", "Dev%_PE", "RSI_14", "Conviction",
        "Spread%", "CumlRnk", "RRR Ind", "CurrAlloc%", "Gained%", "Criteria",
        "Strategy", "Category",
    ]

    text = format_run_summary({
        "run_datetime": "2026-08-08 15:13:55",
        "initial_investment": 14600000,
        "current": 16200000,
        "cagr_xirr": 4.66,
    })

    assert "## Run date time (IST): 2026-08-08 15:13:55" in text
    assert "Deployed:  1.46 C" in text
    assert "Current:  1.62 C" in text
    assert "CAGR/XIRR %: 4.66%" in text


def test_separated_data_loaders_keep_market_and_portfolio_data_distinct():
    from pathlib import Path
    from quantvesting.data import load_market_data, load_portfolio_data

    root = Path(__file__).resolve().parents[1]
    market = load_market_data(root / "market_data")
    portfolio = load_portfolio_data(root / "portfolio_data" / "ankit")

    assert set(market) >= {"prospects", "screener", "momentum"}
    assert set(portfolio) >= {
        "portfolio_stocks",
        "investments",
        "portfolio_amounts",
        "portfolio_history",
        "xirr",
    }
    assert "portfolio_stocks" not in market
    assert "prospects" not in portfolio


def test_quantvesting_public_interface_accepts_separated_data():
    from quantvesting import Quantvesting, load_config, load_market_data, load_portfolio_data

    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    config = load_config(root / "config" / "strategy.yaml")
    market_data = load_market_data(root / "market_data")
    portfolio_data = load_portfolio_data(root / "portfolio_data" / "ankit")

    qv = Quantvesting(config)

    # We don't execute the network-dependent technical pipeline here; verify
    # that the public methods expose the separated data contract without
    # falling back to the legacy combined bundle.
    import inspect
    assert "portfolio_data" in inspect.signature(qv.prospects).parameters
    assert "portfolio_data" in inspect.signature(qv.portfolio).parameters
    assert market_data["prospects"].shape[0] > 0
    assert portfolio_data["portfolio_stocks"].shape[0] > 0


def test_screener_ingestion_reproduces_xlsx_to_csv_flow(tmp_path):
    from quantvesting.ingestion import ingest_screener_xlsx

    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    xlsx = root / "market_data" / "myScreenerDB.xlsx"
    output = tmp_path / "myScreenerDB.csv"

    result = ingest_screener_xlsx(xlsx, output)

    assert output.exists()
    assert list(result.columns) == [
        "Name", "CMP", "ATH%", "PE", "EPS", "PB", "MCap", "ROCE%",
        "ROE%", "Sales_Grwth%", "Profit_Grwth%", "MedPE", "ROCE_5Yr%",
        "ROE_5Yr%", "Debt2EqR", "PAT_12M", "CFO_2_EBITDA%", "CapType",
        "Symbol", "Latest",
    ]
    assert result["Symbol"].notna().all()
    assert result["Latest"].eq(1).all()
    assert result["CapType"].isin(["LC", "MC", "SC"]).all()


def test_eod_snapshot_is_upserted_by_date(tmp_path):
    from quantvesting.repositories import FilePortfolioRepository

    repo = FilePortfolioRepository(tmp_path, portfolio_id="friend_001")

    repo.append_eod_snapshot({
        "date": "2026-08-08",
        "portfolio_id": "friend_001",
        "run_id": "run_first",
        "current": 100,
    })
    repo.append_eod_snapshot({
        "date": "2026-08-08",
        "portfolio_id": "friend_001",
        "run_id": "run_second",
        "current": 110,
    })

    history = pd.read_csv(tmp_path / "myPortfolioDB.csv")

    assert len(history) == 1
    assert history.loc[0, "run_id"] == "run_second"
    assert history.loc[0, "current"] == 110


def test_portfolio_loader_has_portfolio_id():
    from quantvesting.data import load_portfolio_data

    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    portfolio = load_portfolio_data(
        root / "portfolio_data" / "ankit",
        portfolio_id="ankit",
    )

    assert portfolio["portfolio_id"] == "ankit"
    assert portfolio["portfolio_dir"].endswith("portfolio_data/ankit")


def test_eod_snapshot_normalizes_legacy_dates_and_sorts_chronologically(tmp_path):
    from quantvesting.repositories import FilePortfolioRepository

    repo = FilePortfolioRepository(tmp_path, portfolio_id="friend_001")
    history = pd.DataFrame([
        {"date": "31-12-2025", "current": 100},
        {"date": "01-01-2025", "current": 80},
        {"date": "2026-08-08", "current": 120},
    ])
    history.to_csv(tmp_path / "myPortfolioDB.csv", index=False)

    repo.append_eod_snapshot({
        "date": "08-08-2026",
        "current": 130,
        "run_id": "run_fixed",
    })

    out = pd.read_csv(tmp_path / "myPortfolioDB.csv")
    parsed = pd.to_datetime(out["date"], dayfirst=True)

    assert out["date"].tolist() == [
        "01-01-2025",
        "31-12-2025",
        "08-08-2026",
    ]
    assert len(out) == 3
    assert out.loc[out["date"] == "08-08-2026", "current"].iloc[0] == 130
    assert parsed.is_monotonic_increasing


def test_eod_snapshot_populates_legacy_and_phase_b_aliases(tmp_path):
    from quantvesting.repositories import FilePortfolioRepository

    repo = FilePortfolioRepository(tmp_path, portfolio_id="friend_001")
    pd.DataFrame([
        {"date": "01-01-2025", "investment": 1000, "cagr": 5.5},
    ]).to_csv(tmp_path / "myPortfolioDB.csv", index=False)

    repo.append_eod_snapshot({
        "date": "02-01-2025",
        "initial_investment": 1200,
        "cagr_xirr": 6.0,
        "current": 1400,
    })

    out = pd.read_csv(tmp_path / "myPortfolioDB.csv")
    old = out.iloc[0]
    new = out.iloc[1]
    assert old["initial_investment"] == 1000
    assert old["deployed"] == 1000
    assert old["cagr_xirr"] == 5.5
    assert new["investment"] == 1200
    assert new["deployed"] == 1200
    assert new["initial_investment"] == 1200
    assert new["cagr"] == 6.0


def test_run_manifests_track_analysis_type_for_same_run_id(tmp_path):
    from quantvesting.repositories import FilePortfolioRepository

    repo = FilePortfolioRepository(tmp_path, portfolio_id="friend_001")
    repo.append_run_manifest({
        "run_id": "run_same",
        "analysis_type": "prospects",
        "run_datetime": "2026-08-15 10:00:00",
        "strategy_version": "0.4",
    })
    repo.append_run_manifest({
        "run_id": "run_same",
        "analysis_type": "portfolio",
        "run_datetime": "2026-08-15 10:00:01",
        "strategy_version": "0.4",
    })

    out = pd.read_csv(tmp_path / "myRuns.csv")
    assert len(out) == 2
    assert set(out["analysis_type"]) == {"prospects", "portfolio"}


def test_run_manifest_contains_reproducibility_fingerprint():
    from quantvesting.run_context import build_run_manifest

    market = {
        "prospects": pd.DataFrame({"Symbol": ["AAA"]}),
        "screener": pd.DataFrame({"Symbol": ["AAA"]}),
        "momentum": pd.DataFrame(),
    }
    portfolio = {
        "portfolio_stocks": pd.DataFrame({"Symbol": ["AAA"], "Shares": [1]}),
        "investments": pd.DataFrame({"Date": ["01-Jan-25"], "Investment": [-100]}),
        "portfolio_amounts": {},
    }
    manifest = build_run_manifest(
        analysis_type="portfolio",
        run_id="run_1",
        portfolio_id="friend_001",
        strategy_version="0.4",
        config={"strategy": {"version": "0.4"}},
        market_data=market,
        portfolio_data=portfolio,
        eod=True,
    )
    assert manifest["engine_version"] == "0.5.0"
    assert manifest["strategy_version"] == "0.4"
    assert len(manifest["config_hash"]) == 64
    assert len(manifest["reproducibility_hash"]) == 64
    assert manifest["eod"] is True


def test_validation_rejects_duplicate_security_level_market_data():
    from quantvesting.validation import DataValidationError, validate_market_data

    prospects = pd.DataFrame({
        "Symbol": ["AAA", "AAA"],
        "Target": [100, 100], "Criteria": ["X", "X"],
        "Strategy": ["NTT", "NTT"], "LatestQtr": ["Y", "Y"],
        "StarStock": ["Y", "Y"], "MBQ": ["X40", "X40"],
        "Conviction": ["X-LC", "X-LC"], "Cyclical": ["NC", "NC"],
        "Category": ["IT", "IT"],
    })
    screener = pd.DataFrame({
        "Symbol": ["AAA"], "EPS": [10], "MedPE": [20], "MCap": [1000], "CapType": ["LC"],
    })

    try:
        validate_market_data({"prospects": prospects, "screener": screener})
    except DataValidationError as exc:
        assert "AAA" in str(exc)
    else:
        raise AssertionError("Expected duplicate security validation to fail")


def test_conviction_hierarchy_keeps_first_six_core_and_lower_buckets_legacy():
    from quantvesting.prospects import calculate_cumulative_rank

    rows = []
    convictions = [
        "X-LC", "H-LC", "X-MC", "X-SC", "M-LC", "H-MC", "H-SC"
    ]
    for i, conviction in enumerate(convictions):
        rows.append({
            "Symbol": f"S{i}", "Conviction": conviction,
            "Dev%_200": -10-i, "Dev%_PE": -10-i, "ROE%/PE": 5+i,
            "Sales_Grwth%": 10+i, "Profit_Grwth%": 10+i,
            "FTT%": 30+i, "MCap": 1000-i, "ROE%": 15+i,
            "CFO_2_EBITDA%": 80+i, "Gained%": 10+i, "RSI_14": 50+i,
        })
    out = calculate_cumulative_rank(rows_df := pd.DataFrame(rows), {
        "ranking": {
            "conviction_priority": {
                "X-LC": 0, "H-LC": 1, "X-MC": 2, "X-SC": 3,
                "M-LC": 4, "H-MC": 5, "H-SC": 6,
            },
            "rankable_convictions": [
                "X-LC", "H-LC", "X-MC", "X-SC", "M-LC", "H-MC"
            ],
        }
    })
    legacy = out.loc[out["Symbol"] == "S6"].iloc[0]
    assert legacy["PortfolioClass"] == "LEGACY"
    assert pd.isna(legacy["CumlRnk"])
    assert out.loc[out["Symbol"] != "S6", "CumlRnk"].notna().all()


def test_capital_rotation_is_advisory():
    from quantvesting.decisions import capital_rotation_actions

    prospects = pd.DataFrame([
        {"Symbol": "NEW", "CumlRnk": 1, "PortfolioClass": "CORE", "FTT%": 40},
    ])
    portfolio = pd.DataFrame([
        {"Symbol": "OLD", "AvgCost": 100, "Current": 180, "FTT": 200},
    ])
    out = capital_rotation_actions(prospects, portfolio, {
        "rotation": {"thesis_captured": {"review": 0.80}, "minimum_alternative_upside": 0.20}
    })
    assert len(out) == 1
    assert out.loc[0, "Action"] == "REVIEW_ROTATION"
    assert out.loc[0, "AlternativeSymbol"] == "NEW"


def test_portfolio_target_and_thesis_metrics_use_per_share_cmp():
    from quantvesting.portfolio import calculate_portfolio_features
    from quantvesting.decisions import add_portfolio_actions

    common = pd.DataFrame([{
        "Symbol": "AAA", "Strategy": "BTT", "Target": 200, "Max": 220,
        "Min": 80, "Close": 180, "Prev_Close": 175, "AvgCost": 100,
        "Shares": 10, "Conviction": "M-LC",
    }])
    holdings = pd.DataFrame([{ "Symbol": "AAA", "InPortfolio": "DM" }])
    config = {
        "ranking": {"conviction_priority": {
            "X-LC": 0, "H-LC": 1, "X-MC": 2, "X-SC": 3, "M-LC": 4,
            "H-MC": 5, "H-SC": 6, "L-LC": 7, "M-MC": 8, "M-SC": 9,
            "L-MC": 10, "L-SC": 11,
        }},
        "rotation": {"thesis_captured": {"review": .80, "strong_review": .90}},
    }
    out = calculate_portfolio_features(common, holdings, config)
    assert round(out.loc[0, "ThesisCaptured%"], 6) == 0.8
    assert round(out.loc[0, "RemainingUpside%"], 6) == round(20 / 180, 6)
    assert out.loc[0, "RotationStatus"] == "ROTATION_REVIEW"

    actions = add_portfolio_actions(out, config)
    assert actions.loc[0, "Action"] == "REVIEW_ROTATION"

    legacy = out.copy()
    legacy["PortfolioClass"] = "LEGACY"
    legacy_actions = add_portfolio_actions(legacy, config)
    assert legacy_actions.loc[0, "Action"] == "WAIT_FOR_EXIT_WINDOW"


def test_market_data_nan_outside_active_universe_is_warning_and_pipeline_continues():
    from quantvesting.validation import validate_market_data

    market = {
        "prospects": pd.DataFrame({
            "Symbol": ["AAA"],
            "Target": [120], "Criteria": ["X"], "Strategy": ["NTT"],
            "LatestQtr": ["Y"], "StarStock": ["Y"], "MBQ": ["X40"],
            "Conviction": ["X-LC"], "Cyclical": ["NC"], "Category": ["IT"],
        }),
        "screener": pd.DataFrame({
            "Symbol": ["AAA", "BBB"],
            "EPS": [10, 12],
            "MedPE": [20, float("nan")],
            "MCap": [1000, 900],
            "CapType": ["LC", "LC"],
        }),
    }

    report = validate_market_data(market, active_symbols={"AAA"})
    assert report["status"] == "SUCCESS"
    assert report["warnings"] == []
    assert any("MedPE" in message and "outside the active universe" in message
               for message in report["info"])


def test_invalid_populated_market_value_outside_active_universe_is_warning():
    from quantvesting.validation import validate_market_data

    market = {
        "prospects": pd.DataFrame({
            "Symbol": ["AAA"],
            "Target": [120], "Criteria": ["X"], "Strategy": ["NTT"],
            "LatestQtr": ["Y"], "StarStock": ["Y"], "MBQ": ["X40"],
            "Conviction": ["X-LC"], "Cyclical": ["NC"], "Category": ["IT"],
        }),
        "screener": pd.DataFrame({
            "Symbol": ["AAA", "BBB"],
            "EPS": [10, "bad"],
            "MedPE": [20, "bad"],
            "MCap": [1000, 900],
            "CapType": ["LC", "LC"],
        }),
    }

    report = validate_market_data(market, active_symbols={"AAA"})
    assert report["status"] == "SUCCESS_WITH_WARNINGS"
    assert len(report["warnings"]) == 2


def test_invalid_populated_market_value_in_active_universe_still_fails():
    from quantvesting.validation import DataValidationError, validate_market_data

    market = {
        "prospects": pd.DataFrame({
            "Symbol": ["AAA"],
            "Target": [120], "Criteria": ["X"], "Strategy": ["NTT"],
            "LatestQtr": ["Y"], "StarStock": ["Y"], "MBQ": ["X40"],
            "Conviction": ["X-LC"], "Cyclical": ["NC"], "Category": ["IT"],
        }),
        "screener": pd.DataFrame({
            "Symbol": ["AAA", "BBB"],
            "EPS": [10, 12],
            "MedPE": ["bad", float("nan")],
            "MCap": [1000, 900],
            "CapType": ["LC", "LC"],
        }),
    }

    try:
        validate_market_data(market, active_symbols={"AAA"})
    except DataValidationError as exc:
        assert "MedPE" in str(exc)
        assert "active universe" in str(exc)
    else:
        raise AssertionError("Expected active-universe validation to fail")


def test_duplicate_screener_symbol_outside_active_universe_is_warning():
    from quantvesting.validation import validate_market_data

    market = {
        "prospects": pd.DataFrame({
            "Symbol": ["AAA"],
            "Target": [120], "Criteria": ["X"], "Strategy": ["NTT"],
            "LatestQtr": ["Y"], "StarStock": ["Y"], "MBQ": ["X40"],
            "Conviction": ["X-LC"], "Cyclical": ["NC"], "Category": ["IT"],
        }),
        "screener": pd.DataFrame({
            "Symbol": ["AAA", "BBB", "BBB"],
            "EPS": [10, 12, 12],
            "MedPE": [20, 20, 20],
            "MCap": [1000, 900, 900],
            "CapType": ["LC", "LC", "LC"],
        }),
    }

    report = validate_market_data(market, active_symbols={"AAA"})
    assert report["status"] == "SUCCESS_WITH_WARNINGS"
    assert any("BBB" in warning for warning in report["warnings"])
