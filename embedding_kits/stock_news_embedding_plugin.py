from typing import Optional, List

from semantic_kernel.functions.kernel_function_decorator import kernel_function

from embedding_kits.model_news_impact_analysis import NewsAnalysisDoc
from embedding_kits.stock_news_embedding import AzureSearchManager


class RelatedNewsPlugin:

    @kernel_function(name="get_related_stock_news", description="According to the summery provided to get related stock news."
                                                                "Parameters:"
                                                                "- news_summery: A summery of the news article."
                                                                "- ticker: The stock ticker of the company. This can be optional, if not provided, the plugin will load all news articles.")
    async def get_related_stock_news(self, news_summery: str, ticker: str) -> Optional[List[NewsAnalysisDoc]]:
        # TODO: add ticker to the search filter, or do the logic later after search

        return await self.get_related_stock_news_wrapper(news_summery, ticker)

    @staticmethod
    async def get_related_stock_news_wrapper(news_summery: str, ticker: str = None) -> Optional[List[NewsAnalysisDoc]]:
        # TODO: add ticker to the search filter, or do the logic later after search
        azure_search_manager = AzureSearchManager()
        results = azure_search_manager.search_similar_documents(query=news_summery)

        return results
