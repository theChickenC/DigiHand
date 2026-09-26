import sys
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QProgressBar, QPushButton, QLabel
)
from PySide6.QtCore import QProcess, Qt, Signal


class DlgSolver(QDialog):
    # Signal to receive progress value from subprocess (0~100)
    progressUpdate = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solver Process")
        self.resize(700, 450)

        # Subprocess handler
        self.process: QProcess | None = None

        # Build UI
        self.setup_ui()

        # Connect progress signal
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
        self.btnKill = QPushButton("Kill Solver Process")
        self.btnKill.clicked.connect(self.on_kill_process)
        layout_buttons.addWidget(self.btnKill)

        # Button2: Close dialog
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.reject)
        layout_buttons.addWidget(self.btnClose)

        layout_main.addLayout(layout_buttons)

    def start_solver(self, program: str, args: list[str]):
        """Launch solver as external subprocess"""
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            self.log_message("Solver is already running!", is_error=True)
            return

        self.txtOutput.clear()
        self.progressBar.setValue(0)

        self.process = QProcess(self)
        # Connect process signals
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self.on_process_finished)

        self.log_message(f"Starting solver: {program} {' '.join(args)}")
        self.process.start(program, args)

    def read_stdout(self):
        """Read stdout from solver process"""
        raw = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.log_message(raw)
        # Optional: parse progress percentage from stdout
        self.parse_progress(raw)

    def read_stderr(self):
        """Read stderr from solver process"""
        raw = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        self.log_message(raw, is_error=True)
        self.parse_progress(raw)

    def parse_progress(self, text: str):
        """
        If your solver prints lines like: PROGRESS:42
        this extracts number and updates progress bar
        """
        for line in text.splitlines():
            if line.startswith("PROGRESS:"):
                try:
                    val = int(line.split(":", 1)[1])
                    self.progressUpdate.emit(val)
                except ValueError:
                    pass

    def log_message(self, msg: str, is_error: bool = False):
        """Append text to output window"""
        if is_error:
            self.txtOutput.setTextColor(Qt.red)
        else:
            self.txtOutput.setTextColor(Qt.black)
        self.txtOutput.append(msg)
        # Auto scroll to bottom
        self.txtOutput.verticalScrollBar().setValue(self.txtOutput.verticalScrollBar().maximum())

    def on_progress_update(self, value: int):
        """Update progress bar"""
        clamped = max(0, min(100, value))
        self.progressBar.setValue(clamped)

    def on_kill_process(self):
        """Button1: terminate subprocess"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.log_message("Killing solver process...", is_error=True)
            self.process.kill()
        else:
            self.log_message("No running solver process.")

    def on_process_finished(self, exit_code, exit_status):
        """Subprocess finished"""
        if exit_status == QProcess.NormalExit:
            self.log_message(f"Solver finished normally. Exit code: {exit_code}")
        else:
            self.log_message(f"Solver terminated. Exit code: {exit_code}", is_error=True)
        self.process = None

    def reject(self):
        """Override close: if process still running, warn user"""
        if self.process and self.process.state() != QProcess.NotRunning:
            self.log_message("Warning: solver still running! Close will leave it running.", is_error=True)
        super().reject()

