# =============================================================================
# display.py  --  multi-page LCD UI for the Waveshare Pico-LCD-1.14 (240x135).
#
# Pages (next / previous with KEY A / KEY B, or joystick RIGHT / LEFT):
#   0  LIVE     both probes, large temperature + resistance + delta + sigma
#   1  AVERAGES rolling mean over a short and a long window, per probe
#   2  TREND    scrolling chart of A and B temperature (shared autoscaled axis)
#   3  DELTA    scrolling chart of A-B (sensitive, common-mode-cancelled)
#   4  STATS    mean / sigma / min-max span / drift rate, per probe
#
# Buttons:
#   KEY A  (GP15)        next page
#   KEY B  (GP17)        previous page
#   JOY RIGHT/LEFT       next / previous page (backup for KEY A / KEY B)
#   JOY UP (GP2)         cycle backlight  (full -> dim -> off -> full)
#   JOY DOWN (GP18)      reset stats / min-max / history
#   JOY PRESS (GP3)      tap = hold (freeze) toggle, long-press = FAST/QUIET
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
import sampling

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
# blit scaled rectangles for larger, readable numbers. scale=1 is the native
# 8x8 font; scale=2 is 16 px tall; scale=3 is 24 px tall.
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
_NPAGES = 5
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
        if getattr(config, "BACKLIGHT_ON_BOOT", True):
            _bl_level = 2
            _bl.duty_u16(65535)
        else:
            _bl_level = 0
            _bl.duty_u16(0)
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
            "up":    Pin(config.PIN_JOY_UP,    Pin.IN, Pin.PULL_UP),
            "down":  Pin(config.PIN_JOY_DOWN,  Pin.IN, Pin.PULL_UP),
            "a":     Pin(config.PIN_KEY_A,     Pin.IN, Pin.PULL_UP),
            "b":     Pin(config.PIN_KEY_B,     Pin.IN, Pin.PULL_UP),
            "ctrl":  Pin(config.PIN_JOY_CTRL,  Pin.IN, Pin.PULL_UP),
        }
    except Exception:
        _btn = {}

_prev = {k: 1 for k in _btn}     # previous (released) states
_last_btn_ms = 0

# Joystick-centre long-press state (tap = hold toggle, hold = FAST/QUIET switch)
_LONG_MS = 700
_ctrl_down_ms = None
_ctrl_fired_long = False


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
    minutes = span_samples * sampling.period_s() / 60.0
    if minutes <= 0:
        return None
    return (vals[-1] - vals[0]) * 1000.0 / minutes


# ---------------------------------------------------------------------------
# Input polling
# ---------------------------------------------------------------------------
def _poll_buttons():
    global _page, _hold, _bl_level, _last_btn_ms
    global _ctrl_down_ms, _ctrl_fired_long
    if not _btn:
        return
    now = time.ticks_ms()

    # Joystick centre, handled every tick (outside the discrete-press debounce)
    # so the press duration can be measured: a tap toggles hold, a long press
    # switches the FAST/QUIET sampling profile.
    cpin = _btn.get("ctrl")
    if cpin is not None:
        cval = cpin.value()
        if _prev["ctrl"] == 1 and cval == 0:                # pressed
            _ctrl_down_ms = now
            _ctrl_fired_long = False
        elif cval == 0 and _ctrl_down_ms is not None and not _ctrl_fired_long:
            if time.ticks_diff(now, _ctrl_down_ms) >= _LONG_MS:
                _ctrl_fired_long = True                     # long-press fires once
                sampling.toggle()
                _dirty_set()
        elif _prev["ctrl"] == 0 and cval == 1:              # released
            if _ctrl_down_ms is not None and not _ctrl_fired_long:
                _hold = not _hold                           # short tap
                _dirty_set()
            _ctrl_down_ms = None
        _prev["ctrl"] = cval

    # Discrete-press buttons: act on the falling edge, with a shared debounce.
    if time.ticks_diff(now, _last_btn_ms) < 180:
        return
    for name, pin in _btn.items():
        if name == "ctrl":
            continue
        val = pin.value()
        if _prev[name] == 1 and val == 0:                   # falling edge = press
            _last_btn_ms = now
            # Page nav on the two physical keys (most reliable) plus joystick L/R.
            if name in ("a", "right"):
                _page = (_page + 1) % _NPAGES
            elif name in ("b", "left"):
                _page = (_page - 1) % _NPAGES
            elif name == "up":
                _bl_level = (_bl_level - 1) % 3      # full -> dim -> off -> full
                _apply_backlight()
            elif name == "down":
                _reset_stats()
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
    # Right side, right-aligned: HOLD-or-page tag, with a FAST badge to its left.
    rx = W - 4
    tag = "HOLD" if _hold else "P%d" % (_page + 1)
    _text(tag, rx - len(tag) * 8, 3, BLACK)
    if sampling.is_fast():
        _text("FAST", rx - len(tag) * 8 - 4 - 32, 3, RED)


def _probe_block(label, y_label, t, r):
    """One probe: small label + integer-ohm resistance on a header line, then a
    large (scale-3) temperature underneath. y_label is the label-line top."""
    _text(label, 4, y_label, CYAN)
    if r is not None:
        rs = "{:.0f}R".format(r)
        _text(rs, W - len(rs) * 8 - 4, y_label, GREY)
    _text_scaled(_fmt(t, 3) + "C", 4, y_label + 10, 3, GREEN)


def _page_live():
    _lcd.fill(BLACK)
    _header(config.LABEL_A + "/" + config.LABEL_B + "  LIVE")

    _probe_block(config.LABEL_A, 18, _last["t1"], _last["r1"])   # temp 28..52
    _probe_block(config.LABEL_B, 58, _last["t2"], _last["r2"])   # temp 68..92

    # Bottom status line 1: delta (left) and rolling sigma (right-aligned, so a
    # large transient sigma grows leftward instead of into the next field).
    d = None
    if _last["t1"] is not None and _last["t2"] is not None:
        d = _last["t1"] - _last["t2"]
    _text("dT" + ("{:+.3f}C".format(d) if d is not None else " --"), 4, 100, AMBER)
    _, s1 = _stats(_t1, n=config.STATS_WINDOW)
    sig = "--" if s1 is None else "{:.1f}".format(s1 * 1000.0)
    sigs = "sig" + sig + "mK"
    _text(sigs, W - len(sigs) * 8 - 4, 100, WHITE)

    # Bottom status line 2: settle flag (left), ambient (if a DS18B20 is fitted),
    # cycle count (right-aligned).
    settled = "STABLE" if _is_settled() else "SETTLING"
    _text(settled, 4, 118, GREEN if settled == "STABLE" else AMBER)
    # ambient sits just right of the settle flag so it always clears the
    # right-aligned cycle counter, even for a sub-zero ambient and a long run.
    if _last["amb"] is not None:
        _text("amb{:.1f}C".format(_last["amb"]), 80, 118, GREY)
    cs = "c" + str(_last["cycle"])
    _text(cs, W - len(cs) * 8 - 4, 118, GREY)
    _lcd.show()


def _page_averages():
    _lcd.fill(BLACK)
    _header("AVERAGES")
    win = config.STATS_WINDOW

    def block(y, label, buf):
        ms, _ss = _stats(buf, n=win)            # short-window mean
        ml, sl = _stats(buf, n=None)            # long-window (all available) mean + sigma
        _text(label, 4, y, CYAN)
        sls = "--" if sl is None else "{:.1f}".format(sl * 1000.0)
        rt = "sd" + sls + "mK"
        _text(rt, W - len(rt) * 8 - 4, y, GREEN)              # long-window sigma, right
        _text_scaled(_fmt(ml, 4) + "C", 4, y + 10, 2, WHITE)  # big long-window mean
        sms = "--" if ms is None else "{:.4f}".format(ms)
        _text("n%d %s" % (win, sms), 4, y + 28, GREY)         # short-window mean, small

    block(16, config.LABEL_A, _t1)     # label 16, big 26..42, small 44..52
    block(54, config.LABEL_B, _t2)     # label 54, big 64..80, small 82..90

    # dT: signed long-window mean and its sigma
    md, sd = _stats(_dt, n=None)
    _text("dT", 4, 96, AMBER)
    _text(("{:+.4f}C".format(md) if md is not None else "--.----C"), 40, 96, AMBER)
    sds = "--" if sd is None else "{:.1f}".format(sd * 1000.0)
    rt = "sd" + sds + "mK"
    _text(rt, W - len(rt) * 8 - 4, 96, WHITE)

    nshow = len([v for v in _t1 if v is not None])
    _text("n%d  win %d/all smp  %.0fs" % (nshow, win, sampling.period_s()),
          4, 116, GREY)
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


# A wider left gutter so the axis value labels never run into the plot box, even
# a 7-character signed delta like "+12.345" when the two probes are far apart.
_GUT = 58


def _page_trend():
    _lcd.fill(BLACK)
    _header("TREND  A=grn B=cyn")
    x0, y0, x1, y1 = _GUT, 16, W - 2, H - 14
    _plot_axes(x0, y0, x1, y1)
    lo, hi = _plot_series([_t1, _t2], [GREEN, CYAN], x0, y0, x1, y1)
    if lo is not None:
        _text("{:.2f}".format(hi), 2, y0, GREY)
        _text("{:.2f}".format(lo), 2, y1 - 8, GREY)
    span_min = (len(_t1) * sampling.period_s()) / 60.0
    _text("{:.0f}min".format(span_min), x0 + 4, H - 12, GREY)
    _lcd.show()


def _page_delta():
    _lcd.fill(BLACK)
    _header("DELTA  A-B")
    x0, y0, x1, y1 = _GUT, 16, W - 2, H - 14
    _plot_axes(x0, y0, x1, y1)
    lo, hi = _plot_series([_dt], [AMBER], x0, y0, x1, y1)
    if lo is not None:
        _text("{:+.3f}".format(hi), 2, y0, GREY)
        _text("{:+.3f}".format(lo), 2, y1 - 8, GREY)
        m, s = _stats(_dt, n=config.STATS_WINDOW)
        if s is not None:
            _text("sd {:.1f}mK".format(s * 1000.0), x0 + 4, H - 12, WHITE)
    _lcd.show()


def _page_stats():
    _lcd.fill(BLACK)
    _header("STATS")
    win = config.STATS_WINDOW

    def row(y, label, buf, key):
        m, s = _stats(buf, n=win)
        _text(label, 4, y, CYAN)
        _text("u" + _fmt(m, 3), 40, y, WHITE)
        sig = "--" if s is None else "{:.1f}".format(s * 1000.0)
        _text("s" + sig + "mK", 150, y, GREEN)
        # span + drift on the next line, abbreviated so the whole line fits 240 px
        sp = "--"
        if _mins[key] is not None and _maxs[key] is not None:
            sp = "{:.1f}".format((_maxs[key] - _mins[key]) * 1000.0)
        dr = _drift_rate(buf)
        drs = "--" if dr is None else "{:+.1f}".format(dr)
        _text("sp" + sp + "mK  dr" + drs + "mK/m", 16, y + 10, GREY)

    row(18, config.LABEL_A, _t1, "t1")
    row(42, config.LABEL_B, _t2, "t2")
    row(66, "dT", _dt, "dt")

    n = len([v for v in _t1 if v is not None])
    _text("n%d win%d %.0fs/smp" % (n, win, sampling.period_s()), 4, 92, GREY)
    settled = "STABLE" if _is_settled() else "SETTLING"
    _text_scaled(settled, 4, 108, 2, GREEN if settled == "STABLE" else AMBER)
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
        (_page_live, _page_averages, _page_trend, _page_delta,
         _page_stats)[_page]()
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
