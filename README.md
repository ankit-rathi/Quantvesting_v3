# Quantvesting — Product-ready engine v0.6 (Phase B + Customer Onboarding)

Quantvesting is a notebook-first investment-analysis engine built around a curated universe of quality Indian businesses, valuation discipline, FTT-based opportunity assessment and transparent portfolio intelligence.

> **Product principle:** minimum customer input → maximum analytical value.

The current implementation remains CSV-backed and Jupyter/Colab-friendly. The calculation engine is separated from repositories and presentation so storage/API/UI can evolve later without rewriting the core methodology.

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
                         Jupyter today
                         API/UI later
```

## Customer-first data model

### Shared/common data

```text
market_data/
├── myProspectsScrips.csv       # Quantvesting stock universe
├── myScreenerDB.csv
├── myProspects-Momentum.csv
└── myScreenerDB.xlsx
```

`myProspectsScrips.csv` is now a true security/universe dataset. It no longer stores user-specific `InFolio`.

### User-specific data

```text
portfolio_data/
└── <portfolio_id>/
    ├── myPortfolioStocks.csv   # required internal holding contract
    ├── myInvestments.csv       # optional for first onboarding
    ├── myPortfolioAmts.json    # optional
    ├── myPortfolioDB.csv       # generated EOD history
    ├── myStocks-XIRR.csv       # optional
    └── myRuns.csv              # Phase-B execution metadata
```

The engine derives `InFolio` from the user's portfolio at runtime. Multiple account rows for the same security remain supported.

## 5-minute onboarding

A new user does **not** need to prepare all internal files.

Minimum input:

```csv
Symbol,Shares,AvgCost
TCS,100,3200
INFY,150,1450
HDFCBANK,200,1650
```

The onboarding layer accepts common broker/export labels such as `Ticker`, `Quantity` and `Average Price`. If no account column is supplied, it assigns `MAIN`. Duplicate symbols in a no-account upload are consolidated using a cost-weighted average.

Run:

```text
notebooks/01_customer_onboarding.ipynb
```

The notebook normalizes the customer file into the existing internal portfolio contract, loads the shared Quantvesting universe/market data, and produces the existing portfolio analysis and terminal.

Investment history is optional. Without it, XIRR is simply reported as unavailable rather than blocking the first assessment.

## Notebook sequence

| # | Notebook | Purpose |
|---|---|---|
| 01 | `01_customer_onboarding.ipynb` | Minimum-input onboarding → first assessment |
| 02 | `02_prospect_analysis.ipynb` | Prospect/universe analysis |
| 03 | `03_portfolio_analysis.ipynb` | Detailed portfolio analysis |
| 04 | `04_quantvesting_run.ipynb` | End-to-end owner/power-user run |
| 05 | `05_quantvesting_terminal.ipynb` | Premium executive investment terminal |

See `notebooks/README.md` for the recommended customer journey. Earlier standalone notebooks remain under `notebooks/archive/`.

## Existing Quantvesting methodology retained

The customer-onboarding changes do **not** alter the established investment framework:

- X/H/M/L quality classification
- LC/MC/SC categorisation
- full 12-level conviction priority map
- first-six CORE/rankable conviction buckets
- CumlRnk
- FTT / NTT / LTT / BOL
- RRR Ind
- Risk Ind
- portfolio allocation and concentration analysis
- prospect analysis
- capital rotation review
- transparent decision layer
- EOD snapshot persistence
- Phase-B run IDs, portfolio IDs, strategy versions, validation and reproducibility

## Phase status

### Phase A — Foundation

Completed.

### Phase B — Traceability & reproducibility

Completed:

- run ID
- portfolio ID
- strategy version
- run manifest
- historical run tracking
- validation
- reproducibility fingerprints
- corrected EOD upsert/date ordering
- Screener XLSX → CSV replacement/refresh logic

### Phase 1 — Customer onboarding

**Current priority.**

- one-file minimum onboarding
- shared universe/user portfolio separation
- runtime `InFolio`
- optional investment history
- outside-universe handling
- onboarding validation
- customer-first notebook sequence

See `PHASE_1_CUSTOMER_ONBOARDING.md`.

## Recommended product roadmap

```text
PHASE 1  Customer onboarding
   ↓
PHASE 2  Portfolio health & attention intelligence
   ↓
PHASE 3  Capital efficiency / RRR intelligence
   ↓
PHASE 4  Prospect & opportunity intelligence
   ↓
PHASE 5  Customer history / longitudinal portfolio intelligence
   ↓
PHASE 6  Financial health assessment
   ↓
PHASE 7  Premium intelligence + decision journal
   ↓
PHASE 8  API / PostgreSQL / polished web-mobile UI
```

Technical infrastructure should follow demonstrated customer value rather than lead it.

## Tests

Run from the repository root:

```bash
PYTHONPATH=src pytest -q
```

The current suite covers the existing Phase-A/B contracts plus the Phase-1 onboarding and data-separation behaviour.
