"""
password_generator.py
=====================
Password Generator — Enhanced Edition
Features: zxcvbn-style strength, animated bar, password history,
keyboard shortcuts, PIN/pattern mode, named profiles, QR export.

Dependencies: Pillow (PIL) — install with: pip install pillow
Bundled:      strength_scorer.py, qr_generator.py (no extra pip needed)

Run: python password_generator.py
"""

import random
import secrets
import string
import json
import math
import pathlib
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime

# ── Bundled modules (same directory) ─────────────────────────────────────────
from strength_scorer import score_password
from qr_generator import make_qr_image

try:
    from PIL import ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
APP_VERSION   = "2.0"
PROFILES_PATH = pathlib.Path.home() / ".pwgen_profiles.json"
HISTORY_LIMIT = 50

LIGHT = {
    "bg":         "#F4F6F8", "card":       "#FFFFFF",
    "accent":     "#4A90D9", "accent_dk":  "#357ABD",
    "fg":         "#2C3E50", "fg_sub":     "#7F8C8D",
    "entry_bg":   "#FFFFFF", "entry_fg":   "#2C3E50",
    "border":     "#D5DCE3",
    "bar0": "#E74C3C", "bar1": "#E67E22", "bar2": "#F1C40F",
    "bar3": "#27AE60", "bar4": "#1ABC9C",
    "btn_green":  "#27AE60", "btn_purple": "#8E44AD",
    "btn_gray":   "#7F8C8D", "btn_orange": "#E67E22",
    "tab_sel":    "#FFFFFF", "tab_bg":     "#E8ECF0",
}
DARK = {
    "bg":         "#1A1D23", "card":       "#23272F",
    "accent":     "#5B9BD5", "accent_dk":  "#4A7FB5",
    "fg":         "#ECF0F1", "fg_sub":     "#95A5A6",
    "entry_bg":   "#2C3140", "entry_fg":   "#ECF0F1",
    "border":     "#3A3F4B",
    "bar0": "#C0392B", "bar1": "#D35400", "bar2": "#D4AC0D",
    "bar3": "#1E8449", "bar4": "#17A589",
    "btn_green":  "#1E8449", "btn_purple": "#7D3C98",
    "btn_gray":   "#636E72", "btn_orange": "#CA6F1E",
    "tab_sel":    "#2C3140", "tab_bg":     "#1A1D23",
}

# Pattern template reference
PATTERN_CHARS = {
    "A": string.ascii_uppercase,
    "a": string.ascii_lowercase,
    "0": string.digits,
    "!": "!@#$%^&*",
    "*": string.ascii_letters + string.digits + "!@#$%^&*",
    "#": string.digits,
}

DEFAULT_PROFILES = {
    "Default (Strong)": {"length": 16, "upper": True,  "lower": True,  "digits": True,  "symbols": True,  "exclude_ambiguous": False},
    "Wi-Fi Password":   {"length": 20, "upper": True,  "lower": True,  "digits": True,  "symbols": False, "exclude_ambiguous": True},
    "PIN (6-digit)":    {"length": 6,  "upper": False, "lower": False, "digits": True,  "symbols": False, "exclude_ambiguous": False, "mode": "pin"},
    "Simple / Shared":  {"length": 10, "upper": True,  "lower": True,  "digits": True,  "symbols": False, "exclude_ambiguous": True},
}


# ─────────────────────────────────────────────────────────────────────────────
#  PURE GENERATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────
AMBIGUOUS = set("0O1lI5S")


def build_charset(upper, lower, digits, symbols, exclude_ambiguous=False):
    charset = ""
    if upper:   charset += string.ascii_uppercase
    if lower:   charset += string.ascii_lowercase
    if digits:  charset += string.digits
    if symbols: charset += "!@#$%^&*"
    if exclude_ambiguous:
        charset = "".join(c for c in charset if c not in AMBIGUOUS)
    return charset


def generate_password(length, upper, lower, digits, symbols, exclude_ambiguous=False):
    """Generate a secure password guaranteeing one char from each selected group."""
    charset = build_charset(upper, lower, digits, symbols, exclude_ambiguous)
    if not charset:
        return None
    guaranteed = []
    pool_upper   = "".join(c for c in string.ascii_uppercase if not exclude_ambiguous or c not in AMBIGUOUS)
    pool_lower   = "".join(c for c in string.ascii_lowercase if not exclude_ambiguous or c not in AMBIGUOUS)
    pool_digits  = "".join(c for c in string.digits          if not exclude_ambiguous or c not in AMBIGUOUS)
    pool_symbols = "!@#$%^&*"
    if upper   and pool_upper:   guaranteed.append(secrets.choice(pool_upper))
    if lower   and pool_lower:   guaranteed.append(secrets.choice(pool_lower))
    if digits  and pool_digits:  guaranteed.append(secrets.choice(pool_digits))
    if symbols:                  guaranteed.append(secrets.choice(pool_symbols))
    remaining = [secrets.choice(charset) for _ in range(max(0, length - len(guaranteed)))]
    pw_list = guaranteed + remaining
    random.shuffle(pw_list)
    return "".join(pw_list)


def generate_pin(length):
    """Generate a numeric PIN."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_from_pattern(pattern):
    """
    Generate a password from a template string.
    A = uppercase, a = lowercase, 0/#= digit, ! = symbol, * = any
    Any other character is used literally.
    """
    result = []
    for ch in pattern:
        pool = PATTERN_CHARS.get(ch)
        if pool:
            result.append(secrets.choice(pool))
        else:
            result.append(ch)
    return "".join(result)


# ─────────────────────────────────────────────────────────────────────────────
#  PROFILE PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────
def load_profiles():
    data = dict(DEFAULT_PROFILES)
    try:
        if PROFILES_PATH.exists():
            saved = json.loads(PROFILES_PATH.read_text())
            data.update(saved)
    except Exception:
        pass
    return data


def save_profiles(profiles):
    # Only save user-added (non-default) profiles
    user = {k: v for k, v in profiles.items() if k not in DEFAULT_PROFILES}
    try:
        PROFILES_PATH.write_text(json.dumps(user, indent=2))
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class PasswordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Password Generator v{APP_VERSION}")
        self.root.resizable(False, False)

        # ── State ────────────────────────────────────────────────────────────
        self.dark_mode       = tk.BooleanVar(value=False)
        self.pw_length       = tk.IntVar(value=16)
        self.use_upper       = tk.BooleanVar(value=True)
        self.use_lower       = tk.BooleanVar(value=True)
        self.use_digits      = tk.BooleanVar(value=True)
        self.use_symbols     = tk.BooleanVar(value=True)
        self.excl_ambiguous  = tk.BooleanVar(value=False)
        self.num_passwords   = tk.IntVar(value=1)
        self.show_password   = tk.BooleanVar(value=True)
        self.pin_length      = tk.IntVar(value=6)
        self.pattern_var     = tk.StringVar(value="Aaa000!")
        self.current_theme   = LIGHT
        self.profiles        = load_profiles()
        self.history         = []           # list of str
        self._last_passwords = []
        self._bar_target     = 0.0
        self._bar_current    = 0.0

        self._build_ui()
        self._apply_theme()
        self._bind_shortcuts()

    # =========================================================================
    #  UI CONSTRUCTION
    # =========================================================================
    def _build_ui(self):
        root = self.root

        # ── Top bar ──────────────────────────────────────────────────────────
        self.top_bar = tk.Frame(root)
        self.top_bar.pack(fill="x", padx=18, pady=(14, 0))

        self.title_lbl = tk.Label(self.top_bar, text="🔑  Password Generator",
                                   font=("Segoe UI", 17, "bold"))
        self.title_lbl.pack(side="left")

        self.dark_btn = tk.Button(self.top_bar, text="🌙 Dark",
                                   font=("Segoe UI", 9), relief="flat", bd=0,
                                   padx=9, pady=3, cursor="hand2",
                                   command=self._toggle_dark)
        self.dark_btn.pack(side="right", padx=2)

        # ── Notebook (tabs) ──────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=14, pady=10)

        self.tab_pw  = tk.Frame(self.nb)   # Password tab
        self.tab_pin = tk.Frame(self.nb)   # PIN / Pattern tab
        self.tab_his = tk.Frame(self.nb)   # History tab
        self.tab_pro = tk.Frame(self.nb)   # Profiles tab

        self.nb.add(self.tab_pw,  text="  Password  ")
        self.nb.add(self.tab_pin, text="  PIN / Pattern  ")
        self.nb.add(self.tab_his, text="  History  ")
        self.nb.add(self.tab_pro, text="  Profiles  ")

        self._build_password_tab()
        self._build_pin_tab()
        self._build_history_tab()
        self._build_profiles_tab()

        root.update_idletasks()
        root.geometry(f"520x{root.winfo_reqheight() + 20}")

    # ── PASSWORD TAB ─────────────────────────────────────────────────────────
    def _build_password_tab(self):
        p = self.tab_pw
        pad = {"padx": 16, "pady": 0}

        # Length
        f_len = tk.Frame(p)
        f_len.pack(fill="x", padx=16, pady=(12, 6))
        tk.Label(f_len, text="Password Length", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        row = tk.Frame(f_len)
        row.pack(fill="x", pady=(4, 0))
        self.len_slider = tk.Scale(row, from_=4, to=64, orient="horizontal",
                                    variable=self.pw_length, showvalue=False, length=380,
                                    command=lambda _: self.len_lbl.config(text=str(self.pw_length.get())))
        self.len_slider.pack(side="left")
        self.len_lbl = tk.Label(row, text=str(self.pw_length.get()),
                                 font=("Segoe UI", 11, "bold"), width=3)
        self.len_lbl.pack(side="left", padx=(8, 0))

        # Char options
        self.char_frame = tk.LabelFrame(p, text="  Character Types  ",
                                         font=("Segoe UI", 9), padx=10, pady=6)
        self.char_frame.pack(fill="x", padx=16, pady=(0, 6))
        self.checkboxes = []
        options = [
            ("Uppercase  (A–Z)",   self.use_upper),
            ("Lowercase  (a–z)",   self.use_lower),
            ("Numbers  (0–9)",     self.use_digits),
            ("Symbols  (!@#$%^&*)", self.use_symbols),
        ]
        for i, (label, var) in enumerate(options):
            cb = tk.Checkbutton(self.char_frame, text=label, variable=var,
                                 font=("Segoe UI", 9), anchor="w")
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=2)
            self.checkboxes.append(cb)
        self.excl_cb = tk.Checkbutton(self.char_frame,
                                       text="Exclude ambiguous chars  (0, O, 1, l, I…)",
                                       variable=self.excl_ambiguous,
                                       font=("Segoe UI", 9), anchor="w")
        self.excl_cb.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # Quantity
        f_qty = tk.Frame(p)
        f_qty.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(f_qty, text="How many to generate (1–20):",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.qty_entry = tk.Entry(f_qty, textvariable=self.num_passwords,
                                   width=4, font=("Segoe UI", 10), justify="center")
        self.qty_entry.pack(side="left", padx=(10, 0))

        # Generate button
        self.gen_btn = tk.Button(p, text="⚡  Generate Password  (Enter)",
                                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                                  padx=14, pady=7, cursor="hand2",
                                  command=self._on_generate)
        self.gen_btn.pack(fill="x", padx=16, pady=(0, 8))

        # Password display + eye
        f_pw = tk.Frame(p)
        f_pw.pack(fill="x", padx=16, pady=(0, 4))
        self.pw_entry = tk.Entry(f_pw, font=("Courier New", 13),
                                  state="readonly", justify="center",
                                  relief="flat", bd=0)
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.eye_btn = tk.Button(f_pw, text="👁", font=("Segoe UI", 10),
                                  relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
                                  command=self._toggle_show)
        self.eye_btn.pack(side="left")

        # ── Animated strength bar ────────────────────────────────────────────
        f_bar = tk.Frame(p)
        f_bar.pack(fill="x", padx=16, pady=(2, 2))
        self.bar_canvas = tk.Canvas(f_bar, height=10, bd=0, highlightthickness=0)
        self.bar_canvas.pack(fill="x")

        # Strength labels row
        f_str = tk.Frame(p)
        f_str.pack(fill="x", padx=16, pady=(2, 2))
        tk.Label(f_str, text="Strength:", font=("Segoe UI", 9)).pack(side="left")
        self.strength_lbl = tk.Label(f_str, text="—", font=("Segoe UI", 9, "bold"), width=12)
        self.strength_lbl.pack(side="left", padx=(4, 16))
        self.entropy_lbl = tk.Label(f_str, text="Entropy: —", font=("Segoe UI", 9))
        self.entropy_lbl.pack(side="left")
        self.crack_lbl = tk.Label(f_str, text="", font=("Segoe UI", 9))
        self.crack_lbl.pack(side="left", padx=(12, 0))

        # Suggestions
        self.suggest_lbl = tk.Label(p, text="", font=("Segoe UI", 8),
                                     wraplength=460, justify="left")
        self.suggest_lbl.pack(fill="x", padx=16, pady=(0, 4))

        # Action buttons row
        f_act = tk.Frame(p)
        f_act.pack(fill="x", padx=16, pady=(0, 4))
        self.copy_btn = tk.Button(f_act, text="📋  Copy  (Ctrl+C)",
                                   font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                                   padx=10, pady=5, cursor="hand2", command=self._copy)
        self.copy_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.save_btn = tk.Button(f_act, text="💾  Save  (Ctrl+S)",
                                   font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                                   padx=10, pady=5, cursor="hand2", command=self._save)
        self.save_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.qr_btn = tk.Button(f_act, text="🔲  QR Code",
                                 font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                                 padx=10, pady=5, cursor="hand2", command=self._show_qr)
        self.qr_btn.pack(side="left", fill="x", expand=True)

        self.copy_msg = tk.Label(p, text="", font=("Segoe UI", 8))
        self.copy_msg.pack(pady=(0, 2))

        # Multi-output area
        self.multi_frame = tk.Frame(p)
        f_multi_lbl = tk.Frame(self.multi_frame)
        f_multi_lbl.pack(fill="x")
        self.multi_lbl = tk.Label(f_multi_lbl, text="All generated passwords",
                                   font=("Segoe UI", 9, "bold"), anchor="w")
        self.multi_lbl.pack(side="left")
        f_multi_txt = tk.Frame(self.multi_frame)
        f_multi_txt.pack(fill="both", expand=True)
        multi_sb = tk.Scrollbar(f_multi_txt)
        multi_sb.pack(side="right", fill="y")
        self.multi_text = tk.Text(f_multi_txt, font=("Courier New", 10),
                                   state="disabled", height=4, relief="flat",
                                   bd=0, yscrollcommand=multi_sb.set, wrap="none")
        self.multi_text.pack(side="left", fill="both", expand=True)
        multi_sb.config(command=self.multi_text.yview)

    # ── PIN / PATTERN TAB ────────────────────────────────────────────────────
    def _build_pin_tab(self):
        p = self.tab_pin

        # PIN section
        self.pin_frame = tk.LabelFrame(p, text="  Numeric PIN  ",
                                        font=("Segoe UI", 9), padx=12, pady=8)
        self.pin_frame.pack(fill="x", padx=16, pady=(14, 8))

        f1 = tk.Frame(self.pin_frame)
        f1.pack(fill="x")
        tk.Label(f1, text="PIN Length:", font=("Segoe UI", 10)).pack(side="left")
        self.pin_slider = tk.Scale(f1, from_=4, to=12, orient="horizontal",
                                    variable=self.pin_length, showvalue=False, length=280,
                                    command=lambda _: self.pin_len_lbl.config(text=str(self.pin_length.get())))
        self.pin_slider.pack(side="left", padx=(10, 0))
        self.pin_len_lbl = tk.Label(f1, text=str(self.pin_length.get()),
                                     font=("Segoe UI", 11, "bold"), width=3)
        self.pin_len_lbl.pack(side="left", padx=(6, 0))

        self.pin_gen_btn = tk.Button(self.pin_frame, text="⚡  Generate PIN",
                                      font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                                      padx=12, pady=6, cursor="hand2", command=self._gen_pin)
        self.pin_gen_btn.pack(fill="x", pady=(8, 4))

        self.pin_entry = tk.Entry(self.pin_frame, font=("Courier New", 16),
                                   state="readonly", justify="center", relief="flat", bd=0)
        self.pin_entry.pack(fill="x", ipady=6)

        f_pin_btns = tk.Frame(self.pin_frame)
        f_pin_btns.pack(fill="x", pady=(6, 0))
        tk.Button(f_pin_btns, text="📋 Copy PIN", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=lambda: self._copy_widget(self.pin_entry)).pack(side="left", padx=(0, 6))
        tk.Button(f_pin_btns, text="🔲 QR", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=lambda: self._qr_from_entry(self.pin_entry)).pack(side="left")

        # Pattern section
        self.pat_frame = tk.LabelFrame(p, text="  Pattern Template  ",
                                        font=("Segoe UI", 9), padx=12, pady=8)
        self.pat_frame.pack(fill="x", padx=16, pady=(0, 8))

        legend = tk.Label(self.pat_frame,
                           text="A=uppercase  a=lowercase  0/#=digit  !=symbol  *=any  other=literal",
                           font=("Segoe UI", 8), anchor="w")
        legend.pack(fill="x", pady=(0, 6))
        self.pat_legend = legend

        f_pat = tk.Frame(self.pat_frame)
        f_pat.pack(fill="x")
        tk.Label(f_pat, text="Template:", font=("Segoe UI", 10)).pack(side="left")
        self.pat_entry_input = tk.Entry(f_pat, textvariable=self.pattern_var,
                                         width=22, font=("Courier New", 11))
        self.pat_entry_input.pack(side="left", padx=(8, 0))

        self.pat_gen_btn = tk.Button(self.pat_frame, text="⚡  Generate from Pattern",
                                      font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                                      padx=12, pady=6, cursor="hand2", command=self._gen_pattern)
        self.pat_gen_btn.pack(fill="x", pady=(8, 4))

        self.pat_result_entry = tk.Entry(self.pat_frame, font=("Courier New", 14),
                                          state="readonly", justify="center", relief="flat", bd=0)
        self.pat_result_entry.pack(fill="x", ipady=5)

        f_pat_btns = tk.Frame(self.pat_frame)
        f_pat_btns.pack(fill="x", pady=(6, 0))
        tk.Button(f_pat_btns, text="📋 Copy", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=lambda: self._copy_widget(self.pat_result_entry)).pack(side="left", padx=(0, 6))
        tk.Button(f_pat_btns, text="🔲 QR", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=lambda: self._qr_from_entry(self.pat_result_entry)).pack(side="left")

        # Store for theming
        self._pin_tab_btns = [self.pin_gen_btn, self.pat_gen_btn]

    # ── HISTORY TAB ──────────────────────────────────────────────────────────
    def _build_history_tab(self):
        p = self.tab_his

        top = tk.Frame(p)
        top.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(top, text="Session history  (last 50)",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.clear_hist_btn = tk.Button(top, text="Clear", font=("Segoe UI", 9),
                                         relief="flat", bd=0, padx=8, pady=3,
                                         cursor="hand2", command=self._clear_history)
        self.clear_hist_btn.pack(side="right")

        f = tk.Frame(p)
        f.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        sb = tk.Scrollbar(f)
        sb.pack(side="right", fill="y")
        self.hist_text = tk.Text(f, font=("Courier New", 10), state="disabled",
                                  relief="flat", bd=0, yscrollcommand=sb.set, wrap="none")
        self.hist_text.pack(side="left", fill="both", expand=True)
        sb.config(command=self.hist_text.yview)

        tk.Label(p, text="Tip: Right-click a line to copy it.",
                 font=("Segoe UI", 8)).pack(pady=(0, 6))

    # ── PROFILES TAB ─────────────────────────────────────────────────────────
    def _build_profiles_tab(self):
        p = self.tab_pro

        tk.Label(p, text="Named presets — save your favourite settings",
                 font=("Segoe UI", 9)).pack(padx=16, pady=(10, 4), anchor="w")

        # Profile list + action buttons
        f_list = tk.Frame(p)
        f_list.pack(fill="x", padx=16, pady=(0, 6))

        self.profile_lb = tk.Listbox(f_list, font=("Segoe UI", 10), height=7,
                                      selectmode="single", relief="flat", bd=1,
                                      activestyle="none", exportselection=False)
        self.profile_lb.pack(side="left", fill="both", expand=True)
        sb2 = tk.Scrollbar(f_list)
        sb2.pack(side="right", fill="y")
        self.profile_lb.config(yscrollcommand=sb2.set)
        sb2.config(command=self.profile_lb.yview)
        self._refresh_profile_list()

        f_btns = tk.Frame(p)
        f_btns.pack(fill="x", padx=16, pady=(0, 10))

        self.load_profile_btn = tk.Button(f_btns, text="⬇  Load",
                                           font=("Segoe UI", 9, "bold"), relief="flat",
                                           bd=0, padx=12, pady=5, cursor="hand2",
                                           command=self._load_profile)
        self.load_profile_btn.pack(side="left", padx=(0, 6))

        self.save_profile_btn = tk.Button(f_btns, text="💾  Save current settings",
                                           font=("Segoe UI", 9, "bold"), relief="flat",
                                           bd=0, padx=12, pady=5, cursor="hand2",
                                           command=self._save_profile_dialog)
        self.save_profile_btn.pack(side="left", padx=(0, 6))

        self.del_profile_btn = tk.Button(f_btns, text="🗑  Delete",
                                          font=("Segoe UI", 9, "bold"), relief="flat",
                                          bd=0, padx=12, pady=5, cursor="hand2",
                                          command=self._delete_profile)
        self.del_profile_btn.pack(side="left")

        # Profile detail preview
        self.profile_detail = tk.Label(p, text="", font=("Segoe UI", 9),
                                        justify="left", anchor="w")
        self.profile_detail.pack(fill="x", padx=16, pady=(0, 6))
        self.profile_lb.bind("<<ListboxSelect>>", self._preview_profile)

    # =========================================================================
    #  THEME
    # =========================================================================
    def _apply_theme(self):
        t = self.current_theme
        r = self.root

        r.configure(bg=t["bg"])
        self.top_bar.configure(bg=t["bg"])
        self.title_lbl.configure(bg=t["bg"], fg=t["fg"])
        self.dark_btn.configure(bg=t["btn_gray"], fg="#fff",
                                 activebackground=t["btn_gray"], activeforeground="#fff")

        # Notebook style
        style = ttk.Style()
        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=t["tab_bg"], foreground=t["fg"],
                        padding=[10, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", t["tab_sel"])],
                  foreground=[("selected", t["accent"])])

        for tab in (self.tab_pw, self.tab_pin, self.tab_his, self.tab_pro):
            tab.configure(bg=t["bg"])
            self._theme_children(tab, t)

        # Specific widgets
        self.len_slider.configure(bg=t["bg"], troughcolor=t["border"],
                                   activebackground=t["accent"])
        self.len_lbl.configure(bg=t["bg"], fg=t["accent"])
        self.char_frame.configure(bg=t["card"], fg=t["fg_sub"])
        for cb in self.checkboxes + [self.excl_cb]:
            cb.configure(bg=t["card"], fg=t["fg"], selectcolor=t["card"],
                          activebackground=t["card"], activeforeground=t["fg"])

        for entry in (self.pw_entry, self.qty_entry,
                      self.pin_entry, self.pat_entry_input, self.pat_result_entry):
            try:
                entry.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                 insertbackground=t["fg"],
                                 readonlybackground=t["entry_bg"],
                                 highlightthickness=1,
                                 highlightbackground=t["border"],
                                 highlightcolor=t["accent"])
            except tk.TclError:
                pass

        self.gen_btn.configure(bg=t["accent"], fg="#fff",
                                activebackground=t["accent_dk"], activeforeground="#fff")
        self.copy_btn.configure(bg=t["btn_green"], fg="#fff",
                                 activebackground=t["btn_green"], activeforeground="#fff")
        self.save_btn.configure(bg=t["btn_purple"], fg="#fff",
                                 activebackground=t["btn_purple"], activeforeground="#fff")
        self.qr_btn.configure(bg=t["btn_orange"], fg="#fff",
                               activebackground=t["btn_orange"], activeforeground="#fff")

        self.eye_btn.configure(bg=t["bg"], fg=t["fg_sub"],
                                activebackground=t["bg"], activeforeground=t["fg"])
        self.strength_lbl.configure(bg=t["bg"], fg=t["fg"])
        self.entropy_lbl.configure(bg=t["bg"], fg=t["fg_sub"])
        self.crack_lbl.configure(bg=t["bg"], fg=t["fg_sub"])
        self.suggest_lbl.configure(bg=t["bg"], fg=t["fg_sub"])
        self.copy_msg.configure(bg=t["bg"], fg=t["btn_green"])

        self.bar_canvas.configure(bg=t["bg"])

        self.multi_frame.configure(bg=t["bg"])
        self.multi_lbl.configure(bg=t["bg"], fg=t["fg"])
        self.multi_text.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                   selectbackground=t["accent"])

        self.hist_text.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                  selectbackground=t["accent"])
        self.clear_hist_btn.configure(bg=t["btn_gray"], fg="#fff",
                                       activebackground=t["btn_gray"], activeforeground="#fff")

        self.pin_slider.configure(bg=t["bg"], troughcolor=t["border"],
                                   activebackground=t["accent"])
        self.pin_len_lbl.configure(bg=t["bg"], fg=t["accent"])
        self.pin_frame.configure(bg=t["bg"], fg=t["fg_sub"])
        self.pat_frame.configure(bg=t["bg"], fg=t["fg_sub"])
        self.pat_legend.configure(bg=t["bg"], fg=t["fg_sub"])

        for btn in self._pin_tab_btns:
            btn.configure(bg=t["accent"], fg="#fff",
                           activebackground=t["accent_dk"], activeforeground="#fff")

        self.profile_lb.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                   selectbackground=t["accent"],
                                   selectforeground="#fff")
        self.load_profile_btn.configure(bg=t["btn_green"], fg="#fff",
                                         activebackground=t["btn_green"], activeforeground="#fff")
        self.save_profile_btn.configure(bg=t["accent"], fg="#fff",
                                         activebackground=t["accent_dk"], activeforeground="#fff")
        self.del_profile_btn.configure(bg=t["bar0"], fg="#fff",
                                        activebackground=t["bar0"], activeforeground="#fff")
        self.profile_detail.configure(bg=t["bg"], fg=t["fg_sub"])

    def _theme_children(self, widget, t):
        cls = widget.__class__.__name__
        try:
            if cls == "Frame":
                widget.configure(bg=t["bg"])
            elif cls == "Label":
                widget.configure(bg=t["bg"], fg=t["fg"])
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._theme_children(child, t)

    def _toggle_dark(self):
        if self.dark_mode.get():
            self.dark_mode.set(False)
            self.current_theme = LIGHT
            self.dark_btn.config(text="🌙 Dark")
        else:
            self.dark_mode.set(True)
            self.current_theme = DARK
            self.dark_btn.config(text="☀️ Light")
        self._apply_theme()

    # =========================================================================
    #  KEYBOARD SHORTCUTS
    # =========================================================================
    def _bind_shortcuts(self):
        r = self.root
        r.bind("<Return>",      lambda e: self._on_generate())
        r.bind("<Control-c>",   lambda e: self._copy())
        r.bind("<Control-s>",   lambda e: self._save())
        r.bind("<Control-d>",   lambda e: self._toggle_dark())
        r.bind("<Control-h>",   lambda e: self._toggle_show())
        r.bind("<Control-q>",   lambda e: self._show_qr())
        r.bind("<Control-n>",   lambda e: self._on_generate())

    # =========================================================================
    #  PASSWORD GENERATION
    # =========================================================================
    def _validate(self):
        if not any([self.use_upper.get(), self.use_lower.get(),
                    self.use_digits.get(), self.use_symbols.get()]):
            messagebox.showerror("No Character Type",
                                 "Please select at least one character type.")
            return 0, False
        try:
            n = int(self.qty_entry.get())
            if not (1 <= n <= 20):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Count",
                                 "Number of passwords must be between 1 and 20.")
            return 0, False
        return n, True

    def _on_generate(self):
        # Only act if on the password tab
        if self.nb.index(self.nb.select()) != 0:
            return
        n, ok = self._validate()
        if not ok:
            return
        length = self.pw_length.get()
        uu, ul, ud, us = (self.use_upper.get(), self.use_lower.get(),
                          self.use_digits.get(), self.use_symbols.get())
        ea = self.excl_ambiguous.get()
        passwords = [generate_password(length, uu, ul, ud, us, ea) for _ in range(n)]
        if any(p is None for p in passwords):
            messagebox.showerror("Error", "Generation failed. Check settings.")
            return
        self._set_entry(passwords[0])
        self._update_strength(passwords[0])
        self._last_passwords = passwords
        self._add_to_history(passwords)
        self.copy_msg.config(text="")

        if n > 1:
            self.multi_frame.pack(fill="both", padx=16, pady=(0, 8))
            self.multi_text.configure(state="normal")
            self.multi_text.delete("1.0", tk.END)
            for i, pw in enumerate(passwords, 1):
                self.multi_text.insert(tk.END, f"{i:>3}. {pw}\n")
            self.multi_text.configure(state="disabled")
        else:
            self.multi_frame.pack_forget()

    def _set_entry(self, text):
        self.pw_entry.configure(state="normal")
        self.pw_entry.delete(0, tk.END)
        self.pw_entry.insert(0, text)
        self.pw_entry.configure(state="readonly",
                                 show="" if self.show_password.get() else "•")

    def _toggle_show(self):
        self.show_password.set(not self.show_password.get())
        self.pw_entry.configure(show="" if self.show_password.get() else "•")
        self.eye_btn.config(text="👁" if self.show_password.get() else "🙈")

    # =========================================================================
    #  ANIMATED STRENGTH BAR
    # =========================================================================
    def _update_strength(self, password):
        result = score_password(password)
        t = self.current_theme
        bar_colors = [t["bar0"], t["bar1"], t["bar2"], t["bar3"], t["bar4"]]
        score = result["score"]

        self.strength_lbl.config(text=result["label"], fg=bar_colors[score])
        self.entropy_lbl.config(text=f"Entropy: {result['entropy']} bits")
        self.crack_lbl.config(text=f"⏱ {result['crack_time']} to crack")

        if result["suggestions"]:
            self.suggest_lbl.config(text="💡 " + "  ·  ".join(result["suggestions"]))
        else:
            self.suggest_lbl.config(text="✅ Excellent password!")

        # Animate bar
        self._bar_color  = bar_colors[score]
        self._bar_target = result["bar_fraction"]
        self._bar_current = 0.0
        self._animate_bar()

    def _animate_bar(self):
        if self._bar_current >= self._bar_target:
            return
        step = max(0.03, (self._bar_target - self._bar_current) * 0.18)
        self._bar_current = min(self._bar_target, self._bar_current + step)
        self._draw_bar(self._bar_current, self._bar_color)
        if self._bar_current < self._bar_target:
            self.root.after(16, self._animate_bar)

    def _draw_bar(self, fraction, color):
        c = self.bar_canvas
        c.update_idletasks()
        w = c.winfo_width()
        h = c.winfo_height() or 10
        c.delete("all")
        t = self.current_theme
        # Background track
        c.create_rectangle(0, 0, w, h, fill=t["border"], outline="")
        # Filled portion
        filled = int(w * fraction)
        if filled > 0:
            c.create_rectangle(0, 0, filled, h, fill=color, outline="")

    # =========================================================================
    #  COPY / SAVE
    # =========================================================================
    def _copy(self):
        pw = self.pw_entry.get()
        if not pw:
            messagebox.showwarning("Nothing to Copy", "Generate a password first.")
            return
        self._clipboard_set(pw)
        self.copy_msg.config(text="✅  Copied to clipboard!")
        self.root.after(3000, lambda: self.copy_msg.config(text=""))

    def _clipboard_set(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def _copy_widget(self, entry_widget):
        val = entry_widget.get()
        if not val:
            messagebox.showwarning("Nothing to Copy", "Generate first.")
            return
        self._clipboard_set(val)
        messagebox.showinfo("Copied", "Copied to clipboard!")

    def _save(self):
        passwords = self._last_passwords
        if not passwords:
            messagebox.showwarning("Nothing to Save", "Generate passwords first.")
            return
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp  = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"passwords_{ts}.txt",
            title="Save Passwords")
        if not fp:
            return
        try:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Length: {self.pw_length.get()}  Upper: {self.use_upper.get()}  "
                        f"Lower: {self.use_lower.get()}  Digits: {self.use_digits.get()}  "
                        f"Symbols: {self.use_symbols.get()}\n")
                f.write("─" * 44 + "\n")
                for i, pw in enumerate(passwords, 1):
                    f.write(f"{i:>3}. {pw}\n")
            messagebox.showinfo("Saved", f"Passwords saved to:\n{fp}")
        except OSError as e:
            messagebox.showerror("Save Error", str(e))

    # =========================================================================
    #  QR CODE
    # =========================================================================
    def _show_qr(self):
        pw = self.pw_entry.get()
        if not pw:
            messagebox.showwarning("No Password", "Generate a password first.")
            return
        self._open_qr_window(pw, "Password QR Code")

    def _qr_from_entry(self, entry_widget):
        val = entry_widget.get()
        if not val:
            messagebox.showwarning("Empty", "Generate first.")
            return
        self._open_qr_window(val, "QR Code")

    def _open_qr_window(self, text, title):
        if not PIL_AVAILABLE:
            messagebox.showerror("Missing Library",
                                  "Pillow is required for QR codes.\n"
                                  "Install with: pip install pillow")
            return
        try:
            qr_img = make_qr_image(text, box_size=7, border=4)
        except Exception as e:
            messagebox.showerror("QR Error", f"Could not generate QR code:\n{e}")
            return

        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        win.configure(bg=self.current_theme["bg"])

        tk.Label(win, text=title, font=("Segoe UI", 11, "bold"),
                 bg=self.current_theme["bg"], fg=self.current_theme["fg"]).pack(pady=(12, 4))
        tk.Label(win, text=f'"{text}"', font=("Courier New", 10),
                 bg=self.current_theme["bg"], fg=self.current_theme["fg_sub"],
                 wraplength=280).pack(pady=(0, 8))

        photo = ImageTk.PhotoImage(qr_img)
        lbl = tk.Label(win, image=photo, bg=self.current_theme["bg"])
        lbl.image = photo  # prevent GC
        lbl.pack(padx=20)

        def save_qr():
            fp = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png")],
                initialfile="qr_code.png")
            if fp:
                try:
                    qr_img.save(fp)
                    messagebox.showinfo("Saved", f"QR code saved to:\n{fp}")
                except Exception as ex:
                    messagebox.showerror("Error", str(ex))

        f_btns = tk.Frame(win, bg=self.current_theme["bg"])
        f_btns.pack(pady=10)
        tk.Button(f_btns, text="💾  Save PNG", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  bg=self.current_theme["btn_purple"], fg="#fff",
                  command=save_qr).pack(side="left", padx=(0, 8))
        tk.Button(f_btns, text="Close", font=("Segoe UI", 9), relief="flat",
                  bd=0, padx=12, pady=5, cursor="hand2",
                  bg=self.current_theme["btn_gray"], fg="#fff",
                  command=win.destroy).pack(side="left")

    # =========================================================================
    #  PIN / PATTERN
    # =========================================================================
    def _gen_pin(self):
        pin = generate_pin(self.pin_length.get())
        self.pin_entry.configure(state="normal")
        self.pin_entry.delete(0, tk.END)
        self.pin_entry.insert(0, pin)
        self.pin_entry.configure(state="readonly")
        self._add_to_history([pin])

    def _gen_pattern(self):
        pattern = self.pattern_var.get().strip()
        if not pattern:
            messagebox.showerror("Empty Pattern", "Enter a template pattern.")
            return
        try:
            result = generate_from_pattern(pattern)
        except Exception as e:
            messagebox.showerror("Pattern Error", str(e))
            return
        self.pat_result_entry.configure(state="normal")
        self.pat_result_entry.delete(0, tk.END)
        self.pat_result_entry.insert(0, result)
        self.pat_result_entry.configure(state="readonly")
        self._add_to_history([result])

    # =========================================================================
    #  HISTORY
    # =========================================================================
    def _add_to_history(self, passwords):
        ts = datetime.now().strftime("%H:%M:%S")
        for pw in passwords:
            self.history.insert(0, (ts, pw))
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[:HISTORY_LIMIT]
        self._refresh_history()

    def _refresh_history(self):
        self.hist_text.configure(state="normal")
        self.hist_text.delete("1.0", tk.END)
        for ts, pw in self.history:
            self.hist_text.insert(tk.END, f"[{ts}]  {pw}\n")
        self.hist_text.configure(state="disabled")

    def _clear_history(self):
        if messagebox.askyesno("Clear History", "Clear all history?"):
            self.history = []
            self._refresh_history()

    # =========================================================================
    #  PROFILES
    # =========================================================================
    def _refresh_profile_list(self):
        self.profile_lb.delete(0, tk.END)
        for name in self.profiles:
            self.profile_lb.insert(tk.END, f"  {name}")

    def _preview_profile(self, _event=None):
        sel = self.profile_lb.curselection()
        if not sel:
            return
        name = self.profile_lb.get(sel[0]).strip()
        p = self.profiles.get(name, {})
        parts = []
        if "length" in p: parts.append(f"Length: {p['length']}")
        if p.get("upper"):   parts.append("A–Z")
        if p.get("lower"):   parts.append("a–z")
        if p.get("digits"):  parts.append("0–9")
        if p.get("symbols"): parts.append("Symbols")
        if p.get("exclude_ambiguous"): parts.append("No ambiguous chars")
        if p.get("mode"):    parts.append(f"Mode: {p['mode']}")
        self.profile_detail.config(text="  →  " + "   ·   ".join(parts) if parts else "")

    def _load_profile(self):
        sel = self.profile_lb.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a profile to load.")
            return
        name = self.profile_lb.get(sel[0]).strip()
        p = self.profiles[name]
        if "length" in p: self.pw_length.set(p["length"])
        if "upper"  in p: self.use_upper.set(p["upper"])
        if "lower"  in p: self.use_lower.set(p["lower"])
        if "digits" in p: self.use_digits.set(p["digits"])
        if "symbols" in p: self.use_symbols.set(p["symbols"])
        if "exclude_ambiguous" in p: self.excl_ambiguous.set(p["exclude_ambiguous"])
        self.len_lbl.config(text=str(self.pw_length.get()))
        self.nb.select(0)  # switch to password tab

    def _save_profile_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Save Profile")
        win.resizable(False, False)
        win.grab_set()
        win.configure(bg=self.current_theme["bg"])

        tk.Label(win, text="Profile name:", font=("Segoe UI", 10),
                 bg=self.current_theme["bg"], fg=self.current_theme["fg"]).pack(padx=20, pady=(14, 4))
        name_var = tk.StringVar()
        e = tk.Entry(win, textvariable=name_var, font=("Segoe UI", 10), width=26)
        e.pack(padx=20)
        e.focus()

        def do_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Empty Name", "Enter a name.", parent=win)
                return
            self.profiles[name] = {
                "length":  self.pw_length.get(),
                "upper":   self.use_upper.get(),
                "lower":   self.use_lower.get(),
                "digits":  self.use_digits.get(),
                "symbols": self.use_symbols.get(),
                "exclude_ambiguous": self.excl_ambiguous.get(),
            }
            save_profiles(self.profiles)
            self._refresh_profile_list()
            win.destroy()
            messagebox.showinfo("Saved", f'Profile "{name}" saved.')

        tk.Button(win, text="Save", font=("Segoe UI", 10, "bold"), relief="flat",
                  bd=0, padx=16, pady=6, cursor="hand2",
                  bg=self.current_theme["accent"], fg="#fff",
                  command=do_save).pack(pady=12)
        win.bind("<Return>", lambda e: do_save())

    def _delete_profile(self):
        sel = self.profile_lb.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a profile to delete.")
            return
        name = self.profile_lb.get(sel[0]).strip()
        if name in DEFAULT_PROFILES:
            messagebox.showwarning("Built-in Profile",
                                    "Built-in profiles cannot be deleted.")
            return
        if messagebox.askyesno("Delete Profile", f'Delete profile "{name}"?'):
            self.profiles.pop(name, None)
            save_profiles(self.profiles)
            self._refresh_profile_list()
            self.profile_detail.config(text="")


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
