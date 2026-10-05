import os
import sys
import constants
import utils
import multiprocessing
import tempfile

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
    QWidgetAction,
    QSpinBox,
    QAbstractSpinBox,
)
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument

from pypdf import PdfReader, PdfWriter
from pathlib import Path

from customTextEdit import CustomTextEdit
from pdfWidget import PdfWidget
from wordWidget import WordWidget

from solverFlorence import SolverFlorence
from solverQwen2_5 import SolverQwen2_5
from solverQwen3_5 import SolverQwen3_5
from solverMoondream import SolverMoondream

from dlgSolver import DlgSolver

from digiHandEnums import InputType
from digiHandTools import DigiHandTools

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.openPath = None
        self.pdfPath = None
        self.initPage = 0

        self.settings = QSettings("clairc.com", "DigiHand")
        self.restore_window_state()
        self.openPath = self.settings.value("openPath", "")

        # PDF View
        self.pdfWidget = PdfWidget()
        # self.pdfViewer.selectionChanged.connect(self.update_format)

        self.wordWidget = WordWidget()
        # self.wordWidget.selectionChanged.connect(self.update_format)


        self.pdfWidget.pdfController.spCurPage.valueChanged.connect(self.wordWidget.curPage_changed)
        self.pdfWidget.pdfView.pageNavigator().currentPageChanged.connect(self.wordWidget.curPage_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.pdfWidget)
        splitter.addWidget(self.wordWidget)
        splitter.setHandleWidth(3)       
        splitter.setCollapsible(0, True)  
        splitter.setCollapsible(1, True)  
        splitter.setSizes([600, 600]) 
        self.setCentralWidget(splitter)



        pid = os.getpid()
        self.outputPath = Path(tempfile.gettempdir()) / "DigiHand" / f"pid_{os.getpid()}"
        self.outputPath.mkdir(parents=True, exist_ok=True)

        self.wordWidget.editor.dirtyChanged.connect(self.update_title)

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


        tool_toolbar = QToolBar("Tools")
        tool_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(tool_toolbar)
        tool_menu = self.menuBar().addMenu("&Tools")

        # split_action = QAction(QIcon(os.path.join("images", "digihand_solve.svg")), "Solve", self,)
        # split_action.setStatusTip("Split the PDF")
        # split_action.triggered.connect(self.split_pdf_into_pages)
        # tool_menu.addAction(split_action)
        # tool_toolbar.addAction(split_action)


        self.cbSolvers = QComboBox()
        self.cbSolvers.addItems(["Florence", "Moondream", "Qwen2.5", "Qwen3.5"])
        self.cbSolvers.setCurrentIndex(3)
        action_cbSolvers = QWidgetAction(self)
        action_cbSolvers.setDefaultWidget(self.cbSolvers)
        action_cbSolvers.setToolTip("Choose the AI library to solve")
        tool_toolbar.addAction(action_cbSolvers)
        # tool_menu.addAction(action_cbSolvers)


        self.spInitPage = QSpinBox(self)
        self.spInitPage.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spInitPage.setValue(1)
        action_spInitPage = QWidgetAction(self)
        action_spInitPage.setDefaultWidget(self.spInitPage)
        action_spInitPage.setToolTip("Select the Intitial page to Solve")
        tool_toolbar.addAction(action_spInitPage)

        self.spInitPage.valueChanged.connect(self.setInitPage)

        solve_action = QAction(QIcon(os.path.join("images", "digihand_solve.svg")), "Solve", self,)
        solve_action.setStatusTip("Convert to text")
        solve_action.triggered.connect(self.solve)
        tool_menu.addAction(solve_action)
        tool_toolbar.addAction(solve_action)

        # Initialize.
        self.update_title()
        self.show()


    
    def restore_window_state(self):
        geometry = self.settings.value("MainWindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self.settings.setValue("MainWindow/geometry", self.saveGeometry())
        self.settings.setValue("openPath", self.openPath)
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
            "Open a PDF file",
            self.openPath,
            "PDF Files (*.pdf);;All Files (*)",
        )

        if not path:
            return

        self.openPath = os.path.dirname(path)
        self.pdfPath = path
        self.pdfWidget.setFile(path)
        self.statusBar().showMessage(f"PDF loaded: {self.pdfPath}")
        # self.split_pdf_into_pages()

    def set_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, "Choose output folder for pages")
        if not output_folder:
            return

    def split_pdf_into_pages(self):    
        reader = PdfReader(self.pdfPath)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(reader.pages, 1):
            writer = PdfWriter()
            writer.add_page(page)
            out_path = output_folder / f"page_{i:03d}.pdf"
            with open(out_path, "wb") as f:
                writer.write(f)             # <- saves once per page, no dialog

        return len(reader.pages)

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
            % (os.path.basename(self.pdfPath) if self.pdfPath else "Untitled")
        )

    def setInitPage(self, inputPageNum):
        self.initPage = inputPageNum - 1

    
    def solve(self):
        # self.pdfPath = "D://WelSimLLC-github//DigiHand//data//imageJ2"
        self.outputPath = "D://WelSimLLC-github//DigiHand//output//journalReview//"
        idxSolver = self.cbSolvers.currentIndex() 
        dlg = DlgSolver()
        dlg.start_solver(model=idxSolver, input_type = InputType.PDF, input= self.pdfPath, output=self.outputPath, initPage = self.initPage)
        dlg.exec()
        # rst = dlg.getResult()
        # print(rst)
        self.wordWidget.setOutputPath(self.outputPath)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DigiHand v0.1")

    window = MainWindow()
    app.exec()
