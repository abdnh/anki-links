import winreg

from .config import config


def register_protocol_handler() -> None:
    anki_handle = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, "anki")
    winreg.SetValueEx(anki_handle, "URL Protocol", 0, winreg.REG_SZ, "")
    command_handle = winreg.CreateKeyEx(anki_handle, r"shell\open\command")
    # TODO: do not store host and port in the registry so that we don't have to update the entry when the config changes
    winreg.SetValueEx(
        command_handle,
        "",
        0,
        winreg.REG_SZ,
        f"curl http://{config['host']}:{config['port']}/%1",
    )
    # TODO: icon
    # icon_handle = winreg.CreateKeyEx(anki_handle, "DefaultIcon")
    # winreg.SetValueEx(
    #     icon_handle,
    #     "",
    #     0,
    #     winreg.REG_SZ,
    #     r"C:\Users\Abdo\AppData\Local\Programs\Anki\anki.exe,1",
    # )
