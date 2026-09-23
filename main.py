import os
import sys

import constants
import utils
from PySide6.QtCore import (
    Qt, 
    QSize, 
    QSettings,
)
from PySide6.QtGui import (
    QAction, 
    QActionGroup, 
    QFont, 
    QIcon, 
    QKeySequence,
    )
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
    QSplitter,
)
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument

from widgets import CustomTextEdit
from pdfWidget import PdfWidget
from wordWidget import WordWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings("clairc.com", "DigiHand")
        self.restore_window_state()


        # PDF View
        self.pdfWidget = PdfWidget()
        # self.pdfViewer.selectionChanged.connect(self.update_format)

        self.wordWidget = WordWidget()
        # self.wordWidget.selectionChanged.connect(self.update_format)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.pdfWidget)
        splitter.addWidget(self.wordWidget)
        splitter.setHandleWidth(3)       
        splitter.setCollapsible(0, True)  
        splitter.setCollapsible(1, True)  
        splitter.setSizes([600, 600]) 
        self.setCentralWidget(splitter)

        self.path = None

        # # Doc View
        # self.editor = CustomTextEdit()
        # # Setup the QTextEdit editor configuration
        # self.editor.selectionChanged.connect(self.update_format)
        
        # # self.path holds the path of the currently open file.
        # # If none, we haven't got a file open yet (or creating new).
        # self.path = None
        
        # self.main_layout.addWidget(self.editor)


        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Uncomment to disable native menubar on Mac
        # self.menuBar().setNativeMenuBar(False)

        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(14, 14))
        self.addToolBar(file_toolbar)
        file_menu = self.menuBar().addMenu("&File")

        open_file_source_action = QAction(
            QIcon(os.path.join("images", "open_file_source.jpg")),
            "Open source file...",
            self,
        )
        open_file_source_action.setStatusTip("Open source file")
        open_file_source_action.triggered.connect(self.file_open_source)
        file_menu.addAction(open_file_source_action)
        file_toolbar.addAction(open_file_source_action)


        open_file_action = QAction(
            QIcon(os.path.join("images", "blue-folder-open-document.png")),
            "Open file...",
            self,
        )
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        file_toolbar.addAction(open_file_action)

        save_file_action = QAction(
            QIcon(os.path.join("images", "disk.png")), "Save", self
        )
        save_file_action.setStatusTip("Save current page")
        save_file_action.triggered.connect(self.file_save)
        file_menu.addAction(save_file_action)
        file_toolbar.addAction(save_file_action)

        saveas_file_action = QAction(
            QIcon(os.path.join("images", "disk--pencil.png")),
            "Save As...",
            self,
        )
        saveas_file_action.setStatusTip("Save current page to specified file")
        saveas_file_action.triggered.connect(self.file_saveas)
        file_menu.addAction(saveas_file_action)
        file_toolbar.addAction(saveas_file_action)

        print_action = QAction(
            QIcon(os.path.join("images", "printer.png")),
            "Print...",
            self,
        )
        print_action.setStatusTip("Print current page")
        print_action.triggered.connect(self.file_print)
        file_menu.addAction(print_action)
        file_toolbar.addAction(print_action)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(edit_toolbar)
        edit_menu = self.menuBar().addMenu("&Edit")


        format_toolbar = QToolBar("Format")
        format_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(format_toolbar)
        format_menu = self.menuBar().addMenu("&Format")


        # Initialize.
        self.update_title()
        self.show()


    
    def restore_window_state(self):
        geometry = self.settings.value("MainWindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self.settings.setValue("MainWindow/geometry", self.saveGeometry())
        super().closeEvent(event)


    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.show()

    def file_open_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF or JPG file",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )

        if not path:
            return

        self.pdfWidget.setFile(path)

        self.statusBar().showMessage(f"PDF loaded: {path}")


    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open file",
            "",
            "HTML documents (*.html);Text documents (*.txt);All files (*.*)",
        )

        try:
            with open(path, "rU") as f:
                text = f.read()

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.path = path
            # Qt will automatically try and guess the format as txt/html
            self.editor.setText(text)
            self.update_title()
    

    def file_save(self):
        if self.path is None:
            # If we do not have a path, we need to use Save As.
            return self.file_saveas()

        text = (
            self.editor.toHtml()
            if utils.splitext(self.path) in constants.HTML_EXTENSIONS
            else self.editor.toPlainText()
        )

        try:
            with open(self. path, "w") as f:
                f.write(text)

        except Exception as e:
            self.dialog_critical(str(e))

    def file_saveas(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save file",
            "",
            "HTML documents (*.html);Text documents (*.txt);All files (*.*)",
        )

        if not path:
            # If dialog is cancelled, will return ''
            return

        text = (
            self.editor.toHtml()
            if utils.splitext(path) in constants.HTML_EXTENSIONS
            else self.editor.toPlainText()
        )

        try:
            with open(path, "w") as f:
                f.write(text)

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.path = path
            self.update_title()

    def file_print(self):
        dlg = QPrintDialog()
        if dlg.exec():
            self.editor.print_(dlg.printer())

    def update_title(self):
        self.setWindowTitle(
            "%s - DigiHand"
            % (os.path.basename(self.path) if self.path else "Untitled")
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DigiHand v0.1")

    window = MainWindow()
    app.exec()
