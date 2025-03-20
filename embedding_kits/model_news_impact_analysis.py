class NewsAnalysisDoc:

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.sector = kwargs.get('sector')
        self.ticker = kwargs.get('ticker')
        self.title = kwargs.get('title')
        self.content = kwargs.get('content')
        self.publish_at = kwargs.get('publish_at')
        self.url = kwargs.get('url')
        self.source = kwargs.get('source')
        self.next_trading_open = kwargs.get('next_trading_open')
        self.is_in_trading_hour = kwargs.get('is_in_trading_hour')
        self.is_same_day_before_trading_hour = kwargs.get('is_same_day_before_trading_hour')
        self.is_same_day_after_trading_hour = kwargs.get('is_same_day_after_trading_hour')
        self.is_in_weekend = kwargs.get('is_in_weekend')
        self.is_in_holiday = kwargs.get('is_in_holiday')
        self.hours_before_open = kwargs.get('hours_before_open')
        self.position_movement = kwargs.get('position_movement')
        self.impact_days_min = kwargs.get('impact_days_min')
        self.impact_days_max = kwargs.get('impact_days_max')
        self.impact_weight = kwargs.get('impact_weight')
        self.pnl_ratio = kwargs.get('pnl_ratio')
        self.search_score = kwargs.get('@search.score')

    def to_dict(self):
        return {
            'id': self.id,
            'sector': self.sector,
            'ticker': self.ticker,
            'title': self.title,
            'content': self.content,
            'publish_at': self.publish_at,
            'url': self.url,
            'source': self.source,
            'next_trading_open': self.next_trading_open,
            'is_in_trading_hour': self.is_in_trading_hour,
            'is_same_day_before_trading_hour': self.is_same_day_before_trading_hour,
            'is_same_day_after_trading_hour': self.is_same_day_after_trading_hour,
            'is_in_weekend': self.is_in_weekend,
            'is_in_holiday': self.is_in_holiday,
            'hours_before_open': self.hours_before_open,
            'position_movement': self.position_movement,
            'impact_days_min': self.impact_days_min,
            'impact_days_max': self.impact_days_max,
            'impact_weight': self.impact_weight,
            'pnl_ratio': self.pnl_ratio,
            'search_score': self.search_score
        }
