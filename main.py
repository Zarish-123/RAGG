
import logging
from contextlib import asynccontextmanager

from logs.config.logging_config import setup_logging

# Initialize logging before importing application modules
setup_logging()

from fastapi import FastAPI

from api.routes import router
from app import create_rag
from unified_agent import create_unified_agent
from Weather_Search.mcp_client.client import MCPClient


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    mcp_client = None

    try:
        logger.info("Application startup initiated.")

        # Initialize RAG and OCR
        logger.info("Initializing RAG and OCR...")

        app.state.rag = create_rag()

        logger.info("RAG and OCR initialized successfully.")

        # Connect Weather MCP
        logger.info("Connecting to Weather MCP...")

        mcp_client = MCPClient(
            server_module="Weather_Search.weather_server.server"
        )

        await mcp_client.connect()

        app.state.mcp_client = mcp_client

        logger.info("Weather MCP connected successfully.")

        # Initialize Unified Agent
        logger.info("Initializing Unified Agent...")

        app.state.unified_agent = create_unified_agent(
            rag=app.state.rag,
            mcp_client=app.state.mcp_client,
        )

        logger.info("Unified Agent initialized successfully.")

        logger.info(
            "Application ready: RAG, OCR, SQL, Weather MCP and Web Search."
        )

        yield

    except Exception:
        logger.exception(
            "Application startup or runtime failed."
        )
        raise

    finally:

        if mcp_client is not None:

            logger.info("Closing Weather MCP...")

            try:
                await mcp_client.close()

                logger.info(
                    "Weather MCP closed successfully."
                )

            except Exception:
                logger.exception(
                    "Failed to close Weather MCP."
                )

        logger.info("Application shutdown completed.")


app = FastAPI(
    title="Unified AI Assistant",
    description=(
        "AI assistant with document search, OCR, SQL database, "
        "weather MCP, and web search."
    ),
    lifespan=lifespan,
)

app.include_router(router)
