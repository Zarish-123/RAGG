
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ApiResult:
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)

    rag_answer: str = ""
    ocr_answer: str = ""
    weather_answer: str = ""
    web_search_answer: str = ""

    ocr_sources: List[Dict[str, Any]] = field(default_factory=list)

    success: bool = True
    error: Optional[str] = None
