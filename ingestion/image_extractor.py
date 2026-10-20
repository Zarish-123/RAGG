
import io
import os
import re

import pymupdf
from PIL import Image


class PDFImageExtractor:

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def extract_embedded_images(
        self,
        file_path: str,
        page_number: int,
    ) -> list[Image.Image]:

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

                    print(
                        f"[IMAGE] Page {page_number + 1}: "
                        f"extracted image {image.size}"
                    )

                except Exception as exc:
                    print(f"[IMAGE] Could not extract xref {xref}: {exc}")

            return images

        finally:
            pdf.close()

    def render_page(
        self,
        file_path: str,
        page_number: int,
    ) -> Image.Image:

        pdf = pymupdf.open(file_path)

        try:
            page = pdf.load_page(page_number)
            zoom = self.dpi / 72

            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(zoom, zoom),
                alpha=False,
            )

            return Image.open(
                io.BytesIO(pixmap.tobytes("png"))
            ).convert("RGB")

        finally:
            pdf.close()
