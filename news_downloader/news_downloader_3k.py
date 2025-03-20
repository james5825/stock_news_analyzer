import requests
from bs4 import BeautifulSoup
from newspaper import Article, build

class NewsDownloader3K:
    def __init__(self, url):
        self.url = url
        self.supported = self.check_news_support()

    def check_news_support(self):
        """
        Checks if the website is supported by newspaper3k.
        """
        try:
            paper = build(self.url, memoize_articles=False)
            return paper.size() > 0  # If articles are found, it's supported
        except Exception as e:
            print(f"Error checking support for {self.url}: {e}")
            return False

    def fetch_with_newspaper3k(self):
        """
        Fetches news content using newspaper3k.
        """
        try:
            article = Article(self.url)
            article.download()
            article.parse()
            return article
        except Exception as e:
            print(f"newspaper3k failed: {e}")
            return None

    def fetch_with_bs4(self):
        """
        Fetches news content using BeautifulSoup if newspaper3k fails.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(self.url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = soup.find_all('p')
                content = "\n".join([p.get_text() for p in paragraphs])
                return f"Extracted using BeautifulSoup:\n\n{content}"
            else:
                return f"Failed to fetch page: Status Code {response.status_code}"
        except Exception as e:
            return f"BeautifulSoup failed: {e}"

    def get_article_parsed(self):
        """
        Fetches the news content based on the site's compatibility.
        """
        if self.supported:
            print("\nUsing newspaper3k...")
            article = self.fetch_with_newspaper3k()
            if article:
                return article

        print("\nUsing BeautifulSoup as a fallback...")
        return self.fetch_with_bs4()


# Continuous Loop for Testing
if __name__ == "__main__":
    while True:
        url = input("\nEnter the news article URL (or type 'exit' to quit): ")
        if url.lower() == "exit":
            print("Exiting the program...")
            break

        fetcher = NewsDownloader3K(url)
        content = fetcher.get_article_content()
        print("\n" + content[:1000])  # Print first 1000 characters for preview
