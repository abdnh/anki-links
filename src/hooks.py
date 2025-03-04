from __future__ import annotations

import sys
from typing import Any
from urllib.parse import unquote

from aqt import gui_hooks, mw
from aqt.qt import *

from .server import LocalServer, handle_url_protocol


class MonkeyPatch:
    def __init__(self, og_onAppMsg: Callable[[str], None]) -> None:
        self.og_onAppMsg = og_onAppMsg

    def on_app_msg_wrapper_hk(self) -> Callable[[str], None]:
        def normalize_anki_url(url: str) -> str:
            """Normalize Anki URLs across all platforms"""
            print(f"Normalizing URL: {url}")

            anki_pos = url.find("anki:")
            if anki_pos == -1:
                return url

            # Extract full path after anki: including the protocol
            protocol_part = url[anki_pos:]
            print(f"Protocol part: {protocol_part}")

            # Handle different protocol variants
            if protocol_part.startswith("anki://"):
                path = protocol_part[7:]
            elif protocol_part.startswith("anki:\\\\"):  # Windows double-escaped
                path = protocol_part[8:]
            elif protocol_part.startswith("anki:\\"):
                path = protocol_part[6:]  # single escaped
            elif protocol_part.startswith("anki:"):
                path = protocol_part[5:].lstrip("/\\")
            else:
                return url

            # Normalize path separators
            path = path.replace("\\", "/")
            path = unquote(path)

            normalized = f"anki://{path}"
            print(f"Normalized result: {normalized}")
            assert "anki://" in normalized, "Missing protocol in normalized URL"

            return normalized

        def on_app_msg_hk(buf: str) -> None:
            """Handle URL protocol across platforms"""
            print(f"on_app_msg_hk: {buf}")
            print(f"sys.argv: {sys.argv}")

            # Handle both startup and runtime URLs
            url_to_check = buf if buf else (sys.argv[1] if len(sys.argv) > 1 else None)

            if url_to_check and "anki:" in url_to_check:
                print(f"handling URL: {url_to_check}")
                normalized_url = normalize_anki_url(url_to_check)
                print(f"normalized URL: {normalized_url}")

                if len(sys.argv) > 1:
                    del sys.argv[1]

                handle_url_protocol(normalized_url)
                return None

            return self.og_onAppMsg(buf)

        return on_app_msg_hk


class MacosUrlHandler(QObject):
    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FileOpen:
            assert isinstance(event, QFileOpenEvent)
            url = event.url().toString()
            print("Received URL:", url)
            if url and "anki:" in url:
                print(f"handling URL: {url}")
                handle_url_protocol(url)
                return True

        return super().eventFilter(obj, event)


def setup_app_hook() -> None:
    monkeypatch = MonkeyPatch(mw.onAppMsg)
    mw.app.appMsg.disconnect(mw.onAppMsg)
    mw.onAppMsg = monkeypatch.on_app_msg_wrapper_hk()  # type: ignore
    mw.app.appMsg.connect(mw.onAppMsg)
    macos_url_handler = MacosUrlHandler(mw)
    mw.app.installEventFilter(macos_url_handler)


def profile_unloaded_hk(server: LocalServer) -> None:
    if server:
        server.shutdown()


def setup_unload_hook(server: LocalServer) -> None:
    gui_hooks.profile_will_close.append(lambda: profile_unloaded_hk(server))
