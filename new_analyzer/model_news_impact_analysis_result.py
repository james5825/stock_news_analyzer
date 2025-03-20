class NewsImpactAnalysisResult:
    def __init__(self, position_movement: str, impact_weight: int, impact_days_min: int, impact_days_max: int, news_summery: str):
        self.position_movement = position_movement
        self.impact_weight = impact_weight
        self.impact_days_min = impact_days_min
        self.impact_days_max = impact_days_max
        self.news_summery = news_summery

    @classmethod
    def from_dict(cls, data: dict):
        try:
            impact_weight = int(data.get("impact_weight", 0) or 0)
            impact_days_min = int(data.get("minimum_impact_days", 0) or 0)
            impact_days_max = int(data.get("maximum_impact_days", 0) or 0)

            if not (1 <= impact_weight <= 10 and 1 <= impact_days_min <= 10 and 1 <= impact_days_max <= 10):
                return None
        except ValueError:
            return None

        return cls(
            position_movement=data.get("position_movement"),
            impact_weight=impact_weight,
            impact_days_min=impact_days_min,
            impact_days_max=impact_days_max,
            news_summery=data.get("news_summery")
        )

    def __repr__(self):
        return (f"AnalysisResult(position_movement={self.position_movement}, "
                f"impact_weight={self.impact_weight}, impact_days_min={self.impact_days_min}, "
                f"impact_days_max={self.impact_days_max})"
                f"news_summery={self.news_summery}")
