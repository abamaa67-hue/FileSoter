from pathlib import Path
import os
import sys
import json

APP_NAME = "FileSorter"
APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = APP_DIR / "settings.json"
UNDO_PATH = APP_DIR / "undo_history.json"
MAX_UNDO_BATCHES = 20

DEFAULT_RULES = {
    ".jpg": "Изображения",
    ".jpeg": "Изображения",
    ".png": "Изображения",
    ".gif": "Изображения",
    ".webp": "Изображения",
    ".bmp": "Изображения",
    ".pdf": "Документы",
    ".docx": "Документы",
    ".txt": "Документы",
    ".xlsx": "Документы",
    ".csv": "Документы",
    ".doc": "Документы",
    ".mp4": "Видео",
    ".mkv": "Видео",
    ".mov": "Видео",
    ".avi": "Видео",
    ".zip": "Архивы",
    ".rar": "Архивы",
    ".7z": "Архивы",
    ".mp3": "Музыка",
    ".wav": "Музыка",
    ".flac": "Музыка",
}


def windows_dark_mode():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False

def set_windows_autostart(enabled):
    if sys.platform != "win32":
        raise OSError("Автозапуск доступен только в Windows.")

    import winreg
    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        run_key,
        0,
        winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            if getattr(sys, "frozen", False):
                command = f'"{Path(sys.executable).resolve()}"'
            else:
                command = (
                    f'"{Path(sys.executable).resolve()}" '
                    f'"{Path(__file__).resolve()}"'
                )
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass

def load_settings():
    APP_DIR.mkdir(parents=True, exist_ok=True)

    settings = {
        "theme": "system",
        "source_folder": str(Path.home() / "Downloads"),
        "rules": DEFAULT_RULES.copy(),
        "autostart": False,
        "minimize_to_tray": False,
        "confirm_before_sort": True,
        "show_hidden": False,
        "show_summary": True,
        "create_unknown_folder": True,
        "hotkey_enabled": True,
        "auto_sort_enabled": False,
        "auto_sort_minutes": 30,
    }

    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            settings.update(saved)
    except (OSError, json.JSONDecodeError):
        pass

    if not isinstance(settings.get("rules"), dict):
        settings["rules"] = DEFAULT_RULES.copy()

    return settings

def save_settings(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
