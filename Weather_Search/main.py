
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
        print("\nInitializing RAG pipeline...")
        rag = create_rag()

        print("\nConnecting to Weather MCP server...")
        await mcp_client.connect()

        print("\nInitializing unified agent...")
        agent = create_unified_agent(
            rag=rag,
            mcp_client=mcp_client
        )

        app.state.unified_agent = agent

        print("\nUnified AI assistant is ready!")

        yield

    finally:
        print("\nClosing Weather MCP connection...")
        await mcp_client.close()


app = FastAPI(
    title="Unified AI Assistant",
    lifespan=lifespan
)

app.include_router(router)
