import os
import pandas as pd
import yfinance as yf

from config import significant_companies


class StockPriceDataDownloader:
    def __init__(self, ticker: str, start: str, end: str) -> None:
        """
        Initialize the stock price data downloader.
        :param ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        :param start: Start date (format: YYYY-MM-DD)
        :param end: End date (format: YYYY-MM-DD)
        """
        self.ticker = ticker
        self.start = start
        self.end = end
        self.data = None
        self.folder = "data_stock_price"
        os.makedirs(self.folder, exist_ok=True)

    def get_filename(self) -> str:
        """Generate the storage filename following Backtrader CSV format."""
        # period = f"{self.start}_to_{self.end}"
        return os.path.join(self.folder, f"{self.ticker}.csv")

    def get_price_data_in_range(self, start_date_str: str, end_date_str: str) -> pd.DataFrame:
        """Get stock price data within the specified date range."""
        self.fetch_data(from_cache=True)

        self.data.set_index("Date", inplace=True)
        self.data = self.data.sort_index()
        # TODO: temporary fix for date range issue, manual remove lines of Ticker, the download api would fix in the future
        price_data_in_range = self.data.loc[start_date_str:end_date_str]
        return price_data_in_range

    def fetch_data(self, from_cache: bool = True) -> None:
        """Fetch stock data from cache if available; otherwise, download from Yahoo Finance and save it."""
        filename = self.get_filename()
        self.data = None

        if from_cache and os.path.exists(filename):
            print("Loading data from cache...")
            self.data = pd.read_csv(filename, parse_dates=["Date"], header=0)
            # self.data = pd.read_csv(filename, index_col='Date', parse_dates=True)

            # Check if date range is covered
            if not self.is_date_range_covered():
                print("Date range not fully covered, fetching missing data...")
                self.download_and_append_data()
            else:
                print("Date range fully covered.")
        else:
            print("Fetching new data from Yahoo Finance...")
            self.download_and_append_data()

    def is_date_range_covered(self) -> bool:
        """Check if the date range is fully covered in the cached data."""
        if self.data is not None:
            data_start = self.data['Date'].min().date()
            data_end = self.data['Date'].max().date()
            return data_start <= pd.to_datetime(self.start).date() and data_end >= pd.to_datetime(self.end).date()
        return False

    def download_and_append_data(self) -> None:
        """Download missing data and append to existing data."""
        try:
            new_data = yf.download(self.ticker, start=self.start, end=self.end)
            if new_data.empty:
                print("No data retrieved, please check the ticker or date range.")
            else:
                new_data.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }, inplace=True)
                if 'Adj Close' in new_data.columns:
                    new_data.rename(columns={'Adj Close': 'adj_close'}, inplace=True)
                else:
                    new_data['adj_close'] = new_data['close']
                new_data.reset_index(inplace=True)

                if self.data is not None:
                    new_data = self.pre_process_data(new_data)
                    self.data = pd.concat([self.data, new_data]).drop_duplicates(subset='Date').sort_values(by='Date')
                else:
                    self.data = new_data

                self.save_to_csv(self.data)
        except Exception as e:
            print(f"Error occurred while downloading data: {e}")

    @staticmethod
    def pre_process_data(data: pd.DataFrame) -> pd.DataFrame | None:
        """
        Return formatted stock data for Backtrader CSV format.
        :param data: DataFrame containing raw stock data.
        :return: DataFrame containing Datetime, Open, High, Low, Close, Volume, and Adjusted Close.
        """
        if data is not None:
            clean_step_df = data[['Date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']].copy()
            # Ensure no duplicate headers in the CSV file
            if isinstance(clean_step_df.columns, pd.MultiIndex):
                clean_step_df.columns = clean_step_df.columns.get_level_values(0)  # Flatten MultiIndex if it exists
            clean_step_df.columns.name = None
            clean_step_df.reset_index(drop=True, inplace=True)  # Remove index
            return clean_step_df
        else:
            print("Data not provided.")
            return None

    def save_to_csv(self, df) -> None:
        """Save the stock data to a CSV file in Backtrader format, removing any extra headers if needed."""
        filename = self.get_filename()
        if self.data is not None:
            if df is not None:
                df.sort_values(by='Date', inplace=True)  # Sort by Date before saving
                df.to_csv(filename, index=False)
                print(f"Data saved to {filename}")
        else:
            print("No data available to save.")


# Example usage
if __name__ == "__main__":
    for company_ticker in significant_companies.keys():
        start_date = "2024-01-01"
        end_date = "2025-03-17"

        stock_downloader = StockPriceDataDownloader(company_ticker, start_date, end_date)
        stock_downloader.fetch_data(from_cache=True)
        df_processed = stock_downloader.data

        if df_processed is not None:
            print(f"{company_ticker} stock data:")
            print(df_processed.head())
