# Quantvesting notebooks — customer journey

The active notebooks are ordered by **what the customer is trying to accomplish**, not by the historical order in which features were developed.

## Recommended journey

| # | Notebook | Customer question | Primary audience |
|---|---|---|---|
| 00 | `00_START_HERE.ipynb` | What is Quantvesting and where do I start? | Everyone |
| 01 | `01_ONBOARD_MY_PORTFOLIO.ipynb` | How do I get my portfolio into Quantvesting? | New / beta user |
| 02 | `02_MY_PORTFOLIO_HEALTH.ipynb` | How healthy is my portfolio? | Investor |
| 03 | `03_MY_PORTFOLIO_DECISIONS.ipynb` | What deserves my attention? | Investor / beta user |
| 04 | `04_QUANTVESTING_PROSPECTS.ipynb` | What does the Quantvesting universe look like? | Investor |
| 05 | `05_CAPITAL_ROTATION.ipynb` | Where might capital efficiency deserve review? | Advanced investor |
| 06 | `06_MY_QUANTVESTING_JOURNEY.ipynb` | How has my portfolio evolved? | Existing customer |

## Admin notebooks

Operational notebooks remain separate from the customer journey:

- `admin/90_REFRESH_MARKET_DATA.ipynb` — refresh shared Screener snapshot
- `admin/91_VALIDATE_DATA.ipynb` — run scope-aware data validation
- `admin/92_EOD_SNAPSHOT.ipynb` — persist the official daily portfolio snapshot

## Archive

Earlier notebooks are retained under `archive/`. They are preserved for historical reference and backwards compatibility but are **not** part of the recommended customer workflow.

The restructuring intentionally does **not** change the market-data CSV structure, the portfolio-data structure, the Quantvesting calculation engine or the existing investment methodology.
