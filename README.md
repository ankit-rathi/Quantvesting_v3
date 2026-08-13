# Quantvesting

**Peaceful investing using quants & data.**

<p align="center">
  <img 
    src="https://github.com/user-attachments/assets/bce3280d-2e2c-4ad8-ba6e-da8b1bcd49f4"
    alt="AI Agents"
    style="width:100%; max-width:1200px; height:auto; border-radius:8px;"
  />
</p>



Quantvesting is a data-driven investment decision framework designed to help busy investors answer two practical questions:

1. **What should I consider buying or accumulating?**
2. **What should I consider selling or booking profits from in my existing portfolio?**

The core philosophy is:

> **Find high-quality Indian businesses trading below intrinsic value, combine fundamental, valuation and technical signals, construct a disciplined portfolio, and let the framework provide repeatable actions rather than relying on emotions or short-term price movements.**

---

# 1. What is Quantvesting?

Quantvesting combines:

* Quality investing
* Value investing
* Growth analysis
* Quantitative ranking
* Technical analysis
* Portfolio allocation
* Rule-based decision making

The current universe is primarily based on **Nifty 500 companies**, with a filtered investable universe of approximately **50–60 businesses**.

The framework ultimately produces two major analytical views:

### Prospects Analysis

Answers:

> **Which businesses deserve my attention for buying/accumulation?**

The primary ranking is `CumlRnk`.

Lower `CumlRnk` = stronger prospect.

### Portfolio Analysis

Answers:

> **Which stocks in my existing portfolio should I consider exiting/booking profits?**

The primary exit candidate indicator is `FTT Amt`.

Lower `FTT Amt` = stronger candidate for considering an exit when the target is reached.

---

# 2. Current Status

## ✅ Phase A — Completed

The current MVP engine has completed the first major architectural transition from notebook-centric code to a modular Python engine.

Implemented:

* Modular Quantvesting engine
* Configuration-driven strategy
* Prospect analysis
* Portfolio analysis
* Decision generation
* Reporting layer
* Shared market data
* User-specific portfolio data
* Screener XLSX → CSV ingestion
* EOD portfolio snapshot capability
* `portfolio_id` awareness
* Separation of market data and portfolio data
* Jupyter-based interface
* Interactive DataTable output
* Portfolio summary
* Portfolio allocation visualization
* DM + SV portfolio aggregation
* Prospect ranking
* Portfolio target/exit analysis
* Basic action generation

The architecture is now designed so that **Jupyter is the current interface rather than the core application**.

---

# 3. Current Architecture

```text
                         Quantvesting
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
      Shared Market Data               User Portfolio Data
       market_data/                    portfolio_data/<id>/
              │                               │
              └───────────────┬───────────────┘
                              ▼
                     Quantvesting Engine
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          Prospects        Portfolio       Decisions
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                         Reporting
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
                  Jupyter            Web UI
```

The key architectural principle is:

> **Business logic lives in Python modules; notebooks and future Web/Mobile applications are only interfaces.**

---

# 4. Repository Structure

Current target structure:

```text
quantvesting/
│
├── config/
│   └── strategy.yaml
│
├── market_data/
│   ├── myScreenerDB.csv
│   └── ...
│
├── portfolio_data/
│   └── <portfolio_id>/
│       ├── myProspectsScrips.csv
│       ├── myPortfolioStocks.csv
│       ├── myInvestments.csv
│       ├── myPortfolioDB.csv
│       └── ...
│
├── src/
│   └── quantvesting/
│       ├── __init__.py
│       ├── data.py
│       ├── technical.py
│       ├── features.py
│       ├── prospects.py
│       ├── portfolio.py
│       ├── decisions.py
│       ├── reporting.py
│       └── ...
│
├── notebooks/
│   ├── 01_prospect_analysis.ipynb
│   ├── 02_portfolio_analysis.ipynb
│   └── 03_quantvesting_run.ipynb
│
├── tests/
│
└── README.md
```

---

# 5. Data Architecture

Quantvesting deliberately separates **market data** from **portfolio data**.

### Market data

Shared across all future users:

```text
market_data/
```

Examples:

* Screener data
* Price data
* Technical indicators
* Financial metrics
* Valuation metrics

### Portfolio data

Specific to each investor:

```text
portfolio_data/<portfolio_id>/
```

Examples:

* Prospect universe
* Portfolio holdings
* Investments
* EOD snapshots

This separation is critical for future multi-user support.

A future user should be able to provide:

```text
portfolio_data/user123/
```

without changing the Quantvesting engine.

---

# 6. Screener Data Pipeline

Current workflow:

```text
myScreenerDB.xlsx
        │
        ▼
Screener ingestion
        │
        ▼
myScreenerDB.csv
        │
        ▼
Shared market data
        │
        ▼
Prospect / Portfolio analysis
```

The ingestion process is intended to behave as a **refresh/upsert**, rather than blindly appending duplicate records.

Conceptually:

```text
Existing CSV
     +
Latest XLSX
     ↓
Identify security
     ↓
Replace latest record
     ↓
Updated CSV
```

This prevents the market dataset from accumulating duplicate securities across refreshes.

---

# 7. Prospect Analysis

Prospect analysis evaluates businesses using multiple dimensions.

Current conceptual model:

```text
                    Nifty 500
                       │
                       ▼
              Quality / Eligibility
                       │
                       ▼
                  Value
                       │
                       ▼
                  Growth
                       │
                       ▼
                 Momentum
                       │
                       ▼
                Upside / FTT
                       │
                       ▼
               Cumulative Rank
                       │
                       ▼
              Prospect Candidates
```

Current ranking incorporates factors such as:

* Deviation from 200 DMA
* Deviation from PE
* ROE / PE
* Sales growth
* Profit growth
* FTT upside
* Market capitalisation
* ROE
* CFO / EBITDA
* RSI
* Gained %
* Conviction
* Business category

The resulting `CumlRnk` provides a single ranking mechanism.

### Interpretation

```text
Lower CumlRnk
      ↓
Stronger prospect
      ↓
BUY / ACCUMULATE candidate
```

The framework is intentionally designed to make the reasoning visible through the underlying scores rather than presenting an unexplained black-box recommendation.

---

# 8. Portfolio Analysis

Portfolio analysis operates at the **security level**.

DM and SV holdings may contain separate records:

```text
HYUNDAI   DM
HYUNDAI   SV
```

but Quantvesting should ultimately treat them as:

```text
HYUNDAI   aggregated position
```

Therefore the intended portfolio grain is:

> **One row per Symbol.**

Portfolio analysis calculates:

* Current value
* Average cost
* Current P/L
* Today P/L
* Current allocation
* FTT
* FTT %
* OTT %
* FTT Amount
* RRR
* Technical indicators
* Conviction
* Cumulative rank
* Risk indicators
* XIRR

---

# 9. Portfolio Decision Philosophy

The decision engine is intentionally simple.

### Buy / Accumulate

Prospect candidates are primarily driven by:

```text
LOW CumlRnk
```

Therefore:

```text
Lower CumlRnk
       ↓
Stronger prospect
       ↓
BUY / ACCUMULATE candidate
```

### Sell / Book Profit

Portfolio candidates are primarily driven by:

```text
LOW FTT Amt
```

Therefore:

```text
Lower FTT Amt
       ↓
Target is closer / less remaining upside
       ↓
EXIT / BOOK PROFIT candidate
```

`FTT` represents the **Final Technical Target**, combining the framework's valuation and technical target logic.

Importantly:

> `EXIT_TARGET` means **exit when the target is reached**, not an instruction to immediately sell the stock merely because the target exists.

---

# 10. Portfolio Summary

The notebook provides a concise investor-oriented summary:

```text
Run date time (IST): 2026-08-08 15:13:55

Deployed:  1.46 C
Current:   1.62 C
CAGR/XIRR %: 4.66%
```

Detailed portfolio metrics remain available from the engine for future Web UI/API consumption.

---

# 11. Jupyter Interface

Jupyter/Google Colab is currently the primary interface because it provides:

* Interactive development
* Easy experimentation
* Rapid strategy changes
* Interactive DataTables
* Charts
* Easy access to Google Drive
* Low infrastructure cost

The important architectural decision is:

> **Jupyter is not the product. The Quantvesting Engine is the product.**

The notebook is simply the first client of the engine.

---

# 12. Phase B — Current Focus

Phase B is focused on making Quantvesting **reproducible, auditable and production-ready** before introducing the Web/API layer.

## Phase B roadmap

### 1. Run ID

Every Quantvesting execution receives a unique:

```text
run_id
```

Example:

```text
QV-20260808-151355-001
```

---

### 2. Portfolio ID

Every user/portfolio is identified independently:

```text
portfolio_id
```

Example:

```text
portfolio_001
portfolio_002
```

This enables multiple investors to use the same engine.

---

### 3. Strategy Version

Every run records the strategy configuration/version.

Example:

```text
strategy_version: 1.2
```

This is important because recommendations must remain explainable even after the strategy changes.

---

### 4. Run Manifest

Each run should capture:

```text
run_id
portfolio_id
strategy_version
run_timestamp
market_data_version
portfolio_data_version
configuration
engine_version
```

Conceptually:

```text
                 RUN
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
   Portfolio   Strategy    Market Data
      │           │           │
      └───────────┼───────────┘
                  ▼
             Reproducible
                Result
```

---

### 5. Historical Run Tracking

Quantvesting should eventually answer:

> "What did the engine recommend three months ago?"

rather than only:

> "What does it recommend today?"

This enables:

* Historical recommendations
* Performance tracking
* Strategy comparison
* Backtesting
* Auditability

---

### 6. Data Validation

Validation should become a first-class component.

Examples:

```text
✓ One row per Symbol
✓ No unexpected duplicates
✓ Required columns present
✓ Numeric fields valid
✓ Dates valid
✓ Market data sufficiently fresh
✓ Portfolio holdings valid
✓ No missing critical metrics
```

A particularly important invariant is:

```text
Portfolio Analysis
        ↓
Exactly ONE row per Symbol
```

Duplicate symbols should raise a validation error rather than silently being dropped.

---

### 7. Reproducible Runs

Given:

```text
run_id
+
strategy_version
+
market_data_version
+
portfolio_data_version
```

Quantvesting should eventually be able to reproduce the same analysis.

This is a major transition from:

> personal notebook

to:

> investment analytics product.

---

# 13. Phase C — Free MVP Architecture

After Phase B, the next transition is:

```text
                    Quantvesting Engine
                           │
                         FastAPI
                           │
                    PostgreSQL
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
           Web UI                    Mobile
```

The initial MVP can be built largely using free/open-source or free-tier infrastructure.

Potential architecture:

```text
GitHub
   │
   ├── Source Code
   └── Web Frontend
           │
           ▼
      Web Application
           │
           ▼
         FastAPI
           │
           ▼
       PostgreSQL
           │
           ▼
   Quantvesting Engine
```

The important point is that the current Python engine should **not need to be rewritten** when this transition happens.

---

# 14. Phase C Roadmap

### 9. PostgreSQL

Move persistent data from CSV/files toward relational storage.

Likely entities:

```text
users
portfolios
portfolio_holdings
prospects
market_data
runs
run_manifests
strategy_versions
recommendations
portfolio_snapshots
```

---

### 10. FastAPI

Expose the Quantvesting engine through APIs.

Potential endpoints:

```text
GET  /prospects
GET  /portfolio
GET  /decisions
GET  /runs
GET  /runs/{run_id}
GET  /portfolio/{portfolio_id}
POST /portfolio/{portfolio_id}/run
```

---

### 11. Web UI

The first web MVP should focus on the **decision experience**, not reproduce the notebook.

Potential dashboard:

```text
QUANTVESTING
────────────────────────

Portfolio
₹1.62 Cr

Deployed
₹1.46 Cr

XIRR
4.66%

────────────────────────

BUY / ACCUMULATE
Top prospects

1. ABC
2. XYZ
3. PQR

────────────────────────

EXIT / BOOK PROFIT

1. HYUNDAI
2. 5PAISA
3. ABC

────────────────────────

Portfolio
Allocation | P/L | Targets
```

---

# 15. Phase D — Productisation

Once the engine + API + Web UI are stable:

### Authentication

Users can securely access their own portfolio.

### User onboarding

A new user should be able to:

```text
Create account
      ↓
Create portfolio
      ↓
Upload/import portfolio data
      ↓
Run Quantvesting
      ↓
See recommendations
```

without changing Python code.

### Subscription

Possible future model:

```text
Free
    ↓
Basic
    ↓
Premium
```

Potential differentiation could be based on:

* Portfolio size
* Historical analytics
* Advanced insights
* Alerts
* Multiple portfolios
* Advanced strategy analytics

### Mobile

Mobile should consume the same APIs rather than contain separate investment logic.

```text
              Quantvesting API
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
        Web        Mobile     Future
                               Clients
```

---

# 16. Five-Year Vision

Quantvesting aims to become:

> **A platform for peaceful investing using quants and data.**

The long-term product should reduce:

```text
Noise
  ↓
Emotion
  ↓
Decision fatigue
  ↓
Impulsive investing
```

and replace it with:

```text
Data
  ↓
Framework
  ↓
Ranking
  ↓
Decision
  ↓
Discipline
  ↓
Peaceful investing
```

---

# 17. What Quantvesting Is NOT

Quantvesting is not intended to encourage:

* Day trading
* Short-term speculation
* Chasing price movements
* Blind following of recommendations
* Excessive portfolio turnover
* Concentrated bets
* Emotion-driven decisions

The intended user is a:

> **Busy professional who wants a systematic way to manage long-term equity investments without constantly monitoring the market.**

---

# 18. Current Product Philosophy

The central product loop is:

```text
             MARKET
                │
                ▼
        Quantitative Analysis
                │
       ┌────────┴────────┐
       ▼                 ▼
   PROSPECTS          PORTFOLIO
       │                 │
 CumlRnk ↓          FTT Amt ↓
       │                 │
       ▼                 ▼
 BUY / ACCUMULATE     EXIT / TARGET
       │                 │
       └────────┬────────┘
                ▼
             DECISION
                │
                ▼
          INVESTOR ACTION
                │
                ▼
             HISTORY
                │
                ▼
             LEARNING
```

---

# 19. Design Principles

### 1. Engine first

Business logic must remain independent of UI.

### 2. Configuration over hard-coding

Investment strategy should live in configuration wherever practical.

### 3. One source of truth

Market data and portfolio data should have clearly defined ownership.

### 4. One row = one security

Portfolio and prospect analytical datasets should maintain an explicit grain.

### 5. No silent data corruption

Validation should fail loudly rather than silently dropping records.

### 6. Reproducibility

Every recommendation should eventually be traceable to:

```text
Data
+
Strategy Version
+
Engine Version
+
Portfolio
+
Run
```

### 7. UI independence

The same engine should serve:

```text
Jupyter
Web
Mobile
API
```

### 8. Incremental productisation

Don't prematurely build a complex platform.

```text
Notebook
   ↓
Modular Engine
   ↓
Validated Engine
   ↓
Database
   ↓
API
   ↓
Web
   ↓
Mobile
   ↓
Scale
```

---

# 20. Current → Future Journey

```text
TODAY

Jupyter + CSV
     │
     ▼
Quantvesting Engine
     │
     ▼
Personal Portfolio
```

↓

```text
PHASE B

Engine
 + Run ID
 + Portfolio ID
 + Strategy Version
 + Validation
 + Historical Runs
 + Reproducibility
```

↓

```text
PHASE C

PostgreSQL
     │
     ▼
FastAPI
     │
     ▼
Web MVP
```

↓

```text
PHASE D

Authentication
     │
     ▼
User Onboarding
     │
     ▼
Subscriptions
     │
     ▼
Mobile
```

↓

```text
LONG TERM

                    QUANTVESTING
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Investor       Data/AI        Community
       Platform       Engine         Learning
          │              │              │
          └──────────────┼──────────────┘
                         ▼
              PEACEFUL INVESTING
                 USING QUANTS
                    & DATA
```

---

# 21. Current Priority

The immediate priority is **not Web UI, mobile or monetisation**.

The priority is:

```text
1. Finish Phase B
        ↓
2. Make every run reproducible
        ↓
3. Make data quality explicit
        ↓
4. Stabilise the engine
        ↓
5. Introduce PostgreSQL
        ↓
6. Expose engine through FastAPI
        ↓
7. Build Web MVP
```

The strategic objective is to make the following statement true:

> **A new user can provide their portfolio data, run Quantvesting, and receive the same quality of analysis without modifying the Quantvesting code.**

That is the real milestone between **"my investment notebook"** and **"Quantvesting as a product."**

---

### Current status at a glance

| Area                        | Status     |
| --------------------------- | ---------- |
| Investment framework        | ✅          |
| Prospect analysis           | ✅          |
| Portfolio analysis          | ✅          |
| Decision engine             | ✅          |
| Reporting                   | ✅          |
| Config-driven strategy      | ✅          |
| Market/portfolio separation | ✅          |
| Screener ingestion          | ✅          |
| EOD snapshot                | ✅          |
| Multi-portfolio foundation  | 🟡         |
| Run ID                      | 🟡 Phase B |
| Strategy versioning         | 🟡 Phase B |
| Historical runs             | 🟡 Phase B |
| Data validation             | 🟡 Phase B |
| Reproducibility             | 🟡 Phase B |
| PostgreSQL                  | ⏳ Phase C  |
| FastAPI                     | ⏳ Phase C  |
| Web UI                      | ⏳ Phase C  |
| Authentication              | ⏳ Phase D  |
| User onboarding             | ⏳ Phase D  |
| Subscription                | ⏳ Phase D  |
| Mobile                      | ⏳ Phase D  |

**North Star:**

> ### Quantvesting = From *“What should I buy/sell?”* to *“Why, when, and according to which repeatable framework?”* — enabling peaceful investing using quants & data.
