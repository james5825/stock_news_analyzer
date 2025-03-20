import re

from news_downloader.model_news_article import NewsArticle


class NewsAPIArticle(NewsArticle):
    """Represents a news article with structured data."""

    def get_content_for_llm(self) -> str:
        return (f"Title: {self.title}\n\n"
                f"Content: {self.content}")

    def get_content_for_embedding(self) -> str:
        return (f"{self.title}\n\n"
                f"{self.content}")

    def __init__(self, source, author, title, description, url, published_at, content):
        super().__init__(published_at)
        self.source = source
        self.author = author
        self.title = title
        self.description = self._clean_text(description)
        self.url = url
        self.published_at = published_at
        self.content = self._clean_text(content)

    @staticmethod
    def _clean_text(content):
        """Remove unwanted patterns from content and replace special characters."""
        if content and isinstance(content, str) and content != "":
            content = re.sub(r'\[\+\d+ chars\]', '', content).strip()
            content = re.sub(r'\[\+\]', '', content).strip()
            content = content.replace('\u2013', '-').replace('\u2026', '...').replace('\u2019', "'")
        return content

    def to_dict(self):
        """Convert article object to dictionary."""
        return {
            "source": self.source,
            "author": self.author,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "published_at": self.published_at,
            "content": self.content
        }
