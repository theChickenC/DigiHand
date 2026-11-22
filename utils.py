import os
import sys
import uuid

# Root for bundled resources (icons etc). PyInstaller onedir extracts datas
# into an _internal/ folder next to the exe (onefile: sys._MEIPASS); when
# running from source it is the repo folder. os.path.join("images", ...)
# alone breaks in the exe because cwd is not the app folder there.
if getattr(sys, "frozen", False):
    RES_DIR = getattr(sys, "_MEIPASS",
                      os.path.join(os.path.dirname(sys.executable), "_internal"))
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))


def hexuuid():
    return uuid.uuid4().hex


def splitext(p):
    return os.path.splitext(p)[1].lower()
