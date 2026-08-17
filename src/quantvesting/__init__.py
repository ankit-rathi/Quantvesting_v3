from .data import (
    DataLoadError,
    load_config,
    load_all_data,
    load_market_data,
    load_portfolio_data,
    load_quantvesting_data,
)

from .ingestion import (
    extract_hyperlinks_from_xlsx,
    ingest_screener_xlsx,
    ingest_screener_from_config,
    update_cap_type_by_mcap,
)

from .repositories import (
    MarketDataRepository,
    PortfolioRepository,
    FileMarketDataRepository,
    FilePortfolioRepository,
    CSVMarketDataRepository,
    CSVPortfolioRepository,
)

from .run_context import (
    ENGINE_VERSION,
    DATE_FORMAT,
    canonical_date,
    create_run_id,
    now_ist,
    build_run_manifest,
    hash_config,
    hash_dataframe,
)

from .validation import (
    DataValidationError,
    validate_market_data,
    validate_portfolio_data,
    validate_analysis_inputs,
)

from .prospects import (
    run_prospect_analysis,
    calculate_cumulative_rank,
)

from .portfolio import (
    run_portfolio_analysis,
)

from .decisions import (
    add_prospect_actions,
    add_portfolio_actions,
    capital_rotation_actions,
)

from .reporting import (
    PROSPECT_DISPLAY_COLUMNS,
    PORTFOLIO_DISPLAY_COLUMNS,
    display_dataframe,
    display_portfolio_category_chart,
    display_run_summary,
    format_run_summary,
    format_amount,
    summary_to_dict,
    format_validation_report,
)


class Quantvesting:
    """
    Thin public interface to the Quantvesting engine.

    Jupyter notebooks, web applications and future clients
    should depend on this interface rather than importing
    internal modules directly.
    """

    def __init__(self, config):
        self.config = config

    # ---------------------------------------------------------
    # Market-data ingestion
    # ---------------------------------------------------------

    def ingest_screener(self, market_dir):
        # Refresh myScreenerDB.csv from myScreenerDB.xlsx using YAML rules.
        return ingest_screener_from_config(
            market_dir,
            self.config,
        )

    # ---------------------------------------------------------
    # Prospect Analysis
    # ---------------------------------------------------------

    def prospects(
        self,
        market_data,
        portfolio_data=None,
        include_portfolio=True,
        *,
        portfolio_id=None,
        run_id=None,
    ):
        """
        Run Quantvesting prospect analysis.

        Returns
        -------
        pandas.DataFrame
            Prospect analysis results.
        """

        return run_prospect_analysis(
            market_data,
            self.config,
            include_portfolio=include_portfolio,
            portfolio_data=portfolio_data,
            portfolio_id=portfolio_id,
            run_id=run_id,
        )

    # ---------------------------------------------------------
    # Portfolio Analysis
    # ---------------------------------------------------------

    def portfolio(
        self,
        market_data,
        portfolio_data=None,
        eod=False,
        *,
        portfolio_id=None,
        run_id=None,
    ):
        """
        Run Quantvesting portfolio analysis.

        Returns
        -------
        tuple
            (
                portfolio_dataframe,
                portfolio_summary
            )
        """

        return run_portfolio_analysis(
            market_data,
            self.config,
            eod=eod,
            portfolio_data=portfolio_data,
            portfolio_id=portfolio_id,
            run_id=run_id,
        )

    # ---------------------------------------------------------
    # Decision Engine
    # ---------------------------------------------------------

    def prospect_actions(
        self,
        prospects,
        top_n=10,
    ):
        """
        Add Quantvesting actions to prospect analysis.

        Returns
        -------
        pandas.DataFrame
        """

        return add_prospect_actions(
            prospects,
            top_n=top_n,
        )

    def portfolio_actions(
        self,
        portfolio,
    ):
        """
        Add Quantvesting actions to portfolio analysis.

        Returns
        -------
        pandas.DataFrame
        """

        return add_portfolio_actions(
            portfolio,
            config=self.config,
        )

    def capital_rotation(
        self,
        prospects,
        portfolio,
    ):
        """Compare mature holdings with available prospect opportunities."""
        return capital_rotation_actions(
            prospects,
            portfolio,
            config=self.config,
        )

    # ---------------------------------------------------------
    # Presentation Helpers
    # ---------------------------------------------------------

    @staticmethod
    def display_dataframe(
        df,
        columns=None,
        sort_by=None,
        ascending=True,
    ):
        """
        Display a DataFrame interactively in Jupyter/Colab.

        Presentation-only helper.
        """

        return display_dataframe(
            df,
            columns=columns,
            sort_by=sort_by,
            ascending=ascending,
        )

    @staticmethod
    def display_portfolio_category_chart(
        df_portfolio,
        category_column="Category",
        value_column="Current",
        title="Category Current Distribution",
    ):
        """Display current portfolio value distribution by category."""
        return display_portfolio_category_chart(
            df_portfolio,
            category_column=category_column,
            value_column=value_column,
            title=title,
        )

    @staticmethod
    def display_run_summary(
        summary,
    ):
        """
        Display a compact portfolio run summary
        in Jupyter/Colab.

        Presentation-only helper.
        """

        return display_run_summary(
            summary,
        )

    @staticmethod
    def format_run_summary(
        summary,
    ):
        """
        Return the portfolio summary as Markdown.

        Useful for future Web/API presentation.
        """

        return format_run_summary(
            summary,
        )

    @staticmethod
    def format_amount(
        number,
    ):
        """
        Format a numeric amount using K/L/C notation.
        """

        return format_amount(
            number,
        )

    @staticmethod
    def summary_to_dict(summary):
        """Return summary data in plain-dictionary form for future APIs."""
        return summary_to_dict(summary)

# API application is intentionally not imported here to keep the core engine
# dependency-light for existing notebooks. Deployments import
# ``quantvesting.api.app:app`` directly.
