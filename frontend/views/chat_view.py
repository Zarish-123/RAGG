
from typing import Optional, Any, Dict, List
import streamlit as st

from session_manager import SessionStateManager


class ChatView:

    def __init__(self, session_manager: SessionStateManager):
        self.session_manager = session_manager

    @staticmethod
    def _apply_chat_styles() -> None:
        st.markdown(
            """
            <style>
            /* User question blue bubble */
            .user-question-row {
                display: flex;
                justify-content: flex-end;
                width: 100%;
                margin: 4px 0 12px 0;
            }

            .user-question-bubble {
                background-color: #DCEBFF;
                color: #17365D;
                padding: 9px 14px;
                border-radius: 20px;
                width: fit-content;
                max-width: 75%;
                margin-left: auto;
                overflow-wrap: anywhere;
                white-space: pre-wrap;
                font-size: 20px;
                line-height: 1.7;
            }

            .user-question-bubble p {
                margin: 0;
                font-size: 20px !important;
                line-height: 1.7 !important;
            }

            /* Actual text inside Streamlit chat messages */
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
                font-size: 20px !important;
                line-height: 1.8 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def _escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def render_history(self) -> None:
        self._apply_chat_styles()

        messages = self.session_manager.get_messages()

        for message in messages:
            if message.role == "user":
                safe_question = self._escape_html(message.content)

                st.markdown(
                    f"""
                    <div class="user-question-row">
                        <div class="user-question-bubble">{safe_question}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            elif message.role == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(
                        message.content,
                        unsafe_allow_html=False,
                    )

    @staticmethod
    def render_input() -> Optional[str]:
        return st.chat_input(
            "Ask about your PDFs, OCR, weather, or the web...",
            key="chat_input",
        )

    @staticmethod
    def show_user_message(question: str) -> None:
        ChatView._apply_chat_styles()
        safe_question = ChatView._escape_html(question)

        st.markdown(
            f"""
            <div class="user-question-row">
                <div class="user-question-bubble">{safe_question}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def show_assistant_message(answer: str) -> None:
        ChatView._apply_chat_styles()

        with st.chat_message("assistant"):
            st.markdown(answer, unsafe_allow_html=False)

    @staticmethod
    def _show_sources(
        sources: List[Dict[str, Any]],
        label: str,
    ) -> None:
        if not sources:
            return

        with st.expander(f"📄 View {label} sources"):
            for index, source in enumerate(sources, start=1):
                metadata = source.get("metadata", {}) or {}
                source_name = metadata.get("source", "Unknown PDF")
                page = metadata.get("page", "?")

                st.markdown(
                    f"**{label} source {index}** · "
                    f"Page {page} · `{source_name}`"
                )

                st.markdown(
                    source.get("content", "No source content available.")
                )

                if index < len(sources):
                    st.divider()
