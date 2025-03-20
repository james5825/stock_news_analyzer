from abc import ABC, abstractmethod


class NewsArticle(ABC):
    """Abstract base class for news articles."""

    def __init__(self,  published_at: str):
        self.published_at = published_at

    @abstractmethod
    def get_content_for_llm(self) -> str:
        pass

    @abstractmethod
    def get_content_for_embedding(self) -> str:
        pass