
import asyncio
import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.schemas import QuestionRequest, AnswerResponse
from Web_Search.langraph_agent.search_tools import search_web

router = APIRouter()


# --------------------------------------------------
# General helpers
# --------------------------------------------------

def to_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return str(value)


def source_dict(document: Any) -> dict:
    metadata = getattr(document, "metadata", {}) or {}
    content = getattr(document, "content", "") or ""

    return {
        "content": str(content),
        "metadata": metadata,
    }


# --------------------------------------------------
# Question routing
# --------------------------------------------------

def is_weather_question(question: str) -> bool:
    q = question.casefold()

    terms = (
        "weather",
        "temperature",
        "forecast",
        "rainfall",
        "humidity",
        "wind speed",
        "is it raining",
        "will it rain",
        "weather like",
        "feels like temperature",
        "precipitation",
    )

    return any(term in q for term in terms)


def is_forecast_question(question: str) -> bool:
    q = question.casefold()

    terms = (
        "forecast",
        "tomorrow",
        "next few days",
        "next 3 days",
        "next three days",
        "weekly weather",
        "weather this week",
    )

    return any(term in q for term in terms)


def is_ocr_question(question: str) -> bool:
    q = question.casefold()

    terms = (
        "ocr",
        "scanned document",
        "scanned pdf",
        "scanned image",
        "read this document",
        "what does the document say",
        "document.pdf",
        "tass text",
        "khrushchev",
        "cuban missile crisis",
        "what is written in",
        "text extracted from",
    )

    return any(term in q for term in terms)


def is_web_question(question: str) -> bool:
    q = question.casefold()

    terms = (
        "latest",
        "recent developments",
        "current news",
        "latest news",
        "search the web",
        "search online",
        "on the internet",
        "today's news",
        "research online",
        "latest research",
        "recent research",
        "news about",
        "recent updates",
        "current developments",
    )

    return any(term in q for term in terms)


def is_sql_question(question: str) -> bool:
    """Detect questions that should use the company SQL database."""

    q = question.casefold()

    terms = (
        "employee",
        "employees",
        "salary",
        "salaries",
        "payroll",
        "department",
        "departments",
        "project budget",
        "project budgets",
        "projects",
        "company database",
        "company records",
        "total salary",
        "average salary",
        "highest salary",
        "lowest salary",
        "employee count",
        "how many employees",
        "list employees",
        "employee names",
        "who works",
    )

    return any(term in q for term in terms)


# --------------------------------------------------
# City extraction
# --------------------------------------------------

def extract_city(question: str) -> str:
    q = question.strip()

    known_cities = (
        "Islamabad",
        "Rawalpindi",
        "Lahore",
        "Karachi",
        "Peshawar",
        "Quetta",
        "Multan",
        "Faisalabad",
        "Wah Cantt",
        "Wah",
        "Murree",
        "London",
        "Sydney",
        "Melbourne",
        "Canberra",
        "Toronto",
        "New York",
        "Los Angeles",
        "Dubai",
        "Riyadh",
        "Doha",
        "Istanbul",
        "Tokyo",
        "Beijing",
        "Delhi",
        "Mumbai",
        "Bangkok",
        "Singapore",
        "Paris",
        "Berlin",
    )

    for city in sorted(known_cities, key=len, reverse=True):
        if re.search(
            rf"\b{re.escape(city)}\b",
            q,
            flags=re.IGNORECASE,
        ):
            return city

    match = re.search(
        r"\b(?:weather|temperature|forecast)"
        r"\s+(?:in|for|at)\s+"
        r"([A-Za-z][A-Za-z .'-]*?)"
        r"(?:\s+(?:today|tomorrow|right now|now|this week))?"
        r"[?.!,]*$",
        q,
        flags=re.IGNORECASE,
    )

    if match:
        city = match.group(1).strip(" .,!?'\"")

        if city:
            return city

    match = re.search(
        r"\b(?:in|for|at)\s+"
        r"([A-Za-z][A-Za-z .'-]*?)"
        r"(?:\s+(?:right now|currently|today|tomorrow|now))?"
        r"[?.!,]*$",
        q,
        flags=re.IGNORECASE,
    )

    if match:
        city = match.group(1).strip(" .,!?'\"")

        if city and len(city) <= 60:
            return city

    return ""


# --------------------------------------------------
# MCP result parsing
# --------------------------------------------------

def parse_weather_result(result: Any) -> Any:
    if isinstance(result, dict):
        structured = result.get("structuredContent")

        if structured is None:
            structured = result.get("structured_content")

        if structured is not None:
            return parse_weather_result(structured)

        return result

    structured = getattr(result, "structuredContent", None)

    if structured is None:
        structured = getattr(result, "structured_content", None)

    if structured is not None:
        return parse_weather_result(structured)

    content = getattr(result, "content", None)

    if content is not None:
        for item in content:
            text_value = getattr(item, "text", None)

            if not text_value and isinstance(item, dict):
                text_value = item.get("text")

            if not text_value:
                continue

            try:
                return json.loads(text_value)
            except (json.JSONDecodeError, TypeError):
                continue

    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result

    model_dump = getattr(result, "model_dump", None)

    if callable(model_dump):
        try:
            return model_dump()
        except Exception:
            pass

    return str(result)


# --------------------------------------------------
# Current weather formatting
# --------------------------------------------------

def format_current_weather(data: Any, city: str) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data

    if isinstance(data, dict):
        for key in ("data", "weather", "result"):
            nested = data.get(key)

            if isinstance(nested, dict) and (
                "temperature_c" in nested
                or "temperature" in nested
            ):
                data = nested
                break

    if not isinstance(data, dict):
        return (
            f"Unable to format the weather response for {city}. "
            "The weather service returned an unexpected format."
        )

    if data.get("error"):
        return f"**Weather service error:** {data['error']}"

    temperature = data.get("temperature_c")

    if temperature is None:
        temperature = data.get("temperature")

    feels_like = data.get("feels_like_c")

    if feels_like is None:
        feels_like = data.get("apparent_temperature_c")

    humidity = data.get("humidity_percent")

    if humidity is None:
        humidity = data.get("humidity")

    wind = data.get("wind_speed_kmh")

    if wind is None:
        wind = data.get("wind_speed")

    precipitation = data.get("precipitation_mm")

    if precipitation is None:
        precipitation = data.get("precipitation")

    conditions = data.get("conditions")

    if conditions is None:
        conditions = data.get("condition")

    timestamp = data.get("time") or data.get("timestamp")
    country = data.get("country", "")
    actual_city = data.get("city") or city

    if temperature is None or conditions is None:
        return (
            "The weather service did not return the required "
            "temperature and condition fields.\n\n"
            "**Received data:**\n```json\n"
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n```"
        )

    location = str(actual_city)

    if country:
        location = f"{location}, {country}"

    lines = [
        f"## Current Weather in {location}",
        "",
        f"**Temperature:** {temperature}°C",
        f"**Conditions:** {conditions}",
    ]

    if feels_like is not None:
        lines.append(f"**Feels like:** {feels_like}°C")

    if humidity is not None:
        lines.append(f"**Humidity:** {humidity}%")

    if wind is not None:
        lines.append(f"**Wind speed:** {wind} km/h")

    if precipitation is not None:
        lines.append(f"**Precipitation:** {precipitation} mm")

    if timestamp:
        lines.extend([
            "",
            f"**Weather data timestamp:** {timestamp}",
        ])

    is_day = data.get("is_day")

    if is_day is not None:
        day_label = "Day" if str(is_day) == "1" else "Night"
        lines.append(f"**Local daylight status:** {day_label}")

    return "\n".join(lines)


# --------------------------------------------------
# Forecast formatting
# --------------------------------------------------

def format_forecast_response(data: Any, city: str) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data

    if isinstance(data, dict) and data.get("error"):
        return f"**Weather service error:** {data['error']}"

    if not isinstance(data, (dict, list)):
        return str(data)

    if isinstance(data, dict):
        location = data.get("city") or city
        country = data.get("country")

        if country:
            location = f"{location}, {country}"

        title = f"## Weather Forecast for {location}"

        forecast_days = (
            data.get("forecast")
            or data.get("daily")
            or data.get("days")
        )

        if isinstance(forecast_days, list):
            lines = [title, ""]

            for item in forecast_days:
                if not isinstance(item, dict):
                    lines.append(f"- {item}")
                    continue

                date = item.get("date") or item.get("time") or "Forecast"
                lines.append(f"### {date}")

                for key, value in item.items():
                    if key in ("date", "time"):
                        continue

                    readable_key = key.replace("_", " ").capitalize()

                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)

                    lines.append(f"- **{readable_key}:** {value}")

                lines.append("")

            return "\n".join(lines).strip()

        return (
            title
            + "\n\n```json\n"
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n```"
        )

    return (
        f"## Weather Forecast for {city}\n\n```json\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n```"
    )


# --------------------------------------------------
# MCP weather tool call
# --------------------------------------------------

async def call_weather_tool(
    mcp_client: Any,
    question: str,
    city: str,
) -> str:
    forecast_requested = is_forecast_question(question)

    tool_name = (
        "get_weather_forecast"
        if forecast_requested
        else "get_current_weather"
    )

    arguments = {"city": city}

    if forecast_requested:
        arguments["days"] = 3

    print(f"[WEATHER] Selected tool: {tool_name}")
    print(f"[WEATHER] Requested city: {city}")

    result = await mcp_client.call_tool(tool_name, arguments)

    if getattr(result, "isError", False):
        error_data = parse_weather_result(result)
        print("[WEATHER] MCP error:", repr(error_data))
        return "**Weather service error:**\n\n" + str(error_data)

    data = parse_weather_result(result)

    print("[WEATHER] Parsed result:", repr(data))

    if forecast_requested:
        answer = format_forecast_response(data, city)
    else:
        answer = format_current_weather(data, city)

    print("[WEATHER] Formatted answer:", repr(answer))

    return answer


# --------------------------------------------------
# OCR-specific document retrieval
# --------------------------------------------------

def retrieve_ocr_documents(
    rag: Any,
    question: str,
    k: int,
) -> list:
    retriever = getattr(rag, "retriever", None)

    if retriever is None:
        return []

    vector_store = getattr(retriever, "vector_store", None)
    documents = getattr(vector_store, "documents", [])
    ocr_indices = getattr(rag, "ocr_chunk_indices", [])

    ocr_documents = [
        documents[index]
        for index in ocr_indices
        if isinstance(index, int) and 0 <= index < len(documents)
    ]

    if not ocr_documents:
        return retriever.retrieve(question, k)

    candidates = retriever.retrieve(question, max(k * 3, 15))
    ocr_ids = {id(doc) for doc in ocr_documents}

    matched = [doc for doc in candidates if id(doc) in ocr_ids]

    if matched:
        return matched[:k]

    try:
        query_embedding = retriever.embedder.embed(question)
        semantic_results = vector_store.search(
            query_embedding,
            max(k * 5, 30),
        )

        matched = []

        for item in semantic_results:
            if not isinstance(item, dict):
                continue

            doc = item.get("document")

            if doc is not None and id(doc) in ocr_ids:
                matched.append(doc)

        if matched:
            return matched[:k]

    except Exception as exc:
        print(
            "[OCR] Secondary retrieval failed:",
            type(exc).__name__,
            str(exc),
        )

    return ocr_documents[:k]


def generate_ocr_answer(
    rag: Any,
    question: str,
    documents: list,
) -> str:
    if not documents:
        return (
            "I could not retrieve relevant OCR text from the PDFs. "
            "Check whether the document was loaded and OCR chunks "
            "were created."
        )

    context_parts = []

    for index, document in enumerate(documents, start=1):
        content = getattr(document, "content", "") or ""
        metadata = getattr(document, "metadata", {}) or {}

        if not content.strip():
            continue

        context_parts.append(
            f"Document {index}\n"
            f"Page: {metadata.get('page', 'Unknown')}\n"
            f"Text:\n{content}"
        )

    context = "\n\n".join(context_parts)

    if not context.strip():
        return "The retrieved OCR documents contain no readable text."

    prompt = f"""
You answer questions using the supplied OCR-extracted document text.

Rules:
- Use only the text provided below.
- OCR text may contain recognition errors.
- Do not invent missing facts.
- Answer directly when evidence is available.
- If the answer is absent, say so briefly.
- Do not add unrelated external information.

OCR document text:
{context}

Question:
{question}

Answer:
"""

    answer = rag.llm.generate(prompt)

    return to_text(answer).strip() or (
        "I could not generate an answer from the OCR text."
    )


# --------------------------------------------------
# Web search
# --------------------------------------------------

async def call_web_search(question: str) -> str:
    return await asyncio.to_thread(
        search_web.invoke,
        {"query": question},
    )


# --------------------------------------------------
# SQL / unified-agent request
# --------------------------------------------------

async def call_sql_agent(
    request: Request,
    question: str,
) -> str:
    unified_agent = getattr(
        request.app.state,
        "unified_agent",
        None,
    )

    if unified_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Unified agent is not initialized.",
        )

    result = await unified_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        },
        config={"recursion_limit": 10},
    )

    messages = result.get("messages", [])

    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue

        content = getattr(message, "content", "")

        if isinstance(content, str) and content.strip():
            return content.strip()

    return "The SQL agent did not return a readable answer."


# --------------------------------------------------
# Main endpoint
# --------------------------------------------------

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    payload: QuestionRequest,
    http_request: Request,
):
    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    rag = getattr(http_request.app.state, "rag", None)
    mcp_client = getattr(http_request.app.state, "mcp_client", None)

    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline is not initialized.",
        )

    k = max(1, min(payload.k, 20))

    # Route specific questions before the generic RAG fallback.
    if is_weather_question(question):
        selected_tool = "weather"
    elif is_ocr_question(question):
        selected_tool = "ocr"
    elif is_web_question(question):
        selected_tool = "web"
    elif is_sql_question(question):
        selected_tool = "sql"
    else:
        selected_tool = "rag"

    print(f"[ROUTER] Question: {question}")
    print(f"[ROUTER] Selected service: {selected_tool}")

    answer = ""
    sources = []
    ocr_sources = []

    try:
        if selected_tool == "weather":
            city = extract_city(question)

            if not city:
                answer = (
                    "Please mention the city, for example: "
                    "'What is the current weather in Islamabad?'"
                )
            elif mcp_client is None:
                answer = (
                    "Weather MCP client is not initialized. "
                    "Check the FastAPI startup and MCP connection."
                )
            else:
                answer = await call_weather_tool(
                    mcp_client=mcp_client,
                    question=question,
                    city=city,
                )

        elif selected_tool == "ocr":
            ocr_documents = await asyncio.to_thread(
                retrieve_ocr_documents,
                rag,
                question,
                k,
            )

            ocr_sources = [
                source_dict(doc)
                for doc in ocr_documents
                if doc is not None
            ]

            answer = await asyncio.to_thread(
                generate_ocr_answer,
                rag,
                question,
                ocr_documents,
            )

        elif selected_tool == "web":
            answer = to_text(
                await call_web_search(question)
            ).strip()

            if not answer:
                answer = "The web search returned no results."

        elif selected_tool == "sql":
            answer = await call_sql_agent(
                request=http_request,
                question=question,
            )

        else:
            result = await asyncio.to_thread(
                rag.ask,
                question,
                k=k,
            )

            if not isinstance(result, dict):
                raise TypeError(
                    "RAGPipeline.ask() must return a dictionary."
                )

            answer = (
                to_text(result.get("answer")).strip()
                or "No relevant answer was found in the PDFs."
            )

            sources = [
                source_dict(doc)
                for doc in (result.get("documents") or [])
                if doc is not None
            ]

    except HTTPException:
        raise

    except Exception as exc:
        print(
            f"[ERROR] {selected_tool} failed: "
            f"{type(exc).__name__}: {exc}"
        )

        answer = (
            f"Unable to complete the {selected_tool} request. "
            f"Details: {type(exc).__name__}: {exc}"
        )

    print(
        f"[ROUTER] Final answer for {selected_tool}: "
        f"{answer[:500]!r}"
    )

    return AnswerResponse(
        question=question,
        answer=answer,
        rag_answer=answer if selected_tool == "rag" else "",
        ocr_answer=answer if selected_tool == "ocr" else "",
        weather_answer=answer if selected_tool == "weather" else "",
        web_search_answer=answer if selected_tool == "web" else "",
        sources=sources,
        ocr_sources=ocr_sources,
    )
