
import json
import ollama


class CompanyAgent:
    def __init__(self, mcp_client, model="llama3.2:3b"):
        self.mcp_client = mcp_client
        self.model = model

    async def run(self, user_input: str) -> str:
        mcp_tools = await self.mcp_client.list_tools()

        # Convert MCP tools into Ollama-compatible tools
        ollama_tools = []

        for tool in mcp_tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful weather AI assistant. "
                    "Use the available weather tools to find locations, "
                    "current weather, and forecasts. "
                    "Never invent weather data. "
                    "Use tool results to answer clearly."
                ),
            },
            {
                "role": "user",
                "content": user_input,
            },
        ]

        # Allow multiple rounds of tool calls
        for _ in range(5):
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=ollama_tools,
            )

            assistant_message = response.message

            messages.append(
                assistant_message.model_dump(exclude_none=True)
            )

            tool_calls = assistant_message.tool_calls or []

            # Return the final answer if no tool is needed
            if not tool_calls:
                return assistant_message.content or "No answer generated."

            allowed_tools = {tool.name for tool in mcp_tools}

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = tool_call.function.arguments

                if tool_name not in allowed_tools:
                    tool_result = {
                        "error": f"Tool '{tool_name}' is not available."
                    }

                else:
                    try:
                        result = await self.mcp_client.call_tool(
                            tool_name,
                            arguments,
                        )

                        # FIX: Convert MCP CallToolResult to JSON-compatible data
                        if hasattr(result, "model_dump"):
                            tool_result = result.model_dump(mode="json")
                        else:
                            tool_result = str(result)

                    except Exception as exc:
                        tool_result = {
                            "error": f"Tool call failed: {exc}"
                        }

                # Send the tool result back to Ollama
                messages.append({
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                        default=str,
                    ),
                })

        return (
            "I could not complete the request within the tool-call limit. "
            "Please try again."
        )
