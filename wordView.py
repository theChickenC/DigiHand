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

    def is_dirty(self):
        return self.document().revision() != self._saved_revision
    

    # @Slot(bool)
    def set_bold(self, checked: bool):
        # fmt = QTextCharFormat()
        # fmt.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        self.fontWeight() == QFont.Weight.Bold
        # Applies to the current selection if there is one; otherwise
        # applies to whatever gets typed next at the cursor.
        # self.mergeCurrentCharFormat(fmt)

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


    def update_format(self):
        return
