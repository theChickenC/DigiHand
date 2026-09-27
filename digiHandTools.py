import io
import sys
from pathlib import Path
import pymupdf
# import fitz
from PIL import Image

class DigiHandTools():
    @staticmethod
    def pdf_pages_to_images(pdf_path, dpi=150):
        """Convert every page of a PDF to a PIL image. Returns list of (page_index, image)."""
        doc = pymupdf.open(pdf_path)
        pages = []
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(dpi=dpi)          # render page at given DPI
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            # pages.append((i + 1, img))                 # 1-based page number
            pages.append(img)                 # 1-based page number
        doc.close()
        return pages

