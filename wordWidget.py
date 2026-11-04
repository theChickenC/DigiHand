import constants
import os
import utils

from PySide6.QtGui import QFont, QImage, QTextDocument, QTextCharFormat
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument
from PySide6.QtCore import Signal, Slot
from customTextEdit import CustomTextEdit
from wordController import WordController
from wordView import WordView
# from pdfController import PdfController
# from pdfView import PdfView
# from pdfWidget import PdfWidget

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

class WordWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.outputPath = "D://WelSimLLC-github//DigiHand//output//journalReview"  # set via setOutputPath() after a solve run

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        self.editor = WordView()
        self.wordController = WordController(self.editor)

        # self.pdfViewer.selectionChanged.connect(self.update_format)
        self.layout.addWidget(self.wordController)
        self.layout.addWidget(self.editor)


    def setOutputPath(self, outputPath: str):
        self.outputPath = outputPath

    def curPage_changed(self, page_0based):
        # print("page from wordWidget: ", page_0based)
        if not self.outputPath:
            return
        self.wordController.switchFile(str(self.outputPath), page_0based)


    # def _on_format_changed(self, fmt: QTextCharFormat):
    #     is_bold = fmt.fontWeight() == QFont.Weight.Bold
    #     # self.wordController.pbBold.connect(self.editor.fontWeight() == QFont.Weight.Bold)

    #     self.wordController.set_checked_silently(is_bold)
        

    # def edit_toggle_wrap(self):
    #     self.editor.setLineWrapMode(1 if self.editor.lineWrapMode() == 0 else 0)

    
    # def setFile(self, path):
    #     load_result = self.pdf_doc.load(path)
    #     if load_result != QPdfDocument.Error.None_:
    #         self.statusBar().showMessage(f"Failed to load PDF: {load_result}")
    #         return
        
    #     self.pdfView.setDocument(self.pdf_doc)
    #     self.pdfView.setPageMode(QPdfView.PageMode.MultiPage)
    #     # self.pdfView.setPageMode(QPdfView.PageMode.SinglePage)

    #     # jump to first page
    #     # nav = self.pdfView.pageNavigator()
    #     # nav.jumpToPage(0)



        


