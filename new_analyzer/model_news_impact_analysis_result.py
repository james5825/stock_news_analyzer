class NewsImpactAnalysisResult:
    def __init__(self, position_movement: str, impact_weight: int, impact_days_min: int, impact_days_max: int, news_summery: str, possible_pnl_ratio: float = 0.0):
        self.position_movement = position_movement
        self.impact_weight = impact_weight
        self.impact_days_min = impact_days_min
        self.impact_days_max = impact_days_max
        self.news_summery = news_summery
        self.possible_pnl_ratio = possible_pnl_ratio

    @classmethod
    def from_dict(cls, data: dict):
        try:
            impact_weight = int(data.get("impact_weight", 1) or 1)
            impact_days_min = int(data.get("minimum_impact_days", 1) or 1)
            impact_days_max = int(data.get("maximum_impact_days", 1) or 1)

            if not (1 <= impact_weight <= 10 and 0 <= impact_days_min <= 10 and 0 <= impact_days_max <= 10):
                return None
            possible_pnl_ratio = float(data.get("possible_pnl_ratio", 0.0) or 0.0)
        except ValueError:
            return None

        return cls(
            position_movement=data.get("position_movement"),
            impact_weight=impact_weight,
            impact_days_min=impact_days_min,
            impact_days_max=impact_days_max,
            possible_pnl_ratio=possible_pnl_ratio,
            news_summery=data.get("news_summery")
        )

    def __repr__(self):
        return (f"AnalysisResult(position_movement={self.position_movement}, "
                f"impact_weight={self.impact_weight}, impact_days_min={self.impact_days_min}, "
                f"impact_days_max={self.impact_days_max})"
                f"news_summery={self.news_summery}")
