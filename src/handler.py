import queue
import threading
import time

import aqt
from anki.utils import is_win
from aqt import mw
from aqt.qt import *

from .log import logger


def raise_main_window() -> None:
    if is_win:
        mw.showMinimized()
        mw.setWindowState(Qt.WindowState.WindowActive)
        mw.showNormal()
    else:
        mw.activateWindow()
        mw.raise_()


def handle_url_protocol(url: str) -> None:
    """Handle anki:// URLs"""
    if not url.startswith("anki://"):
        return
    print(f"Handling URL: {url}")
    path = url[7:]  # Remove anki:// prefix
    parts = path.strip("/").split("/")
    if not parts:
        raise Exception("Invalid URL format")

    command = parts[0]
    validate_command(command, parts)
    # Queue the command for processing
    command_queue.put((command, parts))


def validate_command(command: str, parts: list) -> None:
    """Validate command and parameters"""
    allowed_commands = {"search", "deck"}
    if not command in allowed_commands:
        raise Exception(f"Invalid command: {command}")
    if command == "deck" and len(parts) < 2:
        raise Exception("Deck name required")
    if command == "search" and len(parts) < 2:
        raise Exception("Query required")


# Add command queue to store pending commands
command_queue: queue.Queue = queue.Queue()


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
        logger.error("Error processing queued command: %s", e)


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


class CommandHandler(threading.Thread):
    daemon = True

    def run(self) -> None:
        while True:
            command, parts = command_queue.get()
            process_command(command, parts)
            command_queue.task_done()
