from semantic_kernel.functions.kernel_function_decorator import kernel_function


class StockNewsAnalysisPlugin:

    @kernel_function(name="analyze_stock_news", description="Analyze stock news for market impact."
                                                            "Parameters:"
                                                            "- position_movement: A string indicating whether the expected market movement suggests a \"long\" or \"short\" position."
                                                            "- impact_weight: An integer from 1 to 10 representing the expected significance of the news on financial markets."
                                                            "- impact_days_min: The minimum number of days the impact is expected to last."
                                                            "- impact_days_max: The maximum number of days the impact is expected to persist."
                                                            "- news_summery: A summery of the news article in around 250 words.")
    async def analyze_stock_news(self, position_movement: str, impact_weight: int, minimum_impact_days: int, maximum_impact_days: int, news_summery: str) -> dict:
        """Fetches weather information for a given city, date, and time."""
        params = {
            "position_movement": position_movement,
            "impact_weight": impact_weight,
            "minimum_impact_days": minimum_impact_days,
            "maximum_impact_days": maximum_impact_days,
            "news_summery": news_summery
        }
        return params

