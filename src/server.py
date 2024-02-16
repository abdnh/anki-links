import threading

import flask
from anki.utils import is_win
from aqt import mw
from aqt.qt import *
from flask import Response
from waitress import create_server

from .log import logger

app = flask.Flask(__name__, root_path="/fake")


def raise_main_window() -> None:
    if is_win:
        mw.showMinimized()
        mw.setWindowState(Qt.WindowState.WindowActive)
        mw.showNormal()
    else:
        mw.activateWindow()
        mw.raise_()


@app.route("/<path:pathin>", methods=["GET", "POST"])
def handle_request(pathin: str) -> Response:
    logger.debug("request: %s", pathin)
    mw.taskman.run_on_main(raise_main_window)
    return flask.make_response("ok")


class LocalServer(threading.Thread):
    _ready = threading.Event()
    daemon = True

    def __init__(self, host: str, port: str) -> None:
        super().__init__()
        self.is_shutdown = False
        self.host = host
        self.port = port

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
