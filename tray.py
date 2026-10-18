import sys
import tkinter as tk
from tkinter import messagebox
from settings import APP_NAME

class TrayMixin:
        def ensure_tray_icon(self):
            """Создаёт значок системного трея, если он ещё не запущен."""
            if self.tray_icon is not None:
                return True

            try:
                import pystray
                from PIL import Image, ImageDraw
            except ImportError:
                messagebox.showerror(
                    "Системный трей",
                    "Для работы трея установите библиотеки командой:\\n"
                    "python -m pip install pystray pillow",
                    parent=self.root
                )
                return False

            # Небольшой собственный значок FileSorter без внешних файлов.
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((4, 4, 60, 60), radius=13, fill="#4778d0")
            draw.rounded_rectangle((16, 14, 48, 50), radius=4, fill="#ffffff")
            draw.line((22, 24, 28, 30, 41, 19), fill="#4778d0", width=4)
            draw.line((22, 38, 42, 38), fill="#4778d0", width=3)
            draw.line((22, 44, 37, 44), fill="#4778d0", width=3)

            def open_from_tray(icon, item):
                self.root.after(0, self.show_window)

            def exit_from_tray(icon, item):
                self.root.after(0, self.quit_app)

            menu = pystray.Menu(
                pystray.MenuItem("Открыть FileSorter", open_from_tray, default=True),
                pystray.MenuItem("Выход", exit_from_tray)
            )
            self.tray_icon = pystray.Icon(
                APP_NAME, image, "FileSorter", menu
            )
            try:
                self.tray_icon.run_detached()
                return True
            except Exception as error:
                self.tray_icon = None
                messagebox.showerror(
                    "Системный трей",
                    f"Не удалось создать значок в трее:\\n{error}",
                    parent=self.root
                )
                return False

        def show_window(self):
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            try:
                self.root.focus_force()
            except tk.TclError:
                pass

        def on_close(self):
            try:
                self.persist()
            except OSError:
                pass

            if self.minimize_to_tray.get() and not self._really_quitting:
                if self.ensure_tray_icon():
                    self.root.withdraw()
                    self.status.set("FileSorter работает в системном трее.")
                    return

            self.quit_app()

        def quit_app(self):
            if self._really_quitting:
                return
            self._really_quitting = True

            try:
                self.persist()
            except (OSError, ValueError):
                pass

            if self._auto_sort_job is not None:
                try:
                    self.root.after_cancel(self._auto_sort_job)
                except tk.TclError:
                    pass
                self._auto_sort_job = None

            if self.tray_icon is not None:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None

            self.root.destroy()
