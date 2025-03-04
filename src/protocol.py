import os
import subprocess
import sys

from anki.utils import is_lin, is_mac, is_win

if is_win:
    import winreg

from aqt.qt import *


def register_protocol_handler_windows() -> None:
    try:
        anki_handle = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, "anki")
        winreg.SetValueEx(anki_handle, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.SetValueEx(anki_handle, "", 0, winreg.REG_SZ, "Anki URL Protocol")

        # we reuse anki.ankiaddon command value
        try:
            ankiaddon_key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"anki.ankiaddon\shell\open\command",
                0,
                winreg.KEY_READ,
            )
            command_value = winreg.QueryValue(ankiaddon_key, "")
            ankiaddon_key.Close()
        except:
            command_value = None

        command_handle = winreg.CreateKeyEx(anki_handle, r"shell\open\command")
        if command_value:
            winreg.SetValueEx(command_handle, "", 0, winreg.REG_SZ, command_value)
        else:
            print("Failed to get command value")
    finally:
        for handle in [command_handle, anki_handle]:
            try:
                handle.Close()
            except:
                pass


def register_protocol_handler_linux() -> None:
    try:
        # 1. Create desktop entry file
        apps_dir = os.path.expanduser("/usr/share/applications")
        os.makedirs(apps_dir, exist_ok=True)

        desktop_content = """[Desktop Entry]
Version=1.0
Name=Anki URI Handler
GenericName=Anki URI Handler
Comment=Handle anki:// links
Exec=anki %u
Terminal=false
Type=Application
Categories=Education;
MimeType=x-scheme-handler/anki;"""

        desktop_path = os.path.join(apps_dir, "anki-protocol-handler.desktop")
        with open(desktop_path, "w", encoding="utf-8") as f:
            f.write(desktop_content)

        # Make desktop file executable
        os.chmod(desktop_path, 0o755)

        # 2. Create and update MIME type
        mime_dir = os.path.expanduser("/usr/share/mime")
        os.makedirs(os.path.join(mime_dir, "packages"), exist_ok=True)

        mime_content = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
    <mime-type type="x-scheme-handler/anki">
        <comment>Anki URL Handler</comment>
        <glob pattern="anki://*"/>
    </mime-type>
</mime-info>"""

        mime_path = os.path.join(mime_dir, "packages", "anki-protocol.xml")
        with open(mime_path, "w", encoding="utf-8") as f:
            f.write(mime_content)

        # 3. Update system databases
        subprocess.run(["update-mime-database", mime_dir], check=True)
        subprocess.run(
            [
                "xdg-mime",
                "default",
                "anki-protocol-handler.desktop",
                "x-scheme-handler/anki",
            ],
            check=True,
        )

        # 4. Update desktop database
        subprocess.run(["update-desktop-database", apps_dir], check=True)

    except Exception as e:
        print(f"Failed to register Linux protocol handler: {e}")


def _register_protocol_handler_macos(bundle_id: str) -> None:
    from Foundation import NSString
    from LaunchServices import LSSetDefaultHandlerForURLScheme

    cf_scheme = NSString.stringWithString_("anki")
    cf_bundle_id = NSString.stringWithString_(bundle_id)
    result = LSSetDefaultHandlerForURLScheme(cf_scheme, cf_bundle_id)
    if result != 0:
        raise Exception("LSSetDefaultHandlerForURLScheme failed")


def register_protocol_handler_macos() -> None:
    try:
        _register_protocol_handler_macos("net.ankiweb.dtop")
    except Exception as e:
        print(f"Failed to register macOS protocol handler: {e}")


def unregister_protocol_handler_macos() -> None:
    try:
        _register_protocol_handler_macos("")
    except Exception as e:
        print(f"Failed to unregister macOS protocol handler: {e}")


def unregister_protocol_handler_windows() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"anki\shell\open\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"anki\shell\open")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"anki\shell")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "anki")
    except OSError as e:
        print(f"Failed to unregister Windows protocol handler: {e}")


def unregister_protocol_handler_linux() -> None:
    try:
        # Remove desktop file
        apps_dir = os.path.expanduser("/usr/share/applications")
        desktop_path = os.path.join(apps_dir, "anki-protocol-handler.desktop")
        if os.path.exists(desktop_path):
            os.remove(desktop_path)

        # Remove MIME database entry
        mime_dir = os.path.expanduser("/usr/share/mime")
        mime_path = os.path.join(mime_dir, "packages", "anki-protocol.xml")
        if os.path.exists(mime_path):
            os.remove(mime_path)
            # Update MIME database
            subprocess.run(["update-mime-database", mime_dir], check=True)
            # Remove protocol association
            subprocess.run(["xdg-mime", "unset", "x-scheme-handler/anki"], check=True)
    except Exception as e:
        print(f"Failed to unregister Linux protocol handler: {e}")


def check_admin_windows() -> bool:
    import ctypes

    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def register_protocol_handler() -> None:
    """Register the protocol handler for the current platform"""

    if is_win:
        if not check_admin_windows():
            raise OSError(
                "Failed to register protocol handler. Make sure to run Anki as admin to perform this operation"
            )
        register_protocol_handler_windows()
    elif is_mac:
        register_protocol_handler_macos()
    elif is_lin:
        register_protocol_handler_linux()
    else:
        raise NotImplementedError(f"Platform {sys.platform} not supported")


def unregister_protocol_handler() -> None:
    if is_win:
        if not check_admin_windows():
            raise OSError(
                "Failed to unregister protocol handler. Make sure to run Anki as admin to perform this operation"
            )
        unregister_protocol_handler_windows()
    elif is_mac:
        unregister_protocol_handler_macos()
    elif is_lin:
        unregister_protocol_handler_linux()
    else:
        raise NotImplementedError(f"Platform {sys.platform} not supported (2)")
