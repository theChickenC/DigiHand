"""Convert generated journal txt files (page_N.txt) into an ePub book.

Chapter rules (options["mode"]):
- "dates":   a txt file whose opening lines contain a date starts a new
  chapter (title = that date); undated files continue the current chapter.
  With options["split_dates"], a SINGLE file holding several date headings
  is split so each date becomes its own chapter (dates must START a line).
- "keyword": any line containing options["keyword"] starts a new chapter,
  including mid-file. Title from options["title_template"] ({n} = chapter
  number, {heading} = the matched line); blank template = the heading line.
- "both": keyword lines AND line-leading dates (bare "12/25/2024" or with a
  leading word, "Date 12/25/2024") each start a chapter. Keyword defaults to
  "Ch:" when none is given. With a literal keyword, "Ch: Adventure" names the
  chapter "Adventure"; date chapters use the formatted date and merge across
  files on a matching leading date.

Front matter and metadata (all optional):
- title page (auto, embeds the cover image when one is given), foreword
  text, credits text, author/description/publisher/language/keywords.

Pure stdlib (zipfile) — no extra dependency; EPUB 2 (toc.ncx) + EPUB 3
(nav.xhtml) for maximum reader compatibility.

CLI:  py txt2epub.py <input_dir> [output.epub]        (journal defaults)
"""

import html
import re
import sys
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path

DEFAULT_OPTIONS = {
    # chapters
    "mode": "dates",          # "dates" | "keyword" | "both"
    "split_dates": False,     # one file, several date headings -> several chapters
    "keyword": "",            # chapter-start keyword for "keyword" mode
    "keyword_regex": False,   # treat keyword as a Python regex
    "title_template": "",     # "Chapter {n}: {heading}"; blank = the heading line
    # book metadata
    "title": "",
    "author": "",
    "description": "",
    "publisher": "",
    "language": "en",
    "keywords": "",           # comma separated epub subjects
    "cover": "",              # optional jpg/png cover image
    # generated front matter
    "foreword": "",
    "credits": "",
}

# ---------------------------------------------------------------- dates ----

_MONTH_NAMES = (
    "january|february|march|april|may|june|july|august|september|october|"
    "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_MONTH_MAP = {}
for _i, _m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1):
    _MONTH_MAP[_m] = _i
for _abbr, _num in [("jan", 1), ("feb", 2), ("mar", 3), ("apr", 4), ("may", 5),
                    ("jun", 6), ("jul", 7), ("aug", 8), ("sep", 9),
                    ("sept", 9), ("oct", 10), ("nov", 11), ("dec", 12)]:
    _MONTH_MAP[_abbr] = _num

_MD = r"(?P<d>3[01]|[12]\d|0?[1-9])(?:st|nd|rd|th)?"
_Y = r"(?P<y>\d{4}|\d{2})"

_DATE_PATTERNS = [
    # 12/5/24 or 12/05/2024
    re.compile(rf"(?P<m>1[0-2]|0?[1-9])/{_MD}/{_Y}"),
    # 2024-12-05
    re.compile(rf"(?P<y>\d{{4}})-(?P<m>0?[1-9]|1[0-2])-{_MD}"),
    # December 5(th), 2024  /  Dec 5 2024
    re.compile(rf"(?P<mn>{_MONTH_NAMES})\.?\s+{_MD},?\s+{_Y}", re.IGNORECASE),
    # 5 December 2024 / 5th of Dec, 2024
    re.compile(rf"{_MD}\s+(?:of\s+)?(?P<mn>{_MONTH_NAMES})\.?,?\s+{_Y}", re.IGNORECASE),
]


def _to_date(m: re.Match) -> date | None:
    y = int(m.group("y"))
    if y < 100:
        y += 2000
    mo = int(m.group("m")) if m.groupdict().get("m") else _MONTH_MAP[m.group("mn").lower()]
    try:
        return date(y, mo, int(m.group("d")))
    except ValueError:
        return None


def extract_date(text: str):
    """Return (date, matched_line) from the first few non-empty lines, else (None, None)."""
    for line in [ln for ln in text.splitlines() if ln.strip()][:3]:
        best = None
        for pat in _DATE_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            if best is None or m.start() < best.start():
                best = m
        if best:
            d = _to_date(best)
            if d:
                return d, line.strip()
    return None, None


_DATE_PREFIX_RE = re.compile(r"^dated?\b[\s:.\u2013-]+", re.IGNORECASE)


def _date_at_line_start(stripped_line: str):
    """Date when the (already stripped) line begins with a date, optionally
    written as 'Date 12/25/2024' / 'Date: March 3' etc. None otherwise."""
    core = _DATE_PREFIX_RE.sub("", stripped_line, count=1)
    best = None
    for pat in _DATE_PATTERNS:
        m = pat.match(core)
        if m and (best is None or m.start() < best.start()):
            best = m
    return _to_date(best) if best else None


def find_date_headings(text: str):
    """All (char_offset, date, line_text) for lines that BEGIN with a date
    (a leading 'Date'/'Dated' word on the line is allowed).

    Anchoring to the line start keeps dates written inside prose
    ("...until March 3, 2025 we waited...") from splitting chapters.
    """
    out, offset = [], 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            d = _date_at_line_start(stripped)
            if d:
                out.append((offset, d, stripped))
        offset += len(line)
    return out


# ------------------------------------------------------------- chapters ----

class Chapter:
    def __init__(self, title: str, epub_type: str = "chapter",
                 custom_html: str | None = None):
        self.title = title
        self.epub_type = epub_type
        self.custom_html = custom_html   # front matter: body is pre-built
        self.entries = []        # list of (filename, body, note)

    def add(self, filename, body, note):
        self.entries.append((filename, body, note))


def sort_key(path: Path):
    m = re.match(r"(.*?)(\d+)$", path.stem)
    if m:
        return (0, m.group(1).lower(), int(m.group(2)), path.name)
    return (1, path.stem.lower(), 0, path.name)


def _drop_heading(segment: str) -> str:
    """Drop a segment's first line: the keyword/date that started the chapter.
    It already became the chapter title, so repeating it in the body is noise."""
    idx = segment.find("\n")
    return segment[idx + 1:] if idx >= 0 else ""


def _drop_line(text: str, line_text: str) -> str:
    """Remove the first line equal to `line_text` (legacy mode: the date line
    that became the chapter title may sit a few lines into the file)."""
    target = line_text.strip()
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            return "\n".join(lines[:i] + lines[i + 1:]).strip()
    return text.strip()


def _merge_or_new(chapters, current, title, fname, body, note, log_rows):
    """Append to the current chapter when it already carries this title."""
    if current and current.title == title:
        current.add(fname, body, "continued (same title)")
    else:
        current = Chapter(title)
        chapters.append(current)
        current.add(fname, body, note)
    log_rows.append((fname, title, note))
    return current


def _title_from_template(template: str, n: int, heading: str) -> str:
    if template:
        try:
            return template.format(n=n, heading=heading)
        except (KeyError, IndexError, ValueError):
            return heading[:120] or template
    return heading[:120]


def _kw_heading(h_line: str, kw: str, n: int, literal: bool) -> str:
    """Chapter name from a keyword start line: with a literal keyword that
    prefixes the line ('Ch: Adventure'), the name is the rest ('Adventure')."""
    if literal and h_line.lower().startswith(kw.lower()):
        rest = h_line[len(kw):].strip(" \t:.\u2013\u2014-")
        return rest or f"Chapter {n}"
    return h_line


def build_chapters(folder: Path, options: dict | None = None):
    """Group txt files into chapters per options (mode, split, keyword)."""
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    mode = opts["mode"]

    keyword_ok = None
    # users (understandably) type keywords quoted, 'Ch:' -- strip any wrapping
    # quotes so the stored value still matches real lines
    kw = str(opts["keyword"]).strip().strip("'\"\u2018\u2019\u201c\u201d").strip()
    if mode in ("keyword", "both"):
        if not kw:
            if mode == "both":
                kw = "Ch:"   # default: 'Ch:' lines and dates each open a chapter
            else:
                raise ValueError("Keyword mode needs a chapter keyword.")
        if opts["keyword_regex"]:
            try:
                rx = re.compile(kw, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid chapter keyword regex: {exc}")
            keyword_ok = lambda line: rx.search(line)
        else:
            low = kw.lower()
            keyword_ok = lambda line: low in line.lower()

    files = sorted((f for f in folder.glob("*.txt")
                    if f.name.lower() != "epub_chapters.log"), key=sort_key)
    chapters, current, log_rows = [], None, []
    kw_counter = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            log_rows.append((f.name, None, f"UNREADABLE: {e}"))
            continue
        body_all = text.strip()

        # ---- keyword mode: any keyword line opens a chapter (also mid-file)
        if mode == "keyword":
            assert keyword_ok is not None   # set above for this mode
            heads = []           # (char offset of line start, heading line)
            offset = 0
            for line in text.splitlines(keepends=True):
                if keyword_ok(line):
                    heads.append((offset, line.strip()))
                offset += len(line)
            if not heads:
                if current is None:
                    current = Chapter("Foreword")
                    chapters.append(current)
                current.add(f.name, body_all, "continues current chapter")
                log_rows.append((f.name, current.title, "no keyword; continues chapter"))
                continue
            for h_idx, (h_off, h_line) in enumerate(heads):
                nxt = heads[h_idx + 1][0] if h_idx + 1 < len(heads) else len(text)
                if h_idx == 0:
                    seg_before = text[:h_off].strip()
                    if seg_before:
                        # text BEFORE the first keyword joins the previous chapter
                        if current is None:
                            current = Chapter("Foreword")
                            chapters.append(current)
                        current.add(f.name, seg_before, "continues previous chapter")
                        log_rows.append((f.name, current.title, "pre-keyword segment"))
                kw_counter += 1
                heading = _kw_heading(h_line, kw, kw_counter,
                                      not opts["keyword_regex"])
                title = _title_from_template(opts["title_template"], kw_counter, heading)
                current = Chapter(title)
                chapters.append(current)
                current.add(f.name, _drop_heading(text[h_off:nxt]).strip(),
                            f'chapter start (keyword "{opts["keyword"]}")')
                log_rows.append((f.name, title,
                                 f'chapter start (keyword "{opts["keyword"]}")'))
            continue

        # ---- both mode: keyword lines AND date headings each open a chapter.
        #      'Ch: Adventure' -> chapter "Adventure"; a line starting with a
        #      date (bare, or 'Date 12/25/2024') -> chapter "December 25, 2024"
        #      and merges with same-date continuations in other files.
        if mode == "both":
            assert keyword_ok is not None   # set above for this mode
            heads = []        # (offset, heading line, date or None)
            offset = 0
            for line in text.splitlines(keepends=True):
                stripped = line.strip()
                d = _date_at_line_start(stripped) if stripped else None
                if d is not None:
                    heads.append((offset, stripped, d))
                elif stripped and keyword_ok(line):
                    heads.append((offset, stripped, None))
                offset += len(line)
            if not heads:
                if current is None:
                    current = Chapter("Foreword")
                    chapters.append(current)
                current.add(f.name, body_all, "continues current chapter")
                log_rows.append((f.name, current.title,
                                 "no keyword/date heading; continues chapter"))
                continue
            for h_idx, (h_off, h_line, d) in enumerate(heads):
                nxt = heads[h_idx + 1][0] if h_idx + 1 < len(heads) else len(text)
                if h_idx == 0 and h_off > 0:
                    lead = text[:h_off].strip()
                    if lead:
                        if current is None:
                            current = Chapter("Foreword")
                            chapters.append(current)
                        current.add(f.name, lead, "continues previous chapter")
                        log_rows.append((f.name, current.title, "pre-heading segment"))
                kw_counter += 1
                seg = _drop_heading(text[h_off:nxt]).strip()
                if d is not None:
                    # plain date title (no template) so cross-file same-date
                    # chapters merge instead of duplicating
                    title = f"{d:%B} {d.day}, {d.year}"
                    current = _merge_or_new(chapters, current, title, f.name, seg,
                                            f'chapter start (date "{h_line}")', log_rows)
                else:
                    heading = _kw_heading(h_line, kw, kw_counter,
                                          not opts["keyword_regex"])
                    title = _title_from_template(opts["title_template"],
                                                 kw_counter, heading)
                    current = Chapter(title)
                    chapters.append(current)
                    current.add(f.name, seg, f'chapter start (keyword "{kw}")')
                    log_rows.append((f.name, title, f'chapter start (keyword "{kw}")'))
            continue

        # ---- dates mode with split_dates: one file may hold several chapters
        if opts["split_dates"]:
            heads = find_date_headings(text)
            if heads:
                if heads[0][0] > 0:
                    lead = text[:heads[0][0]].strip()
                    if lead:
                        if current is None:
                            current = Chapter("Foreword")
                            chapters.append(current)
                        current.add(f.name, lead, "text before first date heading")
                        log_rows.append((f.name, current.title,
                                         "text before first date heading"))
                for h_idx, (h_off, d, h_line) in enumerate(heads):
                    nxt = heads[h_idx + 1][0] if h_idx + 1 < len(heads) else len(text)
                    title = f"{d:%B} {d.day}, {d.year}"
                    current = _merge_or_new(
                        chapters, current, title, f.name,
                        _drop_heading(text[h_off:nxt]).strip(),
                        f'chapter start (date "{h_line}")', log_rows)
                continue
            # no date headings at all -> continuation, same as legacy mode
            if current is None:
                current = Chapter("Foreword")
                chapters.append(current)
            current.add(f.name, body_all, "continues current chapter")
            log_rows.append((f.name, current.title,
                             "no date; continues chapter" + ("" if body_all else " (empty file)")))
            continue

        # ---- legacy dates mode: one chapter decision per file
        d, matched = extract_date(text)
        if d:
            title = f"{d:%B} {d.day}, {d.year}"
            current = _merge_or_new(chapters, current, title, f.name,
                                    _drop_line(body_all, matched or ""),
                                    f'chapter start (date "{matched}")', log_rows)
        else:
            if current is None:
                current = Chapter("Foreword")
                chapters.append(current)
            current.add(f.name, body_all, "continues current chapter")
            log_rows.append((f.name, current.title,
                             "no date; continues chapter" + ("" if body_all else " (empty file)")))
    return chapters, files, log_rows


def _cover_href(cover_src: str) -> str | None:
    """Zip-internal name for the cover image, or None when unusable."""
    if cover_src and Path(cover_src).is_file():
        ext = str(cover_src).lower().rsplit(".", 1)[-1]
        if ext in ("jpg", "jpeg", "png"):
            return f"cover.{ext}"
    return None


def front_matter_chapters(opts: dict, book_title: str, want_titlepage: bool):
    """Title page (+cover), foreword and credits chapters, in spine order."""
    out = []
    author = (opts.get("author") or "").strip()
    cover_html = ""
    href = _cover_href(opts.get("cover", ""))
    if href:
        cover_html = f'<p><img src="{href}" alt="cover" /></p>\n'
    if want_titlepage:
        titlepage = cover_html
        if author:
            titlepage += f"<h2>{html.escape(author)}</h2>\n"
        titlepage += f"<p>{datetime.now():%Y}</p>\n"
        out.append(Chapter(book_title or "Untitled",
                           epub_type="titlepage", custom_html=titlepage))
    fore = (opts.get("foreword") or "").strip()
    if fore:
        out.append(Chapter("Foreword", epub_type="frontmatter",
                           custom_html=_text_to_xhtml(fore)))
    cred = (opts.get("credits") or "").strip()
    if cred:
        out.append(Chapter("Credits", epub_type="copyright-page",
                           custom_html=_text_to_xhtml(cred)))
    return out


# --------------------------------------------------------------- epub ------

_XHTML_TMPL = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{language}">
<head><title>{title}</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head>
<body><section epub:type="{etype}">
<h1>{title}</h1>
{body}
</section></body></html>
"""

_STYLE = """body { font-family: serif; margin: 1em; }
h1 { font-size: 1.4em; }
p { margin: 0.6em 0; }
hr.src { border: none; border-top: 1px dotted #999; margin: 1.2em 0; }
img { max-width: 90%; }
"""


def _text_to_xhtml(text: str) -> str:
    paras = []
    for para in re.split(r"\n\s*\n", text):
        lines = [html.escape(ln.strip()) for ln in para.splitlines() if ln.strip()]
        if lines:
            paras.append("<p>" + "<br/>".join(lines) + "</p>")
    return "\n".join(paras)


def _dc(tag: str, value) -> str:
    value = (str(value) or "").strip()
    if not value:
        return ""
    return f"  <dc:{tag}>{html.escape(value)}</dc:{tag}>\n"


def write_epub(chapters, epub_path: Path, meta: dict):
    """Build the .epub. `meta` is the merged options dict (title, author, ...)."""
    book_title = (meta.get("title") or "Untitled").strip()
    language = (meta.get("language") or "en").strip()
    book_id = "urn:uuid:" + str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype must be the first entry, uncompressed
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   zipfile.ZIP_STORED)

        z.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf"
 media-type="application/oebps-package+xml"/></rootfiles></container>""")

        # cover image
        manifest = []
        href = _cover_href(meta.get("cover", ""))
        if href:
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png"}[href.rsplit(".", 1)[1]]
            z.write(meta["cover"], f"OEBPS/{href}")
            manifest.append(
                f'<item id="coverimg" href="{href}" '
                f'media-type="{mime}" properties="cover-image"/>')

        spine, navpoints, navitems = [], [], []
        for i, ch in enumerate(chapters, 1):
            chref = f"chapter_{i:02d}.xhtml"
            fid = f"ch{i}"
            if ch.custom_html is not None:
                body = ch.custom_html
            else:
                # merged entries (same-date page continuations) flow as normal
                # paragraphs -- no <hr> or source comments breaking them up;
                # per-file provenance stays in epub_chapters.log
                body = "\n".join(_text_to_xhtml(bt) for _f, bt, _n in ch.entries)
            z.writestr(f"OEBPS/{chref}", _XHTML_TMPL.format(
                title=html.escape(ch.title), body=body, etype=ch.epub_type,
                language=html.escape(language)))
            manifest.append(f'<item id="{fid}" href="{chref}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="{fid}"/>')
            navpoints.append(
                f'<navPoint id="np{i}" playOrder="{i}">'
                f'<navLabel><text>{html.escape(ch.title)}</text></navLabel>'
                f'<content src="{chref}"/></navPoint>')
            navitems.append(f'<li><a href="{chref}">{html.escape(ch.title)}</a></li>')

        dc_extra = (_dc("creator", meta.get("author"))
                    + _dc("description", meta.get("description"))
                    + _dc("publisher", meta.get("publisher"))
                    + _dc("date", f"{datetime.now():%Y}")
                    + "".join(_dc("subject", k) for k in
                              re.split(r"[;,]", str(meta.get("keywords") or "")) if k.strip()))

        z.writestr("OEBPS/style.css", _STYLE)
        z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:identifier id="bookid">{book_id}</dc:identifier>
  <dc:title>{html.escape(book_title)}</dc:title>
  <dc:language>{html.escape(language)}</dc:language>
{dc_extra}  <meta property="dcterms:modified">{now}</meta>
</metadata>
<manifest>
{''.join(manifest)}
<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
</manifest>
<spine toc="ncx">
{''.join(spine)}
</spine></package>""")

        z.writestr("OEBPS/toc.ncx", f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/>
<meta name="dtb:depth" content="1"/>
<meta name="dtb:totalPageCount" content="0"/>
<meta name="dtb:maxPageNumber" content="0"/></head>
<docTitle><text>{html.escape(book_title)}</text></docTitle>
<navMap>{''.join(navpoints)}</navMap></ncx>""")

        z.writestr("OEBPS/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{html.escape(language)}">
<head><title>{html.escape(book_title)}</title></head>
<body><nav epub:type="toc"><ol>
{''.join(navitems)}
</ol></nav></body></html>""")


def write_log(log_path: Path, log_rows, chapters, epub_path: Path):
    lines = [
        f"ePub chapters log — generated {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"output: {epub_path}",
        f"chapters: {len(chapters)}  files: {len(log_rows)}",
        "-" * 60,
    ]
    for i, ch in enumerate(chapters, 1):
        tag = "  [front matter]" if ch.custom_html is not None else ""
        lines.append(f"Chapter {i}: {ch.title}  [chapter_{i:02d}.xhtml]{tag}")
        for fname, body, note in ch.entries:
            lines.append(f"    {fname:<16} {note}")
    lines.append("-" * 60)
    for fname, chapter_title, note in log_rows:
        lines.append(f"{fname:<16} -> {chapter_title or '(skipped)'}  ({note})")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def txt_dir_to_epub(folder: Path, epub_path: Path | None = None,
                    options: dict | None = None):
    """Convert every *.txt in folder to an ePub. Returns (epub_path, log_path)."""
    folder = Path(folder)
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    epub_path = Path(epub_path) if epub_path else folder / f"{folder.name}.epub"
    content_chapters, files, log_rows = build_chapters(folder, opts)
    if not files:
        raise FileNotFoundError(f"no txt files in {folder}")
    book_title = (opts.get("title") or "").strip() or folder.name
    opts["title"] = book_title
    # front matter is opt-in: the title page only appears when the user
    # explicitly set a title, author or cover (legacy CLI output unchanged)
    want_titlepage = bool(
        (options or {}).get("title") or (options or {}).get("author")
        or (options or {}).get("cover"))
    all_chapters = front_matter_chapters(opts, book_title, want_titlepage)
    # stray pre-heading text now lands in a "Foreword" chapter too; if the
    # user ALSO typed foreword text, fold the stray text into that chapter
    # instead of shipping two chapters named "Foreword"
    if content_chapters and content_chapters[0].title == "Foreword" \
            and content_chapters[0].custom_html is None:
        for ch in all_chapters:
            if ch.title == "Foreword" and ch.custom_html is not None:
                ch.custom_html += "\n" + "\n".join(
                    _text_to_xhtml(bt) for _f, bt, _n in content_chapters[0].entries)
                content_chapters.pop(0)
                break
    all_chapters += content_chapters
    write_epub(all_chapters, epub_path, opts)
    log_path = folder / "epub_chapters.log"
    write_log(log_path, log_rows, all_chapters, epub_path)
    return epub_path, log_path


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    epub, log = txt_dir_to_epub(src, dst)
    print(f"ePub: {epub}\nlog:  {log}")
