# Quantvesting — MVP Engine v0.2

Quantvesting is being productised from an interactive Google Colab/Jupyter
workflow into a reusable investment-analysis engine. The notebook is now a
thin client of the engine; the ranking, portfolio calculations and reporting
contracts live in `src/quantvesting`.

## Architecture

```text
Jupyter / Colab                 Future Web / Mobile
       |                              |
       +--------------+---------------+
                      |
                      v
             Quantvesting API
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
   prospects.py   portfolio.py  decisions.py
        |             |             |
        +-------------+-------------+
                      |
                  features.py
                      |
                  technical.py
                      |
                    data.py
                      |
                  CSV / JSON /
                  Yahoo Finance

                      |
                      v
                 reporting.py
                      |
                 DataTable / JSON
```

## Current Quantvesting prospect ranking

The ranking logic previously embedded in the prospect notebook is now in
`prospects.py`. It calculates:

- Value rank: `Dev%_200`, `Dev%_PE`, `ROE%/PE`
- Growth rank: `Sales_Grwth%`, `Profit_Grwth%`
- Quality rank: `FTT%`, `MCap`, `ROE%`, `CFO_2_EBITDA%`
- Momentum rank: `Gained%`, `RSI_14`
- Overall rank: sum of the four category scores
- Category rank: rank within `Conviction`
- Final `CumlRnk`: ordered by Conviction Priority and category rank

The defaults reproduce the supplied notebook methodology: equal category
weights and the explicit Conviction Priority map. The notebook's temporary
`stock_list` calculation was not used in the final ranking expression, so it
is intentionally not used to filter the engine's ranking universe.

## Configuration

`config/strategy.yaml` now controls:

- candidate/MBQ rules for future filtering
- ranking categories
- rank directions
- category weights
- Conviction Priority
- universe exclusions
- portfolio constraints
- technical parameters

Changing category weights does not require changing Python code.

## Portfolio membership and DM/SV handling

`myPortfolioStocks.csv` remains holding-level data. The same Symbol can
appear multiple times because a stock may be held in both DM and SV (and the
model can support additional accounts later).

Prospect analysis is security-level, so it now aggregates portfolio
membership before joining it to the prospect universe:

```text
myPortfolioStocks.csv
        |
        +-- ABBOTINDIA / DM
        +-- ABBOTINDIA / SV
        |
        v
portfolio membership
        |
        +-- ABBOTINDIA / DM+SV
        |
        v
Prospects
```

This prevents one-to-many joins from duplicating prospect rows. The original
holding-level records are still retained for portfolio calculations, so DM/SV
shares and average costs continue to be aggregated correctly. A validation
check now fails early if the security-level prospects dataset contains
duplicate Symbols.

When `include_portfolio=False`, the engine uses the aggregated membership view
to exclude all currently held stocks, regardless of whether they are held in
DM, SV or both.

## Portfolio output

`qv.portfolio(data)` returns:

```python
df_portfolio, summary = qv.portfolio(data)
```

The summary is structured data and includes:

- IST run timestamp
- deployed capital
- current value
- CAGR/XIRR
- today's P/L
- current P/L
- current-year P/L
- overall P/L
- booked profits
- FTT/LTT estimates

The compact Jupyter presentation is handled by `reporting.py`, for example:

```python
qv.display_run_summary(summary)
```

which produces:

```text
Run date time (IST): YYYY-MM-DD HH:MM:SS
Deployed:  1.46 C
Current:   1.63 C
CAGR/XIRR %: 5.07%
```

## Colab

```python
from google.colab import drive
drive.mount('/content/drive')

import sys
sys.path.insert(0, '/content/drive/My Drive/quantvesting/src')

from quantvesting import Quantvesting, load_config, load_all_data

config = load_config(
    '/content/drive/My Drive/quantvesting/config/strategy.yaml'
)
data = load_all_data(
    '/content/drive/My Drive/quantvesting/data'
)
qv = Quantvesting(config)

prospects = qv.prospects(data, include_portfolio=False)
qv.display_dataframe(prospects, sort_by='CumlRnk')

portfolio, summary = qv.portfolio(data)
qv.display_dataframe(portfolio, sort_by='CurrAlloc%', ascending=False)
qv.display_run_summary(summary)
```

`display_dataframe()` uses Colab's interactive `data_table.DataTable` when
running in Colab and falls back to normal IPython display elsewhere.

## Decision layer

`decisions.py` currently provides transparent scaffolding only:

- top-N prospect candidate signal based on `CumlRnk`
- `EXIT_TARGET` when current value reaches FTT
- `HOLD` otherwise

These labels are not intended to replace the final Quantvesting decision rules;
they exist so the product architecture has a stable decision layer while the
explicit methodology is being formalised.

## Data files

Expected files under `data/`:

- `myPortfolioStocks.csv`
- `myProspectsScrips.csv`
- `myScreenerDB.csv`
- `myInvestments.csv`
- `myProspects-Momentum.csv`
- `myStocks-XIRR.csv`
- `myPortfolioAmts.json`
- `myPortfolioDB.csv` (optional history file)

## Development sequence

1. Validate engine output against the existing notebook.
2. Freeze Quantvesting strategy v0.2.
3. Add golden-output/regression tests for prospect and portfolio results.
4. Formalise the decision engine.
5. Expose the engine through an API.
6. Build the Web UI on top of the same public interface.
