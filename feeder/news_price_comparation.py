import asyncio
from datetime import timedelta
from typing import List, Optional

import pandas as pd
import pytz
import semantic_kernel.connectors.ai.open_ai as sk_oai  # noqa: F401
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
from semantic_kernel.contents import ChatHistory

from config import Config, significant_companies, DataFeedConfig
from embedding_kits.stock_news_embedding import AzureSearchManager
from embedding_kits.stock_news_embedding_plugin import RelatedNewsPlugin
from new_analyzer.model_news_impact_analysis_result import NewsImpactAnalysisResult
from new_analyzer.stock_news_analysis_plugin import StockNewsAnalysisPlugin
from news_downloader.model_news_article_na import NewsAPIArticle
from news_downloader.news_downloader_na import NewsAPIClient
from stock_price.back_tester import BacktestRunner, BacktestResult
from stock_price.stock_price_data_downloader import StockPriceDataDownloader
from stock_price.trading_date_calculator import TradingDateCalculator
from ui.text_composer import LLMTextComposer


class StockAnalysisResultCollectionItem:
    def __init__(self, ticker: str, news_article: NewsAPIArticle, pre_analysis_result: NewsImpactAnalysisResult, rag_analysis_result: NewsImpactAnalysisResult,
                 pre_analysis_pnl_ratio: float = None, rag_pnl_ratio: float = None):
        self.ticker = ticker
        self.news_article = news_article
        self.pre_analysis_result = pre_analysis_result
        self.rag_analysis_result = rag_analysis_result
        self.pre_analysis_pnl_ratio = pre_analysis_pnl_ratio
        self.rag_pnl_ratio = rag_pnl_ratio


class ChatbotPerformanceComparison:
    def __init__(self):
        self.azure_search = AzureSearchManager(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX)

        self.api_client = NewsAPIClient()

        self.gradio_chat_history = []

        # SK initialization
        self.kernel = Kernel()
        self.chat_completion_service_open_ai = sk_oai.AzureChatCompletion(
            service_id="default",
            deployment_name=Config.aoi_deployment_name,
            api_key=Config.aoi_api_key,
            endpoint=Config.aoi_endpoint,
            api_version=Config.aoi_api_version,
        )

        self.chat_completion_service = OllamaChatCompletion(
            service_id="ollama",
            # ai_model_id="aratan/mistral-small-3.1:24b",
            ai_model_id="llama3.2",
        )
        # Message call settings
        self.sk_chat_history = ChatHistory()

        # tool call settings

        self.kernel.add_plugin(StockNewsAnalysisPlugin(), "StockNewsAnalysisPlugin")
        self.kernel.add_plugin(RelatedNewsPlugin(), "RelatedNewsPlugin")

    # make a get setting funciton to get different setting with different plugins
    @staticmethod
    def _get_pe_settings(included_plugins: list[str], included_function: list[str], auto_invoke) -> PromptExecutionSettings:
        return PromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=auto_invoke)
            # .Required(filters={"included_functions": included_function}, auto_invoke=auto_invoke)
            # .Auto(auto_invoke=auto_invoke),

            # filter = {"included_plugins": included_plugins}
        )

    async def run_analysis_from_csv(self) -> List[StockAnalysisResultCollectionItem]:
        analysis_collection = []

        ######## (1) gethering news
        news_data = {}
        for company_ticker, company_info in list(significant_companies.items()):
            news_data[company_ticker] = self.api_client.cache.load_from_cache(company_ticker, from_date=DataFeedConfig.EMBEDDING_DATE_FROM, to_date=DataFeedConfig.EMBEDDING_DATE_TO)

        ######## (2) analysis incoming news (pre-analysis)
        for company_ticker, articles in news_data.items():

            for article in articles[:3]:
                self.sk_chat_history.add_user_message(
                    "Analysis of the news article is required to determine the impact on the stock price."
                    "\n\nProvide a JSON response with keys: "
                    f"possible_pnl_ratio (a float number, indicate possible profit and loss ratio, range from -100.00 ~ 100.00), "
                    "impact_weight (1~10), "
                    "position_movement (long or short), "
                    "impact_days_min (1~5), and impact_days_max(1~10)."
                    "--------"
                    "NEWS:\n\n" + article.get_content_for_llm())

                pre_analysis_parameter_response = await self.chat_completion_service.get_chat_message_content(
                    chat_history=self.sk_chat_history,
                    settings=self._get_pe_settings(included_plugins=["StockNewsAnalysisPlugin"], included_function=["analyze_stock_news"], auto_invoke=False),
                    kernel=self.kernel
                )
                pre_analysis_result_str = pre_analysis_parameter_response.items[0].arguments
                pre_analysis_result = NewsImpactAnalysisResult.from_dict(pre_analysis_result_str)

                print("\n\n", "parameters:", pre_analysis_result_str, "\n\n--------\n\n")
                self.sk_chat_history.clear()

                ######## (3) retrieve related news analysis
                if pre_analysis_result:
                    if pre_analysis_result.news_summery:
                        index_search_result = await RelatedNewsPlugin.get_related_stock_news_wrapper(pre_analysis_result.news_summery)
                    else:
                        index_search_result = await RelatedNewsPlugin.get_related_stock_news_wrapper(article.get_content_for_llm())
                else:
                    print("ERROR: Can't analysis the news.", '\n')
                    # TODO: add a fail record
                    continue

                related_news_pnl_ratio = LLMTextComposer.calculate_related_news_pnl_ratio(index_search_result)
                related_news_suggestion = LLMTextComposer.compose_related_news_pnl_ratio_for_llm(index_search_result)

                ######## (4) analysis incoming news (final-analysis)
                self.sk_chat_history.add_user_message(
                    "Analysis of the news article is required to determine the impact on the stock price."
                    "\n\nProvide a JSON response with keys: "
                    f"possible_pnl_ratio (a float number, indicate possible profit and loss ratio, range from -100.00 ~ 100.00), "
                    f"impact_weight (1-10), "
                    f"position_movement (long or short), "
                    f"impact_days_min (1-5), and impact_days_max(1-10)."
                    f"--------\n\n"
                    f"NEWS: {article.get_content_for_llm()}\n\n"
                    f"--------\n\n"
                    f"{related_news_suggestion}"
                )

                rag_analysis = await self.chat_completion_service.get_chat_message_content(
                    chat_history=self.sk_chat_history,
                    settings=self._get_pe_settings(included_plugins=["StockNewsAnalysisPlugin"], included_function=["analyze_stock_news"], auto_invoke=False),
                    kernel=self.kernel
                )

                try:
                    rag_analysis_parameter = rag_analysis.items[0].arguments
                    rag_analysis_result = NewsImpactAnalysisResult.from_dict(rag_analysis_parameter)
                    print("\n", "rag_parameters:", rag_analysis_parameter, "\n\n--------")
                except AttributeError:
                    print("ERROR: 'TextContent' object has no attribute 'arguments'. Skipping this loop.")
                    # TODO: add a fail record

                    continue

                # insert to the analysis collection
                analysis_collection.append(StockAnalysisResultCollectionItem(
                    ticker=company_ticker, news_article=article,
                    pre_analysis_result=pre_analysis_result, rag_analysis_result=rag_analysis_result))
        return analysis_collection

    # run backtest for each analysis
    def run_backtest(self, analysis_collection: list[StockAnalysisResultCollectionItem]):
        # make an empty dataframe with fields from all the field from StockAnalysisResultCollectionItem, including their subfields

        columns = [
            "ticker", "news_summery", "published_at", "url",
            "pre_analysis_result.possible_pnl_ratio", "pre_analysis_result.impact_weight", "pre_analysis_result.position_movement",
            "pre_analysis_result.impact_days_min", "pre_analysis_result.impact_days_max",

            "rag_analysis_result.possible_pnl_ratio", "rag_analysis_result.impact_weight", "rag_analysis_result.position_movement",
            "rag_analysis_result.impact_days_min", "rag_analysis_result.impact_days_max",

            "pre_analysis_pnl_ratio", "rag_pnl_ratio"
        ]
        final_compare_df = pd.DataFrame(columns=columns)

        for analysis_item in analysis_collection:
            article_date = analysis_item.news_article.published_at.tz_localize('UTC').astimezone(pytz.timezone('US/Eastern'))
            trading_hour_status = TradingDateCalculator.get_trading_hour(article_date)

            ########
            if trading_hour_status.is_in_trading_hour:
                start_date = article_date
            else:
                start_date = trading_hour_status.next_trading_open

            start_price_date_str = start_date.strftime("%Y-%m-%d")
            end_price_date_str = (start_date + timedelta(days=analysis_item.pre_analysis_result.impact_days_max + 5)).strftime("%Y-%m-%d")

            # Pre Analysis - backtest
            pre_backtest_result = self._run_backtest(
                ticker=analysis_item.ticker, impact=analysis_item.pre_analysis_result,
                start_date=start_date, start_price_date_str=start_price_date_str, end_price_date_str=end_price_date_str, trading_hour_status=trading_hour_status)

            post_backtest_result = self._run_backtest(
                ticker=analysis_item.ticker, impact=analysis_item.rag_analysis_result,
                start_date=start_date, start_price_date_str=start_price_date_str, end_price_date_str=end_price_date_str, trading_hour_status=trading_hour_status)

            # insert to the final_compare_df

            if analysis_item.pre_analysis_result.news_summery:
                article_summery = analysis_item.pre_analysis_result.news_summery
            else:
                article_summery = analysis_item.news_article.get_content_for_llm()

            new_row = {
                "ticker": analysis_item.ticker,
                "news_summery": article_summery,
                "published_at": analysis_item.news_article.published_at,
                "url": analysis_item.news_article.url,

                "pre_analysis_result.possible_pnl_ratio": analysis_item.pre_analysis_result.possible_pnl_ratio,
                "pre_analysis_result.impact_weight": analysis_item.pre_analysis_result.impact_weight,
                "pre_analysis_result.position_movement": analysis_item.pre_analysis_result.position_movement,
                "pre_analysis_result.impact_days_min": analysis_item.pre_analysis_result.impact_days_min,
                "pre_analysis_result.impact_days_max": analysis_item.pre_analysis_result.impact_days_max,

                "rag_analysis_result.possible_pnl_ratio": analysis_item.rag_analysis_result.possible_pnl_ratio,
                "rag_analysis_result.impact_weight": analysis_item.rag_analysis_result.impact_weight,
                "rag_analysis_result.position_movement": analysis_item.rag_analysis_result.position_movement,
                "rag_analysis_result.impact_days_min": analysis_item.rag_analysis_result.impact_days_min,
                "rag_analysis_result.impact_days_max": analysis_item.rag_analysis_result.impact_days_max,

                "pre_analysis_pnl_ratio": pre_backtest_result.total_pnl_ratio if pre_backtest_result else None,
                "rag_pnl_ratio": post_backtest_result.total_pnl_ratio if post_backtest_result else None
            }

            final_compare_df.loc[len(final_compare_df)] = new_row
        return final_compare_df

    @staticmethod
    def _run_backtest(ticker: str, impact: NewsImpactAnalysisResult, start_date, start_price_date_str, end_price_date_str, trading_hour_status) -> Optional[BacktestResult]:
        if impact and impact.impact_weight > 0:
            stock_price_downloader = StockPriceDataDownloader(ticker, start_price_date_str, end_price_date_str)
            stock_price_df = stock_price_downloader.get_price_data_in_range(start_price_date_str, end_price_date_str)

            runner = BacktestRunner(data_frame=stock_price_df)

            backtest_result = runner.run(impact_weight=impact.impact_weight,
                                         maximum_impact_days=impact.impact_days_max,
                                         minimum_impact_days=impact.impact_days_min,
                                         position_movement=impact.position_movement,
                                         start_trading_date=start_date.to_pydatetime().date(),
                                         trading_hour_status=trading_hour_status
                                         )

            print("\n\n", "backtest_parameters:", backtest_result, "\n\n--------")
            return backtest_result

    def plot_pnl_compare(self, df: pd.DataFrame):
        import matplotlib.pyplot as plt

        # Convert the ratios to percentages
        # df['pre_analysis_result.possible_pnl_ratio'] *= 100
        # df['rag_analysis_result.possible_pnl_ratio'] *= 100
        df['pre_analysis_pnl_ratio'] *= 100
        df['rag_pnl_ratio'] *= 100

        # Plot the data
        plt.figure(figsize=(14, 8))
        # plt.plot(df['ticker'], df['pre_analysis_result.possible_pnl_ratio'], label='Pre Analysis PnL Ratio', marker='o')
        # plt.plot(df['ticker'], df['rag_analysis_result.possible_pnl_ratio'], label='RAG Analysis PnL Ratio', marker='o')
        plt.plot(df['ticker'], df['pre_analysis_pnl_ratio'], label='Pre Analysis Backtest PnL Ratio', marker='o')
        plt.plot(df['ticker'], df['rag_pnl_ratio'], label='RAG Analysis Backtest PnL Ratio', marker='o')

        plt.xlabel('Ticker')
        plt.ylabel('PnL Ratio (%)')
        plt.title('PnL Ratio Comparison')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    cpc = ChatbotPerformanceComparison()
    # collection_parameter_analysis = asyncio.run(cpc.run_analysis_from_csv())
    # df_backtest_result = cpc.run_backtest(collection_parameter_analysis)
    # df_backtest_result.to_csv('backtest_results.csv', index=False)
    # print(df_backtest_result)

    df = pd.read_csv("backtest_results.csv")
    cpc.plot_pnl_compare(df)
