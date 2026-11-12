
import io
import os
import re
import logging

import pymupdf
from PIL import Image


logger = logging.getLogger(__name__)


class PDFImageExtractor:

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def extract_embedded_images(
        self,
        file_path: str,
        page_number: int,
    ) -> list[Image.Image]:

        logger.info(
            "Opening PDF for image extraction: %s | Page: %d",
            file_path,
            page_number + 1,
        )

        pdf = pymupdf.open(file_path)
        images = []

        try:
            page = pdf.load_page(page_number)
            processed_xrefs = set()

            safe_name = re.sub(
                r"[^A-Za-z0-9_.-]+",
                "_",
                os.path.basename(file_path),
            )

            for image_info in page.get_images(full=True):
                xref = image_info[0]

                if xref in processed_xrefs:
                    continue

                processed_xrefs.add(xref)

                try:
                    image_data = pdf.extract_image(xref)

                    image = Image.open(
                        io.BytesIO(image_data["image"])
                    ).convert("RGB")

                    output_dir = os.path.join(
                        "data",
                        "extracted_images",
                    )

                    os.makedirs(output_dir, exist_ok=True)

                    image_path = os.path.join(
                        output_dir,
                        f"{safe_name}_page_{page_number + 1}_xref_{xref}.png",
                    )

                    image.save(image_path)
                    images.append(image)

                    logger.info(
                        "Image extracted successfully | "
                        "Page: %d | Size: %s | Saved: %s",
                        page_number + 1,
                        image.size,
                        image_path,
                    )

                except Exception:
                    logger.exception(
                        "Could not extract image | Page: %d | Xref: %d",
                        page_number + 1,
                        xref,
                    )

            logger.info(
                "Image extraction completed | PDF: %s | "
                "Page: %d | Total images: %d",
                file_path,
                page_number + 1,
                len(images),
            )

            return images

        finally:
            pdf.close()

    def render_page(
        self,
        file_path: str,
        page_number: int,
    ) -> Image.Image:

        logger.info(
            "Rendering PDF page | File: %s | Page: %d | DPI: %d",
            file_path,
            page_number + 1,
            self.dpi,
        )

        pdf = pymupdf.open(file_path)

        try:
            page = pdf.load_page(page_number)
            zoom = self.dpi / 72

            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(zoom, zoom),
                alpha=False,
            )

            image = Image.open(
                io.BytesIO(pixmap.tobytes("png"))
            ).convert("RGB")

            logger.info(
                "PDF page rendered successfully | Page: %d | Size: %s",
                page_number + 1,
                image.size,
            )

            return image

        finally:
            pdf.close()
