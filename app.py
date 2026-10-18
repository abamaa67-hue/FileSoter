from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from settings import APP_NAME, load_settings, save_settings, windows_dark_mode, set_windows_autostart
from sorter import SorterMixin
from tray import TrayMixin

class FileSorterApp(SorterMixin, TrayMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("FileSorter")
        # Иконка окна — отдельная от иконки системного трея.
        self.window_icon = tk.PhotoImage(width=32, height=32)
        self.window_icon.put("#4778d0", to=(2, 2, 30, 30))
        self.window_icon.put("#ffffff", to=(9, 7, 23, 25))
        self.window_icon.put("#4778d0", to=(12, 11, 20, 13))
        self.window_icon.put("#4778d0", to=(12, 16, 20, 18))
        self.window_icon.put("#4778d0", to=(12, 21, 18, 23))
        self.root.iconphoto(True, self.window_icon)
        self.root.geometry("900x650")
        self.root.minsize(740, 540)

        self.settings = load_settings()
        self.rules = dict(self.settings["rules"])

        self.folder = tk.StringVar(
            value=self.settings["source_folder"]
        )
        self.extension = tk.StringVar()
        self.category = tk.StringVar()
        self.status = tk.StringVar(
            value="Выберите исходную папку и нажмите «Предпросмотр»."
        )

        self.theme = tk.StringVar(value=self.settings["theme"])
        self.autostart = tk.BooleanVar(
            value=self.settings["autostart"]
        )
        self.minimize_to_tray = tk.BooleanVar(
            value=self.settings.get("minimize_to_tray", False)
        )
        self.confirm_before_sort = tk.BooleanVar(
            value=self.settings["confirm_before_sort"]
        )
        self.show_hidden = tk.BooleanVar(
            value=self.settings["show_hidden"]
        )
        self.show_summary = tk.BooleanVar(
            value=self.settings["show_summary"]
        )
        self.create_unknown_folder = tk.BooleanVar(
            value=self.settings["create_unknown_folder"]
        )
        self.hotkey_enabled = tk.BooleanVar(
            value=self.settings["hotkey_enabled"]
        )
        self.auto_sort_enabled = tk.BooleanVar(
            value=self.settings["auto_sort_enabled"]
        )
        self.auto_sort_minutes = tk.StringVar(
            value=str(self.settings["auto_sort_minutes"])
        )

        self.sorting = False
        self._auto_sort_job = None
        self.undo_history = self.load_undo_history()
        self.undo_button = None
        self.tray_icon = None
        self._really_quitting = False

        self.style = ttk.Style()
        self.apply_theme()
        self.build_interface()
        self.refresh_rules()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.register_hotkey()
        self.configure_auto_sort_timer()

    def apply_theme(self):
        choice = self.theme.get()
        dark = (
            windows_dark_mode()
            if choice == "system"
            else choice == "dark"
        )

        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        if dark:
            bg = "#202124"
            panel = "#2b2d30"
            fg = "#f1f3f4"
            field = "#17181a"
            select = "#355b8c"
            button_bg = "#34363a"
            button_hover = "#41444a"
            button_pressed = "#292b2f"
        else:
            bg = "#f3f4f6"
            panel = "#ffffff"
            fg = "#202124"
            field = "#ffffff"
            select = "#cfe2ff"
            button_bg = "#e7e9ed"
            button_hover = "#d9dde4"
            button_pressed = "#cbd0d8"

        self.root.configure(bg=bg)
        self.style.configure(
            ".", background=bg, foreground=fg,
            fieldbackground=field
        )
        self.style.configure("TFrame", background=bg)
        self.style.configure(
            "TLabelframe", background=bg, foreground=fg
        )
        self.style.configure(
            "TLabelframe.Label", background=bg, foreground=fg
        )
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure(
            "TButton",
            padding=(12, 7),
            background=button_bg,
            foreground=fg,
            bordercolor=button_bg,
            lightcolor=button_bg,
            darkcolor=button_bg,
            relief="flat",
            borderwidth=0,
            focusthickness=0
        )
        button_states = {
            "background": [
                ("disabled", button_bg),
                ("pressed", button_pressed),
                ("active", button_hover),
                ("!disabled", button_bg),
            ],
            "foreground": [("disabled", "#888888"), ("!disabled", fg)],
            "bordercolor": [
                ("pressed", button_pressed),
                ("active", button_hover),
                ("!disabled", button_bg),
            ],
            "lightcolor": [
                ("pressed", button_pressed),
                ("active", button_hover),
                ("!disabled", button_bg),
            ],
            "darkcolor": [
                ("pressed", button_pressed),
                ("active", button_hover),
                ("!disabled", button_bg),
            ],
            "relief": [("pressed", "flat"), ("!pressed", "flat")],
        }
        self.style.map("TButton", **button_states)
        self.style.configure(
            "Settings.TButton",
            padding=(12, 7), background=button_bg, foreground=fg,
            bordercolor=button_bg, lightcolor=button_bg,
            darkcolor=button_bg, relief="flat", borderwidth=0,
            focusthickness=0,
        )
        self.style.map("Settings.TButton", **button_states)
        self.style.configure(
            "TEntry", fieldbackground=field, foreground=fg
        )
        self.style.configure(
            "TCheckbutton", background=bg, foreground=fg,
            indicatorcolor=field, focuscolor=bg
        )
        self.style.map(
            "TCheckbutton",
            background=[
                ("disabled", bg), ("active", bg),
                ("pressed", bg), ("!disabled", bg)
            ],
            foreground=[
                ("disabled", "#888888"), ("active", fg),
                ("!disabled", fg)
            ],
            indicatorcolor=[
                ("disabled", field), ("selected", select),
                ("pressed", button_pressed), ("active", field),
                ("!selected", field)
            ],
            focuscolor=[("focus", bg), ("!focus", bg)]
        )
        self.style.configure(
            "TRadiobutton", background=bg, foreground=fg,
            indicatorcolor=field, focuscolor=bg
        )
        self.style.map(
            "TRadiobutton",
            background=[
                ("disabled", bg), ("active", bg),
                ("pressed", bg), ("!disabled", bg)
            ],
            foreground=[
                ("disabled", "#888888"), ("active", fg),
                ("!disabled", fg)
            ],
            indicatorcolor=[
                ("disabled", field), ("selected", select),
                ("pressed", button_pressed), ("active", field),
                ("!selected", field)
            ],
            focuscolor=[("focus", bg), ("!focus", bg)]
        )
        self.style.configure(
            "Treeview",
            background=field,
            fieldbackground=field,
            foreground=fg,
            rowheight=25
        )
        self.style.configure(
            "Treeview.Heading",
            background=panel,
            foreground=fg
        )
        self.style.map(
            "Treeview",
            background=[("selected", select)],
            foreground=[("selected", fg)]
        )

    def build_interface(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="FileSorter",
            font=("Segoe UI", 20, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="Настройки",
            command=self.open_settings
        ).pack(side="right")

        ttk.Label(
            main,
            text="Сортировка файлов по расширениям"
        ).pack(anchor="w", pady=(0, 12))

        source_frame = ttk.LabelFrame(
            main,
            text="Откуда сортировать файлы",
            padding=10
        )
        source_frame.pack(fill="x", pady=(0, 12))

        source_row = ttk.Frame(source_frame)
        source_row.pack(fill="x")

        ttk.Entry(
            source_row,
            textvariable=self.folder
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ttk.Button(
            source_row,
            text="Выбрать папку...",
            command=self.choose_folder
        ).pack(side="left")

        rules_frame = ttk.LabelFrame(
            main,
            text="Правила сортировки",
            padding=10
        )
        rules_frame.pack(fill="both", expand=True, pady=(0, 12))

        self.rules_table = ttk.Treeview(
            rules_frame,
            columns=("extension", "category"),
            show="headings",
            height=9,
            selectmode="browse"
        )
        self.rules_table.heading(
            "extension", text="Расширение"
        )
        self.rules_table.heading(
            "category", text="Папка назначения"
        )
        self.rules_table.column("extension", width=150)
        self.rules_table.column("category", width=300)
        self.rules_table.pack(fill="both", expand=True)

        add_frame = ttk.Frame(rules_frame)
        add_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(
            add_frame, text="Расширение:"
        ).pack(side="left")

        ttk.Entry(
            add_frame,
            textvariable=self.extension,
            width=12
        ).pack(side="left", padx=(6, 10))

        ttk.Label(add_frame, text="Папка:").pack(side="left")

        ttk.Entry(
            add_frame,
            textvariable=self.category,
            width=16
        ).pack(side="left", padx=6, fill="x", expand=True)

        ttk.Button(
            add_frame,
            text="Обзор...",
            command=self.choose_category_folder
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            add_frame,
            text="Добавить правило",
            command=self.add_rule
        ).pack(side="left", padx=4)

        ttk.Button(
            add_frame,
            text="Удалить выбранное",
            command=self.remove_rule
        ).pack(side="left", padx=4)

        actions = ttk.Frame(main)
        actions.pack(fill="x")

        ttk.Button(
            actions,
            text="Предпросмотр",
            command=self.preview
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Переместить файлы",
            command=self.sort_files
        ).pack(side="left", padx=8)

        self.undo_button = ttk.Button(
            actions,
            text="Отменить перемещение",
            command=self.undo_last_sort,
            state="normal" if self.undo_history else "disabled"
        )
        self.undo_button.pack(side="left")

        ttk.Label(
            actions,
            text="Ctrl+Shift+S — сортировка"
        ).pack(side="right")

        ttk.Label(
            main,
            textvariable=self.status,
            wraplength=850
        ).pack(anchor="w", pady=(12, 0))

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Настройки FileSorter")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Внешний вид",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame, text="Как в Windows",
            variable=self.theme, value="system"
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            frame, text="Светлая",
            variable=self.theme, value="light"
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            frame, text="Тёмная",
            variable=self.theme, value="dark"
        ).pack(anchor="w", pady=2)

        ttk.Separator(frame).pack(fill="x", pady=10)

        ttk.Label(
            frame,
            text="Запуск и сортировка",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Checkbutton(
            frame,
            text="Запускать вместе с Windows",
            variable=self.autostart
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame,
            text="Сворачивать в системный трей при закрытии",
            variable=self.minimize_to_tray
        ).pack(anchor="w", pady=2)

        ttk.Label(
            frame,
            text="При включении крестик скрывает окно, а программа продолжает работать."
        ).pack(anchor="w", pady=(0, 4))

        ttk.Checkbutton(
            frame,
            text="Подтверждать ручную сортировку",
            variable=self.confirm_before_sort
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame,
            text="Показывать итог после сортировки",
            variable=self.show_summary
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame,
            text="Показывать скрытые файлы",
            variable=self.show_hidden
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame,
            text="Неизвестные типы отправлять в «Другое»",
            variable=self.create_unknown_folder
        ).pack(anchor="w", pady=2)

        ttk.Separator(frame).pack(fill="x", pady=10)

        ttk.Label(
            frame,
            text="Горячая клавиша",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Checkbutton(
            frame,
            text="Включить Ctrl+Shift+S для сортировки",
            variable=self.hotkey_enabled
        ).pack(anchor="w", pady=2)

        ttk.Label(
            frame,
            text="Работает, пока окно FileSorter открыто."
        ).pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)

        ttk.Label(
            frame,
            text="Автоматическая сортировка",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Checkbutton(
            frame,
            text="Включить сортировку по таймеру",
            variable=self.auto_sort_enabled
        ).pack(anchor="w", pady=2)

        interval_row = ttk.Frame(frame)
        interval_row.pack(fill="x", pady=4)

        ttk.Label(
            interval_row,
            text="Интервал (минуты):"
        ).pack(side="left")

        ttk.Entry(
            interval_row,
            textvariable=self.auto_sort_minutes,
            width=8
        ).pack(side="left", padx=8)

        ttk.Label(
            frame,
            text="Таймер работает, пока программа запущена."
        ).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))

        ttk.Button(
            buttons,
            text="Сохранить",
            style="Settings.TButton",
            command=lambda: self.save_settings_from_window(win)
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Отмена",
            style="Settings.TButton",
            command=win.destroy
        ).pack(side="right", padx=8)

    def save_settings_from_window(self, win):
        try:
            minutes = int(self.auto_sort_minutes.get().strip())
            if not 1 <= minutes <= 10080:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Интервал",
                "Введите целое число от 1 до 10080 минут.",
                parent=win
            )
            return

        old_autostart = bool(self.settings.get("autostart", False))
        new_autostart = bool(self.autostart.get())

        try:
            if old_autostart != new_autostart:
                set_windows_autostart(new_autostart)
        except Exception as error:
            messagebox.showerror(
                "Автозапуск",
                f"Не удалось изменить автозапуск:\n{error}",
                parent=win
            )
            self.autostart.set(old_autostart)
            return

        self.settings.update(self.collect_settings(minutes))
        save_settings(self.settings)
        self.apply_theme()
        self.register_hotkey()
        self.configure_auto_sort_timer()
        win.destroy()
        self.status.set("Настройки сохранены.")

    def collect_settings(self, minutes=None):
        """Собирает текущие значения настроек в единый словарь."""
        if minutes is None:
            try:
                minutes = int(self.auto_sort_minutes.get().strip())
                if not 1 <= minutes <= 10080:
                    minutes = 30
            except ValueError:
                minutes = 30

        return {
            "theme": self.theme.get(),
            "autostart": bool(self.autostart.get()),
            "minimize_to_tray": bool(self.minimize_to_tray.get()),
            "confirm_before_sort": bool(self.confirm_before_sort.get()),
            "show_hidden": bool(self.show_hidden.get()),
            "show_summary": bool(self.show_summary.get()),
            "create_unknown_folder": bool(self.create_unknown_folder.get()),
            "hotkey_enabled": bool(self.hotkey_enabled.get()),
            "auto_sort_enabled": bool(self.auto_sort_enabled.get()),
            "auto_sort_minutes": minutes,
            "rules": self.rules,
            "source_folder": self.folder.get(),
        }

    def persist(self):
        self.settings.update(self.collect_settings())
        save_settings(self.settings)

    def register_hotkey(self):
        self.root.unbind_all("<Control-Shift-s>")
        if self.hotkey_enabled.get():
            self.root.bind_all(
                "<Control-Shift-s>",
                self.hotkey_sort
            )

    def hotkey_sort(self, _event=None):
        self.sort_files(from_automation=True)
        return "break"

    def configure_auto_sort_timer(self):
        if self._auto_sort_job is not None:
            try:
                self.root.after_cancel(self._auto_sort_job)
            except tk.TclError:
                pass

        self._auto_sort_job = None

        if self.auto_sort_enabled.get():
            try:
                minutes = max(1, int(self.auto_sort_minutes.get()))
            except ValueError:
                minutes = 30

            self._auto_sort_job = self.root.after(
                minutes * 60 * 1000,
                self.auto_sort_tick
            )

    def auto_sort_tick(self):
        self._auto_sort_job = None
        if self.auto_sort_enabled.get():
            self.sort_files(from_automation=True)
            self.configure_auto_sort_timer()

    def choose_folder(self):
        current = self.folder.get().strip()
        initial = (
            current if Path(current).is_dir()
            else str(Path.home())
        )

        selected = filedialog.askdirectory(
            title="Выберите исходную папку",
            initialdir=initial
        )

        if selected:
            self.folder.set(selected)
            self.persist()
            self.status.set(f"Исходная папка: {selected}")

    def choose_category_folder(self):
        base = Path(self.folder.get()).expanduser()
        initial = str(base) if base.is_dir() else str(Path.home())

        selected = filedialog.askdirectory(
            title="Выберите папку назначения",
            initialdir=initial
        )

        if not selected:
            return

        try:
            relative = Path(selected).resolve().relative_to(base.resolve())
            if not relative.parts:
                messagebox.showwarning(
                    "Выберите подпапку",
                    "Выберите папку внутри исходной папки."
                )
                return
            self.category.set(str(relative))
        except (ValueError, OSError):
            messagebox.showwarning(
                "Папка вне исходной",
                "Выберите папку внутри исходной папки "
                "или введите новое название вручную."
            )


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    root = tk.Tk()
    FileSorterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
