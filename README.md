<div align="center">

# 🔑 Password Generator — Enhanced Edition

**A professional-grade, feature-rich desktop password generator built with Python and Tkinter.**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange?style=for-the-badge&logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-QR%20%26%20Images-green?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-2.0-purple?style=for-the-badge)

*Secure passwords. Real strength analysis. Zero internet required.*

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [What's New in v2.0](#-whats-new-in-v20)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [How It Works](#-how-it-works)
- [Strength Scoring Algorithm](#-strength-scoring-algorithm)
- [QR Code Engine](#-qr-code-engine)
- [Keyboard Shortcuts](#-keyboard-shortcuts)
- [Profiles System](#-profiles-system)
- [Validation & Error Handling](#-validation--error-handling)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧭 Overview

Password Generator v2.0 is a fully self-contained desktop application that generates cryptographically secure passwords with advanced analysis, multiple generation modes, and professional UX. Everything runs locally — no internet, no telemetry, no cloud.

Built from Python's standard library plus **Pillow** (for QR code rendering), it runs on any system with Python 3.8+.

---

## 🆕 What's New in v2.0

| Feature | Description |
|---|---|
| 🧠 **zxcvbn-style Strength Scoring** | Bundled pure-Python scorer detecting common passwords, keyboard walks, repeats |
| 🌈 **Animated Strength Bar** | Smooth easing animation that colour-shifts red → amber → yellow → green |
| 📜 **Password History** | Session log of the last 50 generated passwords with timestamps |
| ⌨️ **Keyboard Shortcuts** | Full keyboard control — generate, copy, save, QR, toggle visibility |
| 🔢 **PIN / Pattern Mode** | Dedicated tab for numeric PINs and template-based passwords |
| 📂 **Named Preset Profiles** | Save and load named settings configurations, persisted as JSON |
| 🔲 **QR Code Export** | Scannable QR codes via bundled pure-Python encoder, saveable as PNG |

---

## ✨ Features

### Core Features (v1 — still included)

| Feature | Detail |
|---|---|
| **Length slider** | 4–64 characters with live numeric display |
| **Character types** | Uppercase, Lowercase, Numbers, Symbols — guaranteed diversity |
| **Exclude ambiguous chars** | Remove `0 O 1 l I 5 S` for hand-typed passwords |
| **Batch generation** | 1–20 passwords at once in a scrollable list |
| **Read-only display** | Clean, non-editable password field |
| **Copy to clipboard** | One-click with auto-fading confirmation |
| **Save to .txt** | Export all passwords with timestamp and settings |
| **Show/Hide toggle** | Plain text vs `•` masking |
| **Dark mode** | Full light ↔ dark colour theme |
| **Entropy display** | Exact bits (H = L × log₂(N)) |

### New Features (v2.0)

| Feature | Detail |
|---|---|
| **Strength scoring** | 5-level: Very Weak / Weak / Fair / Strong / Very Strong |
| **Crack-time estimate** | Time to crack at 10 billion guesses/sec (offline fast-hash) |
| **Suggestions panel** | Up to 3 actionable improvement tips |
| **Animated bar** | Smooth easing with colour shift per generation |
| **History tab** | Last 50 passwords with HH:MM:SS timestamps; one-click clear |
| **PIN generator** | Numeric PINs 4–12 digits with QR export |
| **Pattern templates** | `A`=upper `a`=lower `0`=digit `!`=symbol `*`=any; literals pass through |
| **Profiles tab** | 4 built-ins + save/load/delete custom; persisted to `~/.pwgen_profiles.json` |
| **QR Code popup** | Toplevel window with QR image + Save PNG button |
| **`secrets` module** | Cryptographically secure CSPRNG throughout |
| **Tabbed interface** | Clean 4-tab layout: Password · PIN/Pattern · History · Profiles |

---

## 📸 Screenshots

> Add screenshots to a `/screenshots` folder and update the paths below.

| Password Tab (Light) | Password Tab (Dark) |
|:---:|:---:|
| ![Light](screenshots/light_mode.png) | ![Dark](screenshots/dark_mode.png) |

| PIN / Pattern Tab | Profiles Tab |
|:---:|:---:|
| ![PIN](screenshots/pin_tab.png) | ![Profiles](screenshots/profiles_tab.png) |

| QR Code Popup | History Tab |
|:---:|:---:|
| ![QR](screenshots/qr_popup.png) | ![History](screenshots/history_tab.png) |

---

## 🛠 Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.8+ | Core logic and scripting |
| **GUI** | `tkinter` + `ttk` | stdlib | All windows, tabs, widgets, layout |
| **Images** | Pillow (PIL) | 9.0+ | QR rendering and ImageTk display |
| **Cryptography** | `secrets` | stdlib | Cryptographically secure random generation |
| **Character sets** | `string` | stdlib | ASCII group constants |
| **Mathematics** | `math` | stdlib | Entropy calculation (`log2`) |
| **Persistence** | `json` + `pathlib` | stdlib | Profile save/load from disk |
| **File I/O** | `datetime` + `open()` | stdlib | Timestamped password export |
| **Clipboard** | `tkinter` clipboard API | stdlib | Copy-to-clipboard |
| **Strength scoring** | `strength_scorer.py` | bundled | zxcvbn-inspired pure-Python scorer |
| **QR encoding** | `qr_generator.py` | bundled | Pure-Python QR encoder + PIL renderer |

### Why only one external dependency?

The QR *encoding logic* — Reed-Solomon error correction, data codewords, format bits, finder patterns — is implemented from scratch in `qr_generator.py`. Pillow is only needed to convert the computed pixel matrix into a displayable and saveable image.

---

## 📁 Project Structure

```
password-generator/
│
├── password_generator.py   # Main app — UI, tabs, all user interactions
├── strength_scorer.py      # Bundled strength engine (pure Python, no pip)
├── qr_generator.py         # Bundled QR encoder + PIL renderer (pure Python)
│
├── requirements.txt        # Single dependency: Pillow
├── README.md               # This file
└── LICENSE                 # MIT License
```

### Module architecture

```
password_generator.py
│
├── CONSTANTS
│   ├── LIGHT / DARK           — full colour palette dicts
│   ├── PATTERN_CHARS          — template character pools
│   └── DEFAULT_PROFILES       — 4 built-in presets
│
├── PURE GENERATION FUNCTIONS
│   ├── build_charset()
│   ├── generate_password()    — guaranteed diversity, secrets module
│   ├── generate_pin()
│   └── generate_from_pattern()
│
├── PROFILE PERSISTENCE
│   ├── load_profiles()
│   └── save_profiles()
│
└── CLASS: PasswordGeneratorApp
    ├── _build_password_tab()
    ├── _build_pin_tab()
    ├── _build_history_tab()
    ├── _build_profiles_tab()
    ├── _apply_theme() / _toggle_dark()
    ├── _bind_shortcuts()
    ├── _on_generate() / _validate()
    ├── _update_strength() / _animate_bar() / _draw_bar()
    ├── _copy() / _save() / _clipboard_set()
    ├── _show_qr() / _open_qr_window()
    ├── _gen_pin() / _gen_pattern()
    ├── _add_to_history() / _refresh_history() / _clear_history()
    └── _load_profile() / _save_profile_dialog() / _delete_profile()
```

---

## 🚀 Getting Started

### Prerequisites

- Python **3.8 or higher**
- `tkinter` (ships with Python on Windows and macOS)
- `Pillow` (one pip install)

#### Install dependencies

```bash
pip install -r requirements.txt
# or directly:
pip install pillow
```

#### Linux — also install Tkinter if missing

```bash
# Debian / Ubuntu
sudo apt-get install python3-tk

# Fedora / RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

### Run

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/password-generator.git

# 2. Enter the folder
cd password-generator

# 3. Install dependency
pip install -r requirements.txt

# 4. Launch
python password_generator.py
```

---

## ⚙️ How It Works

### Password Generation

1. Build the character pool from selected options (optionally filtering ambiguous characters).
2. Guarantee at least one character from every selected group using `secrets.choice()`.
3. Fill the remainder with `secrets.choice(charset)` calls.
4. Shuffle the combined list with `random.shuffle()`.
5. Join and return.

Using `secrets` (backed by `os.urandom`) makes the output cryptographically secure — unlike `random.choice()` which uses a predictable Mersenne Twister.

### Pattern Template Engine

| Template char | Pool used |
|:---:|---|
| `A` | A–Z uppercase |
| `a` | a–z lowercase |
| `0` or `#` | 0–9 digits |
| `!` | `!@#$%^&*` symbols |
| `*` | All of the above |
| anything else | Used literally in the output |

Example: `Aaa000!` → `Kfm482@`

---

## 🔐 Strength Scoring Algorithm

`strength_scorer.py` is a standalone module — import it in your own projects.

### Pipeline

```
password
  │
  ├─ entropy_bits = length × log₂(pool_size)
  │
  ├─ base_score from entropy:
  │     < 28 bits → 0 (Very Weak)
  │     28–36     → 1 (Weak)
  │     36–60     → 2 (Fair)
  │     60–80     → 3 (Strong)
  │     > 80      → 4 (Very Strong)
  │
  ├─ PENALTIES:
  │     found in common-password list       → −3
  │     leet-substituted common password    → −3
  │     keyboard walk / sequential run ≥ 3  → −1.5
  │     >50% chars are repeats              → −1.5
  │
  ├─ BONUS:
  │     all 4 types used + length ≥ 16      → +1
  │
  └─ final_score = clamp(base − penalty + bonus, 0, 4)
```

### Crack-time model

```
crack_time_seconds = 2^entropy_bits / 10_000_000_000
```

Models an offline fast-hash attack at 10 billion guesses/second — the conservative, realistic worst case.

### Score reference

| Score | Label | Colour |
|:---:|---|:---:|
| 0 | Very Weak | 🔴 |
| 1 | Weak | 🟠 |
| 2 | Fair | 🟡 |
| 3 | Strong | 🟢 |
| 4 | Very Strong | 🩵 |

---

## 📐 QR Code Engine

`qr_generator.py` implements the full QR encoding pipeline in pure Python:

- **GF(256) arithmetic** — generator polynomial, exp/log tables
- **Reed-Solomon error correction** — error correction codeword computation
- **Byte-mode data encoding** — mode indicator, character count, bit padding, pad codewords
- **Matrix construction** — finder patterns, separators, timing patterns, alignment patterns (v2–10), dark module, format information
- **Zigzag data placement** with mask pattern 0
- **PIL rendering** — each module as a filled rectangle on a white `Image`

Supports QR versions 1–10 (up to **213 bytes** of UTF-8 at ECC level M) — sufficient for any password this app generates.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Enter` | Generate password (Password tab) |
| `Ctrl + N` | Generate password |
| `Ctrl + C` | Copy to clipboard |
| `Ctrl + S` | Save to file |
| `Ctrl + H` | Toggle show/hide |
| `Ctrl + Q` | Open QR code |
| `Ctrl + D` | Toggle dark mode |

---

## 📂 Profiles System

### Built-in profiles (read-only, always available)

| Profile | Length | Types |
|---|:---:|---|
| Default (Strong) | 16 | All 4 types |
| Wi-Fi Password | 20 | Upper + Lower + Digits, no ambiguous |
| PIN (6-digit) | 6 | Digits only |
| Simple / Shared | 10 | Upper + Lower + Digits |

### User profiles

- Saved to `~/.pwgen_profiles.json` on your home directory
- Persist across restarts
- User profiles are deletable; built-in profiles are protected

---

## 🛡 Validation & Error Handling

| Scenario | Response |
|---|---|
| No character type checked | Error dialog |
| Count outside 1–20 | Error dialog |
| Copy with empty field | Warning dialog |
| Save with no passwords | Warning dialog |
| QR with empty field | Warning dialog |
| Text too long for QR (>213 bytes) | Error dialog |
| Pillow not installed | Error with install instructions |
| File write fails | Error dialog with OS message |
| Empty pattern template | Error dialog |
| Save profile with empty name | Error dialog |
| Delete built-in profile | Warning dialog |

---

## 🤝 Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add: description"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

### Ideas for future features

- [ ] Pronounceable / Diceware passphrase mode
- [ ] Have I Been Pwned breach check
- [ ] System tray + global hotkey
- [ ] Bulk CSV export (100+ passwords)
- [ ] Custom symbol input field
- [ ] Auto-type into focused window

---

<div align="center">

Made with ❤️ and Python &nbsp;·&nbsp; 1 pip dependency &nbsp;·&nbsp; Runs everywhere

⭐ Star this repo if you found it useful!

</div>
