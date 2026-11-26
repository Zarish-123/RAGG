
import streamlit as st

from api_client import FastApiClient
from config import AppConfig
from controller import ChatController
from session_manager import SessionStateManager
from styles import StyleManager

from views.chat_view import ChatView
from views.header_view import HeaderView
from views.sidebar_view import SidebarView
from views.welcome_view import WelcomeView


class RagStreamlitApp:

    def __init__(self):

        self.config = AppConfig()

        self.session_manager = SessionStateManager()

        self.api_client = FastApiClient(
            self.config.api_url
        )

        self.chat_view = ChatView(
            self.session_manager
        )

        self.controller = ChatController(
            api_client=self.api_client,
            session_manager=self.session_manager,
            chat_view=self.chat_view
        )

    def setup(self) -> None:

        st.set_page_config(
            page_title=self.config.page_title,
            page_icon=self.config.page_icon,
            layout="wide",
            initial_sidebar_state="expanded"
        )

        self.session_manager.initialize()

        StyleManager.apply()

    def render_logs(self) -> None:

        with st.expander(
            "Application Logs",
            expanded=False
        ):

            col1, col2 = st.columns([2, 1])

            with col1:

                level = st.selectbox(
                    "Log Level",
                    [
                        "ALL",
                        "INFO",
                        "WARNING",
                        "ERROR",
                        "DEBUG",
                        "CRITICAL"
                    ],
                    key="log_level"
                )

            with col2:

                limit = st.selectbox(
                    "Number of Entries",
                    [
                        50,
                        100,
                        200,
                        500,
                        1000
                    ],
                    index=2,
                    key="log_limit"
                )

            st.button(
                "Refresh Logs",
                key="refresh_logs"
            )

            # Fetch logs on every Streamlit rerun.
            result = self.api_client.get_logs(
                level=level,
                limit=limit
            )

            st.session_state["application_logs"] = result

            if not isinstance(result, dict):

                st.error(
                    "Invalid response received from the logs API."
                )

                return

            if result.get("error"):

                st.error(
                    result["error"]
                )

                return

            logs = result.get("logs", [])

            st.caption(
                f"Showing {result.get('count', 0)} log entries"
            )

            if logs:

                st.code(
                    "\n".join(logs),
                    language="log"
                )

            else:

                st.info(
                    "No logs found for this filter."
                )

    def run(self) -> None:

        self.setup()

        # Sidebar
        top_k = SidebarView(
            self.config,
            self.session_manager
        ).render()

        # Header
        HeaderView.render()

        # Application Logs
        self.render_logs()

        # Welcome section
        suggestion = WelcomeView.render()

        # Previous messages
        self.chat_view.render_history()

        # Chat input
        question = self.chat_view.render_input()

        if suggestion:
            question = suggestion

        # Process question
        if question:

            self.controller.process_question(
                question=question,
                top_k=top_k
            )


def main():

    app = RagStreamlitApp()

    app.run()


if __name__ == "__main__":

    main()
