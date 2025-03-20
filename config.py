import os

import dotenv

dotenv.load_dotenv()
class Config:
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    AZURE_SEARCH_INDEX = "stock-news-index-dev"
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

    NEWSAPI_BASE_URL = os.getenv("NEWSAPI_BASE_URL")
    NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
    NEWSAPI_CACHE_DIR = os.getenv("NEWSAPI_CACHE_DIR")

    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    ALPHA_VANTAGE_LIMIT = os.getenv("ALPHA_VANTAGE_LIMIT")

    BROKER_STARTING_CASH = int(os.getenv("BROKER_STARTING_CASH"))

    aoi_deployment_name = os.getenv('AZURE_DEPLOYMENT_NAME')
    aoi_api_key = os.getenv('AZURE_OPENAI_KEY')
    aoi_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')  # Used to point to your
    aoi_api_version = os.getenv('AZURE_OPENAI_VERSION')

class DataFeedConfig:
    EMBEDDING_DATE_FROM = "2025-02-17"
    EMBEDDING_DATE_TO = "2025-02-28"

    BACKTEST_DATE_FROM = "2025-03-01"
    BACKTEST_DATE_TO = "2025-03-14"


significant_companies = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Communication Services"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Discretionary"},
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology"},
    "NFLX": {"name": "Netflix Inc.", "sector": "Communication Services"},
}
