import constants
import utils
from PySide6.QtGui import QFont, QImage, QTextDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtCore import QPointF
from PySide6.QtPdf import QPdfDocument
from pdfController import PdfController
from pdfView import PdfView
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

class PdfWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        self.pdf_doc = QPdfDocument()
        self.pdfView = PdfView(self.pdf_doc)
        self.pdfController = PdfController(self.pdfView)
        # self.pdfViewer.selectionChanged.connect(self.update_format)
        self.layout.addWidget(self.pdfController)
        self.layout.addWidget(self.pdfView)


    def setFile(self, path):
        load_result = self.pdf_doc.load(path)
        if load_result != QPdfDocument.Error.None_:
            return load_result  # caller surfaces the error on its status bar

        self.pdfView.setDocument(self.pdf_doc)
        self.pdfView.setPageMode(QPdfView.PageMode.MultiPage)
        # page spin box default max is 99 — keep it in sync with the document
        self.pdfController.spCurPage.setMaximum(max(1, self.pdf_doc.pageCount()))
        self.pdfController.spCurPage.setValue(1)
        return None
        # self.pdfView.setPageMode(QPdfView.PageMode.SinglePage)





