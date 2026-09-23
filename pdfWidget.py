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
            self.statusBar().showMessage(f"Failed to load PDF: {load_result}")
            return
        
        self.pdfView.setDocument(self.pdf_doc)
        self.pdfView.setPageMode(QPdfView.PageMode.MultiPage)
        # self.pdfView.setPageMode(QPdfView.PageMode.SinglePage)



    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        else:
            return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        cursor = self.textCursor()
        document = self.document()

        if source.hasUrls():
            for u in source.urls():
                file_ext = utils.splitext(str(u.toLocalFile()))
                if u.isLocalFile() and file_ext in constants.IMAGE_EXTENSIONS:
                    image = QImage(u.toLocalFile())
                    document.addResource(
                        QTextDocument.ResourceType.ImageResource, u, image
                    )
                    cursor.insertImage(u.toLocalFile())

                else:
                    # If we hit a non-image or non-local URL break the loop and fall out
                    # to the super call & let Qt handle it
                    break

            else:
                # If all were valid images, finish here.
                return

        elif source.hasImage():
            image = source.imageData()
            uuid = utils.hexuuid()
            document.addResource(QTextDocument.ResourceType.ImageResource, uuid, image)
            cursor.insertImage(uuid)
            return

        super().insertFromMimeData(source)


