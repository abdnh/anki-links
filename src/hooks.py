import sys
from urllib.parse import unquote

import anki
import aqt
import aqt.utils
from aqt import gui_hooks, mw
from aqt.qt import *

from .server import LocalServer, handle_url_protocol


class MonkeyPatch:
    _og_onAppMsg = None

    @property
    def og_onAppMsg(self):
        return type(self)._og_onAppMsg

    @og_onAppMsg.setter
    def og_onAppMsg(self, val):
        type(self)._og_onAppMsg = val

    @staticmethod
    def on_app_msg_wrapper_hk(self: "AnkiQt"):
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

            return MonkeyPatch.og_onAppMsg(buf)

        return on_app_msg_hk


def setup_app_hook() -> None:
    MonkeyPatch.og_onAppMsg = mw.onAppMsg
    mw.app.appMsg.disconnect(mw.onAppMsg)
    mw.onAppMsg = MonkeyPatch.on_app_msg_wrapper_hk(mw)
    mw.app.appMsg.connect(mw.onAppMsg)


def profile_unloaded_hk(server: LocalServer) -> None:
    if server:
        server.shutdown()


def setup_unload_hook(server: LocalServer) -> None:
    gui_hooks.profile_will_close.append(lambda: profile_unloaded_hk(server))
