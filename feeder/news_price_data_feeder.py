import asyncio
from datetime import timedelta

import pytz

from config import Config, DataFeedConfig, significant_companies
from embedding_kits.stock_news_embedding import AzureSearchManager
from new_analyzer.news_analyzer import NewsAnalyzer
from news_downloader.news_downloader_na import NewsAPIClient
from stock_price.back_tester import BacktestRunner
from stock_price.stock_price_data_downloader import StockPriceDataDownloader
from stock_price.trading_date_calculator import TradingDateCalculator

########
azure_search = AzureSearchManager(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX)

api_client = NewsAPIClient()


async def start_data_feed():
    # 1. download news data for significant companies
    news_data = {}
    for company_ticker, company_info in list(significant_companies.items()):
        news_data[company_ticker] = api_client.cache.load_from_cache(company_ticker, from_date=DataFeedConfig.EMBEDDING_DATE_FROM, to_date=DataFeedConfig.EMBEDDING_DATE_TO)

    # 2. send to llm to analyze parameters -> ticker, sector, position_movement, impact_days_min, impact_days_max, impact_weight
    news_analyzer = NewsAnalyzer()
    for company_ticker, articles in news_data.items():
        if not articles:
            continue
        for article in articles:

            article_date = article.published_at.tz_localize('UTC').astimezone(pytz.timezone('US/Eastern'))

            print("Article:", article.title)
            print("published_at_UTC:", article.published_at)
            print("published_at_ET:", article_date)

            # 3.1 get trading hour
            trading_hour_status = TradingDateCalculator.get_trading_hour(article_date)

            print(f" is open?: {trading_hour_status.is_in_trading_hour}", '\n')
            print(f" Next Trading Open: {trading_hour_status.next_trading_open}")

            analysis_result = await news_analyzer.get_parameters(article, trading_hour_status)
            if analysis_result:
                print("Analysis Result:", analysis_result)

                # 3.2 base trading hour status to get trading dates
                if trading_hour_status.is_in_trading_hour:
                    start_date = article_date
                else:
                    start_date = trading_hour_status.next_trading_open

                start_price_date_str = start_date.strftime("%Y-%m-%d")
                end_price_date_str = (start_date + timedelta(days=analysis_result.impact_days_max + 5)).strftime("%Y-%m-%d")

                if analysis_result and analysis_result.impact_weight > 0:
                    # 4 prepare price data
                    stock_price_downloader = StockPriceDataDownloader(company_ticker, start_price_date_str, end_price_date_str)
                    stock_price_df = stock_price_downloader.get_price_data_in_range(start_price_date_str, end_price_date_str)

                    # 5. use the parameters to do back testing get pnl
                    runner = BacktestRunner(data_frame=stock_price_df)

                    backtest_result = runner.run(impact_weight=analysis_result.impact_weight,
                                                 maximum_impact_days=analysis_result.impact_days_max,
                                                 minimum_impact_days=analysis_result.impact_days_min,
                                                 position_movement=analysis_result.position_movement,
                                                 start_trading_date=start_date.to_pydatetime().date(),
                                                 trading_hour_status=trading_hour_status
                                                 )

                    # 6. save to azure ai search index
                    azure_search.insert_document(
                        sector=significant_companies[company_ticker]["sector"],
                        ticker=company_ticker,

                        article=article,
                        trading_hour_status=trading_hour_status,
                        analysis_result=analysis_result,
                        backtest_result=backtest_result,
                    )


if __name__ == "__main__":
    asyncio.run(start_data_feed())
