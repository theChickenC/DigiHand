import constants
import utils
import os
import sys

from PySide6.QtGui import QAction, QActionGroup, QFont, QIcon, QKeySequence, QImage, QTextDocument
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument
from wordView import WordView
from widgets import CustomTextEdit

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
    QHBoxLayout,
    QWidget,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QSpinBox,
    QAbstractSpinBox,
)


class PdfController(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        self.pbZoomIn = QPushButton(self)
        self.pbZoomIn.setIcon(QIcon(os.path.join("images", "zoom-in.svg")))
        self.pbZoomIn.setStatusTip("Zoom In PDF")
        self.layout.addWidget(self.pbZoomIn)

        

        self.pbZoomOut = QPushButton(self)
        self.pbZoomOut.setIcon(QIcon(os.path.join("images", "zoom-out.svg")))
        self.pbZoomOut.setStatusTip("Zoom Out PDF")
        self.layout.addWidget(self.pbZoomOut)

        self.pbZoomFit = QPushButton(self)
        self.pbZoomFit.setIcon(QIcon(os.path.join("images", "zoom-fit-best.svg")))
        self.pbZoomFit.setStatusTip("Best Fit PDF Zoom")
        self.layout.addWidget(self.pbZoomFit)

        self.pbZoomOG = QPushButton(self)
        self.pbZoomOG.setIcon(QIcon(os.path.join("images", "zoom-original.svg")))
        self.pbZoomOG.setStatusTip("Original PDF Zoom")
        self.layout.addWidget(self.pbZoomOG)

        self.pbRotateL = QPushButton(self)
        self.pbRotateL.setIcon(QIcon(os.path.join("images", "rotate-left.svg")))
        self.pbRotateL.setStatusTip("Rotate PDF Left")
        self.layout.addWidget(self.pbRotateL)

        self.pbRotateR = QPushButton(self)
        self.pbRotateR.setIcon(QIcon(os.path.join("images", "rotate-right.svg")))
        self.pbRotateR.setStatusTip("Rotate PDF Right")
        self.layout.addWidget(self.pbRotateR)

        self.pbFirstPage = QPushButton(self)
        self.pbFirstPage.setIcon(QIcon(os.path.join("images", "go-first-view-page.svg")))
        self.pbFirstPage.setStatusTip("First Page")
        self.layout.addWidget(self.pbFirstPage)

        self.pbPrevPage = QPushButton(self)
        self.pbPrevPage.setIcon(QIcon(os.path.join("images", "go-previous-view-page.svg")))
        self.pbPrevPage.setStatusTip("Previous Page")
        self.layout.addWidget(self.pbPrevPage)

        self.curPage = QSpinBox(self)
        self.curPage.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.layout.addWidget(self.curPage)

        self.pbNextPage = QPushButton(self)
        self.pbNextPage.setIcon(QIcon(os.path.join("images", "go-next-view-page.svg")))
        self.pbNextPage.setStatusTip("Next Page")
        self.layout.addWidget(self.pbNextPage)

        self.pbLastPage = QPushButton(self)
        self.pbLastPage.setIcon(QIcon(os.path.join("images", "go-last-view-page.svg")))
        self.pbLastPage.setStatusTip("Last Page")
        self.layout.addWidget(self.pbLastPage)

        spacer = QSpacerItem(200, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout.addSpacerItem(spacer)


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
