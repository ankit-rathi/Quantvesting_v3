# Quantvesting — Product-ready engine v0.5 (Phase B)

Quantvesting is being productised from an interactive Google Colab/Jupyter workflow into a reusable investment-analysis engine.

> **Philosophy:** peaceful investing using quants/data.

> **Core problem:** find high-quality Indian businesses trading below intrinsic value.

The current engine remains notebook-first and CSV-backed, but its internal boundaries are now designed so the same calculation engine can later serve a web/mobile product and PostgreSQL without rewriting the investment logic.

## Current architecture

```text
                         Quantvesting
                              |
              +---------------+---------------+
              |                               |
              v                               v
       Shared Market Data              User Portfolio Data
       market_data/                    portfolio_data/<id>/
              |                               |
              +---------------+---------------+
                              |
                              v
                    Quantvesting Engine
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
     Prospects           Portfolio           Decisions
          |                   |                   |
          +-------------------+-------------------+
                              |
                       Validation / Run Context
                              |
                         Repository layer
                              |
                 +------------+------------+
                 |                         |
                 v                         v
              CSV files             Future PostgreSQL
                              |
                              v
                 Reporting / Jupyter today
                         Web/API later
```

## Repository structure

```text
quantvesting_v3/
|
+-- config/
|   +-- strategy.yaml
|
+-- market_data/                       # shared Quantvesting data
|   +-- myProspectsScrips.csv
|   +-- myScreenerDB.csv
|   +-- myProspects-Momentum.csv
|   +-- myScreenerDB.xlsx
|
+-- portfolio_data/
|   +-- ankit/
|       +-- myPortfolioStocks.csv
|       +-- myInvestments.csv
|       +-- myPortfolioAmts.json
|       +-- myPortfolioDB.csv
|       +-- myStocks-XIRR.csv
|       +-- myRuns.csv                 # Phase-B run manifests
|
+-- portfolio_template/
|   +-- ...
|
+-- src/quantvesting/
|   +-- data.py
|   +-- ingestion.py
|   +-- validation.py
|   +-- run_context.py
|   +-- repositories.py
|   +-- features.py
|   +-- technical.py
|   +-- prospects.py
|   +-- portfolio.py
|   +-- decisions.py
|   +-- reporting.py
|   +-- __init__.py
|
+-- notebooks/
|   +-- 01_prospect_analysis.ipynb
|   +-- 02_portfolio_analysis.ipynb
|   +-- 03_quantvesting_run.ipynb
|
+-- tests/
+-- PHASE_A.md
+-- PHASE_B.md
```

## Phase B capabilities

### Portfolio identity

Every user portfolio has a `portfolio_id`. If omitted, it is inferred from the portfolio folder name.

```text
portfolio_data/
    ankit/
    friend_001/
    friend_002/
```

No investment-engine code needs to change for another portfolio.

### Run identity

Every analysis execution has a unique `run_id`.

```text
run_20260815_155936_f8372152
```

The same run ID can be shared by prospect and portfolio analysis in an end-to-end notebook execution.

### Strategy version

The strategy version comes from `config/strategy.yaml`:

```yaml
strategy:
  version: "0.4"
```

Phase B records it with every run but does not change the current methodology.

### Run manifest

Each portfolio folder can contain `myRuns.csv`. It records the execution context required to understand and reproduce a result:

- `run_id`
- `portfolio_id`
- `analysis_type`
- `run_datetime`
- `strategy_version`
- `engine_version`
- `config_hash`
- market-data fingerprints
- portfolio-data fingerprints
- `eod`
- `status`
- `reproducibility_hash`

### Data validation

Before calculations, the engine validates the structural data contract:

- required columns exist
- required datasets are non-empty
- security-level Prospects and Screener data have unique symbols
- numeric fields are numeric
- portfolio shares and average cost are not negative

Portfolio holdings are deliberately allowed to contain multiple rows for the same symbol because DM/SV or future accounts can hold the same security.

### Reproducibility

A run records deterministic SHA-256 fingerprints of the relevant input DataFrames and configuration. This means a future API/UI can answer:

> Which strategy, data and configuration produced this result?

## EOD snapshot persistence

`myPortfolioDB.csv` is the portfolio-level historical EOD result.

When `eod=True`:

1. the current IST calendar date is used;
2. legacy date formats are parsed;
3. all existing rows for that calendar date are removed;
4. the final snapshot is inserted;
5. the complete history is sorted chronologically;
6. dates are written in `DD-MM-YYYY` format.

This fixes the previous issue where `2026-08-15` and `15-08-2026` could be treated as different dates.

## Screener ingestion

When `REFRESH_SCREENER=True`:

```text
myScreenerDB.xlsx
       |
       v
extract + normalise
       |
       v
latest rows by Symbol
       |
       +---- replace matching old CSV rows
       |
       +---- retain older securities not in XLSX
       v
myScreenerDB.csv
```

The XLSX is authoritative for symbols it contains. Existing CSV duplicates are also removed during ingestion.

## Notebook workflow

### Prospect analysis

```python
market_data = load_market_data(MARKET_DATA_DIR)
portfolio_data = load_portfolio_data(PORTFOLIO_DATA_DIR, portfolio_id=PORTFOLIO_ID)

qv = Quantvesting(config)

df_prospects = qv.prospects(
    market_data,
    portfolio_data=portfolio_data,
    include_portfolio=True,
    portfolio_id=PORTFOLIO_ID,
    run_id=RUN_ID,
)
```

### Portfolio analysis

```python
df_portfolio, portfolio_summary = qv.portfolio(
    market_data,
    portfolio_data=portfolio_data,
    eod=EOD_RUN,
    portfolio_id=PORTFOLIO_ID,
    run_id=RUN_ID,
)
```

### Reporting

The engine returns structured results. Jupyter uses presentation helpers for:

- interactive DataTables
- compact portfolio summary
- category-current donut chart

The same structured objects are suitable for a future API.

## Decision layer

Current transparent baseline actions remain:

- Portfolio: `EXIT_TARGET` when `Current >= FTT`, otherwise `HOLD`.
- Prospects: top-N by `CumlRnk` are `BUY_CANDIDATE`, otherwise `WATCHLIST`.

These are deliberately separated from the analytical engine so the decision methodology can evolve independently.

## Roadmap

```text
PHASE A — Foundation
[x] Screener XLSX ingestion
[x] EOD snapshot persistence
[x] Repository abstraction
[x] portfolio_id / run_id awareness

PHASE B — Reproducibility
[x] Historical run tracking
[x] Strategy version tracking
[x] Data validation
[x] Reproducible runs
[x] EOD date normalization/sorting fix

PHASE C — Product backend
[ ] PostgreSQL repositories
[ ] FastAPI
[ ] Web UI

PHASE D — Commercial product
[ ] Authentication
[ ] User onboarding
[ ] Subscription
[ ] Mobile
```

## PostgreSQL / Web readiness

The current engine deliberately uses repository contracts:

```text
Jupyter / Web API / Mobile
            |
            v
    Quantvesting facade
            |
            v
 Engine + validation + runs
            |
            v
   Repository interfaces
        /         \
       v           v
     CSV       PostgreSQL
```

The calculation modules should not need to know whether data came from CSV or PostgreSQL. Phase C therefore focuses on implementing new repository/API adapters rather than rewriting the investment engine.
