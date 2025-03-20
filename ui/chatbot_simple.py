import json

import semantic_kernel.connectors.ai.open_ai as sk_oai  # noqa: F401
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import PromptExecutionSettings, FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from semantic_kernel.planners import SequentialPlanner

from config import Config
from embedding_kits.model_news_impact_analysis import NewsAnalysisDoc
from embedding_kits.stock_news_embedding_plugin import RelatedNewsPlugin
from new_analyzer.model_news_impact_analysis_result import NewsImpactAnalysisResult
from new_analyzer.stock_news_analysis_plugin import StockNewsAnalysisPlugin
from news_downloader.news_downloader_plugin import NewsDownloader3kPlugin


class OllamaChatBot:
    def __init__(self):
        self.gradio_chat_history = []

        # SK initialization
        self.kernel = Kernel()
        # self.chat_completion_service = OllamaChatCompletion(
        #     service_id="ollama",
        #     ai_model_id="llama3.2",
        # )
        self.chat_completion_service_open_ai = sk_oai.AzureChatCompletion(
            service_id="default",

            deployment_name=Config.aoi_deployment_name,
            api_key=Config.aoi_api_key,
            endpoint=Config.aoi_endpoint,
            api_version=Config.aoi_api_version,
        )

        # Message call settings
        self.sk_chat_history = ChatHistory()

        # tool call settings

        self.kernel.add_plugin(NewsDownloader3kPlugin(), "NewsDownloader3kPlugin")
        self.kernel.add_plugin(StockNewsAnalysisPlugin(), "StockNewsAnalysisPlugin")
        self.kernel.add_plugin(RelatedNewsPlugin(), "RelatedNewsPlugin")

    # make a get setting funciton to get different setting with different plugins
    def get_pe_settings(self, included_plugins: list[str], included_function: list[str], auto_invoke) -> PromptExecutionSettings:
        return PromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=auto_invoke)
            # .Required(filters={"included_functions": included_function}, auto_invoke=auto_invoke)
            # .Auto(auto_invoke=auto_invoke),

            # filter = {"included_plugins": included_plugins}
        )

    async def get_response_from_chat_bot_ag(self, input_message, history):
        for plugin_name, plugin in self.kernel.plugins.items():
            for function_name, function in plugin.functions.items():
                print(f"Plugin: {plugin_name}, Function: {function_name}")

        ask = (f"get the news first from {input_message}"
               f"then analyze the news"
               f"then get related news"
               f"then analyze the news again based on the related news")

        # self.kernel.add_service(self.chat_completion_service_open_ai)
        planner_c = SequentialPlanner(self.kernel, "default")
        sequential_plan = await planner_c.create_plan(goal=ask)
        print("The plan's steps are:")
        for step in sequential_plan._steps:
            print(
                f"- {step.description.replace('.', '') if step.description else 'No description'} using {step.metadata.fully_qualified_name} with parameters: {step.parameters}"
            )
        result = await sequential_plan.invoke(self.kernel)
        return result

    async def get_response_from_chat_bot(self, input_message, history):
        # Gradio history
        self.gradio_chat_history = history

        if "http://" in input_message or "https://" in input_message:
            # SK chat history & response
            # analyze what to do, but not summery
            self.sk_chat_history.add_system_message(f"always download the news ulr from {input_message} first"
                                                    f"then analyze the news"
                                                    f"then get related news"
                                                    f"then analyze the news again based on the related news")

            self.sk_chat_history.add_user_message(input_message)

            ######################## work around due to semantic kernel not support sequence call in ollama  ########################
            ######## (1) download news
            response_url = await self.chat_completion_service_open_ai.get_chat_message_content(
                Temperature=0,
                chat_history=self.sk_chat_history,
                settings=self.get_pe_settings(included_plugins=["NewsDownloader3kPlugin"], included_function=["fetch_news_from_url"], auto_invoke=False),
                kernel=self.kernel
            )
            # incoming_news_content = await NewsDownloader3kPlugin.fetch_news_from_url_wrapper(response_url.items[0].arguments["url"])
            incoming_news_content = await NewsDownloader3kPlugin.fetch_news_from_url_wrapper(json.loads(response_url.items[0].arguments)["url"])

            print("News:", incoming_news_content, "...\n\n--------\n\n")
            self.sk_chat_history.clear()

            ######## (1.5) check download news
            self.sk_chat_history.add_user_message(
                f"You are a network expert, based on the NEWS CONTENT, Check if this news is normal, everything is good\n\n"
                f"--------\n\n"
                f"NEWS CONTENT: {incoming_news_content}")
            response_is_news_block = await self.chat_completion_service_open_ai.get_chat_message_content(
                Temperature=0,
                chat_history=self.sk_chat_history,
                settings=self.get_pe_settings(included_plugins=["NewsDownloader3kPlugin"], included_function=["is_news_content_normal"], auto_invoke=False),
                kernel=self.kernel
            )

            # is_news_blocked = response_is_news_block.items[0].arguments["is_news_blocked"]

            if response_is_news_block.items[0].arguments.find('true') > 0:
                return f"The news is blocked by network or provider. ERROR_MESSAGE: {incoming_news_content}"
            self.sk_chat_history.clear()

            ######## (2) analysis incoming news (pre-analysis)
            self.sk_chat_history.add_user_message(
                "Analysis of the news article is required to determine the impact on the stock price."
                "\n\nProvide a JSON response with keys: "
                "impact_weight (1~10), "
                "position_movement (long or short), "
                "impact_days_min (1~5), and impact_days_max(1~10)."
                "--------"
                "NEWS: " + incoming_news_content[:100] + "...")

            pre_analysis_parameter_response = await self.chat_completion_service_open_ai.get_chat_message_content(
                chat_history=self.sk_chat_history,
                settings=self.get_pe_settings(included_plugins=["StockNewsAnalysisPlugin"], included_function=["analyze_stock_news"], auto_invoke=False),
                kernel=self.kernel
            )
            pre_analysis_result_str = pre_analysis_parameter_response.items[0].arguments
            pre_analysis_result = NewsImpactAnalysisResult.from_dict(json.loads(pre_analysis_result_str))

            if not pre_analysis_result:
                return "Can't analysis the news."

            print("parameters:", pre_analysis_parameter_response.items[0].arguments, "--------\n\n")
            self.sk_chat_history.clear()

            ######## (3) retrieve related news analysis
            index_search_result = await RelatedNewsPlugin.get_related_stock_news_wrapper(pre_analysis_result.news_summery)

            related_news_pnl_ratio = self.calculate_related_news_pnl_ratio(index_search_result)
            related_news_suggestion = self.compose_related_news_pnl_ratio_for_llm(index_search_result)
            self.sk_chat_history.clear()

            ######## (4) analysis incoming news (final-analysis)
            self.sk_chat_history.add_user_message(
                f"Analysis of the news article is required to determine the impact on the stock price. But not need to provide the summary."
                f"\n\nProvide a text based analysis with: "
                f"possible profit and loss ratio, "
                f"impact_weight (1-10), "
                f"position_movement (long or short), "
                f"impact_days_min (1-5), and impact_days_max(1-10)."
                f"--------\n\n"
                f"NEWS: {pre_analysis_result.news_summery}\n\n"
                f"--------\n\n"
                f"{related_news_suggestion}"
            )

            final_analysis = await self.chat_completion_service_open_ai.get_chat_message_content(
                chat_history=self.sk_chat_history,
                settings=self.get_pe_settings(included_plugins=["StockNewsAnalysisPlugin"], included_function=["analyze_stock_news"], auto_invoke=True),
                kernel=self.kernel
            )

            final_analysis_parameter = self.sk_chat_history.messages[-1].items[0].result
            post_analysis_result = NewsImpactAnalysisResult.from_dict(final_analysis_parameter)

            final_response = (f"News Summary: {pre_analysis_result.news_summery}\n\n"
                              f"Pre-Analysis: {self.compose_analysis_for_response(pre_analysis_result)}\n\n"
                              f"------------------------------------------------\n\n"
                              f"With related News Analysis: {final_analysis.content}\n\n"
                              f"Analysis Parameters: {self.compose_analysis_for_response(post_analysis_result)}\n\n"
                              )
            self.sk_chat_history.clear()
            self.sk_chat_history.add_user_message(input_message)
            self.sk_chat_history.add_assistant_message(final_response)

            return final_response
        else:
            other_chat = await self.chat_completion_service_open_ai.get_chat_message_content(
                chat_history=self.sk_chat_history,
                settings=self.get_pe_settings(included_plugins=["StockNewsAnalysisPlugin"], included_function=["analyze_stock_news"], auto_invoke=True),
                kernel=self.kernel
            )
            return other_chat.content

    def compose_analysis_for_response(self, pre_analysis_result: NewsImpactAnalysisResult):
        composed_response = (
            f"Impact Weight: {pre_analysis_result.impact_weight}/10\n"
            f"Position Movement: {pre_analysis_result.position_movement}\n"
            f"Impact Duration: {pre_analysis_result.impact_days_min}-{pre_analysis_result.impact_days_max} days\n"
        )
        return composed_response

    def compose_related_news_pnl_ratio_for_llm(self, search_result: NewsAnalysisDoc):
        composed_string = ("Please also consider the following related news, But don't analysis them"
                           "Only consider they are examples as they pressed and how they impact the market:\n\n")
        for doc in search_result:
            composed_string += (f"News Title: {doc.title}\n"
                                f"PNL Ratio: {doc.pnl_ratio}\n"
                                f"Impact Days Min: {doc.impact_days_min}\n"
                                f"Impact Days Max: {doc.impact_days_max}\n\n")
        return composed_string

    def calculate_related_news_pnl_ratio(self, search_result):
        related_news_docs = search_result

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
