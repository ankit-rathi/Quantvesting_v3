# Quantvesting portfolio data template

Copy this folder to a user-specific location and fill the files with that user's portfolio data.

Required for portfolio analysis:
- `myPortfolioStocks.csv`: Symbol, Shares, AvgCost, InPortfolio
- `myInvestments.csv`: Date, Investment, InPortfolio

Optional:
- `myPortfolioAmts.json`
- `myPortfolioDB.csv`
- `myStocks-XIRR.csv`
- `myRuns.csv` (created automatically by Phase-B run tracking)

`InPortfolio` can contain account labels such as `DM`, `SV`, or future account names.


## Phase A files

`myPortfolioDB.csv` is the optional historical EOD snapshot file. The engine
creates/updates it automatically when portfolio analysis is run with
`eod=True`.

A repeated EOD run on the same IST date replaces that day's snapshot.

The portfolio folder name is used as the default `portfolio_id`, so a future
user can simply have:

```text
portfolio_data/
    friend_001/
        myPortfolioStocks.csv
        myInvestments.csv
        myPortfolioAmts.json
        myPortfolioDB.csv
```

No Quantvesting Python code needs to change for the new user.

## Phase B files

`myRuns.csv` is the execution manifest/history for the portfolio. It records:

- `run_id` and `portfolio_id`
- analysis type (`prospects` / `portfolio`)
- run timestamp
- strategy and engine versions
- configuration/data fingerprints
- EOD flag and run status
- reproducibility hash

It is safe to delete and regenerate the file; it is metadata, not portfolio input data.

`myPortfolioDB.csv` remains the portfolio-level EOD history. Phase B writes dates in
`DD-MM-YYYY`, upserts the current date, and sorts the complete history chronologically.
Legacy mixed date formats are normalised when an EOD snapshot is saved.
The established `investment`/`cagr` fields and Phase-B `initial_investment`/`deployed`/`cagr_xirr` aliases are kept populated consistently.
