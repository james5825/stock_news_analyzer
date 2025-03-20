import json
import os
import time
from typing import Optional, List

import pandas as pd
import requests

from jtools.stock_news.config import Config, significant_companies
from jtools.stock_news.news_downloader.model_news_article_na import NewsAPIArticle


class NewsCache:
    """Handles caching of news articles."""
    CACHE_DIR = Config.NEWSAPI_CACHE_DIR

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)

    def _get_cache_filename(self, query: str) -> str:
        """Generate cache file name based on query parameters."""
        return os.path.join(self.CACHE_DIR, f"{query}.csv")

    def load_from_cache(self, ticker: str, from_date: str, to_date: str) -> Optional[List[NewsAPIArticle]]:
        """Load cached news data if available and map it to NewsAPIArticle objects."""
        filename = self._get_cache_filename(ticker)
        if os.path.exists(filename):
            df = pd.read_csv(filename)

            df['published_at'] = pd.to_datetime(df['published_at'], format='%Y-%m-%dT%H:%M:%SZ')
            from_date = pd.to_datetime(from_date)
            to_date = pd.to_datetime(to_date)

            df_filtered = df[(df['published_at'] >= from_date) & (df['published_at'] <= to_date)]
            return self._map_cached_data(df_filtered)
        return None

    def save_to_cache(self, ticker: str, data: List[NewsAPIArticle]) -> None:
        """Save news data to cache."""
        filename = self._get_cache_filename(ticker)
        if os.path.exists(filename):
            df_existing = pd.read_csv(filename)
        else:
            df_existing = pd.DataFrame()

        new_data = pd.DataFrame([article.to_dict() for article in data])
        new_data['key'] = new_data['title'].str[:25]

        new_data = self.clean_data(new_data)

        if not df_existing.empty:
            df_existing['key'] = df_existing['title'].str[:25]
            df_combined = pd.concat([df_existing, new_data]).drop_duplicates(subset='key', keep='last')
        else:
            df_combined = new_data

        df_combined.to_csv(filename, index=False, mode='a', header=not os.path.exists(filename))

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the data by removing empty content/description and cleaning text."""
        # if the content or description is empty or empty string, remove the row
        data = data[(data['content'].notna()) & (data['content'] != '')]
        data = data[(data['description'].notna()) & (data['description'] != '')]
        # remove (Bloomberg) in content and description
        data['content'] = data['content'].str.replace(r'\(Bloomberg\)', '', regex=True)
        data['description'] = data['description'].str.replace(r'\(Bloomberg\)', '', regex=True)
        return data

    def _map_cached_data(self, df: pd.DataFrame) -> List[NewsAPIArticle]:
        """Convert cached DataFrame into list of NewsAPIArticle objects."""
        return [
            NewsAPIArticle(
                source=row["source"],
                author=row["author"],
                title=row["title"],
                description=row["description"],
                url=row["url"],
                published_at=row["published_at"],
                content=row["content"]
            ) for _, row in df.iterrows()
        ]


class NewsAPIClient:
    """A client for fetching news from NewsAPI with local caching."""

    BASE_URL = Config.NEWSAPI_BASE_URL

    def __init__(self):
        self.api_key = Config.NEWSAPI_API_KEY
        if not self.api_key:
            raise ValueError("API key not found. Ensure NEWSAPI_API_KEY is set in .env file.")
        self.cache = NewsCache()

    def get_news(self, ticker: str, from_date=None, to_date=None, language='en', sort_by='publishedAt') -> list[NewsAPIArticle] | None:
        """Fetch news based on query parameters with caching."""
        cached_data = self.cache.load_from_cache(ticker, from_date, to_date)
        if cached_data is not None:
            return cached_data

        return self.download_news(ticker, from_date, to_date, language, sort_by)

    def download_news(self, ticker, from_date=None, to_date=None, language='en', sort_by='publishedAt', page_size=100, page=1) -> Optional[list[NewsAPIArticle]]:
        """Download news from NewsAPI."""
        params = {
            'q': significant_companies[ticker]["name"],
            'from': from_date,
            'to': to_date,
            'language': language,
            'sortBy': sort_by,
            'page': page,
            'pageSize': page_size,
            'apiKey': self.api_key
        }

        response = requests.get(self.BASE_URL, params=params)
        if response.status_code == 200:
            mapped_articles = self._map_response(response.json())
            self.cache.save_to_cache(ticker, mapped_articles)
            return mapped_articles
        else:
            response.raise_for_status()

    @staticmethod
    def _map_response(response_data):
        """Map API response to structured JSON."""
        articles = response_data.get("articles", [])
        return [
            NewsAPIArticle(
                source=article.get("source", {}).get("name"),
                author=article.get("author"),
                title=article.get("title"),
                description=article.get("description"),
                url=article.get("url"),
                published_at=article.get("publishedAt"),
                content=article.get("content")
            ) for article in articles
        ]


if __name__ == "__main__":
    api_client = NewsAPIClient()
    # Download ALL
    for company_ticker, company_info in significant_companies.items():
        for days in range(28, 0, -3):
            # from_date_l = "2025-03-13"
            # to_date_l = "2025-03-14"
            from_date_l = (pd.Timestamp.today() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
            to_date_l = (pd.Timestamp.today() - pd.Timedelta(days=days - 3)).strftime('%Y-%m-%d')

            news_data = api_client.download_news(ticker=company_ticker, from_date=from_date_l, to_date=to_date_l)
            print(company_ticker, ", FROM:", from_date_l, ", TO:", to_date_l, ", news number: ", len(news_data))
            time.sleep(3)

    # news_data = api_client.get_news("AAPL", from_date="2025-03-13", to_date="2025-03-14")
    print(json.dumps([article.to_dict() for article in news_data], indent=4))
