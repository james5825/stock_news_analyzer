from newspaper import Article
from semantic_kernel.functions import kernel_function

from news_downloader.news_downloader_3k import NewsDownloader3K


class NewsDownloader3kPlugin:

    ######## for SK to get parameters
    @kernel_function(name="fetch_news_from_url",
                     description="Fetch news from the url. "
                                 "Parameters: - url: A string url of the news article.")
    async def fetch_news_from_url(self, url: str) -> Article:

        return await self.fetch_news_from_url(url)

    ######## for dev to call the function
    @staticmethod
    async def fetch_news_from_url_wrapper(url: str) -> Article:
        nd3k = NewsDownloader3K(url)
        if nd3k.check_news_support():
            news_article = nd3k.get_article_parsed().text
        else:
            news_article = nd3k.get_article_parsed()

        return news_article

    @kernel_function(name="is_news_content_normal",
                     description="Check the news content is normal. "
                                 "Parameters: - is_news_blocked: A boolean indicating whether the news is block by network or provider. "
                                 "For example, 1. content is blocked by paywall. 2. Status Code 403, Status Code 404, etc.")
    def is_news_content_normal(self, is_news_blocked: bool) -> bool:
        return is_news_blocked
