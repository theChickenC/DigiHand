import sys
import time
import queue
import multiprocessing
from digiHandEnums import InputType
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QProgressBar, QPushButton, QLabel
)
from PySide6.QtCore import QProcess, Qt, Signal, QTimer
from solverFlorence import SolverFlorence
from solverQwen import SolverQwen
from solverMoondream import SolverMoondream


SOLVER_CLASSES = [SolverFlorence, SolverMoondream, SolverQwen]

def _make_solver(idx):
    try:
        cls = SOLVER_CLASSES[idx]
    except IndexError:
        raise ValueError(f"Unknown solver index: {idx}")
    return cls()

def solver_worker(work_queue, model_idx, input_type, input_dir, output_dir):
    def log(msg, is_error=False):
        work_queue.put({"type": "log", "msg": msg, "is_error": is_error})
    def progress(value):
        work_queue.put({"type": "progress", "value": value})

    log(f"Worker started (pid={multiprocessing.current_process().pid})")
    try:
        solver = _make_solver(model_idx)          # <-- pick by index
        log(f"Model: {solver.model_name}")

        progress(10)
        log("Running solver...") 

        result = solver.run(
            input_type, input_dir, output_dir,
            on_file_saved=lambda msg: log(msg),
            on_progress=lambda pct, msg: progress(pct),
        )

        progress(100)
        log("Solver finished successfully")
        if result:
            log(f"Output: {result}")
    except Exception as exc:
        log(f"Solver crashed: {exc!r}", is_error=True)

class DlgSolver(QDialog):
    # Signal to receive progress value from subprocess (0~100)
    progressUpdate = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solver Process")
        self.resize(700, 450)

        # Multiprocessing state — MUST be created here.
        self.work_queue = multiprocessing.Queue()
        self.solver_proc: multiprocessing.Process | None = None
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.poll_queue)

        self.setup_ui()
        self.progressUpdate.connect(self.on_progress_update)

    def setup_ui(self):
        layout_main = QVBoxLayout(self)

        # Output log window
        layout_main.addWidget(QLabel("Solver Output / Log:"))
        self.txtOutput = QTextEdit()
        self.txtOutput.setReadOnly(True)
        layout_main.addWidget(self.txtOutput)

        # Progress bar
        layout_main.addWidget(QLabel("Progress:"))
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        layout_main.addWidget(self.progressBar)

        # Bottom button row
        layout_buttons = QHBoxLayout()

        # Button1: Kill process
        self.btnKill = QPushButton("Stop")
        self.btnKill.clicked.connect(self.on_kill_process)
        layout_buttons.addWidget(self.btnKill)

        # Button2: Close dialog
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.reject)
        layout_buttons.addWidget(self.btnClose)

        layout_main.addLayout(layout_buttons)

    def start_solver(self, model: int, input_type: InputType , input: str, output:str):
        if self.solver_proc is not None and self.solver_proc.is_alive():
            self.log_message("Solver is already running!", is_error=True)
            return
        
        self.txtOutput.clear()
        self.progressBar.setValue(0)
        self._drain_queue()
        
        self.solver_proc = multiprocessing.Process(
            target=solver_worker,
            args=(self.work_queue, model, input_type, input, output),
            daemon=True,
        )
        if input_type == InputType.PDF:
            self.log_message(f"Input PDF File: {input}")
        elif input_type == InputType.IMAGES:
            self.log_message(f"Input Images Folder: {input}")
        self.log_message(f"Output Folder: {output}")                      
        self.log_message("Starting solver process...")
        self.solver_proc.start()
        self.log_message(f"Solver started (pid={self.solver_proc.pid})")
        self.timer.start()

    def _drain_queue(self):
        """Drop any stale messages left over from a previous run."""
        while True:
            try:
                self.work_queue.get_nowait()
            except (queue.Empty, EOFError, OSError):
                break

    def poll_queue(self):
        while True:
            try:
                item = self.work_queue.get_nowait()
            except (queue.Empty, EOFError, OSError):
                break
            kind = item.get("type")
            if kind == "log":
                self.log_message(item["msg"], item.get("is_error", False))
            elif kind == "progress":
                self.progressUpdate.emit(int(item["value"]))
        proc = self.solver_proc
        if proc is not None and not proc.is_alive():
            self.timer.stop()
            if proc.exitcode == 0:
                self.log_message("Solver finished normally.")
            else:
                self.log_message(f"Solver process terminated (exitcode={proc.exitcode}).",
                                 is_error=True)
            self.solver_proc = None

    def log_message(self, msg, is_error=False):
        self.txtOutput.setTextColor(Qt.red if is_error else Qt.black)
        self.txtOutput.append(msg)
        self.txtOutput.verticalScrollBar().setValue(
            self.txtOutput.verticalScrollBar().maximum())

    def on_progress_update(self, value):
        self.progressBar.setValue(max(0, min(100, value)))

    def on_kill_process(self):
        if self.solver_proc is not None and self.solver_proc.is_alive():
            self.log_message("Killing solver process...", is_error=True)
            self.solver_proc.terminate()
        else:
            self.log_message("No running solver process.")

    def reject(self):
        if self.solver_proc is not None and self.solver_proc.is_alive():
            self.log_message("Warning: solver still running! Closing now will terminate it.",
                             is_error=True)
            self.solver_proc.terminate()
        super().reject()

