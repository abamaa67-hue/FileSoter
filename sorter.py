from pathlib import Path
import json
import shutil
import tkinter as tk
from tkinter import messagebox
from settings import APP_DIR, UNDO_PATH, MAX_UNDO_BATCHES

class SorterMixin:
        def valid_folder_name(name):
            return bool(
                name
                and name not in (".", "..")
                and not any(c in name for c in '<>:"|?*')
                and not name.endswith((" ", "."))
            )

        def add_rule(self):
            extension = self.extension.get().strip().lower()
            category = self.category.get().strip().strip("\\/")

            if (
                not extension.startswith(".")
                or len(extension) < 2
                or "/" in extension
                or "\\" in extension
            ):
                messagebox.showwarning(
                    "Расширение",
                    "Введите расширение с точкой, например .psd."
                )
                return

            if not self.valid_folder_name(category):
                messagebox.showwarning(
                    "Папка",
                    "Введите допустимое название папки."
                )
                return

            if extension in self.rules:
                messagebox.showwarning(
                    "Правило существует",
                    f"Правило для {extension} уже существует."
                )
                return

            base = Path(self.folder.get()).expanduser()
            if not base.is_dir():
                messagebox.showerror(
                    "Исходная папка",
                    "Сначала выберите существующую исходную папку."
                )
                return

            destination = (base / category).resolve()

            try:
                destination.relative_to(base.resolve())
                destination.mkdir(parents=True, exist_ok=True)
            except (ValueError, OSError) as error:
                messagebox.showerror(
                    "Папка назначения",
                    f"Не удалось создать папку:\n{error}"
                )
                return

            self.rules[extension] = category
            self.extension.set("")
            self.category.set("")
            self.refresh_rules()
            self.persist()
            self.status.set(f"Добавлено правило: {extension} → {category}")

        def refresh_rules(self):
            for item in self.rules_table.get_children():
                self.rules_table.delete(item)

            for extension, category in sorted(self.rules.items()):
                self.rules_table.insert(
                    "", "end", values=(extension, category)
                )

        def remove_rule(self):
            selection = self.rules_table.selection()
            if not selection:
                messagebox.showinfo(
                    "Правило",
                    "Сначала выберите правило в таблице."
                )
                return

            extension = self.rules_table.item(
                selection[0], "values"
            )[0]

            if messagebox.askyesno(
                "Удалить правило",
                f"Удалить правило для {extension}?"
            ):
                del self.rules[extension]
                self.refresh_rules()
                self.persist()
                self.status.set(f"Правило {extension} удалено.")

        def get_plan(self):
            folder = Path(self.folder.get()).expanduser()

            if not folder.is_dir():
                messagebox.showerror(
                    "Исходная папка",
                    f"Папка не найдена:\n{folder}"
                )
                return None

            plan = []

            try:
                for source in folder.iterdir():
                    if not source.is_file():
                        continue

                    if not self.show_hidden.get() and source.name.startswith("."):
                        continue

                    category = self.rules.get(source.suffix.lower())

                    if category is None:
                        category = (
                            "Другое"
                            if self.create_unknown_folder.get()
                            else None
                        )

                    if category is None:
                        continue

                    destination_folder = (folder / category).resolve()

                    try:
                        destination_folder.relative_to(folder.resolve())
                    except ValueError:
                        continue

                    destination = destination_folder / source.name

                    result = (
                        f"КОНФЛИКТ — пропустить ({category})"
                        if destination.exists()
                        else f"В → {category}"
                    )

                    plan.append(
                        (source, destination_folder, destination, result)
                    )

            except OSError as error:
                messagebox.showerror(
                    "Ошибка чтения папки", str(error)
                )
                return None

            return plan

        def preview(self):
            plan = self.get_plan()
            if plan is None:
                return

            if not plan:
                self.status.set("Нет файлов для сортировки.")
                messagebox.showinfo(
                    "Предпросмотр",
                    "Нет файлов для сортировки."
                )
                return

            lines = [
                f"{source.name}\n  {result}"
                for source, _, _, result in plan
            ]

            messagebox.showinfo(
                "Предпросмотр сортировки",
                "\n\n".join(lines)
            )

            self.status.set(
                f"Предпросмотр готов. Файлов: {len(plan)}"
            )

        def load_undo_history(self):
            """Загружает историю перемещений, чтобы отмена переживала перезапуск."""
            try:
                data = json.loads(UNDO_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    valid_batches = []
                    for batch in data[-MAX_UNDO_BATCHES:]:
                        if not isinstance(batch, list):
                            continue
                        valid_items = [
                            item for item in batch
                            if isinstance(item, dict)
                            and isinstance(item.get("source"), str)
                            and isinstance(item.get("destination"), str)
                        ]
                        if valid_items:
                            valid_batches.append(valid_items)
                    return valid_batches
            except (OSError, json.JSONDecodeError):
                pass
            return []

        def save_undo_history(self):
            APP_DIR.mkdir(parents=True, exist_ok=True)
            UNDO_PATH.write_text(
                json.dumps(self.undo_history[-MAX_UNDO_BATCHES:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            if self.undo_button is not None:
                self.undo_button.configure(
                    state="normal" if self.undo_history else "disabled"
                )

        def undo_last_sort(self):
            """Отменяет последнюю сортировку, не перезаписывая существующие файлы."""
            if not self.undo_history:
                self.status.set("Нет перемещений для отмены.")
                return

            batch = self.undo_history[-1]
            if not messagebox.askyesno(
                "Отменить перемещение",
                f"Попробовать вернуть файлы на исходные места: {len(batch)}?\n\n"
                "Файлы не будут перезаписаны. Если исходное место занято, файл останется на месте."
            ):
                return

            restored = skipped = errors = 0
            remaining = []
            for item in reversed(batch):
                source = Path(item["source"])
                destination = Path(item["destination"])
                try:
                    # Если файл уже отсутствует в месте назначения, его мог переместить пользователь.
                    if not destination.exists():
                        skipped += 1
                        continue
                    if source.exists():
                        skipped += 1
                        remaining.append(item)
                        continue
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(destination), str(source))
                    restored += 1
                except OSError as error:
                    errors += 1
                    remaining.append(item)
                    print(f"Не удалось отменить перемещение {destination}: {error}")

            self.undo_history.pop()
            if remaining:
                self.undo_history.append(list(reversed(remaining)))
            try:
                self.save_undo_history()
            except OSError as error:
                messagebox.showwarning(
                    "История отмены",
                    f"Файлы обработаны, но историю не удалось сохранить:\n{error}",
                    parent=self.root
                )

            self.status.set(
                f"Отмена: возвращено {restored} | пропущено {skipped} | ошибок {errors}"
            )
            if restored or errors:
                messagebox.showinfo(
                    "Отмена завершена",
                    f"Возвращено: {restored}\nПропущено: {skipped}\nОшибок: {errors}",
                    parent=self.root
                )

        def sort_files(self, from_automation=False):
            if self.sorting:
                return

            plan = self.get_plan()
            if plan is None:
                return

            if not plan:
                self.status.set("Нет файлов для сортировки.")
                return

            if not from_automation and self.confirm_before_sort.get():
                if not messagebox.askyesno(
                    "Подтверждение",
                    f"Обработать файлов: {len(plan)}?\n\n"
                    "Существующие файлы не будут перезаписаны."
                ):
                    return

            self.sorting = True
            moved = skipped = errors = 0
            moved_items = []

            try:
                for source, destination_folder, destination, _ in plan:
                    try:
                        if destination.exists():
                            skipped += 1
                            continue

                        destination_folder.mkdir(
                            parents=True,
                            exist_ok=True
                        )

                        if destination.exists():
                            skipped += 1
                            continue

                        shutil.move(str(source), str(destination))
                        moved += 1
                        moved_items.append({
                            "source": str(source),
                            "destination": str(destination),
                        })

                    except OSError as error:
                        errors += 1
                        print(f"Ошибка для {source.name}: {error}")
            finally:
                self.sorting = False

            if moved_items:
                self.undo_history.append(moved_items)
                self.undo_history = self.undo_history[-MAX_UNDO_BATCHES:]
                try:
                    self.save_undo_history()
                except OSError as error:
                    messagebox.showwarning(
                        "История отмены",
                        f"Файлы перемещены, но историю отмены не удалось сохранить:\n{error}",
                        parent=self.root
                    )

            self.persist()

            prefix = (
                "Автоматическая сортировка"
                if from_automation
                else "Сортировка"
            )

            self.status.set(
                f"{prefix}: перемещено {moved} | "
                f"пропущено {skipped} | ошибок {errors}"
            )

            if self.show_summary.get() and (
                not from_automation or moved or errors
            ):
                messagebox.showinfo(
                    "Сортировка завершена",
                    f"Перемещено: {moved}\n"
                    f"Пропущено из-за совпадений: {skipped}\n"
                    f"Ошибок: {errors}"
                )
