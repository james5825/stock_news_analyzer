import json

import dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents._generated.models import VectorizedQuery
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes._generated.models import HnswAlgorithmConfiguration
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType, VectorSearch, VectorSearchProfile,
    SemanticConfiguration, SemanticPrioritizedFields, SemanticField, SemanticSearch, SimpleField
)
from llama_index.embeddings.ollama import OllamaEmbedding

from config import Config
from embedding_kits.model_news_impact_analysis import NewsAnalysisDoc
from new_analyzer.model_news_impact_analysis_result import NewsImpactAnalysisResult
from news_downloader.model_news_article import NewsArticle
from news_downloader.model_news_article_na import NewsAPIArticle
from stock_price.back_tester import BacktestResult
from stock_price.trading_date_calculator import TradingHourStatus


class AzureSearchManager:
    def __init__(self, endpoint=Config.AZURE_SEARCH_ENDPOINT, key=Config.AZURE_SEARCH_KEY, index_name=Config.AZURE_SEARCH_INDEX):
        self.index_name = index_name
        self.index_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        self.search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))
        self.embedding_model = OllamaEmbedding(model_name=Config.OLLAMA_MODEL_EMBEDDING)
        self.ensure_index_exists()

    def ensure_index_exists(self):
        """Ensure that the search index exists, otherwise create it."""
        try:
            self.index_client.get_index(self.index_name)
        except Exception:
            self.create_index()

    def create_index(self):
        """Creates an Azure AI Search index with vector search support."""
        fields = [
            SearchField(name="id", type=SearchFieldDataType.String, key=True, sortable=True),
            SearchField(name="sector", type=SearchFieldDataType.String, searchable=True, sortable=True, filterable=True),
            SearchField(name="ticker", type=SearchFieldDataType.String, searchable=True, sortable=True, filterable=True),

            SearchField(name="title", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            SimpleField(name="publish_at", type=SearchFieldDataType.DateTimeOffset, sortable=True, filterable=True),
            SimpleField(name="url", type=SearchFieldDataType.String, searchable=False, retrievable=True),
            SearchField(name="source", type=SearchFieldDataType.String, searchable=True, sortable=True, filterable=True),

            # Trading hour status
            SearchField(name="next_trading_open", type=SearchFieldDataType.DateTimeOffset, sortable=True, filterable=True),
            SearchField(name="is_in_trading_hour", type=SearchFieldDataType.Boolean, sortable=True, filterable=True),
            SearchField(name="is_same_day_before_trading_hour", type=SearchFieldDataType.Boolean, sortable=True, filterable=True),
            SearchField(name="is_same_day_after_trading_hour", type=SearchFieldDataType.Boolean, sortable=True, filterable=True),
            SearchField(name="is_in_weekend", type=SearchFieldDataType.Boolean, sortable=True, filterable=True),
            SearchField(name="is_in_holiday", type=SearchFieldDataType.Boolean, sortable=True, filterable=True),
            SearchField(name="hours_before_open", type=SearchFieldDataType.Double, sortable=True, filterable=True),

            SearchField(name="position_movement", type=SearchFieldDataType.String, searchable=True, sortable=True, filterable=True),
            SimpleField(name="impact_days_min", type=SearchFieldDataType.Int32, searchable=False, retrievable=True, sortable=True, filterable=True),
            SimpleField(name="impact_days_max", type=SearchFieldDataType.Int32, searchable=False, retrievable=True, sortable=True, filterable=True),
            SimpleField(name="impact_weight", type=SearchFieldDataType.Int32, searchable=True, retrievable=True, sortable=True, filterable=True),

            SimpleField(name="pnl_ratio", type=SearchFieldDataType.Double, searchable=True, retrievable=True, filterable=True),

            SearchField(name="combined_fields_vector",
                        searchable=True,
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        vector_search_dimensions=4096,
                        vector_search_profile_name="vector-config")
        ]

        vector_config = VectorSearch(
            profiles=[VectorSearchProfile(name="vector-config", algorithm_configuration_name="algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="algorithms-config")],
        )

        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")]
            ),
        )

        semantic_search = SemanticSearch(configurations=[semantic_config])

        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_config, semantic_search=semantic_search)
        self.index_client.create_index(index)
        print(f"✅ Successfully created Azure Search index: {self.index_name}")

    def generate_embedding(self, text: str):
        """Generate embedding for a given text using Ollama and LlamaIndex."""
        embedding = self.embedding_model.get_text_embedding(text)
        return embedding  # Ensuring consistency between vector and embedding

    def insert_document(self, sector: str, ticker: str, article: NewsArticle, trading_hour_status: TradingHourStatus, analysis_result: NewsImpactAnalysisResult, backtest_result: BacktestResult):
        """Insert document into Azure AI Search with vector embedding."""
        embedding = self.generate_embedding(article.get_content_for_embedding())
        total_count = self.get_total_document_count()

        doc_id = f"doc_{total_count + 1}"

        if isinstance(article, NewsAPIArticle):
            article: NewsAPIArticle = article

            doc = {
                "@search.action": "mergeOrUpload",
                "id": doc_id,
                "sector": sector,
                "ticker": ticker,

                "title": article.title,
                "content": article.content,
                "publish_at": article.published_at,
                "url": article.url,
                "source": article.source,

                "next_trading_open": trading_hour_status.next_trading_open,
                "is_in_trading_hour": trading_hour_status.is_in_trading_hour,
                "is_same_day_before_trading_hour": trading_hour_status.is_same_day_before_trading_hour,
                "is_same_day_after_trading_hour": trading_hour_status.is_same_day_after_trading_hour,
                "is_in_weekend": trading_hour_status.is_in_weekend,
                "is_in_holiday": trading_hour_status.is_in_holiday,
                "hours_before_open": trading_hour_status.hours_before_open,

                "position_movement": analysis_result.position_movement,
                "impact_days_min": analysis_result.impact_days_min,
                "impact_days_max": analysis_result.impact_days_max,
                "impact_weight": analysis_result.impact_weight,

                "pnl_ratio": backtest_result.total_pnl_ratio,
                "combined_fields_vector": embedding  # Using the embedding for vector field
            }
            self.search_client.upload_documents(documents=[doc])
            print(f"Inserted document {doc_id} into Azure AI Search.")

    def search_similar_documents(self, query: str, top_k: int = 5):
        """Search for similar documents using vector search in Azure AI Search."""
        v_search_vector = VectorizedQuery(vector=self.generate_embedding(query), k_nearest_neighbors=top_k, fields="combined_fields_vector")

        results = self.search_client.search(
            search_text="*",
            vector_queries=[v_search_vector],
            include_total_count=True,
        )

        return [NewsAnalysisDoc(**doc) for doc in results]

    def get_total_document_count(self):
        """Get the total count of documents in the index."""
        results = self.search_client.search(search_text="*", include_total_count=True)
        return results.get_count()


if __name__ == "__main__":
    dotenv.load_dotenv()
    azure_search = AzureSearchManager(Config.AZURE_SEARCH_ENDPOINT, Config.AZURE_SEARCH_KEY, Config.AZURE_SEARCH_INDEX)
    # azure_search.insert_document(
    #     sector="Technology",
    #     ticker="MSFT",
    #     article=NewsAPIArticle(
    #         source="Example Source",
    #         author="Author Name",
    #         title="AI in Finance",
    #         description="Exploring the impact of AI on financial markets.",
    #         url="http://example.com",
    #         published_at="2022-01-01T00:00:00Z",
    #         content="Full content of the article."
    #     ),
    #     trading_hour_status=TradingHourStatus(
    #         next_trading_open="2022-01-03T09:30:00Z",
    #         is_in_trading_hour=False,
    #         is_same_day_before_trading_hour=False,
    #         is_same_day_after_trading_hour=False,
    #         is_in_weekend=False,
    #         is_in_holiday=False,
    #         hours_before_open=48
    #     ),
    #     analysis_result=NewsImpactAnalysisResult(
    #         position_movement="long",
    #         impact_days_min=1,
    #         impact_days_max=5,
    #         impact_weight=3
    #     ),
    #     backtest_result=BacktestResult(
    #         total_pnl_ratio=0.775,
    #         total_pnl=775.0
    #     )
    # )
    search_results = azure_search.search_similar_documents("Level Financial Advisors Purchases 688 Shares of Amazon.co")

    print(json.dumps([doc.__dict__ for doc in search_results], indent=2))