import os
import sys
import json
import constants
import utils
import multiprocessing
import tempfile

from PySide6.QtCore import (
    Qt, 
    QSize, 
    QSettings,
    QByteArray,
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
    QDialog,
    QFileDialog,
    QFontComboBox,
    QMainWindow,
    QMenu,
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
from dlgEpub import DlgEpub
from txt2epub import txt_dir_to_epub

from digiHandEnums import InputType
from digiHandTools import DigiHandTools
from projectIO import (
    make_state,
    save_project as write_project_file,
    load_project, ProjectFileError,
    PROJECT_EXTENSION, project_name,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.openPath = None
        self.pdfPath = None
        self.path = None      # current text file edited by wordWidget
        self.initPage = 0

        self.settings = QSettings("clairc.com", "DigiHand")
        self.restore_window_state()
        self.openPath = self.settings.value("openPath", "")
        # per-purpose last-used dialog folders ("stay where I was")
        self.projectDir = str(self.settings.value("projectDir", "") or "")
        self.epubFolder = str(self.settings.value("epubFolder", "") or "")

        # PDF View
        self.pdfWidget = PdfWidget()
        # self.pdfViewer.selectionChanged.connect(self.update_format)

        self.wordWidget = WordWidget()
        self.editor = self.wordWidget.editor
        # self.wordWidget.selectionChanged.connect(self.update_format)


        # the spin box is 1-based but the page_N.txt files are 0-based:
        # pass the converted number so typing a page number loads the right file
        self.pdfWidget.pdfController.spCurPage.valueChanged.connect(
            lambda page_1based: self.wordWidget.curPage_changed(page_1based - 1))
        self.pdfWidget.pdfView.pageNavigator().currentPageChanged.connect(self.wordWidget.curPage_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.pdfWidget)
        splitter.addWidget(self.wordWidget)
        splitter.setHandleWidth(3)       
        splitter.setCollapsible(0, True)  
        splitter.setCollapsible(1, True)  
        splitter.setSizes([600, 600]) 
        self.setCentralWidget(splitter)



        # Output folder for generated txt files: remembered between runs.
        # Until the user names one, fall back to a per-session temp folder.
        saved_out = self.settings.value("outputPath", "")
        self.outputPathUserSet = bool(saved_out)
        self.outputPath = Path(saved_out) if saved_out else Path(tempfile.gettempdir()) / "DigiHand" / f"pid_{os.getpid()}"
        self.outputPath.mkdir(parents=True, exist_ok=True)

        # Project session state
        self.projectPath = None      # path of the open .digihand.json, if any
        self.epubFiles = []          # epubs generated this session/project
        self.projectDirty = False    # unsaved project changes
        self.epubOptions = self._load_epub_options()  # remembered ePub settings

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

        # --- project session actions ------------------------------------
        file_menu.addSeparator()

        new_project_action = QAction("New Project", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_project_action.setStatusTip("Start a new DigiHand project session")
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction("Open Project...", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_project_action.setStatusTip(
            "Reload a saved project: PDF, output folder, model, pages, epubs")
        open_project_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_project_action)

        save_project_action = QAction("Save Project", self)
        save_project_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_project_action.setStatusTip("Save the project session")
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        save_project_as_action = QAction("Save Project As...", self)
        save_project_as_action.setStatusTip(
            "Save the project session to a new .digihand.json file")
        save_project_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_project_as_action)

        self.menuRecent = QMenu("Open Recent", self)
        self.menuRecent.aboutToShow.connect(self._rebuild_recent_menu)
        file_menu.addMenu(self.menuRecent)

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
        self.cbSolvers.currentIndexChanged.connect(lambda _i: self._mark_dirty())
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
        self.spInitPage.valueChanged.connect(lambda _v: self._mark_dirty())

        solve_action = QAction(QIcon(os.path.join("images", "digihand_solve.svg")), "Solve", self,)
        solve_action.setStatusTip("Convert to text")
        solve_action.triggered.connect(self.solve)
        tool_menu.addAction(solve_action)
        tool_toolbar.addAction(solve_action)

        epub_action = QAction(QIcon(os.path.join("images", "epub_book.svg")), "To ePub", self,)
        epub_action.setStatusTip("Convert all generated txt files to an ePub (dated files start a new chapter)")
        epub_action.triggered.connect(self.export_epub)
        tool_menu.addAction(epub_action)
        tool_toolbar.addAction(epub_action)

        out_folder_action = QAction("Output folder...", self)
        out_folder_action.setStatusTip("Name or choose the folder for the generated txt files")
        out_folder_action.triggered.connect(self.set_output_folder)
        tool_menu.addAction(out_folder_action)

        # Initialize.
        self.update_title()
        self.show()


    
    def restore_window_state(self):
        geometry = self.settings.value("MainWindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        # autosave the project session when there is one
        if self.projectPath and self.projectDirty:
            try:
                write_project_file(self.projectPath, self._project_state())
            except OSError:
                pass  # cannot show a dialog mid-close; changes stay unsaved
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
        self.settings.setValue("openPath", self.openPath)
        self.pdfPath = path
        self._mark_dirty()
        result = self.pdfWidget.setFile(path)
        if result is not None:
            self.statusBar().showMessage(f"Failed to load PDF: {result}")
        else:
            self.statusBar().showMessage(f"PDF loaded: {self.pdfPath}")
            # keep the start-page spinner inside the document's range
            self.spInitPage.setMaximum(max(1, self.pdfWidget.pdf_doc.pageCount()))
            # until the user names a folder, suggest one named after the PDF
            if not self.outputPathUserSet:
                self.outputPath = self.default_output_path()
                self.statusBar().showMessage(
                    f"PDF loaded: {self.pdfPath}   |   output: {self.outputPath}", 8000)
        # self.split_pdf_into_pages()

    def default_output_path(self) -> Path:
        # <folder of the PDF>/<pdf name>_text
        if self.pdfPath:
            src = Path(self.pdfPath)
            return src.parent / f"{src.stem}_text"
        return Path(tempfile.gettempdir()) / "DigiHand" / f"pid_{os.getpid()}"

    def choose_output_folder(self, title: str):
        """Directory picker that ALSO lets you type a new folder name.

        The native Windows picker cannot name a not-yet-existing directory,
        so the Qt dialog is used with a save-style line edit.
        """
        dlg = QFileDialog(self, title, str(self.outputPath))
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        # PySide6 >=6.11 renamed QFileDialog.Label to QFileDialog.DialogLabel;
        # touching the old name raises AttributeError and would silently kill
        # solve() in a windowed app, so probe both names defensively.
        label_enum = getattr(QFileDialog, "DialogLabel",
                             getattr(QFileDialog, "Label", None))
        if label_enum is not None:
            dlg.setLabelText(label_enum.Accept, "Choose")
        # QDialog.DialogCode is the canonical home of the enum; safe across
        # PySide6 versions (the QFileDialog re-export comes and goes).
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        picked = dlg.selectedFiles()
        return Path(picked[0]) if picked and picked[0] else None

    def set_output_path(self, path):
        self.outputPath = Path(path)
        self.outputPathUserSet = True
        self.outputPath.mkdir(parents=True, exist_ok=True)
        self.settings.setValue("outputPath", str(self.outputPath))
        self.statusBar().showMessage(f"Output folder: {self.outputPath}", 5000)
        self._mark_dirty()

    def set_output_folder(self):
        picked = self.choose_output_folder("Name or choose the output folder for the txt files")
        if picked:
            self.set_output_path(picked)

    def split_pdf_into_pages(self, output_folder=None):
        if not self.pdfPath:
            return 0
        reader = PdfReader(self.pdfPath)
        output_folder = Path(output_folder or self.outputPath)
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
            self.openPath,
            "HTML documents (*.html);Text documents (*.txt);All files (*.*)",
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
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
            with open(self.path, "w", encoding="utf-8") as f:
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
            with open(path, "w", encoding="utf-8") as f:
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
        parts = []
        if self.projectPath:
            parts.append(project_name(self.projectPath) + (" *" if self.projectDirty else ""))
        parts.append(os.path.basename(self.pdfPath) if self.pdfPath else "Untitled")
        self.setWindowTitle(" - ".join(parts + ["DigiHand"]))

    def setInitPage(self, inputPageNum):
        self.initPage = inputPageNum - 1

    # ---- project sessions (.digihand.json) ------------------------------

    def _mark_dirty(self):
        self.projectDirty = True
        self.update_title()

    def _project_state(self):
        geom = bytes(self.saveGeometry().toHex().data()).decode("ascii")
        try:
            cur_page = int(self.pdfWidget.pdfController.spCurPage.value())
        except Exception:
            cur_page = 1
        return make_state(
            pdf=self.pdfPath,
            output=self.outputPath,
            solver_idx=self.cbSolvers.currentIndex(),
            init_page=self.spInitPage.value(),
            current_page=cur_page,
            epubs=self.epubFiles,
            geometry_hex=geom,
            project_dir=Path(self.projectPath).parent,
            epub_options=self.epubOptions,
        )

    def _remember_dir(self, key: str, path) -> str:
        """Persist the folder a dialog last used, so it reopens 'where I was'."""
        d = str(Path(path))
        self.settings.setValue(key, d)
        if key == "projectDir":
            self.projectDir = d
        elif key == "epubFolder":
            self.epubFolder = d
        return d

    def _existing_dir(self, *cands) -> str:
        """First candidate that is an actual directory (dialog start folder)."""
        for c in cands:
            if c and Path(str(c)).is_dir():
                return str(c)
        return ""

    def save_project(self):
        if not self.projectPath:
            return self.save_project_as()
        try:
            write_project_file(self.projectPath, self._project_state())
        except OSError as exc:
            self.dialog_critical(f"Could not save project: {exc}")
            return
        self.projectDirty = False
        self._remember_recent(self.projectPath)
        self._remember_dir("projectDir", self.projectPath.parent)
        self.statusBar().showMessage(f"Project saved: {self.projectPath}", 5000)
        self.update_title()

    def save_project_as(self):
        suggested = str(self.projectPath) if self.projectPath else ""
        if not suggested and self.pdfPath:
            suggested = str(Path(self.pdfPath).with_suffix(PROJECT_EXTENSION))
        if not suggested and self.projectDir:
            suggested = str(Path(self.projectDir) / ("project" + PROJECT_EXTENSION))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project as", suggested,
            f"DigiHand project (*{PROJECT_EXTENSION})")
        if not path:
            return
        if not path.endswith(PROJECT_EXTENSION):
            path += PROJECT_EXTENSION
        self.projectPath = Path(path)
        self.save_project()

    def new_project(self):
        self.projectPath = None
        self.epubFiles = []
        self.pdfPath = None
        self.initPage = 0
        self.spInitPage.blockSignals(True)
        self.spInitPage.setValue(1)
        self.spInitPage.blockSignals(False)
        self.wordWidget.setOutputPath(None)
        self.projectDirty = False
        self.update_title()
        self.statusBar().showMessage("New project. Open a source PDF to begin.", 5000)

    def open_project_dialog(self):
        # reopen where the last project was saved/opened, not at home
        start = self._existing_dir(
            self.projectPath.parent if self.projectPath else "",
            self.projectDir,
            self.openPath)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open DigiHand project", start,
            f"DigiHand project (*{PROJECT_EXTENSION});;All Files (*)")
        if path:
            self.open_project(Path(path))

    def open_project(self, path):
        try:
            state = load_project(path)
        except ProjectFileError as exc:
            self.dialog_critical(str(exc))
            return

        self.projectPath = Path(path)
        self._remember_dir("projectDir", self.projectPath.parent)
        self.epubFiles = list(state.get("epubs", []))
        if state.get("epub_options"):
            self.epubOptions = state["epub_options"]

        geom = state.get("geometry")
        if geom:
            try:
                self.restoreGeometry(QByteArray.fromHex(geom.encode("ascii")))
            except Exception:
                pass  # stale/odd geometry: keep the current window

        idx = int(state.get("solver", self.cbSolvers.currentIndex()))
        if 0 <= idx < self.cbSolvers.count():
            self.cbSolvers.setCurrentIndex(idx)

        out = state.get("output")
        if out:
            self.outputPath = Path(out)
            self.outputPathUserSet = True
            self.outputPath.mkdir(parents=True, exist_ok=True)
            self.wordWidget.setOutputPath(str(self.outputPath))

        pdf = state.get("pdf")
        if pdf and Path(pdf).is_file():
            self.openPath = str(Path(pdf).parent)
            self.pdfPath = pdf
            result = self.pdfWidget.setFile(pdf)
            if result is not None:
                self.statusBar().showMessage(f"Failed to load PDF: {result}")
            else:
                self.spInitPage.setMaximum(max(1, self.pdfWidget.pdf_doc.pageCount()))

        init_page = max(1, int(state.get("init_page", 1)))
        self.spInitPage.blockSignals(True)
        self.spInitPage.setValue(init_page)
        self.spInitPage.blockSignals(False)
        self.initPage = init_page - 1

        if self.pdfPath:
            # spin box is 1-based; its valueChanged loads the page in the
            # text editor because outputPath was set above
            cur = min(max(1, int(state.get("current_page", 1))),
                      self.pdfWidget.pdf_doc.pageCount())
            self.pdfWidget.pdfController.spCurPage.setValue(cur)

        self.projectDirty = False
        self._remember_recent(self.projectPath)
        self.update_title()
        missing = [e for e in self.epubFiles if e and not Path(e).is_file()]
        msg = f"Project loaded: {project_name(self.projectPath)}"
        if missing:
            msg += f"   ({len(missing)} epub(s) missing on disk)"
        self.statusBar().showMessage(msg, 8000)

    def _remember_recent(self, path):
        current = str(Path(path).resolve())
        recent = [current]
        stored = self.settings.value("recentProjects", []) or []
        if isinstance(stored, str):
            stored = [stored]
        for p in stored:
            if p and str(Path(p).resolve()) not in [str(Path(r).resolve()) for r in recent]:
                recent.append(str(p))
        self.settings.setValue("recentProjects", recent[:8])

    def _rebuild_recent_menu(self):
        self.menuRecent.clear()
        stored = self.settings.value("recentProjects", []) or []
        if isinstance(stored, str):
            stored = [stored]
        added = False
        for p in stored:
            if not p or not Path(p).is_file():
                continue
            act = QAction(p, self)
            act.triggered.connect(lambda _=False, path=p: self.open_project(Path(path)))
            self.menuRecent.addAction(act)
            added = True
        if not added:
            empty = QAction("(no recent projects)", self)
            empty.setEnabled(False)
            self.menuRecent.addAction(empty)

    
    def _load_epub_options(self) -> dict:
        """ePub options remembered from previous exports (QSettings JSON blob)."""
        raw = self.settings.value("epubOptions", "")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                pass
        return {}

    def export_epub(self):
        # reopen where the last ePub was exported from; else the current
        # session's solve output if it has txt files
        start = self._existing_dir(
            self.epubFolder,
            str(self.outputPath) if (self.outputPath
                                     and any(Path(self.outputPath).glob("*.txt"))) else "",
            self.openPath)
        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder of generated txt files to convert", start)
        if not folder:
            return
        self._remember_dir("epubFolder", folder)
        defaults = dict(self.epubOptions)
        if not defaults.get("title"):
            defaults["title"] = Path(folder).name
        dlg = DlgEpub(self, defaults, cover_start=folder)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        opts = dlg.get_options()
        try:
            epub, log = txt_dir_to_epub(Path(folder), options=opts)
        except Exception as e:
            self.dialog_critical(f"ePub conversion failed: {e}")
            return
        self.epubOptions = opts
        self.settings.setValue("epubOptions", json.dumps(opts, ensure_ascii=False))
        self.epubFiles.append(str(epub))
        self._mark_dirty()
        self.statusBar().showMessage(f"ePub written: {epub}   (chapter log: {log})", 10000)

    def solve(self):
        if not self.pdfPath:
            self.dialog_critical("Open a source PDF first.")
            return
        # let the user name/choose where the page txt files go;
        # cancelling keeps the current (suggested) output folder
        picked = self.choose_output_folder(
            f"Output folder for '{os.path.basename(self.pdfPath)}'")
        if picked:
            self.set_output_path(picked)
        idxSolver = self.cbSolvers.currentIndex()
        dlg = DlgSolver()
        dlg.start_solver(model=idxSolver, input_type = InputType.PDF, input= self.pdfPath, output=str(self.outputPath), initPage = self.initPage)
        dlg.exec()
        # rst = dlg.getResult()
        # print(rst)
        self.wordWidget.setOutputPath(str(self.outputPath))
        # a completed solve is a project milestone: record it, but only for
        # an already-open project -- no .digihand.json is created unless the
        # user chose File > Save Project (user preference: keep explicit saves)
        self._mark_dirty()
        if self.projectPath:
            self.save_project()


if __name__ == "__main__":
    # Required in the PyInstaller build (packDigiHand.bat): without this,
    # every spawned solver worker re-runs this module and opens another window.
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("DigiHand v0.1")

    window = MainWindow()
    app.exec()
