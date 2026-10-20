
from ddgs import DDGS
from langchain_core.tools import tool


@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic."""

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return "No search results were found."

        formatted_results = []

        for index, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("href") or result.get("url", "")
            snippet = result.get("body", "")

            formatted_results.append(
                f"{index}. {title}\n"
                f"URL: {url}\n"
                f"Information: {snippet}"
            )

        return "\n\n".join(formatted_results)

    except Exception as error:
        return f"Web search failed: {error}"
