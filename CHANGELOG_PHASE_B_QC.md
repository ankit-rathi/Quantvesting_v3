# Phase-B Data Quality Refinement

## Scope-aware validation

This release keeps the existing Quantvesting calculation and decision logic
intact while refining Phase-B validation:

- Shared market/screener data is validated broadly but quality problems outside
  the active analysis universe do not fail a run.
- Missing numeric market values (`NaN`) are treated as incomplete data rather
  than malformed data.
- Missing values generate informational messages.
- Populated non-numeric values outside the active universe generate warnings.
- Populated non-numeric values inside the active universe remain hard errors.
- Duplicate security symbols in the active universe remain hard errors.
- Duplicate screener symbols outside the active universe generate warnings.
- Prospect analysis scopes validation to the prospect universe plus portfolio
  holdings when portfolio context is enabled.
- Portfolio analysis scopes validation to current portfolio holdings.
- Validation reports are attached to prospect DataFrame attrs and portfolio
  summaries.
- `format_validation_report()` is available for Jupyter/Web/API presentation.

The goal is that a broad NSE/screener repository can contain imperfect records
without preventing Quantvesting from analysing the user's actual decision
universe.
