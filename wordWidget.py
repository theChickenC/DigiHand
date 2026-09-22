import constants
import utils
from PySide6.QtGui import QFont, QImage, QTextDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument
from widgets import CustomTextEdit
from wordController import WordController
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
    QWidget,
)

class WordWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        self.wordController = WordController()
        self.editor = WordView()
        # self.pdfViewer.selectionChanged.connect(self.update_format)
        self.layout.addWidget(self.wordController)
        self.layout.addWidget(self.editor)

        # start_width = self.width()
        # half_width = int(start_width * 0.5)
        # self.wordController.setMaximumWidth(half_width)

        self.update_format()

        #initConnection
        # self.wordController.undo_action.triggered.connect(self.editor.undo)
        # self.wordController.redo_action.triggered.connect(self.editor.redo)
        # self.wordController.cut_action.triggered.connect(self.editor.cut)
        # self.wordController.copy_action.triggered.connect(self.editor.copy)
        # self.wordController.paste_action.triggered.connect(self.editor.paste)
        # self.wordController.select_action.triggered.connect(self.editor.selectAll)
        # self.wordController.wrap_action.triggered.connect(self.edit_toggle_wrap)

        #self.fonts.currentFontChanged.connect(self.editor.setCurrentFont)
        # # Connect to the signal producing the text of the current selection. Convert the string to float
        # # and set as the pointsize. We could also use the index + retrieve from FONT_SIZES.
        # self.fontsize.currentTextChanged.connect(
        #     lambda s: self.editor.setFontPointSize(float(s))
        # )

        # self.bold_action.toggled.connect(
        #     lambda x: self.editor.setFontWeight(
        #         QFont.Weight.Bold if x else QFont.Weight.Normal
        #     )
        # )

        # self.italic_action.toggled.connect(self.editor.setFontItalic)
        # self.underline_action.toggled.connect(self.editor.setFontUnderline)
        # self.alignl_action.triggered.connect(
        #     lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # )
        # self.alignc_action.triggered.connect(
        #     lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # )
        # self.alignr_action.triggered.connect(
        #     lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignRight)
        # )
        # self.alignj_action.triggered.connect(
        #     lambda: self.editor.setAlignment(Qt.AlignmentFlag.AlignJustify)
        # )


    def edit_toggle_wrap(self):
        self.editor.setLineWrapMode(1 if self.editor.lineWrapMode() == 0 else 0)

    
    def setFile(self, path):
        load_result = self.pdf_doc.load(path)
        if load_result != QPdfDocument.Error.None_:
            self.statusBar().showMessage(f"Failed to load PDF: {load_result}")
            return
        
        self.pdfView.setDocument(self.pdf_doc)
        # self.pdfView.setPageMode(QPdfView.PageMode.MultiPage)
        # self.pdfView.setPageMode(QPdfView.PageMode.SinglePage)

        # jump to first page
        nav = self.pdfView.pageNavigator()
        nav.jumpToPage(0)



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
        """
        Update the font format toolbar/actions when a new text selection is made. This is necessary to keep
        toolbars/etc. in sync with the current edit state.
        :return:
        """
        # Disable signals for all format widgets, so changing values here does not trigger further formatting.
        # self.block_signals(self._format_actions, True)

        # self.wordController.update_format()
        # self.editor.update_format()


        # self.fonts.setCurrentFont(self.editor.currentFont())
        # # Nasty, but we get the font-size as a float but want it was an int
        # self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))

        # self.italic_action.setChecked(self.editor.fontItalic())
        # self.underline_action.setChecked(self.editor.fontUnderline())
        # self.bold_action.setChecked(self.editor.fontWeight() == QFont.Weight.Bold)

        # self.alignl_action.setChecked(
        #     self.editor.alignment() == Qt.AlignmentFlag.AlignLeft
        # )
        # self.alignc_action.setChecked(
        #     self.editor.alignment() == Qt.AlignmentFlag.AlignCenter
        # )
        # self.alignr_action.setChecked(
        #     self.editor.alignment() == Qt.AlignmentFlag.AlignRight
        # )
        # self.alignj_action.setChecked(
        #     self.editor.alignment() == Qt.AlignmentFlag.AlignJustify
        # )

        # self.block_signals(self._format_actions, False)