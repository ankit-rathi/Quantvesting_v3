# Quantvesting_v3

Quantvesting — MVP Starter
This is a refactoring starter for the existing Quantvesting notebooks.
Design
```text
Jupyter / Colab
       |
       v
Quantvesting public interface
       |
       +--> Prospect Engine
       |
       +--> Portfolio Engine
       |
       +--> Decision layer
       |
       v
CSV / JSON data + Yahoo Finance
```
The current investment calculations are kept close to the supplied code.
The major change is separation of:
data access
technical calculations
feature assembly
prospect analysis
portfolio analysis
decisions
configuration
Current data files expected
Put the existing files in your Google Drive `quantvesting/data/` folder:
myPortfolioStocks.csv
myProspectsScrips.csv
myScreenerDB.csv
myInvestments.csv
myProspects-Momentum.csv
myStocks-XIRR.csv
myPortfolioAmts.json
myPortfolioDB.csv (optional; created when EOD history is written)
Important
The supplied code does not contain an explicit BUY/HOLD/EXIT decision algorithm.
Therefore `decisions.py` contains only a transparent baseline scaffold. Do not
consider those action labels the final Quantvesting methodology.
Colab setup
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
```
Then:
```python
prospects = qv.prospects(data, include_portfolio=False)
portfolio, summary = qv.portfolio(data)

display(prospects)
display(portfolio)
summary
```
Next refactoring
Validate output against the existing notebook.
Freeze QV strategy v0.1.
Add golden-output tests.
Add explicit decision rules.
Only then introduce an API/web UI.
