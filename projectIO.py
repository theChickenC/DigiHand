"""DigiHand project persistence: one small JSON file per project.

A project remembers everything needed to resume a session:
source PDF, output folder, chosen solver, start/current page,
generated epub files, and the window geometry.
Paths are stored relative to the project file when possible,
so moving a project folder keeps it working.
"""
import json
from datetime import datetime
from pathlib import Path

PROJECT_EXTENSION = ".digihand.json"
FORMAT_VERSION = 2       # v2 adds epub_options; v1 files still load


class ProjectFileError(Exception):
    pass


def make_state(pdf, output, solver_idx, init_page, current_page,
               epubs, geometry_hex, project_dir, epub_options=None) -> dict:
    """Build the JSON-serializable state dict.

    Paths inside project_dir are stored relative to it; anything else
    (different drive, outside folder) stays absolute.
    """
    base = Path(project_dir).resolve()

    def rel(p):
        if not p:
            return None
        full = Path(p).resolve()
        try:
            return full.relative_to(base).as_posix()
        except ValueError:
            return str(full)

    eo = dict(epub_options or {})
    if eo.get("cover"):
        eo["cover"] = rel(eo["cover"]) or eo["cover"]

    return {
        "digihand_project": FORMAT_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "pdf": rel(pdf),
        "output": rel(output),
        "solver": int(solver_idx),
        "init_page": int(init_page),       # 1-based, as shown in the UI
        "current_page": int(current_page), # 1-based
        "epubs": [rel(e) for e in (epubs or [])],
        "epub_options": eo,
        "geometry": geometry_hex,          # base64 QByteArray from saveGeometry()
    }


def save_project(path, state: dict):
    Path(path).write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_project(path) -> dict:
    """Read and validate a project file; returns the state dict with
    all paths absolutized."""
    path = Path(path)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProjectFileError(f"Project file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ProjectFileError(f"Project file is corrupt: {exc}")

    ver = state.get("digihand_project") if isinstance(state, dict) else None
    if not isinstance(state, dict) or not (1 <= int(ver or 0) <= FORMAT_VERSION):
        raise ProjectFileError(
            "Not a DigiHand project file (or saved by a newer version).")

    base = path.parent

    def absolute(p):
        if not p:
            return None
        q = Path(p)
        return str((base / q).resolve()) if not q.is_absolute() else str(q)

    state["pdf"] = absolute(state.get("pdf"))
    state["output"] = absolute(state.get("output"))
    state["epubs"] = [absolute(e) for e in state.get("epubs", []) if e]
    eo = dict(state.get("epub_options") or {})
    if eo.get("cover"):
        eo["cover"] = absolute(eo["cover"])
    state["epub_options"] = eo
    return state


def project_name(path) -> str:
    p = Path(path)
    name = p.name
    if name.endswith(PROJECT_EXTENSION):
        name = name[: -len(PROJECT_EXTENSION)]
    return name or p.stem
