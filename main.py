
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router
from app import create_rag
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

        print(
            "\n[STARTUP] Ready: RAG + OCR + "
            "Weather MCP + Web Search"
        )

        yield

    finally:
        print("\n[SHUTDOWN] Closing Weather MCP...")
        await mcp_client.close()


app = FastAPI(
    title="Four-Answer AI Assistant",
    description=(
        "Separate RAG, OCR, Weather Search, and Web Search answers."
    ),
    lifespan=lifespan,
)

app.include_router(router)
