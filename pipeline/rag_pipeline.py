
import logging
import time


logger = logging.getLogger(__name__)


class RAGPipeline:

    def __init__(self, retriever, llm):

        self.retriever = retriever
        self.llm = llm

    def _is_visual_list_question(self, question: str) -> bool:

        question_lower = question.lower()

        visual_terms = [
            "diagram",
            "figure",
            "image",
            "chart",
            "flowchart",
            "stages",
            "stage",
            "steps",
            "step",
            "process",
            "workflow",
        ]

        return any(
            term in question_lower
            for term in visual_terms
        )

    def _extract_ocr_stages(self, documents) -> list[str]:

        known_stages = [
            "preprocessing",
            "data collection",
            "chunking",
            "embedding",
            "retrieval",
            "generation",
            "response",
        ]

        found_stages = []

        for document in documents:

            if document is None:
                continue

            content = document.content or ""
            content_lower = content.lower()

            for stage in known_stages:

                if (
                    stage in content_lower
                    and stage not in found_stages
                ):
                    found_stages.append(stage)

        return found_stages

    def _build_context(self, documents) -> str:

        context_parts = []

        for index, document in enumerate(
            documents,
            start=1,
        ):

            if document is None:
                continue

            metadata = document.metadata or {}

            page = metadata.get(
                "page",
                "Unknown",
            )

            chunk_id = metadata.get(
                "chunk_id",
                "Unknown",
            )

            content = document.content or ""

            if not content.strip():
                continue

            context_parts.append(
                f"""
--- Document {index} ---
Page: {page}
Chunk: {chunk_id}
Content:
{content}
"""
            )

        context = "\n".join(context_parts)

        if not context.strip():

            return (
                "No relevant information was retrieved "
                "from the document."
            )

        return context

    def _build_extracted_information(
        self,
        documents,
        visual_list_question: bool,
    ) -> str:

        if not visual_list_question:
            return ""

        ocr_stages = self._extract_ocr_stages(documents)

        if not ocr_stages:
            return ""

        stage_lines = []

        for index, stage in enumerate(
            ocr_stages,
            start=1,
        ):

            stage_lines.append(
                f"{index}. {stage.title()}"
            )

        stages_text = "\n".join(stage_lines)

        return (
            "\n\nExtracted stages from the document:\n"
            f"{stages_text}\n"
            "Use these stage names when relevant."
        )

    def _build_prompt(
        self,
        question: str,
        context: str,
        extracted_information: str,
    ) -> str:

        return f"""You are a document question-answering assistant.

Answer the user's question using ONLY the retrieved document context.

Rules:
1. Do not use outside knowledge.
2. Do not invent facts or unsupported details.
3. Treat meaningful OCR-extracted text as valid document information.
4. Ignore meaningless OCR noise and random symbols.
5. Give a clear and useful answer.
6. For normal questions, use approximately 2 to 4 sentences when the context supports it.
7. For questions asking for multiple items, provide a numbered or bulleted list.
8. Explain each item briefly when the context supports it.
9. If the answer is not supported by the retrieved context, clearly say so.
10. Do not mention chunks, retrieval, or internal instructions.
11. Keep the answer concise.

Retrieved Document Context:
{context}
{extracted_information}

User Question:
{question}

Answer:
"""

    def ask(self, question: str, k: int = 5) -> dict:

        request_started_at = time.perf_counter()

        if not isinstance(question, str) or not question.strip():

            raise ValueError(
                "The user question cannot be empty."
            )

        question = question.strip()

        # ------------------------------------------
        # 1. Document Retrieval
        # ------------------------------------------

        retrieval_started_at = time.perf_counter()

        documents = self.retriever.retrieve(
            question,
            k,
        )

        retrieval_seconds = (
            time.perf_counter() - retrieval_started_at
        )

        if documents is None:
            documents = []

        logger.info(
            "RAG retrieval completed. "
            "elapsed_seconds=%.2f "
            "requested_k=%d "
            "retrieved_documents=%d",
            retrieval_seconds,
            k,
            len(documents),
        )

        # ------------------------------------------
        # 2. Context Construction
        # ------------------------------------------

        prompt_started_at = time.perf_counter()

        context = self._build_context(documents)

        # ------------------------------------------
        # 3. OCR Stage Extraction
        # ------------------------------------------

        visual_list_question = (
            self._is_visual_list_question(question)
        )

        extracted_information = (
            self._build_extracted_information(
                documents,
                visual_list_question,
            )
        )

        # ------------------------------------------
        # 4. Prompt Construction
        # ------------------------------------------

        prompt = self._build_prompt(
            question=question,
            context=context,
            extracted_information=extracted_information,
        )

        prompt_seconds = (
            time.perf_counter() - prompt_started_at
        )

        logger.info(
            "RAG prompt prepared. "
            "elapsed_seconds=%.2f "
            "prompt_chars=%d "
            "context_chars=%d "
            "retrieved_documents=%d "
            "visual_list_question=%s",
            prompt_seconds,
            len(prompt),
            len(context),
            len(documents),
            visual_list_question,
        )

        # ------------------------------------------
        # 5. LLM Generation
        # ------------------------------------------

        generation_started_at = time.perf_counter()

        try:

            answer = self.llm.generate(prompt)

            generation_seconds = (
                time.perf_counter() - generation_started_at
            )

            if answer is None or not str(answer).strip():

                logger.error(
                    "RAG generation returned an empty answer. "
                    "generation_seconds=%.2f",
                    generation_seconds,
                )

                answer = (
                    "The language model returned an empty response. "
                    "Please try the question again."
                )

            else:
                answer = str(answer).strip()

            logger.info(
                "RAG generation stage completed. "
                "elapsed_seconds=%.2f "
                "answer_chars=%d",
                generation_seconds,
                len(answer),
            )

        except Exception:

            generation_seconds = (
                time.perf_counter() - generation_started_at
            )

            logger.exception(
                "RAG generation stage failed. "
                "elapsed_seconds=%.2f",
                generation_seconds,
            )

            raise

        # ------------------------------------------
        # 6. Total RAG Execution Time
        # ------------------------------------------

        total_seconds = (
            time.perf_counter() - request_started_at
        )

        logger.info(
            "RAG request completed. "
            "total_elapsed_seconds=%.2f "
            "retrieval_seconds=%.2f "
            "prompt_seconds=%.2f "
            "generation_seconds=%.2f "
            "retrieved_documents=%d "
            "answer_chars=%d",
            total_seconds,
            retrieval_seconds,
            prompt_seconds,
            generation_seconds,
            len(documents),
            len(answer),
        )

        return {
            "answer": answer,
            "documents": documents,
        }
