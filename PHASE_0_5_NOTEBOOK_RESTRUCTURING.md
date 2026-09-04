# Phase 0.5 — Notebook & Product Restructuring

## Objective

Make the existing Quantvesting implementation easy for a new customer/repository visitor to understand without changing the market-data or portfolio-data structure or the investment engine.

## Implemented

- Customer-journey notebook sequence from Start Here through longitudinal journey.
- Historical/duplicate notebooks retained under `notebooks/archive/`.
- Operational notebooks separated under `notebooks/admin/`.
- New customer-facing root `README.md`.
- New `00_START_HERE.ipynb`.
- Existing onboarding notebook promoted to the primary `01_ONBOARD_MY_PORTFOLIO.ipynb` entry point.
- New `06_MY_QUANTVESTING_JOURNEY.ipynb` using existing EOD history.
- Existing calculation engine, CSV schemas and strategy logic left intact.

## Explicitly not changed

- `market_data/` structure
- `portfolio_data/` structure
- Quantvesting methodology
- Phase-A/B engine behaviour
- RRR / FTT / conviction / CumlRnk logic
- Repository interfaces

## Phase-1 onboarding

The onboarding flow accepts minimum `Symbol`, `Shares` and `AvgCost`, supports common broker column aliases, defaults account to `MAIN` when absent, permits investment history to be added later, and surfaces outside-universe holdings without blocking in-universe analysis.
