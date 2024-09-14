"""
strength_scorer.py
==================
A lightweight zxcvbn-inspired password strength estimator.
Pure Python, zero dependencies.

Scoring is based on:
  - Length bonus
  - Character diversity (uppercase, lowercase, digits, symbols)
  - Common password / dictionary penalties
  - Keyboard walk / sequential pattern penalties
  - Repeat-character penalties
  - Entropy estimation

Returns a score 0–4 and human-readable crack-time estimate.
"""

import math
import re

# ─────────────────────────────────────────────────────────
#  TOP-500 COMMON PASSWORDS (abbreviated for bundle size)
# ─────────────────────────────────────────────────────────
COMMON_PASSWORDS = {
    "password", "123456", "12345678", "1234", "qwerty", "12345", "dragon",
    "baseball", "iloveyou", "master", "monkey", "abc123", "letmein", "1234567",
    "sunshine", "princess", "welcome", "shadow", "superman", "michael",
    "football", "charlie", "donald", "password1", "qwerty123", "iloveyou1",
    "admin", "login", "hello", "test", "pass", "temp", "1111", "0000",
    "1234567890", "password123", "abc", "111111", "000000", "123123",
    "654321", "121212", "2222", "3333", "4444", "5555", "6666", "7777",
    "8888", "9999", "1122", "1212", "696969", "123321", "666666", "7777777",
    "888888", "987654321", "pass123", "trustno1", "batman", "access",
    "mustang", "jessica", "hunter", "ranger", "buster", "thomas", "robert",
    "soccer", "hockey", "killer", "george", "harley", "ranger", "dakota",
    "jordan", "tigger", "cheese", "hammer", "summer", "corvette", "taylor",
    "fucker", "austin", "1qaz2wsx", "qazwsx", "zxcvbnm", "asdfgh",
}

# Keyboard adjacency sequences
KEYBOARD_SEQUENCES = [
    "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "1234567890", "qwerty", "asdfg", "zxcvb",
    "qazwsx", "!@#$%^&*()",
]

LEET_MAP = {"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "@": "a", "$": "s"}


def _deleet(password: str) -> str:
    """Reverse leet substitutions for dictionary matching."""
    result = []
    for ch in password.lower():
        result.append(LEET_MAP.get(ch, ch))
    return "".join(result)


def _has_sequential(password: str) -> bool:
    """Detect keyboard walks or alphabetic/numeric runs of 3+."""
    pw = password.lower()
    for seq in KEYBOARD_SEQUENCES:
        for i in range(len(seq) - 2):
            chunk = seq[i:i+3]
            if chunk in pw or chunk[::-1] in pw:
                return True
    alpha = "abcdefghijklmnopqrstuvwxyz"
    digits = "0123456789"
    for base in (alpha, digits):
        for i in range(len(base) - 2):
            chunk = base[i:i+3]
            if chunk in pw or chunk[::-1] in pw:
                return True
    return False


def _repeat_ratio(password: str) -> float:
    """Return fraction of characters that are repeats (0=none, 1=all same)."""
    if not password:
        return 0.0
    seen = {}
    for ch in password.lower():
        seen[ch] = seen.get(ch, 0) + 1
    max_repeats = max(seen.values())
    return max_repeats / len(password)


def _pool_size(password: str) -> int:
    """Estimate character pool size based on actual characters used."""
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"\d", password):
        pool += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        pool += 32
    return max(pool, 1)


def _entropy_bits(password: str) -> float:
    """H = L * log2(pool)"""
    return len(password) * math.log2(_pool_size(password))


def _crack_time_seconds(entropy: float) -> float:
    """
    Estimate seconds to crack at 10 billion guesses/second
    (offline fast-hash scenario — the hardest case for the user).
    """
    return (2 ** entropy) / 10_000_000_000


def _format_crack_time(seconds: float) -> str:
    """Convert seconds into a human-readable duration."""
    if seconds < 1:
        return "less than a second"
    if seconds < 60:
        return f"{int(seconds)} second{'s' if seconds >= 2 else ''}"
    if seconds < 3600:
        m = int(seconds / 60)
        return f"{m} minute{'s' if m > 1 else ''}"
    if seconds < 86400:
        h = int(seconds / 3600)
        return f"{h} hour{'s' if h > 1 else ''}"
    if seconds < 31_536_000:
        d = int(seconds / 86400)
        return f"{d} day{'s' if d > 1 else ''}"
    if seconds < 3_153_600_000:
        y = int(seconds / 31_536_000)
        return f"{y} year{'s' if y > 1 else ''}"
    return "centuries"


# ─────────────────────────────────────────────────────────
#  MAIN SCORING FUNCTION
# ─────────────────────────────────────────────────────────
def score_password(password: str) -> dict:
    """
    Score a password and return a result dict with keys:
      score       : int 0–4
      label       : str "Very Weak" | "Weak" | "Fair" | "Strong" | "Very Strong"
      entropy     : float (bits)
      crack_time  : str  human-readable offline crack time
      suggestions : list[str]
      bar_fraction: float 0.0–1.0 for progress bar
    """
    if not password:
        return {
            "score": 0, "label": "—", "entropy": 0.0,
            "crack_time": "—", "suggestions": [], "bar_fraction": 0.0,
        }

    length = len(password)
    entropy = _entropy_bits(password)
    crack_secs = _crack_time_seconds(entropy)

    # ── Penalties ────────────────────────────────
    penalty = 0.0
    suggestions = []

    pw_lower = password.lower()
    if pw_lower in COMMON_PASSWORDS or _deleet(pw_lower) in COMMON_PASSWORDS:
        penalty += 3.0
        suggestions.append("Avoid common passwords or simple substitutions.")

    if _has_sequential(password):
        penalty += 1.5
        suggestions.append("Avoid keyboard walks or sequences (abc, 123, qwerty).")

    repeat = _repeat_ratio(password)
    if repeat > 0.5:
        penalty += 1.5
        suggestions.append("Avoid repeating the same characters.")

    # ── Length suggestions ───────────────────────
    if length < 8:
        suggestions.append("Use at least 8 characters.")
    elif length < 12:
        suggestions.append("Consider using 12+ characters for better security.")

    # ── Diversity suggestions ────────────────────
    has_upper   = bool(re.search(r"[A-Z]", password))
    has_lower   = bool(re.search(r"[a-z]", password))
    has_digit   = bool(re.search(r"\d",    password))
    has_symbol  = bool(re.search(r"[^a-zA-Z0-9]", password))
    active_types = sum([has_upper, has_lower, has_digit, has_symbol])

    if not has_upper:
        suggestions.append("Add uppercase letters.")
    if not has_digit:
        suggestions.append("Add numbers.")
    if not has_symbol:
        suggestions.append("Add symbols (!@#$%^&*).")

    # ── Compute adjusted score ───────────────────
    # Base score from entropy thresholds
    if entropy < 28:
        base = 0
    elif entropy < 36:
        base = 1
    elif entropy < 60:
        base = 2
    elif entropy < 80:
        base = 3
    else:
        base = 4

    # Apply penalty (integer deduction)
    adjusted = max(0, base - int(penalty))

    # Diversity bonus: push up if all 4 types used and long enough
    if active_types >= 4 and length >= 16:
        adjusted = min(4, adjusted + 1)

    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    bar_fractions = [0.1, 0.3, 0.55, 0.78, 1.0]

    return {
        "score":        adjusted,
        "label":        labels[adjusted],
        "entropy":      round(entropy, 1),
        "crack_time":   _format_crack_time(crack_secs),
        "suggestions":  suggestions[:3],  # cap at 3
        "bar_fraction": bar_fractions[adjusted],
    }
