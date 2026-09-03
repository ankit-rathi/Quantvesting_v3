# Phase 1 — Customer-first onboarding

## Objective

Reduce the first-user experience to:

> **One portfolio file → one useful Quantvesting assessment.**

A new user should not have to understand the internal repository structure, market-data files, `InFolio`, Phase-B manifests or transaction history before seeing value.

## Minimum customer input

```csv
Symbol,Shares,AvgCost
TCS,100,3200
INFY,150,1450
HDFCBANK,200,1650
```

The onboarding layer also accepts common labels such as `Ticker`, `Quantity` and `Average Price`.

`InPortfolio`/account is optional. If it is absent, `MAIN` is assigned automatically.

## Data ownership model

### Shared/common

`market_data/` contains Quantvesting-owned market/strategy data:

- `myProspectsScrips.csv` — the Quantvesting stock universe
- `myScreenerDB.csv`
- `myProspects-Momentum.csv`
- `myScreenerDB.xlsx`

`myProspectsScrips.csv` no longer stores the user-specific `InFolio` attribute.

### User-specific

`portfolio_data/<portfolio_id>/` contains customer/portfolio data:

- `myPortfolioStocks.csv` — required internal portfolio contract
- `myInvestments.csv` — optional transaction history
- `myPortfolioAmts.json` — optional booked P/L/reserve inputs
- `myPortfolioDB.csv` — generated EOD history
- `myStocks-XIRR.csv` — optional historical XIRR data
- `myRuns.csv` — Phase-B execution metadata

## Derived portfolio membership

`InFolio` is now derived from the user's holdings during analysis:

```text
Quantvesting Universe
        +
User Portfolio Holdings
        ↓
Symbol-level InFolio
```

This preserves the existing `InFolio` reporting/analysis behaviour without coupling the shared universe to any customer.

## Optional investment history

A first-time user can run portfolio analysis without `myInvestments.csv`.

In that mode:

- current holdings and cost basis are analysed normally;
- portfolio allocation/P&L/FTT/RRR and existing stock-level analytics remain available;
- XIRR is reported as unavailable;
- the deployed amount is provisionally based on current holdings' cost basis plus reserve;
- adding investment history later unlocks transaction-based XIRR/performance analysis.

The existing investment-history path is unchanged when the file is supplied.

## Outside-universe holdings

Holdings not present in the Quantvesting universe do not make onboarding fail. They are surfaced as an outside-universe coverage item while in-universe holdings continue through the normal analysis.

## Notebook sequence

1. `01_customer_onboarding.ipynb` — minimum-input onboarding and first assessment
2. `02_prospect_analysis.ipynb` — prospect/universe analysis
3. `03_portfolio_analysis.ipynb` — detailed portfolio analysis
4. `04_quantvesting_run.ipynb` — complete owner/power-user run
5. `05_quantvesting_terminal.ipynb` — premium executive terminal

Older standalone notebooks are retained under `notebooks/archive/` for reference and backwards compatibility, but are not the recommended current workflow.

## Phase-1 acceptance criteria

- A new user supplies only Symbol, Shares and AvgCost.
- No user-specific `InFolio` data is stored in the shared universe.
- Missing investment history does not fail the portfolio-analysis pipeline.
- Existing Phase-A/B features remain available.
- Existing portfolio calculations continue to use the established internal schema.
- A clear onboarding validation/report is available before analysis.
- Existing tests pass.
