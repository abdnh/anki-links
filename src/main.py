import os
import sys

from aqt import mw
from aqt.qt import *
from aqt.utils import showWarning

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .config import config
from .consts import consts
from .protocol import register_protocol_handler
from .server import LocalServer


def on_register() -> None:
    try:
        register_protocol_handler()
    except OSError as exc:
        showWarning(
            f"Failed to register protocol handler. Make sure to run Anki as admin to perform this operation. Error:\n\n{exc}"
        )


def add_menu() -> None:
    menu = QMenu(consts.name, mw)
    action = QAction("Register protocol handler", menu)
    qconnect(action.triggered, on_register)
    menu.addAction(action)
    mw.form.menuTools.addMenu(menu)


add_menu()
server = LocalServer(config["host"], config["port"])
server.start()
