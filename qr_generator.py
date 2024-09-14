"""
qr_generator.py
===============
Minimal QR Code generator (Version 1–10, ECC level M).
Pure Python — uses only the PIL/Pillow library for rendering.

Based on the ISO/IEC 18004 standard.
Generates a PIL Image that can be embedded directly in Tkinter.
"""

from PIL import Image, ImageDraw


# ── Reed-Solomon GF(256) arithmetic ────────────────────────────────────────
GF_EXP = [0] * 512
GF_LOG  = [0] * 256

_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    GF_EXP[_i] = GF_EXP[_i - 255]


def _gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return GF_EXP[(GF_LOG[x] + GF_LOG[y]) % 255]


def _gf_poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, pi in enumerate(p):
        for j, qj in enumerate(q):
            r[i + j] ^= _gf_mul(pi, qj)
    return r


def _rs_generator_poly(n_ec):
    g = [1]
    for i in range(n_ec):
        g = _gf_poly_mul(g, [1, GF_EXP[i]])
    return g


def _rs_encode(data, n_ec):
    gen = _rs_generator_poly(n_ec)
    msg = list(data) + [0] * n_ec
    for i in range(len(data)):
        coef = msg[i]
        if coef:
            for j in range(1, len(gen)):
                msg[i + j] ^= _gf_mul(gen[j], coef)
    return msg[len(data):]


# ── QR version / capacity tables (version 1–10, ECC M) ─────────────────────
# (data_codewords, ec_codewords, remainder_bits)
_VERSION_INFO = {
    1:  (16,  10, 0),
    2:  (28,  16, 7),
    3:  (44,  26, 7),
    4:  (64,  36, 7),
    5:  (86,  48, 7),
    6:  (108, 64, 7),
    7:  (124, 72, 0),
    8:  (154, 88, 0),
    9:  (182, 110, 0),
    10: (216, 130, 0),
}

# Max byte-mode capacity at ECC M
_MAX_BYTES = {
    1: 14, 2: 26, 3: 42, 4: 62, 5: 84,
    6: 106, 7: 122, 8: 152, 9: 180, 10: 213,
}


def _choose_version(n_bytes):
    for v in range(1, 11):
        if _MAX_BYTES[v] >= n_bytes:
            return v
    raise ValueError(f"Data too long for QR version 1-10 ({n_bytes} bytes, max {_MAX_BYTES[10]})")


def _encode_data(data_bytes, version):
    """Encode as byte mode + padding codewords."""
    n_data, n_ec, _ = _VERSION_INFO[version]
    bits = []

    def add_bits(value, length):
        for i in range(length - 1, -1, -1):
            bits.append((value >> i) & 1)

    add_bits(0b0100, 4)                    # mode: byte
    add_bits(len(data_bytes), 8)           # char count
    for byte in data_bytes:
        add_bits(byte, 8)

    # Terminator + bit padding
    for _ in range(min(4, n_data * 8 - len(bits))):
        bits.append(0)
    while len(bits) % 8:
        bits.append(0)

    # Pad codewords
    pad_bytes = [0xEC, 0x11]
    i = 0
    while len(bits) < n_data * 8:
        add_bits(pad_bytes[i % 2], 8)
        i += 1

    # Convert bits → codewords
    codewords = []
    for i in range(0, len(bits), 8):
        val = 0
        for b in bits[i:i+8]:
            val = (val << 1) | b
        codewords.append(val)

    ec = _rs_encode(codewords, n_ec)
    return codewords + ec


# ── Matrix construction ─────────────────────────────────────────────────────
def _make_matrix(version):
    size = version * 4 + 17
    matrix    = [[None] * size for _ in range(size)]
    reserved  = [[False] * size for _ in range(size)]

    def place(r, c, val):
        matrix[r][c] = val
        reserved[r][c] = True

    # Finder pattern
    def finder(row, col):
        for dr in range(7):
            for dc in range(7):
                on = (dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4))
                place(row + dr, col + dc, 1 if on else 0)

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    # Separators
    def sep_row(r, cs):
        for c in cs:
            if 0 <= r < size and 0 <= c < size:
                place(r, c, 0)

    def sep_col(rs, c):
        for r in rs:
            if 0 <= r < size and 0 <= c < size:
                place(r, c, 0)

    for c in range(8):
        place(7, c, 0); place(7, size - 8 + c, 0) if c < 8 else None
        if c < 8: place(size - 8, c, 0)
    for r in range(8):
        place(r, 7, 0); place(r, size - 8, 0)
        if r < 8: place(size - 8 + r, 7, 0) if size - 8 + r < size else None

    # Timing patterns
    for i in range(8, size - 8):
        val = 1 if i % 2 == 0 else 0
        place(6, i, val)
        place(i, 6, val)

    # Dark module
    place(size - 8, 8, 1)

    # Format information (mask 0, ECC M = 00, mask 000 → 101010000010010)
    FORMAT_BITS = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]
    fmt_coords = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5),
                  (8, 7), (8, 8), (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    for bit, (r, c) in zip(FORMAT_BITS, fmt_coords):
        place(r, c, bit)
    fmt2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
            (size - 5, 8), (size - 6, 8), (size - 7, 8),
            (8, size - 8), (8, size - 7), (8, size - 6),
            (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
    for bit, (r, c) in zip(FORMAT_BITS, fmt2):
        place(r, c, bit)

    # Alignment patterns (version >= 2)
    _ALIGN = {2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
              6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
    if version >= 2:
        centers = _ALIGN[version]
        for r in centers:
            for c in centers:
                if not reserved[r][c]:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            on = (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0))
                            place(r + dr, c + dc, 1 if on else 0)

    return matrix, reserved, size


def _place_data(matrix, reserved, size, codewords, remainder_bits):
    """Zigzag data placement with mask pattern 0 (i+j) % 2 == 0."""
    bits = []
    for cw in codewords:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)
    bits += [0] * remainder_bits

    bit_idx = 0
    right = True
    col = size - 1
    while col >= 0:
        if col == 6:
            col -= 1
            continue
        for row in range(size - 1, -1, -1) if right else range(size):
            for dc in range(2):
                c = col - dc
                if 0 <= c < size and not reserved[row][c]:
                    if bit_idx < len(bits):
                        bit = bits[bit_idx]
                        bit_idx += 1
                    else:
                        bit = 0
                    # Mask 0: (row + c) % 2 == 0
                    if (row + c) % 2 == 0:
                        bit ^= 1
                    matrix[row][c] = bit
        right = not right
        col -= 2


def make_qr_image(text: str, box_size: int = 8, border: int = 4) -> Image.Image:
    """
    Generate a QR Code PIL Image for the given text.

    Args:
        text:     The string to encode.
        box_size: Pixel size of each module (default 8).
        border:   Quiet zone in modules (default 4).

    Returns:
        PIL.Image.Image (mode 'RGB')
    """
    data_bytes = text.encode("utf-8")
    version = _choose_version(len(data_bytes))
    codewords = _encode_data(data_bytes, version)
    matrix, reserved, size = _make_matrix(version)
    _, _, remainder_bits = _VERSION_INFO[version]
    _place_data(matrix, reserved, size, codewords, remainder_bits)

    total = (size + 2 * border) * box_size
    img  = Image.new("RGB", (total, total), "white")
    draw = ImageDraw.Draw(img)

    for r in range(size):
        for c in range(size):
            if matrix[r][c] == 1:
                x0 = (border + c) * box_size
                y0 = (border + r) * box_size
                draw.rectangle([x0, y0, x0 + box_size - 1, y0 + box_size - 1], fill="black")

    return img


# ── Quick self-test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    img = make_qr_image("https://github.com", box_size=6)
    img.save("/tmp/test_qr.png")
    print(f"QR saved: {img.size}")
