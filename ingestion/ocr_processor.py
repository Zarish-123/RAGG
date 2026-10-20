
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from core.interfaces.ocr import OCRProcessor


class TesseractOCRProcessor(OCRProcessor):

    def __init__(self, language: str = "eng"):
        self.language = language
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        image = image.convert("L")

        width, height = image.size
        image = image.resize((width * 2, height * 2))

        image = ImageEnhance.Contrast(image).enhance(2.0)
        image = image.filter(ImageFilter.SHARPEN)
        return ImageOps.autocontrast(image)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        cleaned_lines = []

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            # Sirf almost-empty noise lines remove karo.
            if sum(ch.isalnum() for ch in line) < 2:
                continue

            line = re.sub(r"[ \t]+", " ", line)
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def _quality_score(text: str) -> int:
        if not text:
            return -1

        words = re.findall(r"\b[\w'-]+\b", text)
        readable_chars = sum(ch.isalnum() for ch in text)
        noise = text.count("�")

        return readable_chars + len(words) * 3 - noise * 10

    def extract_text(self, image: Image.Image) -> str:
        processed = self.preprocess_image(image)

        configs = [
            "--oem 3 --psm 3",
            "--oem 3 --psm 6",
            "--oem 3 --psm 11",
        ]

        results = []

        for config in configs:
            try:
                raw_text = pytesseract.image_to_string(
                    processed,
                    lang=self.language,
                    config=config,
                )

                cleaned = self.clean_text(raw_text)

                if cleaned:
                    results.append(cleaned)

            except pytesseract.TesseractError as exc:
                print(f"[OCR] Tesseract error: {exc}")

        if not results:
            return ""

        # Historical, scientific, aur general text sab ke liye
        # same topic-independent quality scoring.
        return max(results, key=self._quality_score)
