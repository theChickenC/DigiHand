import constants
import utils
from PySide6.QtGui import QFont, QImage, QTextDocument, QTextCharFormat
from PySide6.QtCore import Signal, Slot
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument
# from wordController import WordController
from customTextEdit import CustomTextEdit

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
    QTextEdit,
)

class WordView(CustomTextEdit):
    # formatChanged = Signal(QTextCharFormat) 
    dirtyChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        font = QFont("Times", 18)
        self.setFont(font)
        self.setFontPointSize(18)

        self.bDirty = False
        self.document().contentsChanged.connect(self.onContentsChanged)
        # self.document().cursorPositionChanged.connect(self.onCursorPositionChanged)
        # self.document().documentLayoutChanged.connect(self.onDocumentLayoutChanged)
        # self.document().modificationChanged.connect(self.onModificationChanged)

    def onContentsChanged(self):
        self.bDirty = True

    def resetDirty(self):
        self.bDirty = False        

    def isDirty(self) -> bool:
        return self.bDirty

    # def onCursorPositionChanged(self):
    #     print("cursor position changed")
    #     return
    
    # def onDocumentLayoutChanged(self):
    #     print("document layout changed")
    #     return

    # def onModificationChanged(self, modified):
    #     print("modification changed")
    #     # self.dirtyChanged.emit(modified)
    #     return


    






