import os
import queue
import sys
import threading
import time

import anki
import aqt
import flask
import requests
from anki.utils import is_win
from aqt import mw
from aqt.qt import *
from flask import Response
from waitress import create_server

from .log import logger

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .config import config

app = flask.Flask(__name__, root_path="/fake")


def raise_main_window() -> None:
    if is_win:
        mw.showMinimized()
        mw.setWindowState(Qt.WindowState.WindowActive)
        mw.showNormal()
    else:
        mw.activateWindow()
        mw.raise_()


def handle_url_protocol(url: str) -> None:
    """Handle anki:// URLs by passing them to the local server"""
    if not url.startswith("anki://"):
        return
    print(f"Handling URL: {url}")
    try:
        path = url[7:]  # Remove anki:// prefix
        response = requests.get(
            f"http://{config['host']}:{config['port']}/{path}", timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to handle URL: {e}")


def validate_command(command: str, parts: list) -> tuple[bool, str]:
    """Validate command and parameters"""
    allowed_commands = {"search", "deck"}
    if not command in allowed_commands:
        return False, f"Invalid command: {command}"
    if command == "deck" and len(parts) < 2:
        return False, "Deck name required"
    if command == "search" and len(parts) < 2:
        return False, "Query required"
    return True, ""


# Add command queue to store pending commands
command_queue = queue.Queue()


def process_command(command: str, parts: list) -> None:
    """Process a command"""
    try:
        while (
            not mw.col
        ):  # wait for collection to load since a task may come at startup when collection is not loaded
            time.sleep(1)

        # Raise main window first
        mw.taskman.run_on_main(raise_main_window)

        # Handle different commands
        if command == "search":
            query = "/".join(parts[1:])
            mw.taskman.run_on_main(lambda: open_browser_with_query(query))
        elif command == "deck":
            deck_name = "/".join(parts[1:])
            mw.taskman.run_on_main(lambda: select_deck(deck_name))

    except Exception as e:
        logger.error(f"Error processing queued command: {e}")


def command_processor() -> None:
    """Background thread to process queued commands"""
    while True:
        command, parts = command_queue.get()
        process_command(command, parts)
        command_queue.task_done()


@app.route("/<path:pathin>", methods=["GET", "POST"])
def handle_request(pathin: str) -> Response:
    try:
        logger.debug("request: %s", pathin)
        parts = pathin.strip("/").split("/")
        if not parts:
            return flask.make_response("Invalid URL format", 400)

        command = parts[0]
        valid, error = validate_command(command, parts)
        if not valid:
            return flask.make_response(error, 400)

        # Queue the command for processing
        command_queue.put((command, parts))

        return flask.make_response("Command queued", 202)
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return flask.make_response(str(e), 500)


def select_deck(deck_name: str) -> None:
    """Safely select a deck by name"""
    did = mw.col.decks.id(deck_name)
    if did:
        mw.col.decks.select(did)
    else:
        raise ValueError(f"Deck not found: {deck_name}")


def open_browser_with_query(search_query: str) -> None:
    browser = aqt.dialogs.open("Browser", mw)
    browser.form.searchEdit.lineEdit().setText(search_query)
    browser.onSearchActivated()


class LocalServer(threading.Thread):
    _ready = threading.Event()
    daemon = True

    def __init__(self, host: str, port: str) -> None:
        super().__init__()
        self.is_shutdown = False
        self.host = host
        self.port = port

        # Start command processor thread
        self.processor = threading.Thread(target=command_processor, daemon=True)
        self.processor.start()

    def run(self) -> None:
        try:
            self.server = create_server(
                app,
                host=self.host,
                port=self.port,
                clear_untrusted_proxy_headers=True,
            )
            self._ready.set()
            self.server.run()

        except Exception:
            if not self.is_shutdown:
                raise

    def shutdown(self) -> None:
        self.is_shutdown = True
        sockets = list(self.server._map.values())  # type: ignore
        for socket in sockets:
            socket.handle_close()
        self.server.task_dispatcher.shutdown()
