
import streamlit as st

from config import AppConfig
from session_manager import SessionStateManager


class SidebarView:

    def __init__(
        self,
        config: AppConfig,
        session_manager: SessionStateManager
    ):
        self.config = config
        self.session_manager = session_manager

    @staticmethod
    def _apply_sidebar_styles() -> None:
        st.markdown(
            """
            <style>
            /* =====================================
               SIDEBAR BACKGROUND AND EDGE
            ===================================== */

            section[data-testid="stSidebar"] {
                background: #FFFFFF;
                border-right: 1px solid #D1D1D1 !important;
            }

            /* Sidebar content layout */
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding-right: 0 !important;
                overflow: hidden !important;
            }

            /* Sidebar user content */
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
                padding-right: 0 !important;
                margin-right: 0 !important;
                scrollbar-width: thin;
                scrollbar-color: #A6A6A6 #E5E5E5;
            }

            /* Sidebar inner spacing */
            section[data-testid="stSidebar"] > div {
                padding-left: 0.75rem !important;
                padding-right: 0 !important;
                box-sizing: border-box !important;
            }

            /* =====================================
               FIXED TOP SECTION
            ===================================== */

            section[data-testid="stSidebar"] .st-key-sidebar_top {
                background: #FFFFFF;
                position: relative;
                z-index: 10;
                flex-shrink: 0;
            }

            /* =====================================
               SCROLLABLE SECTION
            ===================================== */

            section[data-testid="stSidebar"] .st-key-sidebar_scroll_area {
                height: calc(100vh - 190px) !important;
                max-height: calc(100vh - 190px) !important;
                min-height: 100px !important;

                /* Expand the scroll area towards the right edge */
                width: calc(100% + 12px) !important;
                max-width: none !important;
                margin-right: -12px !important;
                padding-right: 0 !important;
                box-sizing: border-box !important;

                overflow-y: auto !important;
                overflow-x: hidden !important;
                overscroll-behavior: contain;

                scrollbar-width: thin;
                scrollbar-color: #A6A6A6 #E5E5E5;
            }

            /* Chrome and Edge: inner scroll area */
            section[data-testid="stSidebar"] .st-key-sidebar_scroll_area::-webkit-scrollbar {
                width: 8px;
            }

            section[data-testid="stSidebar"] .st-key-sidebar_scroll_area::-webkit-scrollbar-track {
                background: #E5E5E5;
                border-radius: 8px;
            }

            section[data-testid="stSidebar"] .st-key-sidebar_scroll_area::-webkit-scrollbar-thumb {
                background: #A6A6A6;
                border-radius: 8px;
            }

            section[data-testid="stSidebar"] .st-key-sidebar_scroll_area::-webkit-scrollbar-thumb:hover {
                background: #888888;
            }

            /* Chrome and Edge: sidebar user content scrollbar */
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar {
                width: 8px;
            }

            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar-track {
                background: #E5E5E5;
            }

            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar-thumb {
                background: #A6A6A6;
                border-radius: 8px;
            }

            /* =====================================
               CHATGPT HEADING
            ===================================== */

            section[data-testid="stSidebar"] h1 {
                font-size: 26px !important;
                font-weight: 650 !important;
                color: #262626 !important;
                text-align: left !important;
                margin-top: -18px !important;
                margin-bottom: 18px !important;
                padding-left: 0 !important;
            }

            /* =====================================
               SIDEBAR BUTTONS
            ===================================== */

            section[data-testid="stSidebar"] [data-testid="stButton"] {
                width: 100% !important;
            }

            section[data-testid="stSidebar"] [data-testid="stButton"] > button {
                width: 100% !important;
                min-height: 46px !important;
                padding: 9px 10px !important;
                margin: 0 !important;

                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;

                background: #FFFFFF !important;
                color: #262626 !important;
                border: none !important;
                border-radius: 9px !important;
                box-shadow: none !important;
            }

            /* Align button icons and text */
            section[data-testid="stSidebar"] [data-testid="stButton"] > button > div {
                width: 100% !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                gap: 10px !important;
            }

            /* Material icons */
            section[data-testid="stSidebar"] [data-testid="stIconMaterial"] {
                flex: 0 0 24px !important;
                width: 24px !important;
                font-size: 22px !important;
                color: #303030 !important;
                text-align: left !important;
            }

            /* Button text */
            section[data-testid="stSidebar"] [data-testid="stButton"] button p {
                flex: 1 1 auto !important;
                width: auto !important;
                font-size: 19px !important;
                line-height: 1.5 !important;
                font-weight: 400 !important;
                text-align: left !important;
                margin: 0 !important;
            }

            /* Button hover */
            section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
                background: #F0F0F0 !important;
                color: #262626 !important;
            }

            /* =====================================
               RECENTS HEADING
            ===================================== */

            .recents-heading {
                font-size: 19px !important;
                font-weight: 600 !important;
                color: #262626 !important;
                text-align: left !important;
                padding: 8px 10px !important;
                margin: 8px 0 4px 0 !important;
            }

            /* Dividers */
            section[data-testid="stSidebar"] hr {
                border-color: #EEEEEE !important;
                margin-top: 10px !important;
                margin-bottom: 10px !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    def render(self) -> int:
        self._apply_sidebar_styles()

        with st.sidebar:

            # Fixed top section
            with st.container(key="sidebar_top"):

                st.title("AskME")

                # New chat
                if st.button(
                    "New chat",
                    icon=":material/edit_square:",
                    key="menu_new_chat",
                    use_container_width=True
                ):
                    self.session_manager.new_chat()
                    st.session_state.pop("sidebar_notice", None)
                    st.rerun()

                # Images placeholder
                if st.button(
                    "Images",
                    icon=":material/image:",
                    key="menu_images",
                    use_container_width=True
                ):
                    st.session_state["sidebar_notice"] = (
                        "Images is not connected to a page "
                        "in this application yet."
                    )
                    st.rerun()

            # Scrollable section begins at Scheduled
            with st.container(key="sidebar_scroll_area"):

                # Scheduled placeholder
                if st.button(
                    "Scheduled",
                    icon=":material/schedule:",
                    key="menu_scheduled",
                    use_container_width=True
                ):
                    st.session_state["sidebar_notice"] = (
                        "Scheduled is not connected to a page "
                        "in this application yet."
                    )
                    st.rerun()

                # Library placeholder
                if st.button(
                    "Library",
                    icon=":material/folder_open:",
                    key="menu_library",
                    use_container_width=True
                ):
                    st.session_state["sidebar_notice"] = (
                        "Library is not connected to a page "
                        "in this application yet."
                    )
                    st.rerun()

                # Plugins placeholder
                if st.button(
                    "Plugins",
                    icon=":material/extension:",
                    key="menu_plugins",
                    use_container_width=True
                ):
                    st.session_state["sidebar_notice"] = (
                        "Plugins is not connected to a page "
                        "in this application yet."
                    )
                    st.rerun()

                # Codex placeholder
                if st.button(
                    "Codex",
                    icon=":material/code:",
                    key="menu_codex",
                    use_container_width=True
                ):
                    st.session_state["sidebar_notice"] = (
                        "Codex is not connected to a page "
                        "in this application yet."
                    )
                    st.rerun()

                # Placeholder notice
                notice = st.session_state.get("sidebar_notice")
                if notice:
                    st.caption(notice)

                st.markdown("---")

                # Recent chats
                st.markdown(
                    '<div class="recents-heading">Recents</div>',
                    unsafe_allow_html=True
                )

                chat_names = self.session_manager.get_chat_names()

                if not chat_names:
                    st.caption("No recent chats yet.")

                for index, chat_name in enumerate(chat_names):
                    if st.button(
                        chat_name,
                        icon=":material/chat_bubble_outline:",
                        key=f"recent_chat_{index}",
                        use_container_width=True,
                        help=chat_name
                    ):
                        self.session_manager.switch_chat(chat_name)
                        st.session_state.pop("sidebar_notice", None)
                        st.rerun()

                st.markdown("---")

                # Knowledge Base
                with st.expander(
                    "Knowledge Base",
                    icon=":material/description:"
                ):
                    st.write(self.config.document_name)

                # Settings
                with st.expander(
                    "Settings",
                    icon=":material/settings:"
                ):
                    st.slider(
                        "Number of retrieved chunks",
                        min_value=1,
                        max_value=self.config.max_top_k,
                        value=self.config.default_top_k,
                        key="retrieval_top_k"
                    )

                # Clear current chat
                if st.button(
                    "Clear current chat",
                    icon=":material/delete_outline:",
                    key="clear_current_chat",
                    use_container_width=True
                ):
                    self.session_manager.clear()
                    st.rerun()

                st.markdown("---")
                st.caption("Powered by FastAPI + Ollama + FAISS")

        return st.session_state.get(
            "retrieval_top_k",
            self.config.default_top_k
        )
