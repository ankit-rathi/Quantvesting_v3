# Quantvesting

> **From portfolio data to decision intelligence.**

## Introduction

Quantvesting is a **notebook-first investment-analysis and decision-support framework** built around a curated universe of quality Indian businesses, valuation discipline, FTT-based opportunity assessment and portfolio intelligence.

It was originally developed as a personal investing framework and is being productised carefully around a simple principle:

> **Minimum customer input → maximum analytical value.**

Quantvesting is designed to help an investor understand their financial/equity position, identify what deserves attention, evaluate remaining opportunity and improve capital-allocation decisions.

It is deliberately **not** designed to make investment decisions on behalf of the user or to promise returns.

---

## What does Quantvesting help answer?

### 1. Portfolio Health

Understand:

- current and deployed value
- P/L and CAGR/XIRR where available
- allocation and concentration
- quality and conviction
- FTT-based remaining opportunity

### 2. Portfolio Decisions

Use the existing Quantvesting decision layer to identify holdings that deserve review based on the framework's evidence, including FTT, RRR Ind, risk and thesis-capture measures.

### 3. Quantvesting Prospects

Explore the curated universe using the established quality, valuation, growth, momentum, conviction and CumlRnk framework.

### 4. Capital Rotation

Compare positions whose investment thesis is substantially captured with currently available Quantvesting opportunity. The rotation layer is **advisory and review-oriented**, not an automatic sell mechanism.

### 5. Quantvesting Journey

Use persisted EOD history to understand how portfolio value and performance measures have evolved over time.

---

## Customer journey

```text
00 START HERE
      ↓
01 ONBOARD MY PORTFOLIO
      ↓
02 MY PORTFOLIO HEALTH
      ↓
03 MY PORTFOLIO DECISIONS
      ↓
04 QUANTVESTING PROSPECTS
      ↓
05 CAPITAL ROTATION
      ↓
06 MY QUANTVESTING JOURNEY
```

### The first experience

A new customer should be able to start with a simple CSV:

```csv
Symbol,Shares,AvgCost
TCS,100,3200
INFY,150,1450
HDFCBANK,200,1650
```

The onboarding layer accepts common broker/export labels such as `Ticker`, `Quantity` and `Average Price`. Account information is optional. Investment history can be supplied later to unlock deeper transaction-based performance analysis.

---

## Quantvesting philosophy

The framework focuses on a small number of durable ideas:

1. **Business quality first** — X/H businesses are carefully selected according to the established framework.
2. **Buy quality at sensible valuation** — the framework looks for situations where price has room to catch up with business performance.
3. **FTT as an explicit opportunity reference** — FTT represents the framework's target/technical reference rather than a promise of future price.
4. **Conviction matters** — the full 12-level conviction priority hierarchy remains part of the framework.
5. **Capital is finite** — RRR and capital-rotation analysis help identify where existing capital may deserve review.
6. **Evidence before action** — outputs are designed to make the reasoning visible rather than hide it behind a black-box score.

---

## Key Quantvesting concepts

| Concept | Meaning in the framework |
|---|---|
| **FTT** | Final target/reference used to estimate remaining opportunity |
| **NTT** | Near-term target derived from the configured strategy |
| **LTT** | Longer-term target derived from the configured strategy |
| **BOL** | Base/reference lower level used in the existing framework |
| **RRR Ind** | Relationship between profit already captured and remaining FTT opportunity |
| **Risk Ind** | Portfolio-weighted risk indicator used by the existing framework |
| **Conviction** | Quality + market-cap bucket classification |
| **CumlRnk** | Cumulative opportunity ranking within the configured framework |

The exact calculations remain in the engine and configuration rather than in the notebooks.

---

## Existing methodology retained

The restructuring and customer-onboarding work do **not** change the established analytical foundation, including:

- X/H/M/L quality classification
- LC/MC/SC market-cap classification
- full conviction priority map
- first-six CORE versus remaining LEGACY treatment for portfolio presentation
- Value / Growth / Quality / Momentum analysis
- CumlRnk
- FTT / NTT / LTT / BOL
- RRR Ind
- Risk Ind
- allocation and concentration analysis
- prospect analysis
- capital-rotation review
- EOD snapshots
- Phase-B run IDs, portfolio IDs, strategy versions, validation and reproducibility

---

## Architecture

```text
                 QUANTVESTING
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
   Shared Market Data        User Portfolio Data
     market_data/             portfolio_data/<id>/
          │                         │
          └────────────┬────────────┘
                       ▼
              Quantvesting Engine
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Prospects      Portfolio      Decisions
                       │
                       ▼
                Reporting / Dashboard
                       │
                       ▼
                  Jupyter today
                  API/Web later
```

The architectural rule is:

> **Notebooks orchestrate. Engine calculates. Repositories persist. Reporting presents.**

The current implementation remains CSV-backed and Jupyter/Colab-friendly. The repository abstraction allows PostgreSQL and API layers to be introduced later without moving investment logic into the UI.

---

## Repository structure

```text
quantvesting_v3/
├── config/
├── market_data/                 # shared Quantvesting data — unchanged
├── portfolio_data/              # user-specific portfolio data — unchanged
├── portfolio_template/
├── src/quantvesting/             # analytical engine
├── notebooks/                   # customer journey
│   ├── 00_START_HERE.ipynb
│   ├── 01_ONBOARD_MY_PORTFOLIO.ipynb
│   ├── 02_MY_PORTFOLIO_HEALTH.ipynb
│   ├── 03_MY_PORTFOLIO_DECISIONS.ipynb
│   ├── 04_QUANTVESTING_PROSPECTS.ipynb
│   ├── 05_CAPITAL_ROTATION.ipynb
│   ├── 06_MY_QUANTVESTING_JOURNEY.ipynb
│   ├── admin/
│   └── archive/
└── tests/
```

The data structure is intentionally **not being reorganised in Phase 0.5/1**. This reduces migration risk while customer onboarding is validated.

---

## Customer onboarding

### Minimum input

`Symbol`, `Shares`, `AvgCost` are sufficient for the first portfolio assessment.

### Optional inputs

- account label
- investment/transaction history
- portfolio amounts / booked P&L
- historical EOD snapshots

### What happens

```text
Customer CSV
     ↓
Normalize broker/export columns
     ↓
Validate holdings
     ↓
Create portfolio-specific internal input
     ↓
Join against Quantvesting universe
     ↓
Portfolio assessment
```

Holdings outside the current Quantvesting universe do not block the assessment; they are surfaced as a coverage item while in-universe holdings continue through the normal analysis path.

---

## Phase status

### Phase A — Operational foundation

**Completed.**

Includes shared/user data separation, XLSX ingestion, repository abstraction, portfolio/run awareness and EOD snapshot persistence.

### Phase B — Traceability & reproducibility

**Completed / operational.**

Includes historical run tracking, strategy versioning, run manifests, data validation, reproducibility support and corrected EOD upsert/date ordering.

### Phase 0.5 — Notebook & product restructuring

**Implemented in this release.**

- customer-journey notebook sequence
- old notebooks retained under `archive/`
- admin notebooks separated
- customer-facing README
- Start Here notebook
- longitudinal Journey notebook

### Phase 1 — Customer onboarding

**Implemented and ready for beta feedback.**

- minimum-input portfolio CSV
- broker/export column aliases
- optional account field
- optional investment history
- runtime portfolio membership
- outside-universe handling
- onboarding validation
- first-assessment flow

---

## Product roadmap

```text
CURRENT
  ↓
Phase 0.5  Notebook/Product restructuring       ✅
  ↓
Phase 1    Frictionless customer onboarding     ✅ / BETA
  ↓
Phase 2    Portfolio health + attention         🔴 NEXT
  ↓
Phase 3    Capital efficiency / RRR             🟠
  ↓
Phase 4    Prospect & opportunity intelligence   🟠
  ↓
Phase 5    Longitudinal customer intelligence    🟡
  ↓
Phase 6    Financial health assessment           🟡
  ↓
Phase 7    Premium intelligence / journal        🟡
  ↓
Phase 8    API + PostgreSQL + web/mobile         🟢 LATER
```

The priority is deliberately **customer-first**: prove value and reduce onboarding friction before investing heavily in infrastructure.

---

## For developers

Run tests from the repository root:

```bash
PYTHONPATH=src pytest -q
```

The engine returns structured DataFrames/dictionaries and is intended to remain presentation-agnostic.

---

## Disclaimer

Quantvesting is an analytical and educational framework. Its outputs are based on the data and methodology available at the time of analysis and involve uncertainty and investment risk. No analytical output guarantees future performance or returns. Users remain responsible for their own investment decisions and should obtain appropriately regulated professional advice where required.
