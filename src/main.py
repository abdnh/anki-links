import os
import sys

import anki
import aqt
import aqt.utils
from aqt import mw
from aqt.qt import *

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .config import config
from .consts import consts
from .hooks import setup_app_hook, setup_unload_hook
from .protocol import register_protocol_handler, unregister_protocol_handler
from .server import LocalServer


def on_register() -> None:
    try:
        register_protocol_handler()
    except OSError as exc:
        print(
            f"Failed to register protocol handler. Make sure to run Anki as admin to perform this operation. Error:\n\n{exc}"
        )


def on_unregister() -> None:
    try:
        unregister_protocol_handler()
    except OSError as exc:
        print(
            f"Failed to unregister protocol handler. Make sure to run Anki as admin to perform this operation. Error:\n\n{exc}"
        )


def add_menu() -> None:
    menu = QMenu(consts.name, mw)

    action = QAction("Register protocol handler", menu)
    qconnect(action.triggered, on_register)
    menu.addAction(action)

    action = QAction("Unregister protocol handler", menu)
    qconnect(action.triggered, on_unregister)
    menu.addAction(action)

    mw.form.menuTools.addMenu(menu)


def init():
    print("init")
    server = LocalServer(config["host"], config["port"])
    server.start()
    print("Server started")
    setup_app_hook()
    setup_unload_hook(server)
    print("Hooks set up")
    add_menu()


init()
