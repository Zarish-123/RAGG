
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:

    def __init__(self, server_module="weather_server.server"):
        self.server_module = server_module
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """Start the MCP server and establish a connection."""

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.server_module],
            env=os.environ.copy(),
        )

        try:
            read_stream, write_stream = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self.session.initialize()

            print("Connected to MCP server successfully.")

        except Exception:
            await self.exit_stack.aclose()
            raise

    async def list_tools(self):
        """Get all tools exposed by the MCP server."""

        if self.session is None:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, tool_name, arguments):
        """Execute a tool on the MCP server."""

        if self.session is None:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        return await self.session.call_tool(
            tool_name,
            arguments=arguments,
        )

    async def close(self):
        """Close the MCP connection safely."""

        await self.exit_stack.aclose()
        self.session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
