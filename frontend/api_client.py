
import requests

from interfaces import ApiClientInterface
from models import ApiResult


class FastApiClient(ApiClientInterface):

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")

        # api_url normally ends with /ask.
        self.base_url = (
            self.api_url[:-4]
            if self.api_url.endswith("/ask")
            else self.api_url
        )

    def ask(self, question: str, k: int) -> ApiResult:

        try:
            response = requests.post(
                self.api_url,
                json={
                    "question": question,
                    "k": k
                },
                timeout=300
            )

            response.raise_for_status()
            data = response.json()

            return ApiResult(
                answer=data.get(
                    "answer",
                    data.get("rag_answer", "No answer returned.")
                ),
                sources=data.get("sources", []),
                rag_answer=data.get("rag_answer", data.get("answer", "")),
                ocr_answer=data.get("ocr_answer", "No OCR answer returned."),
                weather_answer=data.get("weather_answer", "No weather result returned."),
                web_search_answer=data.get("web_search_answer", "No web-search result returned."),
                ocr_sources=data.get("ocr_sources", [])
            )

        except requests.exceptions.RequestException as error:

            return ApiResult(
                answer="",
                sources=[],
                success=False,
                error=str(error)
            )

    def get_logs(
        self,
        level: str = "ALL",
        limit: int = 200
    ) -> dict:

        try:
            response = requests.get(
                f"{self.base_url}/logs",
                params={
                    "level": level,
                    "limit": limit
                },
                timeout=15
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:

            return {
                "logs": [],
                "count": 0,
                "error": str(error)
            }
