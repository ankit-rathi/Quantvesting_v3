# Quantvesting — Product-ready engine v0.4

Quantvesting is being productised from an interactive Google Colab/Jupyter
workflow into a reusable investment-analysis engine.

The key architectural boundary in v0.4 is:

> **Market/strategy data is shared and owned by Quantvesting. Portfolio data is owned by the individual user.**

This means a new user can provide their portfolio files in a folder and use
the same Quantvesting engine without changing the investment logic or copying
the shared market-data files into their portfolio folder.

## Architecture

```text
                         Quantvesting
                              |
              +---------------+---------------+
              |                               |
              v                               v
       Shared Market Data              User Portfolio Data
       market_data/                    portfolio_data/<user>/
              |                               |
              +---------------+---------------+
                              |
                              v
                    Quantvesting Engine
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
     prospects.py        portfolio.py        decisions.py
          |                   |                   |
          +-------------------+-------------------+
                              |
                         reporting.py
                              |
                    +---------+---------+
                    |                   |
                    v                   v
                 Jupyter            Future Web/API
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
|   +-- ankit/                          # current user's portfolio
|       +-- myPortfolioStocks.csv
|       +-- myInvestments.csv
|       +-- myPortfolioAmts.json
|       +-- myPortfolioDB.csv
|       +-- myStocks-XIRR.csv
|
+-- portfolio_template/                # copy for a new user
|   +-- portfolio_stocks.csv
|   +-- investments.csv
|   +-- portfolio_amounts.json
|   +-- portfolio_history.csv
|   +-- xirr.csv
|   +-- README.md
|
+-- data/                               # legacy single-directory compatibility
|
+-- src/quantvesting/
|   +-- data.py
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
```

The `data/` directory is retained only for backward compatibility with the
original notebook/data layout. New code should use `market_data/` and
`portfolio_data/<portfolio_id>/`.

## Data ownership model

### Shared Quantvesting data

These files are common to all users:

- `myProspectsScrips.csv`
- `myScreenerDB.csv`
- `myProspects-Momentum.csv`
- `myScreenerDB.xlsx` (supporting source/workbook)

They live under `market_data/`.

### User-owned data

Each user supplies:

- `myPortfolioStocks.csv`
- `myInvestments.csv`
- `myPortfolioAmts.json` (optional; defaults to zero amounts)
- `myPortfolioDB.csv` (optional history)
- `myStocks-XIRR.csv` (optional supporting file)

They live under a user-specific directory such as:

```text
portfolio_data/ankit/
```

A future web application can map this directory to an authenticated
`portfolio_id` without changing the engine.

## New data-loading API

Use the explicit loaders in new notebooks/application code:

```python
from quantvesting import (
    load_market_data,
    load_portfolio_data,
)

market_data = load_market_data(MARKET_DATA_DIR)
portfolio_data = load_portfolio_data(PORTFOLIO_DATA_DIR)
```

Or load both in one call:

```python
from quantvesting import load_quantvesting_data

market_data, portfolio_data = load_quantvesting_data(
    MARKET_DATA_DIR,
    PORTFOLIO_DATA_DIR,
)
```

For prospect analysis, `portfolio_data` can be `None` if the user wants
prospects without portfolio membership information.

## New user onboarding

A new user should not modify Python code.

1. Copy `portfolio_template/` to a user-specific location.
2. Fill in `portfolio_stocks.csv`.
3. Fill in `investments.csv`.
4. Fill optional portfolio amounts/history files if required.
5. Point `PORTFOLIO_DATA_DIR` in the notebook to that folder.
6. Run the same notebook.

For example:

```text
portfolio_data/
    friend_001/
        myPortfolioStocks.csv
        myInvestments.csv
        myPortfolioAmts.json
```

The shared `market_data/` remains unchanged.

## Portfolio vs security level

This distinction is important for the framework.

```text
Portfolio source
holding/account level
        |
        | ABBOTINDIA / DM
        | ABBOTINDIA / SV
        v
Portfolio analysis
aggregate shares + investment by Symbol
        |
        v
Security-level result
ABBOTINDIA
```

Prospect analysis is always security-level. Therefore portfolio membership is
aggregated before joining:

```text
ABBOTINDIA / DM
ABBOTINDIA / SV
       |
       v
ABBOTINDIA / DM+SV
       |
       v
Prospects
```

This prevents duplicate prospect rows when a stock exists in multiple
accounts.

The original holding-level records remain available to portfolio analysis,
so DM/SV shares and average costs continue to aggregate correctly.

Portfolio analysis is now account-label agnostic: DM/SV continue to work as
before, while future users can use other account labels without changing the
engine.

## Public engine interface

### Prospect analysis

```python
prospects = qv.prospects(
    market_data,
    portfolio_data=portfolio_data,
    include_portfolio=True,
)
```

Without portfolio information:

```python
prospects = qv.prospects(
    market_data,
    portfolio_data=None,
    include_portfolio=False,
)
```

### Portfolio analysis

```python
portfolio, summary = qv.portfolio(
    market_data,
    portfolio_data=portfolio_data,
)
```

The engine returns structured data only. It does not print or display results.

### Backward compatibility

The original API is still supported:

```python
from quantvesting import load_all_data

data = load_all_data("/path/to/old/data")

prospects = qv.prospects(data, include_portfolio=True)
portfolio, summary = qv.portfolio(data)
```

This allows existing notebooks/integrations to migrate gradually.

## Notebook presentation

The notebooks remain the primary interface until the Web UI/MVP stage.

Prospect display order:

```text
Symbol, FTT, Dev%_200, Dev%_PE, Spread%, Conviction, Cyclical,
RSI_14, RSP, FTT%, ATH%, Gained%, CumlRnk, ROE%/PE, Criteria,
Strategy, Category, InFolio
```

Portfolio display order:

```text
Symbol, Today P/L%, Current P/L%, FTT%, OTT%, FTT Amt, Current P/L,
Current, FTT, Dev%_PE, RSI_14, Conviction, Spread%, CumlRnk, RRR Ind,
CurrAlloc%, Gained%, Criteria, Strategy, Category
```

The portfolio notebook also renders:

- compact IST run summary
- Deployed / Current / CAGR-XIRR
- current-value category donut chart

These are presentation helpers in `reporting.py`, not investment logic.

## Prospect ranking

The ranking logic previously embedded in the prospect notebook is now in
`prospects.py`. It calculates:

- Value rank: `Dev%_200`, `Dev%_PE`, `ROE%/PE`
- Growth rank: `Sales_Grwth%`, `Profit_Grwth%`
- Quality rank: `FTT%`, `MCap`, `ROE%`, `CFO_2_EBITDA%`
- Momentum rank: `Gained%`, `RSI_14`
- Overall rank: sum of category scores
- Category rank: rank within `Conviction`
- Final `CumlRnk`: ordered by Conviction Priority and category rank

The defaults reproduce the supplied notebook methodology: equal category
weights and the explicit Conviction Priority map.

## Productisation boundary

The intended evolution is:

```text
Today

Jupyter -> Quantvesting Engine -> CSV/JSON + Yahoo Finance

Next

Jupyter -> Quantvesting Engine <- shared market data
                              <- user portfolio data

MVP

Jupyter / Web -> API -> Quantvesting Engine
                       |
              +--------+--------+
              |                 |
        Market Data        User Portfolio
```

The investment methodology should not move into the notebooks or UI. Those
layers should only supply inputs and present structured engine outputs.

## Development sequence

1. Validate engine output against the existing notebook.
2. Keep the market-data/user-portfolio boundary stable.
3. Freeze Quantvesting strategy versions.
4. Add golden-output/regression tests.
5. Formalise the decision engine.
6. Add historical recommendation/run tracking.
7. Expose the engine through an API.
8. Build the Web UI on top of the same public interface.
9. Add authentication, subscriptions and multi-user storage only after the
   engine is stable.


## Phase A — operationalisation

Phase A is implemented without changing the notebook-first workflow.

### 1. Screener XLSX ingestion

The notebook no longer needs to contain the XLSX-to-CSV transformation logic.
The same logic is available through:

```python
from quantvesting import Quantvesting, load_config

config = load_config("config/strategy.yaml")
qv = Quantvesting(config)

df_screener = qv.ingest_screener("market_data")
```

The ingestion:

1. reads `myScreenerDB.xlsx`
2. extracts Screener hyperlinks from `Name`
3. derives `Symbol`
4. merges with the existing `myScreenerDB.csv`
5. recalculates LC/MC/SC using market-cap ordering
6. writes the canonical `myScreenerDB.csv`

The workbook is still the source; the CSV is the engine-ready snapshot.

### 2. EOD snapshot persistence

Portfolio analysis now accepts:

```python
portfolio, summary = qv.portfolio(
    market_data,
    portfolio_data=portfolio_data,
    portfolio_id="ankit",
    run_id="run_...",
    eod=True,
)
```

When `eod=True`, the engine persists the final summary to:

```text
portfolio_data/<portfolio_id>/myPortfolioDB.csv
```

The same day's snapshot is replaced when the EOD run is repeated. This
prevents duplicate daily snapshots.

Each new snapshot carries:

- `portfolio_id`
- `run_id`
- `run_datetime`
- `strategy_version`
- the existing portfolio summary metrics

Older `myPortfolioDB.csv` rows remain readable; the new metadata columns are
added only to newly generated snapshots.

### 3. Repository abstraction

The engine now separates analysis from persistence:

```text
Quantvesting Engine
       |
       +--> MarketDataRepository
       |       |
       |       +--> FileMarketDataRepository   (now)
       |       +--> PostgreSQL repository       (later)
       |
       +--> PortfolioRepository
               |
               +--> FilePortfolioRepository    (now)
               +--> PostgreSQL repository       (later)
```

The current Jupyter/Colab implementation uses the file repositories. This is
the deliberate Phase A boundary for the future PostgreSQL/Web API MVP.

### 4. Portfolio/run awareness

Portfolio data is identified by `portfolio_id`. Every engine execution can
also be identified by a `run_id`.

Example:

```python
RUN_ID = create_run_id()

df_prospects = qv.prospects(
    market_data,
    portfolio_data=portfolio_data,
    portfolio_id="ankit",
    run_id=RUN_ID,
)

df_portfolio, summary = qv.portfolio(
    market_data,
    portfolio_data=portfolio_data,
    portfolio_id="ankit",
    run_id=RUN_ID,
    eod=False,
)
```

The notebook remains the primary interface; these identifiers simply create
the boundary required for Phase B historical/reproducible runs and Phase C
APIs.

### Phase A notebook controls

`03_quantvesting_run.ipynb` exposes two simple controls:

```python
REFRESH_SCREENER = False
EOD_RUN = False
```

Set `REFRESH_SCREENER=True` when a new Screener workbook is available.

Set `EOD_RUN=True` only for the final portfolio run of the day.

Both default to `False`, so existing interactive runs do not write data
accidentally.

## Phase A → Phase B → Phase C

```text
PHASE A — NOW
XLSX ingestion
     ↓
CSV repository
     ↓
portfolio_id + run_id
     ↓
EOD snapshot

PHASE B — NEXT
historical runs
strategy versions
data validation
reproducibility

PHASE C — MVP
PostgreSQL repository
     ↓
FastAPI
     ↓
Web UI
```

The important architectural rule is:

> **Notebooks orchestrate. The Quantvesting engine calculates. Repositories
> persist. Reporting presents.**

This keeps the investment logic independent of Google Drive, CSV, PostgreSQL,
FastAPI, Web UI or Mobile.
