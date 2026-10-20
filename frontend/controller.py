import streamlit as st

from interfaces import ApiClientInterface
from session_manager import SessionStateManager
from views.chat_view import ChatView


class ChatController:
    def __init__(
        self,
        api_client: ApiClientInterface,
        session_manager: SessionStateManager,
        chat_view: ChatView,
    ):
        self.api_client = api_client
        self.session_manager = session_manager
        self.chat_view = chat_view

    def process_question(self, question: str, top_k: int) -> None:
        question = question.strip()

        if not question:
            return

        messages = self.session_manager.get_messages()

        if len(messages) == 0:
            title = question

            if len(title) > 35:
                title = title[:35].strip() + "..."

            self.session_manager.set_chat_title(title)

        self.session_manager.add_message("user", question)
        self.chat_view.show_user_message(question)

        with st.chat_message("assistant"):
            with st.spinner("Finding the relevant answer..."):
                result = self.api_client.ask(question, top_k)

            if not result.success:
                error_message = (
                    "Unable to connect to the backend.\n\n"
                    f"Error: {result.error}"
                )

                st.error(error_message)
                self.session_manager.add_message(
                    "assistant",
                    error_message,
                )
                return

            # Display only one answer instead of four separate answers.
            answer = (result.answer or "").strip()

            if not answer:
                answer = "No answer was returned."

            self.chat_view.show_assistant_message(answer)

            # Save only the displayed answer in chat history.
            self.session_manager.add_message(
                "assistant",
                answer,
            )

        st.rerun()