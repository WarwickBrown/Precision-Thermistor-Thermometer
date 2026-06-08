# =============================================================================
# display.py  --  multi-page LCD UI for the Waveshare Pico-LCD-1.14 (240x135).
#
# Pages (cycle with joystick LEFT / RIGHT):
#   0  LIVE     both probes, temperature + resistance + delta + rolling sigma
#   1  TREND    scrolling chart of A and B temperature (shared autoscaled axis)
#   2  DELTA    scrolling chart of A-B (sensitive, common-mode-cancelled)
#   3  STATS    mean / sigma / min-max span / drift rate, per probe
#
# Buttons:
#   KEY A  (GP15)  cycle backlight  (full -> dim -> off -> full)
#   KEY B  (GP17)  reset stats / min-max / history
#   CTRL   (GP3)   hold (freeze) toggle  -- pauses history scroll, marks a point
#
# Self-contained: if Waveshare's `lcd_1inch14.py` driver is not present, the
# module disables rendering and the rest of the system runs console-only.
#
# Integration contract with main.py:
#   display.push(t1, r1, t2, r2, t_amb, cycle)   # once per measurement cycle
#   display.tick()                               # call often (~25 Hz) for UI
# =============================================================================
import time
import config

try:
    import framebuf
    _HAVE_FB = True
except Exception:
    _HAVE_FB = False

_lcd = None
_ok = False

if config.USE_LCD:
    try:
        from lcd_1inch14 import LCD_1inch14
        _lcd = LCD_1inch14()
        _ok = True
    except Exception as e:
        print("[display] LCD driver unavailable (%s); console-only." % e)
        _ok = False


# ---------------------------------------------------------------------------
# Colour helper. Waveshare's framebuffer is RGB565; some builds need a byte
# swap. If colours look wrong, flip config.DISPLAY_BYTESWAP.
# ---------------------------------------------------------------------------
def _c(r, g, b):
    v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    if getattr(config, "DISPLAY_BYTESWAP", True):
        v = ((v & 0xFF) << 8) | (v >> 8)
    return v

BLACK = 0x0000
WHITE = _c(255, 255, 255)
GREY  = _c(140, 140, 140)
GREEN = _c(60, 230, 90)
CYAN  = _c(0, 220, 230)
AMBER = _c(255, 180, 0)
RED   = _c(255, 70, 70)
BLUE  = _c(80, 150, 255)

W, H = 240, 135

# ---------------------------------------------------------------------------
# Scaled text: the framebuf font is fixed 8x8. Render into a temp buffer and
# blit scaled rectangles for larger, readable numbers.
# ---------------------------------------------------------------------------
def _text_scaled(text, x, y, scale, color):
    if not _ok or not _HAVE_FB:
        return
    n = len(text)
    if n == 0:
        return
    tmp = framebuf.FrameBuffer(bytearray(8 * n), 8 * n, 8, framebuf.MONO_HLSB)
    tmp.fill(0)
    tmp.text(text, 0, 0, 1)
    for ty in range(8):
        for tx in range(8 * n):
            if tmp.pixel(tx, ty):
                _lcd.fill_rect(x + tx * scale, y + ty * scale, scale, scale, color)


def _text(text, x, y, color):
    if _ok:
        _lcd.text(text, x, y, color)


# ---------------------------------------------------------------------------
# History buffers + state
# ---------------------------------------------------------------------------
_MAXHIST = 240
_t1 = []
_t2 = []
_dt = []
_last = {"t1": None, "r1": None, "t2": None, "r2": None, "amb": None, "cycle": 0}

# min/max trackers
_mins = {"t1": None, "t2": None, "dt": None}
_maxs = {"t1": None, "t2": None, "dt": None}

_page = 0
_NPAGES = 4
_hold = False
_bl_level = 2          # 0 off, 1 dim, 2 full
_dirty = True          # needs redraw

# Backlight PWM (GP13). Falls back silently if unavailable.
_bl = None
if _ok:
    try:
        from machine import Pin, PWM
        _bl = PWM(Pin(config.PIN_LCD_BL))
        _bl.freq(1000)
        _bl.duty_u16(65535)
    except Exception:
        _bl = None

# Buttons (active-low, internal pull-ups)
_btn = {}
if _ok:
    try:
        from machine import Pin
        _btn = {
            "left":  Pin(config.PIN_JOY_LEFT,  Pin.IN, Pin.PULL_UP),
            "right": Pin(config.PIN_JOY_RIGHT, Pin.IN, Pin.PULL_UP),
            "a":     Pin(config.PIN_KEY_A,     Pin.IN, Pin.PULL_UP),
            "b":     Pin(config.PIN_KEY_B,     Pin.IN, Pin.PULL_UP),
            "ctrl":  Pin(config.PIN_JOY_CTRL,  Pin.IN, Pin.PULL_UP),
        }
    except Exception:
        _btn = {}

_prev = {k: 1 for k in _btn}     # previous (released) states
_last_btn_ms = 0


def available():
    return _ok


# ---------------------------------------------------------------------------
# Data intake (called once per measurement cycle by main.py)
# ---------------------------------------------------------------------------
def push(t1, r1, t2, r2, t_amb, cycle):
    _last.update({"t1": t1, "r1": r1, "t2": t2, "r2": r2,
                  "amb": t_amb, "cycle": cycle})
    if _hold:
        _dirty_set()
        return
    d = None
    if t1 is not None and t2 is not None:
        d = t1 - t2
    for buf, val in ((_t1, t1), (_t2, t2), (_dt, d)):
        buf.append(val)
        if len(buf) > _MAXHIST:
            buf.pop(0)
    # min/max
    _track("t1", t1)
    _track("t2", t2)
    _track("dt", d)
    _dirty_set()


def _track(key, val):
    if val is None:
        return
    if _mins[key] is None or val < _mins[key]:
        _mins[key] = val
    if _maxs[key] is None or val > _maxs[key]:
        _maxs[key] = val


def _reset_stats():
    _t1.clear(); _t2.clear(); _dt.clear()
    for k in _mins:
        _mins[k] = None
        _maxs[k] = None


def _dirty_set():
    global _dirty
    _dirty = True


# ---------------------------------------------------------------------------
# Rolling statistics
# ---------------------------------------------------------------------------
def _stats(buf, n=None):
    """Return (mean, sigma) over the last n samples (mean/sigma in same units)."""
    vals = [v for v in buf if v is not None]
    if n is not None:
        vals = vals[-n:]
    if len(vals) < 2:
        return (vals[0] if vals else None, None)
    m = sum(vals) / len(vals)
    var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
    return m, var ** 0.5


def _drift_rate(buf):
    """Crude drift in mK per minute via first-vs-last over the window."""
    vals = [v for v in buf if v is not None]
    if len(vals) < 2:
        return None
    span_samples = len(vals) - 1
    minutes = span_samples * config.CYCLE_PERIOD_S / 60.0
    if minutes <= 0:
        return None
    return (vals[-1] - vals[0]) * 1000.0 / minutes


# ---------------------------------------------------------------------------
# Input polling
# ---------------------------------------------------------------------------
def _poll_buttons():
    global _page, _hold, _bl_level, _last_btn_ms
    if not _btn:
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_btn_ms) < 180:    # debounce / repeat guard
        return
    for name, pin in _btn.items():
        val = pin.value()
        if _prev[name] == 1 and val == 0:           # falling edge = press
            _last_btn_ms = now
            if name == "right":
                _page = (_page + 1) % _NPAGES
            elif name == "left":
                _page = (_page - 1) % _NPAGES
            elif name == "a":
                _bl_level = (_bl_level + 1) % 3
                _apply_backlight()
            elif name == "b":
                _reset_stats()
            elif name == "ctrl":
                _hold = not _hold
            _dirty_set()
        _prev[name] = val


def _apply_backlight():
    if _bl is None:
        return
    duty = {0: 0, 1: 12000, 2: 65535}.get(_bl_level, 65535)
    try:
        _bl.duty_u16(duty)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(v, nd=3):
    return "--.---" if v is None else ("{:.%df}" % nd).format(v)


def _header(title):
    _lcd.fill_rect(0, 0, W, 14, BLUE)
    _text(title, 4, 3, BLACK)
    # hold + page indicators on the right
    tag = "HOLD" if _hold else "P%d" % (_page + 1)
    _text(tag, W - 36, 3, BLACK)


def _page_live():
    _lcd.fill(BLACK)
    _header(config.LABEL_A + "/" + config.LABEL_B + "  LIVE")

    # Probe A
    _text(config.LABEL_A, 4, 20, CYAN)
    _text_scaled(_fmt(_last["t1"], 3) + "C", 4, 30, 2, GREEN)
    _text(_fmt(_last["r1"], 1) + " ohm", 4, 50, GREY)

    # Probe B
    _text(config.LABEL_B, 4, 66, CYAN)
    _text_scaled(_fmt(_last["t2"], 3) + "C", 4, 76, 2, GREEN)
    _text(_fmt(_last["r2"], 1) + " ohm", 4, 96, GREY)

    # Delta + sigma + cycle
    d = None
    if _last["t1"] is not None and _last["t2"] is not None:
        d = _last["t1"] - _last["t2"]
    _text("dT " + ("{:+.3f}C".format(d) if d is not None else "--"), 4, 112, AMBER)

    _, s1 = _stats(_t1, n=config.STATS_WINDOW)
    sig = "--" if s1 is None else "{:.1f}".format(s1 * 1000.0)
    _text("sig " + sig + "mK", 120, 112, WHITE)
    _text("c" + str(_last["cycle"]), 190, 112, GREY)
    _lcd.show()


def _plot_axes(x0, y0, x1, y1):
    _lcd.rect(x0, y0, x1 - x0, y1 - y0, GREY)


def _plot_series(series_list, colors, x0, y0, x1, y1):
    # gather all values for shared autoscale
    allv = [v for s in series_list for v in s if v is not None]
    if len(allv) < 2:
        _text("collecting...", x0 + 6, (y0 + y1) // 2, GREY)
        return None, None
    lo, hi = min(allv), max(allv)
    if hi - lo < 1e-6:
        hi += 0.001
        lo -= 0.001
    pad = (hi - lo) * 0.08
    lo -= pad
    hi += pad
    pw = x1 - x0 - 2
    ph = y1 - y0 - 2

    def xmap(i, n):
        if n < 2:
            return x0 + 1
        return x0 + 1 + int(i * (pw - 1) / (n - 1))

    def ymap(v):
        return y1 - 1 - int((v - lo) * (ph - 1) / (hi - lo))

    for s, col in zip(series_list, colors):
        pts = [(i, v) for i, v in enumerate(s) if v is not None]
        n = len(s)
        for k in range(1, len(pts)):
            i0, v0 = pts[k - 1]
            i1_, v1_ = pts[k]
            _lcd.line(xmap(i0, n), ymap(v0), xmap(i1_, n), ymap(v1_), col)
    return lo, hi


def _page_trend():
    _lcd.fill(BLACK)
    _header("TREND  A=grn B=cyn")
    x0, y0, x1, y1 = 28, 16, W - 2, H - 14
    _plot_axes(x0, y0, x1, y1)
    lo, hi = _plot_series([_t1, _t2], [GREEN, CYAN], x0, y0, x1, y1)
    if lo is not None:
        _text("{:.2f}".format(hi), 0, y0, GREY)
        _text("{:.2f}".format(lo), 0, y1 - 8, GREY)
    span_min = (len(_t1) * config.CYCLE_PERIOD_S) / 60.0
    _text("{:.0f}min".format(span_min), x0 + 4, H - 12, GREY)
    _lcd.show()


def _page_delta():
    _lcd.fill(BLACK)
    _header("DELTA  A-B")
    x0, y0, x1, y1 = 28, 16, W - 2, H - 14
    _plot_axes(x0, y0, x1, y1)
    lo, hi = _plot_series([_dt], [AMBER], x0, y0, x1, y1)
    if lo is not None:
        _text("{:+.3f}".format(hi), 0, y0, GREY)
        _text("{:+.3f}".format(lo), 0, y1 - 8, GREY)
        m, s = _stats(_dt, n=config.STATS_WINDOW)
        if s is not None:
            _text("sd {:.1f}mK".format(s * 1000.0), x0 + 4, H - 12, WHITE)
    _lcd.show()


def _page_stats():
    _lcd.fill(BLACK)
    _header("STATS  (KEY B = reset)")
    win = config.STATS_WINDOW

    def row(y, label, buf, key, nd=3, unit="C"):
        m, s = _stats(buf, n=win)
        _text(label, 4, y, CYAN)
        _text("u:" + _fmt(m, nd), 56, y, WHITE)
        sig = "--" if s is None else "{:.1f}".format(s * 1000.0)
        _text("s:" + sig + "mK", 150, y, GREEN)
        # span on next line
        sp = "--"
        if _mins[key] is not None and _maxs[key] is not None:
            sp = "{:.1f}mK".format((_maxs[key] - _mins[key]) * 1000.0)
        dr = _drift_rate(buf)
        drs = "--" if dr is None else "{:+.1f}".format(dr)
        _text("  span:" + sp + " drift:" + drs + "mK/min", 4, y + 10, GREY)

    row(20, config.LABEL_A, _t1, "t1")
    row(46, config.LABEL_B, _t2, "t2")
    row(72, "dT", _dt, "dt")

    n = len([v for v in _t1 if v is not None])
    _text("n=%d  win=%d  %.0fs/smpl" % (n, win, config.CYCLE_PERIOD_S),
          4, 104, GREY)
    settled = "STABLE" if _is_settled() else "SETTLING"
    _text(settled, 4, 118, GREEN if settled == "STABLE" else AMBER)
    _lcd.show()


def _is_settled():
    _, s = _stats(_t1, n=config.STATS_WINDOW)
    if s is None:
        return False
    return (s * 1000.0) <= config.SETTLE_SIGMA_MK


def tick():
    """Poll inputs and redraw if needed. Call frequently (~25 Hz)."""
    if not _ok:
        return
    _poll_buttons()
    global _dirty
    if not _dirty:
        return
    _dirty = False
    try:
        (_page_live, _page_trend, _page_delta, _page_stats)[_page]()
    except Exception as e:
        print("[display] render error:", e)


def message(line1, line2=""):
    if not _ok:
        return
    _lcd.fill(BLACK)
    _text(line1, 4, 54, WHITE)
    if line2:
        _text(line2, 4, 70, WHITE)
    _lcd.show()


# Backwards-compat shim: older main.py called display.update(...)
def update(t1, r1, t2, r2, t_amb, cycle):
    push(t1, r1, t2, r2, t_amb, cycle)
    tick()
