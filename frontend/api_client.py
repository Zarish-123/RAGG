
import requests

from interfaces import ApiClientInterface
from models import ApiResult


class FastApiClient(ApiClientInterface):

    def __init__(self, api_url: str):
        self.api_url = api_url

    def ask(
        self,
        question: str,
        k: int
    ) -> ApiResult:

        try:
            response = requests.post(
                self.api_url,
                json={
                    "question": question,
                    "k": k
                },
                timeout=180
            )

            response.raise_for_status()
            data = response.json()

            return ApiResult(
                answer=data.get(
                    "answer",
                    data.get("rag_answer", "No answer returned.")
                ),
                sources=data.get("sources", []),

                rag_answer=data.get(
                    "rag_answer",
                    data.get("answer", "")
                ),
                ocr_answer=data.get(
                    "ocr_answer",
                    "No OCR answer returned."
                ),
                weather_answer=data.get(
                    "weather_answer",
                    "No weather result returned."
                ),
                web_search_answer=data.get(
                    "web_search_answer",
                    "No web-search result returned."
                ),

                ocr_sources=data.get(
                    "ocr_sources",
                    []
                )
            )

        except requests.exceptions.RequestException as error:

            return ApiResult(
                answer="",
                sources=[],
                success=False,
                error=str(error)
            )
