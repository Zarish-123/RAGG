
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str
    k: int = 10


class Source(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    question: str

    # Backward compatibility
    answer: str

    rag_answer: str
    ocr_answer: str
    weather_answer: str
    web_search_answer: str

    sources: List[Source] = Field(default_factory=list)
    ocr_sources: List[Source] = Field(default_factory=list)
