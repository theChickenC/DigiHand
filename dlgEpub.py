"""Options dialog for ePub export: chapter rules, book metadata, front matter."""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout,
)

from txt2epub import DEFAULT_OPTIONS


class DlgEpub(QDialog):
    """Collects the options dict txt2epub.txt_dir_to_epub expects."""

    MODES = ("dates", "keyword", "both")

    def __init__(self, parent=None, options: dict | None = None,
                 cover_start: str = ""):
        super().__init__(parent)
        self.setWindowTitle("ePub options")
        self.setMinimumWidth(520)
        opts = {**DEFAULT_OPTIONS, **(options or {})}
        self.coverPath = str(opts.get("cover") or "")
        self.coverStart = cover_start   # folder the ePub is built from

        root = QVBoxLayout(self)

        # ---- chapters ------------------------------------------------------
        gb_ch = QGroupBox("Chapters", self)
        form = QFormLayout(gb_ch)
        self.cbMode = QComboBox()
        self.cbMode.addItems(["Dates  (journal: each date starts a chapter)",
                              "Keyword  (any line with the keyword starts a chapter)",
                              "Both  (keyword lines AND dates each start a chapter)"])
        try:
            self.cbMode.setCurrentIndex(self.MODES.index(str(opts.get("mode"))))
        except ValueError:
            self.cbMode.setCurrentIndex(0)
        form.addRow("Chapter rule:", self.cbMode)

        self.leKeyword = QLineEdit(str(opts.get("keyword") or "Ch:"))
        self.leKeyword.setPlaceholderText(
            "a line with this starts a chapter (default: Ch:)")
        form.addRow("Keyword:", self.leKeyword)

        self.leTemplate = QLineEdit(str(opts.get("title_template") or ""))
        self.leTemplate.setPlaceholderText("e.g. Chapter {n}: {heading}   (blank = the heading line)")
        form.addRow("Chapter name:", self.leTemplate)

        self.cbSplitDates = QCheckBox(
            "Split files that contain several dates (each date becomes its own chapter)")
        self.cbSplitDates.setChecked(bool(opts.get("split_dates")))
        form.addRow("", self.cbSplitDates)

        hint = QLabel("Dates count as a chapter break when they start their own line\n"
                      "(a leading word like 'Date 12/25/2024' is fine; dates inside a\n"
                      "sentence do not split). Keyword and name template work in both\n"
                      "keyword and both modes; {n} = chapter number, {heading} = name.")
        hint.setStyleSheet("color: gray;")
        form.addRow(hint)
        root.addWidget(gb_ch)

        # ---- book metadata --------------------------------------------------
        gb_meta = QGroupBox("Book metadata", self)
        fm2 = QFormLayout(gb_meta)
        self.leTitle = QLineEdit(str(opts.get("title") or ""))
        self.leTitle.setPlaceholderText("blank = output folder name")
        fm2.addRow("Title:", self.leTitle)
        self.leAuthor = QLineEdit(str(opts.get("author") or ""))
        fm2.addRow("Author:", self.leAuthor)
        self.teDesc = QPlainTextEdit(str(opts.get("description") or ""))
        self.teDesc.setPlaceholderText("short book description for the ePub metadata")
        fm2.addRow("Description:", self.teDesc)
        self.lePublisher = QLineEdit(str(opts.get("publisher") or ""))
        fm2.addRow("Publisher:", self.lePublisher)
        self.leLanguage = QLineEdit(str(opts.get("language") or "en"))
        fm2.addRow("Language:", self.leLanguage)
        self.leKeywords = QLineEdit(str(opts.get("keywords") or ""))
        self.leKeywords.setPlaceholderText("comma separated subjects")
        fm2.addRow("Subjects:", self.leKeywords)

        row = QHBoxLayout()
        self.leCover = QLineEdit(self.coverPath)
        self.leCover.setPlaceholderText("optional jpg/png cover image")
        self.leCover.setReadOnly(True)
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._pick_cover)
        row.addWidget(self.leCover)
        row.addWidget(btn)
        fm2.addRow("Cover:", row)
        root.addWidget(gb_meta)

        # ---- front matter ---------------------------------------------------
        gb_front = QGroupBox("Front matter (each field adds its own page)", self)
        fm3 = QFormLayout(gb_front)
        self.teForeword = QPlainTextEdit(str(opts.get("foreword") or ""))
        self.teForeword.setPlaceholderText("foreword text (optional)")
        fm3.addRow("Foreword:", self.teForeword)
        self.teCredits = QPlainTextEdit(str(opts.get("credits") or ""))
        self.teCredits.setPlaceholderText("credits / copyright text (optional)")
        fm3.addRow("Credits:", self.teCredits)
        fm3.addRow(QLabel("A title page (title, author, cover, year) is generated "
                          "automatically when a title or author is set."))
        root.addWidget(gb_front)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                               | QDialogButtonBox.StandardButton.Cancel)
        box.button(QDialogButtonBox.StandardButton.Ok).setText("Create ePub")
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        root.addWidget(box)

        self.cbMode.currentIndexChanged.connect(self._sync_mode)
        self._sync_mode()

    # ------------------------------------------------------------------ slots
    def _sync_mode(self):
        kw_mode = self.cbMode.currentIndex() in (1, 2)   # keyword / both
        for w in (self.leKeyword, self.leTemplate):
            w.setEnabled(kw_mode)

    def _pick_cover(self):
        # open where a cover was picked before, else beside the txt files
        start = ""
        if self.coverPath:
            start = str(Path(self.coverPath).parent)
        elif self.coverStart:
            start = self.coverStart
        path, _ = QFileDialog.getOpenFileName(
            self, "Cover image", start, "Images (*.png *.jpg *.jpeg)")
        if path:
            self.coverPath = path
            self.leCover.setText(path)

    # ------------------------------------------------------------------- api
    def get_options(self) -> dict:
        """The options dict for txt_dir_to_epub (mode + metadata + front matter)."""
        return {
            "mode": self.MODES[self.cbMode.currentIndex()],
            "split_dates": self.cbSplitDates.isChecked(),
            "keyword": self.leKeyword.text().strip().strip("'\"\u2018\u2019\u201c\u201d").strip(),
            "keyword_regex": False,   # GUI always matches plain text
            "title_template": self.leTemplate.text().strip(),
            "title": self.leTitle.text().strip(),
            "author": self.leAuthor.text().strip(),
            "description": self.teDesc.toPlainText().strip(),
            "publisher": self.lePublisher.text().strip(),
            "language": self.leLanguage.text().strip() or "en",
            "keywords": self.leKeywords.text().strip(),
            "cover": self.coverPath,
            "foreword": self.teForeword.toPlainText().strip(),
            "credits": self.teCredits.toPlainText().strip(),
        }
