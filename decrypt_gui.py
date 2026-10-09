#!/usr/bin/env python3
"""Windows Tkinter GUI for MTA:SA luac.mtasa.com (0x1C) decryption."""
from __future__ import annotations

import os
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

try:
    from mta_luac_decrypt import decrypt_mta_luac, normalize_luaq
except ImportError as exc:  # pragma: no cover - shown in the UI
    decrypt_mta_luac = None  # type: ignore[assignment]
    normalize_luaq = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

BG = "#1b1d21"
PANEL = "#24272c"
FIELD = "#121417"
FG = "#e8eaed"
MUTED = "#9aa3ad"
ACCENT = "#2b7de9"
ACCENT_HOVER = "#3d8df5"
SUCCESS = "#3dd68c"
WARN = "#f5c542"
ERROR = "#ff6b6b"
BORDER = "#3a3f46"


def _windows_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


class HoverButton(tk.Button):
    def __init__(self, master: tk.Misc, hover: str, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._bg = str(kwargs.get("bg") or kwargs.get("background") or ACCENT)
        self._hover = hover
        self.bind("<Enter>", lambda _e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg))


class DecryptApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MTA LuaC Decryptor")
        self.configure(bg=BG)
        self.minsize(720, 560)
        self.geometry("820x640")
        self.files: list[Path] = []
        self.busy = False
        self.output_var = tk.StringVar(value="")
        self.save_raw = tk.BooleanVar(value=True)
        self.normalize = tk.BooleanVar(value=True)
        self._build()
        if IMPORT_ERROR is not None:
            self.after(200, self._warn_import)

    def _font(self, size: int = 11, weight: str = "normal") -> tuple:
        return ("Segoe UI", size, weight)

    def _build(self) -> None:
        pad = {"padx": 18, "pady": (16, 0)}

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", **pad)
        tk.Label(
            header,
            text="MTA LuaC Decryptor",
            bg=BG,
            fg=FG,
            font=self._font(18, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text="اختر ملف .luac مشفّر (علامة 0x1C) ثم اضغط Decrypt — الناتج يُحفظ في مجلد.",
            bg=BG,
            fg=MUTED,
            font=self._font(10),
            anchor="w",
            wraplength=760,
            justify="left",
        ).pack(fill="x", pady=(4, 0))

        files_box = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        files_box.pack(fill="both", expand=False, padx=18, pady=(14, 0))
        top = tk.Frame(files_box, bg=PANEL)
        top.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(top, text="الملفات", bg=PANEL, fg=FG, font=self._font(11, "bold")).pack(side="left")
        HoverButton(
            top,
            hover="#3a4048",
            text="مسح",
            command=self.clear_files,
            bg="#32363c",
            fg=FG,
            activebackground="#3a4048",
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            font=self._font(9),
        ).pack(side="right", padx=(8, 0))
        HoverButton(
            top,
            hover=ACCENT_HOVER,
            text="إضافة ملفات…",
            command=self.add_files,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
            font=self._font(9, "bold"),
        ).pack(side="right")

        list_wrap = tk.Frame(files_box, bg=FIELD)
        list_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.listbox = tk.Listbox(
            list_wrap,
            bg=FIELD,
            fg=FG,
            selectbackground=ACCENT,
            selectforeground="white",
            relief="flat",
            highlightthickness=0,
            font=("Consolas", 10),
            height=6,
            activestyle="none",
        )
        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        out_box = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        out_box.pack(fill="x", padx=18, pady=(12, 0))
        tk.Label(out_box, text="مجلد الحفظ", bg=PANEL, fg=FG, font=self._font(11, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        row = tk.Frame(out_box, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 8))
        self.out_entry = tk.Entry(
            row,
            textvariable=self.output_var,
            bg=FIELD,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=self._font(10),
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        HoverButton(
            row,
            hover="#3a4048",
            text="استعراض…",
            command=self.pick_output,
            bg="#32363c",
            fg=FG,
            activebackground="#3a4048",
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            font=self._font(9),
        ).pack(side="right")

        opts = tk.Frame(out_box, bg=PANEL)
        opts.pack(fill="x", padx=12, pady=(0, 12))
        tk.Checkbutton(
            opts,
            text="تطبيع LuaQ (ملف Lua 5.1 قياسي)",
            variable=self.normalize,
            bg=PANEL,
            fg=FG,
            selectcolor=FIELD,
            activebackground=PANEL,
            activeforeground=FG,
            highlightthickness=0,
            font=self._font(10),
        ).pack(side="left")
        tk.Checkbutton(
            opts,
            text="حفظ ناتج RSA الخام أيضاً",
            variable=self.save_raw,
            bg=PANEL,
            fg=FG,
            selectcolor=FIELD,
            activebackground=PANEL,
            activeforeground=FG,
            highlightthickness=0,
            font=self._font(10),
        ).pack(side="left", padx=(16, 0))

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=18, pady=(14, 0))
        self.decrypt_btn = HoverButton(
            actions,
            hover=ACCENT_HOVER,
            text="Decrypt",
            command=self.start_decrypt,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=28,
            pady=10,
            cursor="hand2",
            font=self._font(12, "bold"),
        )
        self.decrypt_btn.pack(side="left")
        HoverButton(
            actions,
            hover="#3a4048",
            text="فتح مجلد الحفظ",
            command=self.open_output,
            bg="#32363c",
            fg=FG,
            activebackground="#3a4048",
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            font=self._font(10),
        ).pack(side="left", padx=(10, 0))
        self.status = tk.Label(actions, text="جاهز", bg=BG, fg=MUTED, font=self._font(10), anchor="e")
        self.status.pack(side="right", fill="x", expand=True)

        log_box = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True, padx=18, pady=14)
        tk.Label(log_box, text="السجل", bg=PANEL, fg=FG, font=self._font(11, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        log_wrap = tk.Frame(log_box, bg=FIELD)
        log_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log = tk.Text(
            log_wrap,
            bg=FIELD,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            highlightthickness=0,
            font=("Consolas", 10),
            wrap="word",
            state="disabled",
        )
        log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        self.log.tag_configure("ok", foreground=SUCCESS)
        self.log.tag_configure("err", foreground=ERROR)
        self.log.tag_configure("warn", foreground=WARN)
        self.log.tag_configure("muted", foreground=MUTED)

    def _warn_import(self) -> None:
        self._log("تعذر تحميل أداة الفك (المكتبة القياسية فقط، بدون pip):", "err")
        self._log(str(IMPORT_ERROR), "muted")
        messagebox.showerror("خطأ", f"تعذر تحميل أداة الفك:\n\n{IMPORT_ERROR}")

    def _log(self, text: str, tag: str | None = None) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, fg=color)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="اختر ملفات luac",
            filetypes=[
                ("MTA / Lua compiled", "*.luac *.lua *.mtasa"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        added = 0
        for raw in paths:
            path = Path(raw)
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", str(path))
                added += 1
        if added and not self.output_var.get().strip():
            self.output_var.set(str(self.files[0].parent / "decrypted"))
        self._log(f"تمت إضافة {added} ملف.", "ok")

    def clear_files(self) -> None:
        self.files.clear()
        self.listbox.delete(0, "end")
        self._log("تم مسح قائمة الملفات.", "muted")

    def pick_output(self) -> None:
        initial = self.output_var.get().strip() or os.getcwd()
        chosen = filedialog.askdirectory(title="مجلد الحفظ", initialdir=initial)
        if chosen:
            self.output_var.set(chosen)

    def open_output(self) -> None:
        dest = self._output_dir()
        if dest is None:
            messagebox.showinfo("مجلد الحفظ", "حدّد مجلد الحفظ أولاً.")
            return
        try:
            _open_folder(dest)
        except Exception as exc:
            messagebox.showerror("خطأ", str(exc))

    def _output_dir(self) -> Path | None:
        raw = self.output_var.get().strip()
        if raw:
            return Path(raw)
        if self.files:
            return self.files[0].parent / "decrypted"
        return None

    def start_decrypt(self) -> None:
        if self.busy:
            return
        if IMPORT_ERROR is not None:
            self._warn_import()
            return
        if not self.files:
            messagebox.showwarning("لا يوجد ملف", "أضف ملفاً واحداً على الأقل.")
            return
        if not self.save_raw.get() and not self.normalize.get():
            messagebox.showwarning("خيارات", "فعّل حفظ RSA أو تطبيع LuaQ على الأقل.")
            return
        dest = self._output_dir()
        if dest is None:
            messagebox.showwarning("مجلد الحفظ", "حدّد مجلد الحفظ.")
            return
        self.busy = True
        self.decrypt_btn.configure(state="disabled")
        self._set_status("جاري الفك…", WARN)
        threading.Thread(target=self._worker, args=(list(self.files), dest), daemon=True).start()

    def _worker(self, files: list[Path], dest: Path) -> None:
        ok = 0
        fail = 0
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.after(0, lambda: self._done(0, len(files), f"تعذر إنشاء المجلد: {exc}"))
            return
        for path in files:
            try:
                self.after(0, lambda p=path: self._log(f"\n── {p.name} ──"))
                saved = self._decrypt_one(path, dest)
                ok += 1
                self.after(0, lambda n=len(saved): self._log(f"تم حفظ {n} ملف.", "ok"))
            except Exception as exc:
                fail += 1
                msg = str(exc)
                self.after(0, lambda m=msg: self._log("فشل: " + m, "err"))
                self.after(0, lambda t=traceback.format_exc(): self._log(t, "muted"))
        self.after(0, lambda: self._done(ok, fail, str(dest)))

    def _decrypt_one(self, path: Path, dest: Path) -> list[Path]:
        data = path.read_bytes()
        self.after(0, lambda: self._log(f"الحجم: {len(data)} بايت  |  أول بايت: 0x{data[0]:02X}", "muted"))
        chunk, info = decrypt_mta_luac(data)
        checksum = "OK" if info.get("checksum_ok") else "MISMATCH"
        self.after(
            0,
            lambda: self._log(
                f"RSA: {len(chunk)} بايت  |  checksum {checksum}  |  header {chunk[:4]!r}",
                "ok",
            ),
        )
        written: list[Path] = []
        if self.save_raw.get():
            raw_path = dest / f"{path.stem}.decrypted.luac"
            raw_path.write_bytes(chunk)
            written.append(raw_path)
            self.after(0, lambda p=raw_path: self._log(f"RSA → {p}", "muted"))
        if self.normalize.get():
            normalized, stats = normalize_luaq(chunk)
            norm_path = dest / f"{path.stem}.normalized.luac"
            norm_path.write_bytes(normalized)
            written.append(norm_path)
            self.after(
                0,
                lambda s=stats, p=norm_path: self._log(
                    f"LuaQ {s} → {p}",
                    "ok",
                ),
            )
        return written

    def _done(self, ok: int, fail: int, dest: str) -> None:
        self.busy = False
        self.decrypt_btn.configure(state="normal")
        if fail:
            self._set_status(f"تم {ok} — فشل {fail}", ERROR)
            self._log(f"\nانتهى: نجح {ok} / فشل {fail}\nالمجلد: {dest}", "warn")
        else:
            self._set_status(f"تم فك {ok} ملف", SUCCESS)
            self._log(f"\nانتهى بنجاح. الملفات في:\n{dest}", "ok")
            messagebox.showinfo("تم", f"تم فك {ok} ملف.\n\n{dest}")


def main() -> int:
    _windows_dpi()
    app = DecryptApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
