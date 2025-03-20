from newspaper import Article
from semantic_kernel.functions import kernel_function

from news_downloader.news_downloader_3k import NewsDownloader3K


class NewsDownloader3kPlugin:

    @kernel_function(name="is_news_blocked",
                     description="Fetch news from the url. Parameters: - url: A string indicating whether the expected market movement suggests a \"long\" or \"short\" position.")
    async def is_news_blocked(self, url: str) -> Article:

        return await self.fetch_news_from_url(url)

    @staticmethod
    async def fetch_news_from_url_wraper(url: str) -> Article:
        nd3k = NewsDownloader3K(url)
        if nd3k.check_news_support():
            news_article = nd3k.get_article_parsed().text
        else:
            news_article = nd3k.get_article_parsed()

        return news_article
