import constants
import utils
import os
import sys

from PySide6.QtGui import QAction, QActionGroup, QFont, QIcon, QKeySequence, QImage, QTextDocument
from PySide6.QtCore import QSize, Qt
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
)

class WordController(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        # self.pbUndo = QPushButton("Undo", self)
        self.pbUndo = QPushButton(self)
        self.pbUndo.setIcon(QIcon(os.path.join("images", "arrow-curve-180-left.png")))
        self.pbUndo.setStatusTip("Undo last change")
        self.layout.addWidget(self.pbUndo)
        self.pbUndo.setVisible(False)

        # self.pbRedo = QPushButton("Redo", self)
        self.pbRedo = QPushButton(self)
        self.pbRedo.setIcon(QIcon(os.path.join("images", "arrow-curve.png")))
        self.pbRedo.setStatusTip("Redo last change")
        self.layout.addWidget(self.pbRedo)
        self.pbRedo.setVisible(False)

        # self.pbCut = QPushButton("Cut", self)
        self.pbCut = QPushButton(self)
        self.pbCut.setIcon(QIcon(os.path.join("images", "scissors.png")))
        self.pbCut.setStatusTip("Cut selected text")
        self.layout.addWidget(self.pbCut)
        self.pbCut.setVisible(False)

        # self.pbCopy = QPushButton("Copy", self)
        self.pbCopy = QPushButton(self)
        self.pbCopy.setIcon(QIcon(os.path.join("images", "document-copy.png")))
        self.pbCopy.setStatusTip("Copy selected text")
        self.layout.addWidget(self.pbCopy)       
        self.pbCopy.setVisible(False)

        # self.pbPaste = QPushButton("Paste", self)
        self.pbPaste = QPushButton(self)
        self.pbPaste.setIcon(QIcon(os.path.join("images", "clipboard-paste-document-text.png")))
        self.pbPaste.setStatusTip("Paste from clipboard")
        self.layout.addWidget(self.pbPaste)    
        self.pbPaste.setVisible(False)

        # self.pbSelectAll = QPushButton("Select all", self)
        self.pbSelectAll = QPushButton(self)
        self.pbSelectAll.setIcon(QIcon(os.path.join("images", "selection-input.png")))
        self.pbSelectAll.setStatusTip("Select all text")
        self.layout.addWidget(self.pbSelectAll)   
        self.pbSelectAll.setVisible(False)

        # self.pbWrap = QPushButton("Wrap text to window", self)
        self.pbWrap = QPushButton(self)
        self.pbWrap.setIcon(QIcon(os.path.join("images", "arrow-continue.png")))
        self.pbWrap.setStatusTip("Toggle wrap text to window")
        self.layout.addWidget(self.pbWrap)

        self.fonts = QFontComboBox()
        self.fonts.setMaximumWidth(110)
        self.fonts.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.fontsize = QComboBox()
        self.fontsize.addItems([str(s) for s in constants.FONT_SIZES])
        self.layout.addWidget(self.fonts)
        self.layout.addWidget(self.fontsize)

        # self.pbBold = QPushButton("Bold", self)
        self.pbBold = QPushButton(self)
        self.pbBold.setIcon(QIcon(os.path.join("images", "edit-bold.png")))
        self.pbBold.setStatusTip("Bold")
        self.layout.addWidget(self.pbBold)

        # self.pbItalic = QPushButton("Italic", self)
        self.pbItalic = QPushButton(self)
        self.pbItalic.setIcon(QIcon(os.path.join("images", "edit-italic.png")))
        self.pbItalic.setStatusTip("Italic")
        self.layout.addWidget(self.pbItalic)

        # self.pbUnderline = QPushButton("Underline", self)
        self.pbUnderline = QPushButton(self)
        self.pbUnderline.setIcon(QIcon(os.path.join("images", "edit-underline.png")))
        self.pbUnderline.setStatusTip("Underline")
        self.layout.addWidget(self.pbUnderline)

        # self.pbAlignL = QPushButton("Align left", self)
        self.pbAlignL = QPushButton(self)
        self.pbAlignL.setIcon(QIcon(os.path.join("images", "edit-alignment.png")))
        self.pbAlignL.setStatusTip("Align text left")
        self.layout.addWidget(self.pbAlignL)

        # self.pbAlignC = QPushButton("Align center", self)
        self.pbAlignC = QPushButton(self)
        self.pbAlignC.setIcon(QIcon(os.path.join("images", "edit-alignment-center.png")))
        self.pbAlignC.setStatusTip("Align text center")
        self.layout.addWidget(self.pbAlignC)

        # self.pbAlignR = QPushButton("Align right", self)
        self.pbAlignR = QPushButton(self)
        self.pbAlignR.setIcon(QIcon(os.path.join("images", "edit-alignment-right.png")))
        self.pbAlignR.setStatusTip("Align text right")
        self.layout.addWidget(self.pbAlignR)

        # self.pbAlignJ = QPushButton("Justify", self)
        self.pbAlignJ = QPushButton(self)
        self.pbAlignJ.setIcon(QIcon(os.path.join("images", "edit-alignment-justify.png")))
        self.pbAlignJ.setStatusTip("Justify text")
        self.layout.addWidget(self.pbAlignJ)

        spacer = QSpacerItem(200, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout.addSpacerItem(spacer)
    
        # format_group = QActionGroup(self)
        # format_group.setExclusive(True)
        # format_group.addAction(self.alignl_action)
        # format_group.addAction(self.alignc_action)
        # format_group.addAction(self.alignr_action)
        # format_group.addAction(self.alignj_action)

        # self._format_actions = [
        #     self.fonts,
        #     self.fontsize,
        #     self.bold_action,
        #     self.italic_action,
        #     self.underline_action,
        #     # We don't need to disable signals for alignment, as they are paragraph-wide.
        # ]



        # Initialize.
        self.update_format()
        # self.update_title()
        self.show()

 
    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    def update_format(self):
        """
        Update the font format toolbar/actions when a new text selection is made. This is necessary to keep
        toolbars/etc. in sync with the current edit state.
        :return:
        """
        # Disable signals for all format widgets, so changing values here does not trigger further formatting.
        self.block_signals(self._format_actions, True)

        self.fonts.setCurrentFont(self.editor.currentFont())
        # Nasty, but we get the font-size as a float but want it was an int
        self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))

        self.italic_action.setChecked(self.editor.fontItalic())
        self.underline_action.setChecked(self.editor.fontUnderline())
        self.bold_action.setChecked(self.editor.fontWeight() == QFont.Weight.Bold)

        self.alignl_action.setChecked(
            self.editor.alignment() == Qt.AlignmentFlag.AlignLeft
        )
        self.alignc_action.setChecked(
            self.editor.alignment() == Qt.AlignmentFlag.AlignCenter
        )
        self.alignr_action.setChecked(
            self.editor.alignment() == Qt.AlignmentFlag.AlignRight
        )
        self.alignj_action.setChecked(
            self.editor.alignment() == Qt.AlignmentFlag.AlignJustify
        )

        self.block_signals(self._format_actions, False)

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.show()

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
