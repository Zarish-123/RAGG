
import re

from pypdf import PdfReader

from core.interfaces.document_loader import DocumentLoader
from core.interfaces.models.document import Document
from core.interfaces.ocr import OCRProcessor
from ingestion.image_extractor import PDFImageExtractor


class PDFLoader(DocumentLoader):

    def __init__(
        self,
        ocr_processor: OCRProcessor | None = None,
        image_extractor: PDFImageExtractor | None = None,
    ):
        self.ocr_processor = ocr_processor
        self.image_extractor = image_extractor

    @staticmethod
    def _merge_ocr_text(texts: list[str]) -> str:
        seen = set()
        lines = []

        for text in texts:
            for line in text.splitlines():
                line = line.strip()
                normalized = re.sub(
                    r"\s+",
                    " ",
                    line,
                ).casefold()

                if not normalized or normalized in seen:
                    continue

                seen.add(normalized)
                lines.append(line)

        return "\n".join(lines)

    def load(self, file_path: str):
        reader = PdfReader(file_path)
        documents = []

        for page_index, page in enumerate(reader.pages):
            page_number = page_index + 1
            native_text = (page.extract_text() or "").strip()
            ocr_parts = []

            if self.ocr_processor and self.image_extractor:
                try:
                    images = self.image_extractor.extract_embedded_images(
                        file_path,
                        page_index,
                    )

                    for image in images:
                        text = self.ocr_processor.extract_text(image)

                        if text.strip():
                            ocr_parts.append(text.strip())

                    # Sparse/empty native text may indicate a scanned page.
                    # OCR the rendered page if native extraction is incomplete.
                    if len(native_text) < 250:
                        page_image = self.image_extractor.render_page(
                            file_path,
                            page_index,
                        )

                        page_text = self.ocr_processor.extract_text(
                            page_image
                        )

                        if page_text.strip():
                            ocr_parts.append(page_text.strip())

                except Exception as exc:
                    print(
                        f"[PDF LOADER] OCR failed on page "
                        f"{page_number}: {exc}"
                    )

            metadata = {
                "page": page_number,
                "source": file_path,
            }

            if native_text:
                documents.append(
                    Document(
                        content=native_text,
                        metadata={
                            **metadata,
                            "content_type": "native",
                        },
                    )
                )

            ocr_text = self._merge_ocr_text(ocr_parts)

            if ocr_text:
                documents.append(
                    Document(
                        content=ocr_text,
                        metadata={
                            **metadata,
                            "content_type": "ocr",
                        },
                    )
                )

            if not native_text and not ocr_text:
                print(
                    f"[PDF LOADER] No text extracted "
                    f"from page {page_number}."
                )

        return documents
