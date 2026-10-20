
import json
import re

from langchain_ollama import ChatOllama
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from Web_Search.langraph_agent.search_tools import search_web
from database.sql_tool import sql_database_tool

SYSTEM_PROMPT = """
You are a unified AI assistant with three capabilities.

DOCUMENT SEARCH
- Use search_documents for questions about the user's PDFs and OCR.
- Base document-specific claims on retrieved document evidence.
- Never invent missing text or quotations.
- If a user asks for a full original text, verify that the retrieved
  source contains the full text, not just a mention or summary.
- If the requested text is missing or incomplete in the PDFs,
  use search_web to look for the original source.
- Do not claim that a partial excerpt is the complete original text.

WEB SEARCH
- The search_web tool searches the internet.
- If the user explicitly asks to search the web, search online,
  look something up online, or perform a web search, you MUST
  call search_web before answering.
- Do not answer an explicit web-search request using PDF context alone.
- For current information, recent developments, news, or information
  missing from the PDFs, use search_web.
- After receiving web results, summarize the actual results.
- Include relevant real URLs returned by search_web.
- Never invent URLs, sources, search results, or publication dates.
- If search results are empty or fail, explain this honestly.
- A web search must actually execute before you claim that you
  searched the internet.

WEATHER
- When the user asks about current weather, call the
  appropriate weather tool and use its returned data.
- Never display raw JSON directly to the user.
- Format weather information as a readable report.
- Start with the city, current temperature, and conditions.
- Include feels-like temperature, humidity, wind speed,
  and precipitation when available.
- Mention the reported local date and time when available.
- Add a short, natural-language summary.
- Use Celsius and km/h when those are the tool's units.
- Do not invent weather values or claim that rain is expected
  unless the returned data supports that conclusion.
- If a field is missing, omit it instead of guessing.

ANSWER FORMATTING — STRICT RULES

For answers containing multiple topics, applications, examples,
steps, categories, advantages, disadvantages, or distinct points:

1. Give every item its own bold Markdown heading.
2. Put the heading on its own line.
3. Leave one blank line after the heading.
4. Put the explanation in a separate paragraph below the heading.
5. Leave one blank line before the next heading.
6. Start directly with the first heading. Do not add an introductory
   sentence such as "Here are the applications mentioned in the
   retrieved context".
7. Never put a heading and its explanation on the same line.
8. Never combine different topics into one bullet or paragraph.
9. Use sequential numbering for multiple related items.
10. Use bullets only for short supporting details under a heading.
11. Preserve relevant facts from the retrieved evidence.
12. Do not invent facts or add unsupported details.

REQUIRED OUTPUT STRUCTURE:

**1. Grid Optimization**

Utilities use RAG to analyze consumption patterns, weather data,
and equipment information to support grid management.

**2. Education and Training**

Educational institutions use RAG to support personalized learning
and intelligent tutoring.

**3. Financial Sector**

Financial organizations use RAG to retrieve relevant information
for market analysis, regulatory compliance, and customer service,
when supported by the available evidence.

The example above demonstrates formatting only. Answer the actual
user question using the available evidence.

For simple questions that need one direct answer, answer naturally
without unnecessary headings.

Apply these formatting rules to document, OCR, web search, weather,
and general answers.

GENERAL
- Choose tools based on the user's actual question.
- Do not call unrelated tools.
- Explain tool errors honestly.
- Answer in the user's language.
- Historical questions are allowed; do not refuse simply because
  they mention a historical political figure.
"""


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def format_mcp_result(result) -> str:
    """Convert MCP responses into readable text."""

    if hasattr(result, "content"):
        parts = []

        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))

        if parts:
            return "\n".join(parts)

    if hasattr(result, "model_dump"):
        return json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            default=str,
        )

    if isinstance(result, (dict, list)):
        return json.dumps(
            result,
            ensure_ascii=False,
            default=str,
        )

    return str(result)


def extract_city(question: str):
    """Extract a city name from common weather questions."""

    known_cities = (
        "Wah Cantt",
        "Rawalpindi",
        "Islamabad",
        "Faisalabad",
        "Los Angeles",
        "New York",
        "Melbourne",
        "Canberra",
        "Sydney",
        "Toronto",
        "Karachi",
        "Peshawar",
        "Quetta",
        "Lahore",
        "Multan",
        "Murree",
        "London",
        "Dubai",
        "Riyadh",
        "Doha",
        "Istanbul",
        "Tokyo",
        "Beijing",
        "Mumbai",
        "Delhi",
        "Singapore",
        "Bangkok",
        "Paris",
        "Berlin",
    )

    for city in sorted(known_cities, key=len, reverse=True):
        if re.search(
            rf"\b{re.escape(city)}\b",
            question,
            re.IGNORECASE,
        ):
            return city

    pattern = (
        r"\b(?:in|for|at)\s+"
        r"([A-Za-z][A-Za-z .'-]*?)"
        r"(?=\s+(?:right now|currently|today|tomorrow|"
        r"this week|next week|now)\b|[?.!,]|$)"
    )

    match = re.search(pattern, question, re.IGNORECASE)

    if match:
        city = match.group(1).strip(" .,'?!")
        return city or None

    return None


def is_weather_question(question: str) -> bool:
    keywords = (
        "weather",
        "temperature",
        "forecast",
        "rainfall",
        "humidity",
        "wind speed",
        "is it raining",
        "will it rain",
        "precipitation",
    )

    text = question.casefold()
    return any(word in text for word in keywords)


def is_forecast_question(question: str) -> bool:
    text = question.casefold()

    return any(
        word in text
        for word in (
            "forecast",
            "tomorrow",
            "next week",
            "coming days",
            "upcoming days",
            "next few days",
            "next 3 days",
            "next three days",
        )
    )


def is_original_text_request(question: str) -> bool:
    text = question.casefold()

    indicators = (
        "full text",
        "full transcript",
        "original text",
        "complete text",
        "entire transcript",
        "verbatim",
        "full tass",
    )

    return any(term in text for term in indicators)


def is_explicit_web_search(question: str) -> bool:
    """Detect an explicit request to search the internet."""

    text = question.casefold()

    triggers = (
        "web search",
        "search the web",
        "search online",
        "search the internet",
        "look it up online",
        "find online",
        "google search",
        "browse the web",
        "search the web for",
        "search internet for",
        "look online for",
    )

    return any(trigger in text for trigger in triggers)


# --------------------------------------------------
# Unified agent
# --------------------------------------------------

def create_unified_agent(rag, mcp_client):

    # --------------------------------------------------
    # 1. Document search tool
    # --------------------------------------------------

    def search_documents(
        question: str,
        k: int = 10,
    ) -> str:

        print("\n[TOOL EXECUTING] search_documents")
        print(f"[DOCUMENT QUERY] {question}")

        result = rag.ask(question, k=k)

        if not isinstance(result, dict):
            raise TypeError(
                "RAGPipeline.ask() must return a dictionary."
            )

        documents = result.get("documents", [])
        sources = []

        for index, document in enumerate(documents, start=1):
            content = getattr(document, "content", "")
            metadata = getattr(document, "metadata", {}) or {}

            sources.append({
                "content": content,
                "metadata": metadata,
            })

            print(f"\n[RETRIEVED DOCUMENT {index}]")
            print(f"Metadata: {metadata}")
            print(f"Content: {content[:1000]}")

        print(
            f"\n[RETRIEVED DOCUMENT COUNT] {len(documents)}"
        )

        return json.dumps(
            {
                "question": question,
                "document_answer": result.get("answer", ""),
                "sources": sources,
            },
            ensure_ascii=False,
            default=str,
        )

    document_tool = StructuredTool.from_function(
        func=search_documents,
        name="search_documents",
        description=(
            "Search the user's indexed PDFs and OCR text. "
            "Use for questions about the contents of the user's "
            "documents. Arguments: question (string), k (integer)."
        ),
    )

    # --------------------------------------------------
    # 2. Weather MCP tools
    # --------------------------------------------------

    async def search_location(city: str) -> str:
        print(
            f"\n[TOOL EXECUTING] search_location | city={city}"
        )

        result = await mcp_client.call_tool(
            "search_location",
            {"city": city},
        )

        output = format_mcp_result(result)
        print(f"\n[LOCATION RESULT] {output}")

        return output

    async def get_current_weather(city: str) -> str:
        print(
            f"\n[TOOL EXECUTING] get_current_weather | city={city}"
        )

        result = await mcp_client.call_tool(
            "get_current_weather",
            {"city": city},
        )

        output = format_mcp_result(result)
        print(f"\n[WEATHER RESULT] {output}")

        return output

    async def get_weather_forecast(
        city: str,
        days: int = 3,
    ) -> str:

        days = max(1, min(days, 7))

        print(
            f"\n[TOOL EXECUTING] get_weather_forecast "
            f"| city={city}, days={days}"
        )

        result = await mcp_client.call_tool(
            "get_weather_forecast",
            {"city": city, "days": days},
        )

        output = format_mcp_result(result)
        print(f"\n[FORECAST RESULT] {output}")

        return output

    location_tool = StructuredTool.from_function(
        coroutine=search_location,
        name="search_location",
        description=(
            "Find a city's country, coordinates, and timezone. "
            "Argument: city (string)."
        ),
    )

    current_weather_tool = StructuredTool.from_function(
        coroutine=get_current_weather,
        name="get_current_weather",
        description=(
            "Get current weather conditions for a city. "
            "Argument: city (string)."
        ),
    )

    forecast_tool = StructuredTool.from_function(
        coroutine=get_weather_forecast,
        name="get_weather_forecast",
        description=(
            "Get a weather forecast for a city. "
            "Arguments: city (string), days (integer from 1 to 7)."
        ),
    )

    # Keep the actual imported search_web tool.
    tools = [
        document_tool,
        search_web,
        location_tool,
        current_weather_tool,
        forecast_tool,
    ]

    print(
        "\n[AGENT INITIALIZED] Available tools:",
        [tool.name for tool in tools],
    )

    # --------------------------------------------------
    # 3. LLM
    # --------------------------------------------------

    llm = ChatOllama(
        model="llama3.2:3b",
        temperature=0,
    )

    llm_with_tools = llm.bind_tools(tools)

    # Use a dedicated binding to request the web tool explicitly.
    # This requires support from the installed Ollama/LangChain versions.
    try:
        web_search_llm = llm.bind_tools(
            tools,
            tool_choice="search_web",
        )
    except Exception as error:
        print(
            "[WEB TOOL BINDING WARNING] "
            f"{type(error).__name__}: {error}"
        )
        web_search_llm = llm_with_tools

    # --------------------------------------------------
    # 4. Weather response
    # --------------------------------------------------

    async def answer_weather(
        question: str,
        city: str,
    ) -> AIMessage:

        if is_forecast_question(question):
            weather_result = await get_weather_forecast(
                city=city,
                days=3,
            )
        else:
            weather_result = await get_current_weather(
                city=city,
            )

        messages = [
            SystemMessage(
                content=(
                    SYSTEM_PROMPT
                    + "\n\nAnswer this weather question using "
                    "the returned weather data only. Do not invent "
                    "values. Explain tool errors honestly."
                )
            ),
            HumanMessage(content=question),
            SystemMessage(
                content="Weather tool result:\n" + weather_result
            ),
        ]

        response = await llm.ainvoke(messages)

        return AIMessage(content=response.content)

    # --------------------------------------------------
    # 5. Explicit web-search response
    # --------------------------------------------------

    async def answer_explicit_web_search(
        question: str,
    ):
        """Make the model request search_web before answering."""

        print("\n[WEB ROUTER] Explicit web search detected.")
        print(f"[WEB ROUTER] Query: {question}")

        web_messages = [
            SystemMessage(
                content=(
                    SYSTEM_PROMPT
                    + "\n\nMANDATORY WEB SEARCH:\n"
                    "The user explicitly requested an internet search. "
                    "You MUST call the search_web tool before answering. "
                    "Do not answer from PDF context or prior knowledge "
                    "alone. After the tool returns, summarize the actual "
                    "search results and include their real URLs. "
                    "Never invent sources or claim a search succeeded "
                    "if it did not."
                )
            ),
            HumanMessage(content=question),
        ]

        response = await web_search_llm.ainvoke(web_messages)

        print("\n[WEB ROUTER] Initial model response:")
        print("Content:", response.content)
        print("Tool calls:", response.tool_calls)

        # Verify that the model actually requested search_web.
        tool_calls = getattr(response, "tool_calls", []) or []

        has_web_call = any(
            call.get("name") == "search_web"
            for call in tool_calls
        )

        if not has_web_call:
            raise RuntimeError(
                "The model did not call search_web. "
                "Check tool_choice support and search_web's name."
            )

        # Let LangGraph's ToolNode execute the requested tool call.
        return response

    # --------------------------------------------------
    # 6. Agent model node
    # --------------------------------------------------

    async def call_model(state: MessagesState):

        messages = list(state["messages"])

        if not messages:
            return {"messages": []}

        last_message = messages[-1]

        if getattr(last_message, "type", None) == "human":
            question = str(last_message.content)

            # Explicit web search takes priority over document search.
            if is_explicit_web_search(question):
                try:
                    response = await answer_explicit_web_search(
                        question
                    )
                    return {"messages": [response]}

                except Exception as error:
                    print(
                        f"\n[WEB SEARCH ERROR] "
                        f"{type(error).__name__}: {error}"
                    )

                    return {
                        "messages": [
                            AIMessage(
                                content=(
                                    "I couldn't initiate the web search. "
                                    "Please check the search_web tool "
                                    "definition, tool_choice support, "
                                    "and server logs."
                                )
                            )
                        ]
                    }

            # Direct weather routing.
            if is_weather_question(question):
                city = extract_city(question)

                if city:
                    print("\n[WEATHER ROUTER] Weather detected.")
                    print(f"[WEATHER ROUTER] City: {city}")

                    try:
                        response = await answer_weather(
                            question=question,
                            city=city,
                        )
                        return {"messages": [response]}

                    except Exception as error:
                        print(
                            f"\n[WEATHER ERROR] "
                            f"{type(error).__name__}: {error}"
                        )

                        return {
                            "messages": [
                                AIMessage(
                                    content=(
                                        "I couldn't retrieve the weather. "
                                        "Please check the MCP server logs."
                                    )
                                )
                            ]
                        }

            # Original/full-text requests first check document evidence.
            if is_original_text_request(question):
                print(
                    "\n[TEXT ROUTER] Full/original text request detected."
                )

                try:
                    document_result = search_documents(
                        question=question,
                        k=10,
                    )

                    messages_for_web = [
                        SystemMessage(
                            content=(
                                SYSTEM_PROMPT
                                + "\n\nThe user requests a full original "
                                "text. Check the PDF retrieval result. "
                                "If the original text is absent or "
                                "incomplete, call search_web to locate "
                                "the original source. Never invent it."
                            )
                        ),
                        HumanMessage(content=question),
                        SystemMessage(
                            content=(
                                "PDF retrieval result:\n"
                                + document_result
                            )
                        ),
                    ]

                    response = await llm_with_tools.ainvoke(
                        messages_for_web
                    )

                    return {"messages": [response]}

                except Exception as error:
                    print(
                        f"\n[TEXT ROUTER ERROR] "
                        f"{type(error).__name__}: {error}"
                    )

                    return {
                        "messages": [
                            AIMessage(
                                content=(
                                    "I couldn't complete the document "
                                    "search. Please check the server logs."
                                )
                            )
                        ]
                    }

        # Normal document/web/general agent flow.
        if not isinstance(messages[0], SystemMessage):
            messages.insert(
                0,
                SystemMessage(content=SYSTEM_PROMPT),
            )

        response = await llm_with_tools.ainvoke(messages)

        print("\n[DEBUG] Model response:")
        print("Content:", response.content)
        print("Tool calls:", response.tool_calls)

        for tool_call in getattr(response, "tool_calls", []) or []:
            print(
                "\n[TOOL REQUEST]",
                tool_call["name"],
                tool_call["args"],
            )

        return {"messages": [response]}

    # --------------------------------------------------
    # 7. LangGraph workflow
    # --------------------------------------------------

    builder = StateGraph(MessagesState)

    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        tools_condition,
    )

    builder.add_edge("tools", "agent")

    graph = builder.compile()

    print("[AGENT READY] Unified LangGraph agent is ready.")

    return graph
