import io
import pymupdf
from PIL import Image


class DigiHandTools:
    @staticmethod
    def pdf_page_images(pdf_path, dpi=150, start=0):
        """Lazily render PDF pages from `start` on as PIL images.

        Yields (page_index_0based, image). A generator on purpose: pages
        before `start` never get rendered and each page is released after
        use, so a 300-page scan does not sit in RAM all at once.
        """
        doc = pymupdf.open(pdf_path)
        try:
            for i in range(start, len(doc)):
                pix = doc[i].get_pixmap(dpi=dpi)          # render page at given DPI
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                yield i, img
        finally:
            doc.close()

    @staticmethod
    def pdf_pages_to_images(pdf_path, dpi=150):
        """Eager list version, kept for scripts/tests."""
        return [img for _i, img in DigiHandTools.pdf_page_images(pdf_path, dpi)]

    @staticmethod
    def pdf_page_count(pdf_path):
        doc = pymupdf.open(pdf_path)
        try:
            return len(doc)
        finally:
            doc.close()

