import asyncio

from semantic_kernel.connectors.ai import PromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
from semantic_kernel.contents import FunctionCallContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.kernel import Kernel

from new_analyzer.model_news_impact_analysis_result import NewsImpactAnalysisResult
from new_analyzer.stock_news_analysis_plugin import StockNewsAnalysisPlugin
from news_downloader.model_news_article import NewsArticle
from news_downloader.news_downloader_na import NewsAPIClient
from stock_price.trading_date_calculator import TradingHourStatus, TradingDateCalculator


class NewsAnalyzer:
    """Class responsible for analyzing news articles."""

    def __init__(self):
        self.kernel = Kernel()
        self.chat_completion_service = OllamaChatCompletion(
            service_id="ollama",
            # ai_model_id="deepseek-r1:14b",
            ai_model_id="llama3.2",
        )
        self.kernel.add_plugin(StockNewsAnalysisPlugin(), "StockNewsAnalysisPlugin")
        self.settings = PromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False),
        )
        self.system_message = self._load_system_message()

    @staticmethod
    def _load_system_message() -> str:
        with open('../prompts/news_analyzer_system_instruction_na.txt', 'r') as file:
            return file.read()

    async def get_parameters(self, article: NewsArticle, trading_hour_status: TradingHourStatus) -> NewsImpactAnalysisResult:
        """Extract parameters from the given article."""
        chat_history = ChatHistory()
        chat_history.add_system_message(self.system_message)

        chat_history.add_user_message(article.get_content_for_llm() +
                                      f"\n\nNews Publish Time Comments: {trading_hour_status.get_publication_comment(article.published_at)}"
                                      "\n\nProvide a JSON response with keys: "
                                      "impact_weight (1-10), "
                                      "position_movement (long or short), "
                                      "impact_days_min, and impact_days_max.")

        response = await self.chat_completion_service.get_chat_message_content(
            chat_history, self.settings, kernel=self.kernel)
        function_call_content = response.items[0]

        if isinstance(function_call_content, FunctionCallContent) :
            converted_params = NewsImpactAnalysisResult.from_dict(function_call_content.arguments)
        else:
            print("\n","######## CAN'T Analysis")
            print(function_call_content)
            print(article.get_content_for_llm(), '\n')
            converted_params = None
        return converted_params
        # return function_call_content


if __name__ == "__main__":
    api_client = NewsAPIClient()
    news_data = api_client.get_news("AAPL", from_date="2025-03-01", to_date="2025-03-02")

    if not news_data:
        print("No relevant news found for the given timeframe.")
    else:
        # av_news_instance.display_news(news_data)
        news_analyzer = NewsAnalyzer()
        loop = asyncio.get_event_loop()

        for news_article in news_data[:3]:
            trading_hour_status_l = TradingDateCalculator.get_trading_hour(timestamp=news_article.published_at)
            analysis_result = loop.run_until_complete(news_analyzer.get_parameters(news_article, trading_hour_status_l))

            if analysis_result:
                print("date", news_article.published_at)
                print("Analysis Result:", analysis_result)
