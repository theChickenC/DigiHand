"""Find & Replace across all txt files in the output folder (or current file).

Scan/replace logic lives in module-level pure functions so it can be unit
tested without a QApplication; the dialog just drives them.
"""

import os
import re
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

# ---------------------------------------------------------------- scan/replace

def read_text(path):
    """Decode a text file BOM-safely; returns (text, encoding)."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16"
    if b"\x00" in raw[:4096]:
        raise ValueError(f"{Path(path).name} is not a text file.")
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "cp1252"


def compile_pattern(find: str, case: bool, whole_word: bool, regex: bool):
    pattern = find if regex else re.escape(find)
    if whole_word:
        pattern = rf"\b(?:{pattern})\b"
    return re.compile(pattern, 0 if case else re.IGNORECASE)


def scan_file(path, rx):
    """Return (total_hits, [(lineno, snippet), ...]) for one file."""
    text, _enc = read_text(path)
    total = 0
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        n = len(rx.findall(line))
        if not n:
            continue
        total += n
        if len(hits) < 50:      # display cap per file; count stays exact
            snippet = line.strip()
            if len(snippet) > 90:
                snippet = snippet[:90] + "…"
            hits.append((lineno, snippet))
    return total, hits


def count_hits(text, rx):
    return len(rx.findall(text))


def replace_in_text(text, rx, repl):
    r"""Safe repl: a literal & or \g in the replacement cannot explode."""
    try:
        return rx.subn(repl, text)
    except re.error:
        return rx.subn(repl.replace("\\", "\\\\"), text)


def iter_txt_files(folder):
    return sorted(p for p in Path(folder).glob("*.txt"))


# ---------------------------------------------------------------- the dialog

class DlgFindReplace(QDialog):
    """Ctrl+F dialog: search & replace in the output folder or current file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = parent
        self.setWindowTitle("Find & Replace")
        self.setMinimumWidth(640)
        self.last_scan = []          # [(path, hit_count, [(lineno, snip)...])]

        root = QVBoxLayout(self)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Scope:"))
        self.cbScope = QComboBox()
        self.cbScope.addItems(["All .txt files in output folder",
                               "Current file only"])
        row1.addWidget(self.cbScope, 1)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Find:"))
        self.leFind = QLineEdit()
        self.leFind.setPlaceholderText("text to find")
        row2.addWidget(self.leFind, 1)
        root.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Replace:"))
        self.leRepl = QLineEdit()
        self.leRepl.setPlaceholderText("replacement (leave blank to delete)")
        row3.addWidget(self.leRepl, 1)
        root.addLayout(row3)

        row4 = QHBoxLayout()
        self.cbCase = QCheckBox("Match case")
        self.cbWord = QCheckBox("Whole words")
        self.cbRegex = QCheckBox("Regular expression")
        for cb in (self.cbCase, self.cbWord, self.cbRegex):
            row4.addWidget(cb)
        row4.addStretch(1)
        self.btnFind = QPushButton("Find")
        self.btnReplace = QPushButton("Replace All")
        self.btnReplace.setEnabled(False)
        row4.addWidget(self.btnFind)
        row4.addWidget(self.btnReplace)
        root.addLayout(row4)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Match", "Line"])
        self.tree.setColumnWidth(0, 420)
        self.tree.itemDoubleClicked.connect(self._jump_to)
        root.addWidget(self.tree, 1)

        self.lblStatus = QLabel("Enter a search and press Find.")
        root.addWidget(self.lblStatus)

        self.btnFind.clicked.connect(self.do_find)
        self.btnReplace.clicked.connect(self.do_replace_all)
        self.leFind.returnPressed.connect(self.do_find)

    # ------------------------------------------------------------ helpers

    def _current_file(self):
        wc = getattr(self.main.wordWidget, "wordController", None)
        return wc.curFile if wc else None

    def _folder(self):
        return self.main.wordWidget.outputPath

    def _targets(self):
        if self.cbScope.currentIndex() == 1:
            cur = self._current_file()
            return [cur] if cur else []
        folder = self._folder()
        if not folder or not Path(folder).is_dir():
            return []
        return list(iter_txt_files(folder))

    def _pattern(self):
        try:
            return compile_pattern(self.leFind.text(),
                                   self.cbCase.isChecked(),
                                   self.cbWord.isChecked(),
                                   self.cbRegex.isChecked())
        except re.error as e:
            QMessageBox.warning(self, "Bad regex", str(e))
            return None

    # ------------------------------------------------------------ actions

    def do_find(self):
        if not self.leFind.text():
            return
        rx = self._pattern()
        if rx is None:
            return
        targets = self._targets()
        if not targets:
            self.lblStatus.setText("Nothing to search — no files / no file open.")
            return

        self.tree.clear()
        self.last_scan = []
        total_files = total_hits = 0
        for path in targets:
            try:
                n, hits = scan_file(path, rx)
            except (OSError, ValueError):
                continue
            if not n:
                continue
            total_files += 1
            total_hits += n
            top = QTreeWidgetItem(self.tree,
                                  [Path(path).name, f"{n} match(es)"])
            top.setData(0, Qt.ItemDataRole.UserRole, str(path))
            for lineno, snippet in hits[:25]:
                child = QTreeWidgetItem(top, [snippet, str(lineno)])
                child.setData(0, Qt.ItemDataRole.UserRole, str(path))
                child.setData(1, Qt.ItemDataRole.UserRole, lineno)
            self.last_scan.append((path, n, hits))
            top.setExpanded(total_files == 1)

        self.btnReplace.setEnabled(total_hits > 0)
        if total_hits == 0:
            self.lblStatus.setText(
                f"No matches in {len(targets)} file(s).")
        else:
            self.lblStatus.setText(
                f"{total_hits} match(es) in {total_files} "
                f"file(s) — double-click a match to open it.")

    def do_replace_all(self):
        rx = self._pattern()
        if rx is None or not self.last_scan:
            return
        total = sum(n for _, n, _ in self.last_scan)
        files = len(self.last_scan)
        answer = QMessageBox.question(
            self, "Replace all?",
            f"Replace {total} match(es) in {files} file(s) on disk?\n"
            "A .bak copy of each changed file is kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return

        # save the open buffer first so we never replace under unsaved edits
        wc = getattr(self.main.wordWidget, "wordController", None)
        cur = self._current_file()
        if wc and cur and (wc.wordView.document().isModified()
                           or wc.wordView.isDirty()):
            wc.saveChanges(cur)

        touched = 0
        changed_total = 0
        for path in {p for p, _, _ in self.last_scan}:
            try:
                text, enc = read_text(path)
            except (OSError, ValueError):
                continue
            new_text, n = replace_in_text(text, rx, self.leRepl.text())
            if n == 0:
                continue
            Path(str(path) + ".bak").write_bytes(Path(path).read_bytes())
            with open(path, "w", encoding=enc) as f:
                f.write(new_text)
            touched += 1
            changed_total += n

        # reload the open file if we just rewrote it underneath the editor
        if wc and cur and any(str(p) == str(cur) for p, _, _ in self.last_scan):
            try:
                text, _ = read_text(cur)
                wc.wordView.clear()
                wc.wordView.setText(text)
                wc.wordView.resetDirty()
                wc.wordView.document().setModified(False)
            except (OSError, ValueError):
                pass

        self.lblStatus.setText(
            f"Replaced {changed_total} match(es) in {touched} file(s) "
            "(.bak saved).")
        self.btnReplace.setEnabled(False)
        self.do_find()   # reshow what is left (usually zero)

    def _jump_to(self, item, _col):
        """Double-click: open the containing file (page_N.txt jumps pages)."""
        if self.main is None:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:   # a parent row
            path = item.child(0).data(0, Qt.ItemDataRole.UserRole) \
                if item.childCount() else None
        if not path:
            return
        m = re.fullmatch(r"page_(\d+)\.txt", Path(path).name)
        if m:
            nav = self.main.pdfWidget.pdfView.pageNavigator()
            nav.jump(int(m.group(1)), QPointF(0, 0))
        else:
            try:
                text, _ = read_text(path)
            except (OSError, ValueError) as e:
                QMessageBox.warning(self, "Cannot open", str(e))
                return
            self.main.path = path
            self.main.editor.setText(text)
            self.main.update_title()
