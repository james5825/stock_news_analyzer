from typing import List

from embedding_kits.model_news_impact_analysis import NewsAnalysisDoc
from new_analyzer.model_news_impact_analysis_result import NewsImpactAnalysisResult


class LLMTextComposer:
    @staticmethod
    def compose_analysis_for_response(pre_analysis_result: NewsImpactAnalysisResult) -> str:
        composed_response = (
            f"Impact Weight: {pre_analysis_result.impact_weight}/10\n"
            f"Position Movement: {pre_analysis_result.position_movement}\n"
            f"Impact Duration: {pre_analysis_result.impact_days_min}-{pre_analysis_result.impact_days_max} days\n"
        )
        return composed_response

    @staticmethod
    def compose_related_news_pnl_ratio_for_llm(search_result: list[NewsAnalysisDoc]) -> str:
        composed_string = ("Please also consider the following related news, But don't analysis them"
                           "Only consider they are examples as they pressed and how they impact the market:\n\n")
        for doc in search_result:
            composed_string += (f"News Title: {doc.title}\n"
                                f"PNL Ratio: {doc.pnl_ratio}\n"
                                f"Impact Days Min: {doc.impact_days_min}\n"
                                f"Impact Days Max: {doc.impact_days_max}\n\n")
        return composed_string

    @staticmethod
    def calculate_related_news_pnl_ratio(related_news_docs: List[NewsAnalysisDoc]) -> dict:
        pnl_ratios = [doc.pnl_ratio for doc in related_news_docs]
        min_impact_days = [doc.impact_days_min for doc in related_news_docs]
        max_impact_days = [doc.impact_days_max for doc in related_news_docs]

        pnl_ratio_max = max(pnl_ratios)
        pnl_ratio_min = min(pnl_ratios)
        pnl_ratio_avg = sum(pnl_ratios) / len(pnl_ratios)

        min_impact_days_max = max(min_impact_days)
        min_impact_days_min = min(min_impact_days)
        min_impact_days_avg = sum(min_impact_days) / len(min_impact_days)

        max_impact_days_max = max(max_impact_days)
        max_impact_days_min = min(max_impact_days)
        max_impact_days_avg = sum(max_impact_days) / len(max_impact_days)

        return {
            "pnl_ratio_max": pnl_ratio_max,
            "pnl_ratio_min": pnl_ratio_min,
            "pnl_ratio_avg": pnl_ratio_avg,
            "min_impact_days_max": min_impact_days_max,
            "min_impact_days_min": min_impact_days_min,
            "min_impact_days_avg": min_impact_days_avg,
            "max_impact_days_max": max_impact_days_max,
            "max_impact_days_min": max_impact_days_min,
            "max_impact_days_avg": max_impact_days_avg,
        }
