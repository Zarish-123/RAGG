
import logging
import time
from typing import Any

import ollama

from core.interfaces.llm import LLM


logger = logging.getLogger(__name__)


class OllamaLLM(LLM):

    def __init__(self, model: str = "llama3.2:3b"):

        self.model = model

        # Generation settings
        self.options = {
            "temperature": 0.1,
            "num_predict": 128,
            "num_ctx": 4096,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """
        Extract generated text from Ollama response.

        Ollama can return a GenerateResponse object,
        while some versions or wrappers may return a dictionary.
        """

        if isinstance(response, dict):
            answer = response.get("response", "")

        else:
            answer = getattr(response, "response", "")

        if answer is None:
            return ""

        return str(answer).strip()

    @staticmethod
    def _get_response_metadata(response: Any) -> dict:
        """
        Extract useful generation metadata for logging.
        """

        metadata = {}

        fields = [
            "total_duration",
            "load_duration",
            "prompt_eval_count",
            "prompt_eval_duration",
            "eval_count",
            "eval_duration",
        ]

        for field in fields:

            if isinstance(response, dict):
                value = response.get(field)

            else:
                value = getattr(response, field, None)

            if value is not None:
                metadata[field] = value

        return metadata

    def generate(self, prompt: str) -> str:

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("The generation prompt cannot be empty.")

        prompt_length = len(prompt)
        started_at = time.perf_counter()

        logger.info(
            "Ollama generation started. "
            "model=%s prompt_chars=%d options=%s",
            self.model,
            prompt_length,
            self.options,
        )

        try:

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options=self.options,
                keep_alive="5m",
                stream=False,
            )

            # Important fix:
            # GenerateResponse is normally an object,
            # not a dictionary.
            answer = self._extract_response_text(response)

            elapsed_seconds = time.perf_counter() - started_at

            metadata = self._get_response_metadata(response)

            if not answer:

                logger.error(
                    "Ollama returned an empty response. "
                    "model=%s elapsed_seconds=%.2f "
                    "metadata=%s",
                    self.model,
                    elapsed_seconds,
                    metadata,
                )

                raise RuntimeError(
                    "Ollama generated an empty response."
                )

            logger.info(
                "Ollama generation completed. "
                "model=%s elapsed_seconds=%.2f "
                "prompt_chars=%d answer_chars=%d "
                "metadata=%s",
                self.model,
                elapsed_seconds,
                prompt_length,
                len(answer),
                metadata,
            )

            return answer

        except Exception:

            elapsed_seconds = time.perf_counter() - started_at

            logger.exception(
                "Ollama generation failed. "
                "model=%s elapsed_seconds=%.2f "
                "prompt_chars=%d",
                self.model,
                elapsed_seconds,
                prompt_length,
            )

            raise
