import constants
import utils
import os
import tempfile

import pymupdf
from PySide6.QtGui import QFont, QImage, QTextDocument
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMessageBox
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument


class PdfView(QPdfView):
    def __init__(self, pdf_doc):
        super().__init__()
        # self.setAutoFormatting(QPdfView.AutoFormattingFlag.AutoAll)
        # Initialize default font size.
        font = QFont("Times", 12)
        self.setFont(font)
        self.pdf_doc = pdf_doc
        self.sourcePath: str | None = None    # set by PdfWidget.setFile
        self.rotated_bytes = None   # in-memory copy with rotations baked in
        self.rot_tmp_path = None    # temp file backing that copy
        self._rotation = 0          # Qt removed the rotation getter; track ours

    def resetRotation(self):
        """Drop per-file rotation state (called when a new PDF is opened)."""
        self.sourcePath = None
        self.rotated_bytes = None
        self._rotation = 0
        if self.rot_tmp_path:
            try:
                os.remove(self.rot_tmp_path)
            except OSError:
                pass
            self.rot_tmp_path = None
    
    def zoomIn(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        zoom = self.zoomFactor() 
        self.setZoomFactor(zoom + 0.2)
        # QMessageBox.information(self, "Info", "zoomIn() gets called.")
        return

    def zoomOut(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        zoom = self.zoomFactor() 
        self.setZoomFactor(zoom - 0.2)
        # QMessageBox.information(self, "Info", "zoomOut() gets called.")
        return
    
    def zoomFit(self):
        self.setZoomMode(QPdfView.ZoomMode.FitInView)
        # QMessageBox.information(self, "Info", "zoomFit() gets called.")
        return
    
    def zoomOG(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        self.setZoomFactor(1)
        # QMessageBox.information(self, "Info", "zoomOG() gets called.")
        return
    
    def rotateL(self):
        self._rotate(-90)
        # QMessageBox.information(self, "Info", "rotateL() gets called.")
        
        return
    
    def rotateR(self):
        self._rotate(90)
        # QMessageBox.information(self, "Info", "rotateR() gets called.")
        return

    def _rotate(self, delta):
        setter = getattr(self, "setPageRotation", None)
        if callable(setter):
            # Qt <= 6.11: display-only rotation API on the view itself
            self._rotation = (self._rotation + delta) % 360
            setter(self._rotation)
            return

        # Qt >= 6.12 removed QPdfView's rotation API entirely. Bake the
        # rotation into an in-memory copy of the PDF and reload it; the file
        # on disk is never modified.
        src = self.rotated_bytes
        if src is None:
            if not self.sourcePath or not os.path.isfile(self.sourcePath):
                return
            with open(self.sourcePath, "rb") as fh:
                src = fh.read()
        try:
            doc = pymupdf.open(stream=src, filetype="pdf")
            for pg in doc:
                pg.set_rotation((pg.rotation + delta) % 360)
            data = doc.tobytes()
            doc.close()
        except Exception:
            return  # corrupt/encrypted PDF: rotation is a no-op, not a crash

        nav = self.pageNavigator()
        cur_page = nav.currentPage()
        self.rotated_bytes = data
        # Qt 6.12 dropped QPdfDocument.loadFromData, so reload through a
        # temp file; the source file on disk is never modified.
        fd, tmp = tempfile.mkstemp(prefix="digihand_rot_", suffix=".pdf")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        old_tmp = self.rot_tmp_path
        self.rot_tmp_path = tmp
        if self.pdf_doc.load(tmp) != QPdfDocument.Error.None_:
            return
        if old_tmp:
            try:
                os.remove(old_tmp)
            except OSError:
                pass
        nav.jump(cur_page, QPointF(0, 0))  # stay on the page we were reading
    
    def firstPage(self):
        # QMessageBox.information(self, "Info", "firstPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        nav.jump(0, QPointF(0, 0))
        return
    
    def prevPage(self):
        nav = self.pageNavigator()
        cur = nav.currentPage()
        if cur > 0:
            # jump(page, position, zoom=0 keeps current zoom)
            nav.jump(cur - 1, QPointF(0, 0))    

    def nextPage(self):
        # QMessageBox.information(self, "Info", "nextPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        numPages = self.pdf_doc.pageCount()
        if cur < numPages - 1:
            # jump(page, position, zoom=0 keeps current zoom)
            nav.jump(cur + 1, QPointF(0, 0))        
        return

    def lastPage(self):
        # QMessageBox.information(self, "Info", "lastPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        numPages = self.pdf_doc.pageCount()
        nav.jump(numPages-1, QPointF(0, 0))
        return


    
