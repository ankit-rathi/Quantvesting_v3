# Quantvesting notebook sequence

The notebooks are intentionally ordered around the customer journey rather than the implementation phases.

| # | Notebook | Purpose | Typical user |
|---|---|---|---|
| 01 | `01_customer_onboarding.ipynb` | Minimal-input onboarding: one portfolio CSV → first assessment | New/beta user |
| 02 | `02_prospect_analysis.ipynb` | Quantvesting universe and prospect analysis | Existing user |
| 03 | `03_portfolio_analysis.ipynb` | Detailed portfolio analytics | Existing user |
| 04 | `04_quantvesting_run.ipynb` | Full end-to-end run: prospects + portfolio + decisions + rotation | Power user / owner |
| 05 | `05_quantvesting_terminal.ipynb` | Premium executive investment terminal | Power user / beta |

## Legacy notebooks

The earlier standalone notebooks were retained under `notebooks/archive/` so their original features remain available for reference. They are not part of the recommended current workflow because they pre-date the separated shared-market/user-portfolio architecture.

## Recommended new-user path

```text
01 Customer Onboarding
        ↓
03 Portfolio Analysis
        ↓
05 Quantvesting Terminal
        ↓
02 Prospect Analysis (when the user wants to explore opportunities)
        ↓
04 Full Quantvesting Run (advanced)
```
