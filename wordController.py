import constants
import utils
import os
import sys

from PySide6.QtGui import QAction, QActionGroup, QFont, QIcon, QKeySequence, QImage, QShortcut, QTextDocument
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument
from wordView import WordView
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
    QHBoxLayout,
    QWidget,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QLabel,
)

class WordController(QWidget):
    def __init__(self, wordView):
        super().__init__()

        self.wordView = wordView
        self.curFile = None

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
        self.fontsize.setCurrentText("18")
        self.layout.addWidget(self.fonts)
        self.layout.addWidget(self.fontsize)
        self.fontsize.currentTextChanged.connect(lambda s: self.wordView.setFontPointSize(float(s)))

        # self.pbBold = QPushButton("Bold", self)
        self.pbBold = QPushButton(self)
        self.pbBold.setIcon(QIcon(os.path.join("images", "edit-bold.png")))
        self.pbBold.setStatusTip("Bold (Ctrl+B)")
        self.pbBold.setCheckable(True)
        self.layout.addWidget(self.pbBold)
        self.pbBold.clicked.connect(self.toggle_bold)

        # self.pbItalic = QPushButton("Italic", self)
        self.pbItalic = QPushButton(self)
        self.pbItalic.setIcon(QIcon(os.path.join("images", "edit-italic.png")))
        self.pbItalic.setStatusTip("Italic (Ctrl+I)")
        self.pbItalic.setCheckable(True)
        self.layout.addWidget(self.pbItalic)
        self.pbItalic.clicked.connect(self.toggle_italic)

        # self.pbUnderline = QPushButton("Underline", self)
        self.pbUnderline = QPushButton(self)
        self.pbUnderline.setIcon(QIcon(os.path.join("images", "edit-underline.png")))
        self.pbUnderline.setStatusTip("Underline (Ctrl+U)")
        self.pbUnderline.setCheckable(True)
        self.layout.addWidget(self.pbUnderline)
        self.pbUnderline.clicked.connect(self.toggle_underline)

        # Ctrl+B / Ctrl+I / Ctrl+U, active only while the editor has focus
        for seq, fn in (
            ("Ctrl+B", self.toggle_bold),
            ("Ctrl+I", self.toggle_italic),
            ("Ctrl+U", self.toggle_underline),
        ):
            sc = QShortcut(QKeySequence(seq), self.wordView)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

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

        # self.pbTest = QPushButton(self, "T")
        # self.pbTest.setStatusTip("Test")
        # self.layout.addWidget(self.pbTest)
        # self.pbTest.clicked.connect(self.on_clicked_pbTest)

        self.lblPage = QLabel(self)
        self.lblPage.setStatusTip("Current page")
        self.layout.addWidget(self.lblPage)

        spacer = QSpacerItem(200, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout.addSpacerItem(spacer)
    
        # self._format_actions = [
        #     self.fonts,
        #     self.fontsize,
        #     self.bold_action,
        #     self.italic_action,
        #     self.underline_action,
        #     # We don't need to disable signals for alignment, as they are paragraph-wide.
        # ]


        # Initialize.
        # keep the format buttons in sync as the cursor moves/selections change
        self.wordView.cursorPositionChanged.connect(self.update_format)
        self.update_format()
        # self.update_title()
        self.show()

    
    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    # --- character formatting (bold / italic / underline) -----------------
    # Applied through the editor's current char format: acts on the
    # selection when there is one, otherwise sets the style typed next.

    def toggle_bold(self):
        fmt = self.wordView.currentCharFormat()
        on = not (fmt.fontWeight() >= QFont.Weight.Bold)
        fmt.setFontWeight(QFont.Weight.Bold if on else QFont.Weight.Normal)
        self._apply_toggle(self.pbBold, fmt, on)

    def toggle_italic(self):
        fmt = self.wordView.currentCharFormat()
        on = not fmt.fontItalic()
        fmt.setFontItalic(on)
        self._apply_toggle(self.pbItalic, fmt, on)

    def toggle_underline(self):
        fmt = self.wordView.currentCharFormat()
        on = not fmt.fontUnderline()
        fmt.setFontUnderline(on)
        self._apply_toggle(self.pbUnderline, fmt, on)

    def _apply_toggle(self, button, fmt, on):
        self.wordView.mergeCurrentCharFormat(fmt)
        button.blockSignals(True)
        button.setChecked(on)
        button.blockSignals(False)

    def update_format(self):
        """Sync the format buttons with the text under the cursor."""
        fmt = self.wordView.currentCharFormat()
        for btn, on in (
            (self.pbBold, fmt.fontWeight() >= QFont.Weight.Bold),
            (self.pbItalic, fmt.fontItalic()),
            (self.pbUnderline, fmt.fontUnderline()),
        ):
            btn.blockSignals(True)
            btn.setChecked(on)
            btn.blockSignals(False)

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.show()

    def switchFile(self, fold_in:str, page_index0:int):
        if not fold_in:
            return
        file_path_target = os.path.join(fold_in, f"page_{page_index0}.txt")
        # only save when there is a real previous file; the first page switch
        # has curFile None and saving would raise TypeError
        if (self.wordView.document().isModified() or self.wordView.isDirty()) and self.curFile:
            self.saveChanges(self.curFile)

        try:
            with open(file_path_target, "r", encoding="utf-8") as file:
                content = file.read()
            self.wordView.clear()
            self.wordView.setText(content)
        except FileNotFoundError:
            print("missing:", file_path_target)
            self.wordView.clear()
        # clear()/setText() re-mark the document dirty; reset it here or the
        # next page switch silently overwrites the previous txt with empties
        self.wordView.resetDirty()
        self.wordView.document().setModified(False)

        self.lblPage.setText(f"Page: {page_index0 + 1}")
        self.curFile = file_path_target

    def saveChanges(self, fold_in: str):
            with open(fold_in, "w", encoding="utf-8") as f:
                f.write(self.wordView.toPlainText())


