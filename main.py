
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router
from app import create_rag
from unified_agent import create_unified_agent
from Weather_Search.mcp_client.client import MCPClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_client = MCPClient(
        server_module="Weather_Search.weather_server.server"
    )

    try:
        print("\n[STARTUP] Initializing RAG + OCR...")
        app.state.rag = create_rag()

        print("\n[STARTUP] Connecting to Weather MCP...")
        await mcp_client.connect()
        app.state.mcp_client = mcp_client

        print("\n[STARTUP] Initializing Unified Agent...")
        app.state.unified_agent = create_unified_agent(
            rag=app.state.rag,
            mcp_client=app.state.mcp_client,
        )

        print(
            "\n[STARTUP] Ready: RAG + OCR + "
            "SQL Database + Weather MCP + Web Search"
        )

        yield

    finally:
        print("\n[SHUTDOWN] Closing Weather MCP...")
        await mcp_client.close()


app = FastAPI(
    title="Unified AI Assistant",
    description=(
        "AI assistant with document search, OCR, SQL database, "
        "weather MCP, and web search."
    ),
    lifespan=lifespan,
)

app.include_router(router)
