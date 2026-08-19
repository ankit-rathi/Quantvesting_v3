# Phase 2 — Premium Jupyter Investment Terminal

## Objective

Turn the existing notebook workflow into a premium, HNI-friendly investment terminal **without moving business logic into notebooks** and without changing the existing investment methodology.

## What is implemented

### 1. Executive dashboard

`src/quantvesting/dashboard.py` adds a presentation-only terminal with:

- current portfolio value
- deployed capital
- existing CAGR/XIRR metric
- active decisions
- core vs legacy allocation
- top-5 concentration
- weighted remaining upside
- median RRR Ind
- action feed with reason + evidence

### 2. Interactive intelligence views

The notebook now exposes:

- portfolio action table
- prospect opportunity table
- portfolio health chart
- remaining-upside chart
- top prospect `CumlRnk` chart
- capital-rotation review

The existing `display_dataframe()` contract remains intact, so the previous notebook workflow continues to work.

### 3. Explainable actions

The decision layer keeps its existing `Action` values and adds presentation-safe fields:

- `ActionReason`
- `ActionEvidence`
- prospect `Reason`
- prospect `Evidence`

No action is converted into an automatic sell instruction.

### 4. Run / date selector

The terminal can inspect:

- historical run manifests from `myRuns.csv`
- stored EOD portfolio snapshots from `myPortfolioDB.csv`

The selector does not pretend that per-stock historical snapshots exist when they are not persisted by the current repository.

### 5. Dedicated premium notebook

Added:

```text
notebooks/04_quantvesting_terminal.ipynb
```

The existing notebooks remain available. The end-to-end notebook (`03_quantvesting_run.ipynb`) also surfaces the new terminal after the existing analysis.

## What is deliberately NOT changed

- priority / conviction hierarchy
- prospect ranking methodology
- FTT semantics
- EOD persistence rules
- repository architecture
- market-data vs portfolio-data separation
- run IDs / strategy versions / reproducibility
- existing portfolio action values
- existing prospect action values
- PostgreSQL / FastAPI / Render infrastructure

## Phase 2 exit criteria

The notebook should let a sophisticated user complete a review in this order:

```text
Executive view
    ↓
Today's decisions
    ↓
Portfolio drill-down
    ↓
Remaining upside
    ↓
Best prospects
    ↓
Capital rotation review
    ↓
Run / EOD history
```

This is intentionally a presentation/product-interface phase. Capital-allocation methodology expansion remains the next phase.
