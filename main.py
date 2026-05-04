import re
import tkinter as tk
from tkinter import ttk
import threading
import queue

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from db import preview_serial, activate_serial


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

SN_PATTERN = re.compile(r"^[A-Z0-9]{13}$")

result_queue = queue.Queue()


class SerialActivationGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Serial Activation")
        self.configure(bg=BG)

        W, H = 1300, 850
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H) // 2)
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.minsize(760, 520)
        self.resizable(True, True)

        self._running = False
        self._preview_after_id = None
        self._last_preview_sn = ""

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=0)
        self.columnconfigure(0, weight=1)

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        PAD = 36

        header = tk.Frame(self, bg=BG, pady=20)
        header.grid(row=0, column=0, sticky="ew", padx=PAD)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        tk.Label(
            header,
            text="Serial Activation",
            font=("Consolas", 30, "bold"),
            bg=BG,
            fg=TEXT,
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Enter a 13-character alphanumeric SN, then activate it",
            font=("Consolas", 11),
            bg=BG,
            fg=MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.status_var = tk.StringVar(value="Waiting")
        status_box = tk.Frame(
            header,
            bg=PANEL,
            padx=18,
            pady=10,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        status_box.grid(row=0, column=1, rowspan=2, sticky="e")

        tk.Label(
            status_box,
            text="STATUS",
            font=("Consolas", 9),
            bg=PANEL,
            fg=MUTED,
        ).grid(row=0, column=0, sticky="w")

        self.lbl_status = tk.Label(
            status_box,
            textvariable=self.status_var,
            font=("Consolas", 14, "bold"),
            bg=PANEL,
            fg=MUTED,
        )
        self.lbl_status.grid(row=1, column=0, sticky="w")

        tk.Frame(self, bg=BORDER, height=1).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=PAD,
        )

        form = tk.Frame(
            self,
            bg=PANEL,
            padx=30,
            pady=24,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        form.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(16, 0))
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
            wraplength=620,
        )
        self.lbl_message.grid(row=4, column=1, sticky="ew", pady=(14, 0))

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

        self.progress = ttk.Progressbar(
            self,
            style="g.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self.progress.grid(row=3, column=0, sticky="ew", padx=PAD, pady=(10, 0))

        btn_frame = tk.Frame(self, bg=BG, height=92)
        btn_frame.grid(row=4, column=0, sticky="ew", padx=PAD, pady=(6, 12))
        btn_frame.grid_propagate(False)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.rowconfigure(0, weight=1)

        self.btn_activate = tk.Button(
            btn_frame,
            text="ACTIVATE SERIAL",
            font=("Consolas", 15, "bold"),
            bg=GREEN,
            fg="#0d1117",
            activebackground=GREEN_H,
            activeforeground="#0d1117",
            bd=0,
            cursor="hand2",
            relief="flat",
            height=2,
            command=self._start_activation,
        )
        self.btn_activate.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(170, 170),
            pady=12,
        )

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
            entry.bind("<KeyRelease>", self._on_sn_key_release)

        return entry

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.lbl_status.config(fg=color)

    def _on_sn_key_release(self, event=None):
        value = self.sn_var.get()
        cleaned = "".join(ch.upper() for ch in value if ch.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

        if len(cleaned) > 13:
            cleaned = cleaned[:13]

        if value != cleaned:
            self.sn_var.set(cleaned)

        self._validate_sn_entered()

    def _validate_sn_entered(self):
        sn = self.sn_var.get().strip().upper()

        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None

        self._clear_result_fields()

        if not sn:
            self.message_var.set("Waiting for serial number...")
            self.lbl_message.config(fg=MUTED)
            self._set_status("Waiting", MUTED)
            self._last_preview_sn = ""
            return

        if len(sn) < 13:
            self.message_var.set("SN must be 13 alphanumeric characters.")
            self.lbl_message.config(fg=MUTED)
            self._set_status("Typing", MUTED)
            self._last_preview_sn = ""
            return

        if not SN_PATTERN.fullmatch(sn):
            self.message_var.set("SN must contain only letters and numbers.")
            self.lbl_message.config(fg=RED)
            self._set_status("Invalid", RED)
            self._last_preview_sn = ""
            return

        if sn == self._last_preview_sn:
            return

        # The old CHECK SERIAL procedure now runs automatically after SN validation.
        self._preview_after_id = self.after(450, lambda: self._start_auto_preview(sn))

    def _start_auto_preview(self, sn):
        if self._running:
            return

        self._running = True
        self._last_preview_sn = sn
        self._set_loading("Checking serial...")
        self._set_status("Checking", YELLOW)

        threading.Thread(
            target=self._run_preview,
            args=(sn,),
            daemon=True,
        ).start()

    def _run_preview(self, sn):
        result = preview_serial(sn)
        result_queue.put(("preview_result", result))

    def _validate_sn_before_activation(self):
        sn = self.sn_var.get().strip().upper()

        if not SN_PATTERN.fullmatch(sn):
            self.message_var.set("Serial number must be exactly 13 alphanumeric characters.")
            self.lbl_message.config(fg=RED)
            self._set_status("Invalid", RED)
            return None

        return sn

    def _clear_result_fields(self):
        self.days_var.set("")
        self.current_date_var.set("")
        self.expiry_date_var.set("")

    def _set_loading(self, text):
        self.btn_activate.config(state="disabled", bg=BORDER, fg=MUTED)
        self.message_var.set(text)
        self.lbl_message.config(fg=YELLOW)
        self.progress.start(12)

    def _reset_loading(self):
        self._running = False
        self.progress.stop()
        self.btn_activate.config(
            text="ACTIVATE SERIAL",
            state="normal",
            bg=GREEN,
            fg="#0d1117",
        )

    def _start_activation(self):
        if self._running:
            return

        sn = self._validate_sn_before_activation()
        if not sn:
            return

        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None

        self._running = True
        self.btn_activate.config(text="ACTIVATING...")
        self._set_loading("Activating serial and saving expiry date...")
        self._set_status("Activating", YELLOW)

        threading.Thread(
            target=self._run_activation,
            args=(sn,),
            daemon=True,
        ).start()

    def _run_activation(self, sn):
        result = activate_serial(sn)
        result_queue.put(("activation_result", result))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = result_queue.get_nowait()

                if kind == "preview_result":
                    self._finish_preview(payload)

                elif kind == "activation_result":
                    self._finish_activation(payload)

        except queue.Empty:
            pass

        finally:
            self.after(100, self._poll_queue)

    def _fill_result_fields(self, result):
        self.days_var.set(str(result.get("validity_days", "") or ""))
        self.current_date_var.set(str(result.get("current_date", "") or ""))
        self.expiry_date_var.set(str(result.get("expiry_date", "") or ""))
        self.message_var.set(result.get("message", ""))

    def _finish_preview(self, result):
        self._reset_loading()
        self._fill_result_fields(result)

        if result.get("success"):
            if result.get("already_used"):
                self.lbl_message.config(fg=YELLOW)
                self._set_status("Already used", YELLOW)
            else:
                self.lbl_message.config(fg=ACCENT)
                self._set_status("Ready", ACCENT)
        else:
            self.lbl_message.config(fg=RED)
            self._set_status("Failed", RED)

    def _finish_activation(self, result):
        self._reset_loading()
        self._fill_result_fields(result)

        if result.get("success"):
            self.lbl_message.config(fg=GREEN)
            self._set_status("Activated", GREEN)
        else:
            self.lbl_message.config(fg=RED)
            self._set_status("Failed", RED)


if __name__ == "__main__":
    app = SerialActivationGUI()
    app.mainloop()
