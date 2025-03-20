import gradio as gr

from ui.chatbot_simple import OllamaChatBot


class ChatBotUI:
    def __init__(self, chatbot: OllamaChatBot):
        self.chatbot = chatbot


    def launch(self):
        # with gr.Blocks() as demo:
        gr.Markdown("### Chat with Stock News Chatbot")
        chat_interface = gr.ChatInterface(
            self.chatbot.get_response_from_chat_bot,
            type="messages",
            flagging_mode="manual",
            flagging_options=["Like", "Spam", "Inappropriate", "Other"],
            save_history=True,
            editable=True,
            stop_btn=True,
            fill_height=True,
            autoscroll=True,
        )
        chat_interface.launch()


if __name__ == "__main__":
    bot = OllamaChatBot()
    ui = ChatBotUI(bot)
    ui.launch()
