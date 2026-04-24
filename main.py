import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from db import get_db_name, get_server_name, get_serial_count, activate_serial


BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#21262d"
GREEN = "#2ea043"
GREEN_H = "#3fb950"
RED = "#da3633"
YELLOW = "#d29922"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
INPUT_BG = "#0a0e14"

log_queue = queue.Queue()


class SerialActivationGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AppSys Serial Activation")
        self.configure(bg=BG)

        W, H = 1200, 1150
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H) // 2)
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.minsize(1000, 700)
        self.resizable(True, True)

        self._running = False
        self._thread = None

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=0)
        self.rowconfigure(6, weight=0)
        self.columnconfigure(0, weight=1)

        self._build_ui()
        self._load_db_info()
        self._poll_queue()

    def _build_ui(self):
        PAD = 36

        header = tk.Frame(self, bg=BG, pady=20)
        header.grid(row=0, column=0, sticky="ew", padx=PAD)
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="AppSys Serial Activation",
            font=("Consolas", 30, "bold"),
            bg=BG,
            fg=TEXT,
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Enter a 13-digit SN to calculate and save its expiry date",
            font=("Consolas", 11),
            bg=BG,
            fg=MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        tk.Frame(self, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=PAD)

        info = tk.Frame(
            self,
            bg=PANEL,
            pady=14,
            padx=24,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        info.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(12, 0))
        for i in range(3):
            info.columnconfigure(i, weight=1)

        for col, lbl_text, attr, color in [
            (0, "DATABASE", "lbl_db", ACCENT),
            (1, "TOTAL SERIALS", "lbl_count", YELLOW),
            (2, "STATUS", "lbl_status", MUTED),
        ]:
            tk.Label(
                info,
                text=lbl_text,
                font=("Consolas", 9),
                bg=PANEL,
                fg=MUTED,
            ).grid(row=0, column=col, sticky="w")
            value = tk.Label(
                info,
                text="—",
                font=("Consolas", 15, "bold"),
                bg=PANEL,
                fg=color,
            )
            value.grid(row=1, column=col, sticky="w")
            setattr(self, attr, value)

        form = tk.Frame(
            self,
            bg=PANEL,
            padx=30,
            pady=24,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        form.grid(row=3, column=0, sticky="ew", padx=PAD, pady=(12, 0))
        form.columnconfigure(1, weight=1)

        self.sn_var = tk.StringVar()
        self.days_var = tk.StringVar()
        self.current_date_var = tk.StringVar()
        self.expiry_date_var = tk.StringVar()
        self.message_var = tk.StringVar(value="Waiting for serial number...")

        self._add_field(form, 0, "SERIAL #", self.sn_var, readonly=False)
        self._add_field(form, 1, "NB OF DAYS", self.days_var, readonly=True)
        self._add_field(form, 2, "CURRENT DATE", self.current_date_var, readonly=True)
        self._add_field(form, 3, "EXPIRY DATE", self.expiry_date_var, readonly=True)

        tk.Label(
            form,
            text="MESSAGE",
            font=("Consolas", 9),
            bg=PANEL,
            fg=MUTED,
        ).grid(row=4, column=0, sticky="nw", pady=(14, 0))

        self.lbl_message = tk.Label(
            form,
            textvariable=self.message_var,
            font=("Consolas", 12, "bold"),
            bg=PANEL,
            fg=MUTED,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.lbl_message.grid(row=4, column=1, sticky="ew", pady=(14, 0))

        tk.Label(
            self,
            text="",
            font=("Consolas", 9),
            bg=BG,
            fg=MUTED,
        ).grid(row=4, column=0, sticky="nw", padx=PAD, pady=(12, 3))

        self.log_box = scrolledtext.ScrolledText(
            self,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            font=("Consolas", 11),
            bd=0,
            relief="flat",
            wrap="word",
            state="disabled",
            highlightbackground=BORDER,
            highlightthickness=1,
            height=10,
        )
        self.log_box.grid(row=4, column=0, sticky="nsew", padx=PAD, pady=(30, 0))

        self.log_box.tag_config("ok", foreground=GREEN)
        self.log_box.tag_config("err", foreground=RED)
        self.log_box.tag_config("warn", foreground=YELLOW)
        self.log_box.tag_config("info", foreground=ACCENT)
        self.log_box.tag_config("dim", foreground=MUTED)
        self.log_box.tag_config("normal", foreground=TEXT)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "g.Horizontal.TProgressbar",
            troughcolor=PANEL,
            background=GREEN,
            darkcolor=GREEN,
            lightcolor=GREEN,
            bordercolor=BORDER,
            thickness=6,
        )
        self.progress = ttk.Progressbar(self, style="g.Horizontal.TProgressbar", mode="indeterminate")
        self.progress.grid(row=5, column=0, sticky="ew", padx=PAD, pady=(8, 0))

        btn_frame = tk.Frame(self, bg=BG, height=90)
        btn_frame.grid(row=6, column=0, sticky="ew", padx=PAD, pady=(6, 12))
        btn_frame.grid_propagate(False)
        btn_frame.pack_propagate(False)

        self.btn_activate = tk.Button(
            btn_frame,
            text="ACTIVATE SERIAL",
            font=("Consolas", 16, "bold"),
            bg=GREEN,
            fg="#0d1117",
            activebackground=GREEN_H,
            activeforeground="#0d1117",
            bd=0,
            cursor="hand2",
            relief="flat",
            width=38,
            height=2,
            command=self._start_activation,
        )
        self.btn_activate.place(relx=0.5, rely=0.5, anchor="center")

        self.bind("<Return>", lambda event: self._start_activation())

    def _add_field(self, parent, row, label, variable, readonly=False):
        tk.Label(
            parent,
            text=label,
            font=("Consolas", 9),
            bg=PANEL,
            fg=MUTED,
        ).grid(row=row, column=0, sticky="w", pady=9)

        entry = tk.Entry(
            parent,
            textvariable=variable,
            font=("Consolas", 14),
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            disabledbackground=INPUT_BG,
            disabledforeground=TEXT,
            readonlybackground=INPUT_BG,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            highlightthickness=1,
        )
        entry.grid(row=row, column=1, sticky="ew", pady=9, ipady=10)

        if readonly:
            entry.config(state="readonly")
        else:
            entry.focus_set()
            entry.bind("<KeyRelease>", self._limit_sn_length)

        return entry

    def _limit_sn_length(self, event=None):
        value = self.sn_var.get()
        digits_only = "".join(ch for ch in value if ch.isdigit())
        if len(digits_only) > 13:
            digits_only = digits_only[:13]
        if value != digits_only:
            self.sn_var.set(digits_only)

    def _load_db_info(self):
        try:
            db = get_db_name()
            server = get_server_name()
            count = get_serial_count()
            self.lbl_db.config(text=db, fg=ACCENT)
            self.lbl_count.config(text=str(count), fg=GREEN if count else MUTED)
            self.lbl_status.config(text="Ready", fg=MUTED)
            self._log(f"Connected to {server} / DB: {db} / {count} serial(s)", "info")
        except Exception as e:
            self.lbl_db.config(text="Config error", fg=RED)
            self.lbl_count.config(text="—", fg=RED)
            self.lbl_status.config(text="Error", fg=RED)
            self._log(f"Cannot connect/read config: {e}", "err")
            self.message_var.set("Database/config error. Check config.txt and SQL Server connection.")
            self.lbl_message.config(fg=RED)

    def _start_activation(self):
        if self._running:
            return

        sn = self.sn_var.get().strip()
        self.days_var.set("")
        self.current_date_var.set("")
        self.expiry_date_var.set("")

        if len(sn) != 13:
            self.message_var.set("Serial number must be exactly 13 digits.")
            self.lbl_message.config(fg=RED)
            self._log("Invalid SN: must be exactly 13 digits", "err")
            return

        self._running = True
        self.btn_activate.config(text="CHECKING…", state="disabled", bg=BORDER, fg=MUTED)
        self.lbl_status.config(text="In progress", fg=YELLOW)
        self.message_var.set("Checking serial number...")
        self.lbl_message.config(fg=YELLOW)
        self.progress.start(12)
        self._log("─" * 60, "dim")
        self._log(f"Checking SN: {sn}", "info")

        self._thread = threading.Thread(target=self._run_activation, args=(sn,), daemon=True)
        self._thread.start()

    def _run_activation(self, sn):
        result = activate_serial(sn)
        log_queue.put(("result", result))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = log_queue.get_nowait()
                if kind == "result":
                    self._finish_activation(payload)
                else:
                    tag = kind if kind in ("ok", "err", "warn", "info", "dim") else "normal"
                    self._log(str(payload), tag)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_queue)

    def _finish_activation(self, result):
        self._running = False
        self.progress.stop()
        self.btn_activate.config(text="ACTIVATE SERIAL", state="normal", bg=GREEN, fg="#0d1117")

        self.days_var.set(str(result.get("validity_days", "") or ""))
        self.current_date_var.set(str(result.get("current_date", "") or ""))
        self.expiry_date_var.set(str(result.get("expiry_date", "") or ""))
        self.message_var.set(result.get("message", ""))

        if result.get("success"):
            self.lbl_status.config(text="Done ✓", fg=GREEN)
            self.lbl_message.config(fg=GREEN)
            self._log(result.get("message"), "ok")
            self._log(f"ExpiryDate saved: {result.get('expiry_date')}", "ok")
        else:
            self.lbl_status.config(text="Failed ✗", fg=RED)
            self.lbl_message.config(fg=RED)
            self._log(result.get("message"), "err")

        # Refresh serial count / DB status after each operation.
        try:
            count = get_serial_count()
            self.lbl_count.config(text=str(count), fg=GREEN if count else MUTED)
        except Exception:
            pass

    def _log(self, text, tag="normal"):
        ts = time.strftime("%H:%M:%S")
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{ts}]  ", "dim")
        self.log_box.insert("end", str(text) + "\n", tag)
        self.log_box.config(state="disabled")
        self.log_box.see("end")


if __name__ == "__main__":
    app = SerialActivationGUI()
    app.mainloop()
