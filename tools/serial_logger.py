#!/usr/bin/env python3
# =============================================================================
# serial_logger.py  --  capture the Pico's CSV stream on the host computer.
#
# The firmware already prints one CSV row per cycle over USB serial (and, when
# LOG_TO_FLASH is set, also to the Pico's own flash). This tool runs on the
# computer the Pico is plugged into, opens that serial port, echoes the stream
# to the screen, and saves it to a timestamped .csv file you can then feed to
# analyse_log.py. With --plot it also shows a live temperature chart.
#
# Each captured row gets a host wall-clock time column (host_time) appended, so
# the data can be matched against other measurements taken on the same computer.
# The Pico has no real-time clock of its own, so this host stamp is the reliable
# way to get an absolute time per row. Disable it with --no-timestamp.
#
# Runs on a normal computer (not the Pico). Needs pyserial (plus matplotlib
# only if you use --plot):
#     pip install pyserial matplotlib
#
# Usage:
#     python tools/serial_logger.py                 # auto-detect port, save to data/
#     python tools/serial_logger.py --port COM5     # pick the port yourself
#     python tools/serial_logger.py --plot          # also draw a live chart
#     python tools/serial_logger.py --out run1.csv  # choose the output file
#     python tools/serial_logger.py --list          # just list serial ports
# =============================================================================
import argparse
import os
import sys
import time
from datetime import datetime

# Raspberry Pi USB vendor id, used to spot a Pico when auto-detecting.
_RPI_VID = 0x2E8A
_HINTS = ("pico", "micropython", "board in fs mode", "rp2", "usb serial")


def _require_pyserial():
    try:
        import serial                      # noqa: F401
        import serial.tools.list_ports     # noqa: F401
        return serial
    except ImportError:
        sys.exit("This tool needs pyserial. Install it with:  pip install pyserial")


def list_ports():
    serial = _require_pyserial()
    from serial.tools import list_ports as lp
    ports = list(lp.comports())
    if not ports:
        print("No serial ports found.")
        return ports
    for p in ports:
        vid = ("%04x" % p.vid) if p.vid is not None else "----"
        print("  %-20s vid=%s  %s" % (p.device, vid, p.description))
    return ports


def auto_port():
    """Best guess at the Pico's serial port, or None."""
    serial = _require_pyserial()
    from serial.tools import list_ports as lp
    cands = list(lp.comports())
    for p in cands:                                   # prefer a Raspberry Pi VID
        if p.vid == _RPI_VID:
            return p.device
    for p in cands:                                   # then a hint in the name
        text = ("%s %s" % (p.description or "", p.manufacturer or "")).lower()
        if any(h in text for h in _HINTS):
            return p.device
    if len(cands) == 1:                               # only one port: use it
        return cands[0].device
    return None


def default_out_path():
    """data/log_YYYYmmdd_HHMMSS.csv next to the repo if data/ exists, else cwd."""
    stamp = time.strftime("log_%Y%m%d_%H%M%S.csv")
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(here), "data")
    if os.path.isdir(data_dir):
        return os.path.join(data_dir, stamp)
    return stamp


# ---------------------------------------------------------------------------
# Optional live plot of t1_c / t2_c against t_s. Kept deliberately simple and
# fully optional, so the capture works even without matplotlib.
#
# The chart shows a rolling window of the most recent max_points samples so its
# memory and redraw time stay flat no matter how long the capture runs. Older
# points scroll off the chart but are still written to the saved file, so the
# capture itself is effectively unlimited.
# ---------------------------------------------------------------------------
class LivePlot:
    def __init__(self, max_points=3000):
        import matplotlib.pyplot as plt
        self.plt = plt
        self.t, self.a, self.b = [], [], []
        self.max_points = max_points
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(9, 4))
        (self.la,) = self.ax.plot([], [], color="tab:green", lw=0.9, label="A (t1_c)")
        (self.lb,) = self.ax.plot([], [], color="tab:cyan", lw=0.9, label="B (t2_c)")
        self.ax.set_xlabel("t_s (s)")
        self.ax.set_ylabel("temperature (C)")
        self.ax.legend(loc="best", fontsize=8)
        self.ax.grid(alpha=0.3)
        self.fig.tight_layout()
        self._last_draw = 0.0

    def add(self, t_s, t1, t2):
        self.t.append(t_s); self.a.append(t1); self.b.append(t2)
        if len(self.t) > self.max_points:
            self.t = self.t[-self.max_points:]
            self.a = self.a[-self.max_points:]
            self.b = self.b[-self.max_points:]

    def maybe_draw(self):
        now = time.time()
        if now - self._last_draw < 0.5:        # throttle redraws to ~2 Hz
            return
        self._last_draw = now
        self.la.set_data(self.t, self.a)
        self.lb.set_data(self.t, self.b)
        self.ax.relim(); self.ax.autoscale_view()
        try:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass


def parse_row(line):
    """Return (t_s, t1_c, t2_c) from a data line, or None for headers/logs."""
    parts = line.split(",")
    if len(parts) < 8:
        return None
    try:
        return float(parts[1]), float(parts[4]), float(parts[7])
    except ValueError:
        return None


def stamp_line(line, enabled):
    """Append a host wall-clock timestamp column so each row can be matched to
    other data taken on the same computer. The CSV header gets the column name,
    a data row gets a local ISO timestamp (millisecond resolution), and status
    or log lines pass through unchanged. The column is appended last so it does
    not disturb the fixed firmware column order that analyse_log.py expects."""
    if not enabled or not line:
        return line
    if line.startswith("cycle"):
        return line + ",host_time"
    if line[0].isdigit():
        return line + "," + datetime.now().isoformat(timespec="milliseconds")
    return line


def main():
    ap = argparse.ArgumentParser(description="Capture the Pico CSV stream to a file.")
    ap.add_argument("--port", default=None, help="serial port (default: auto-detect)")
    ap.add_argument("--baud", type=int, default=115200,
                    help="baud rate (ignored by USB CDC, kept for compatibility)")
    ap.add_argument("--out", default=None, help="output CSV path (default: timestamped in data/)")
    ap.add_argument("--no-file", action="store_true", help="echo only, do not save a file")
    ap.add_argument("--plot", action="store_true", help="show a live temperature chart")
    ap.add_argument("--plot-points", type=int, default=3000,
                    help="points kept on the live chart window (the saved file keeps everything)")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--quiet", action="store_true", help="do not echo each line to the screen")
    ap.add_argument("--no-timestamp", action="store_true",
                    help="do not append a host wall-clock time column")
    args = ap.parse_args()

    if args.list:
        list_ports()
        return

    serial = _require_pyserial()

    port = args.port or auto_port()
    if not port:
        print("Could not auto-detect the Pico. Available ports:")
        list_ports()
        sys.exit("Pass one explicitly with --port.")

    try:
        ser = serial.Serial(port, args.baud, timeout=1)
    except Exception as e:
        sys.exit("Could not open %s (%s)" % (port, e))

    out_path = None
    fh = None
    if not args.no_file:
        out_path = args.out or default_out_path()
        fh = open(out_path, "a")

    plot = None
    if args.plot:
        try:
            plot = LivePlot(args.plot_points)
        except Exception as e:
            print("[plot] disabled (%s). Continuing with capture only." % e)

    print("Listening on %s%s. Press Ctrl-C to stop." %
          (port, "" if not out_path else " -> %s" % out_path))

    nlines = 0
    try:
        while True:
            # Read one line, and if the port drops (Pico reset or cable bump)
            # keep trying to reconnect so a long capture survives it. The file
            # stays open across reconnects; the firmware reprints its header on
            # restart, which analyse_log.py harmlessly skips.
            try:
                raw = ser.readline()
            except (OSError, serial.SerialException) as e:
                print("\n[serial] connection lost (%s). Reconnecting..." % e)
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None
                while ser is None:
                    time.sleep(1.0)
                    p = args.port or auto_port()
                    if not p:
                        continue
                    try:
                        ser = serial.Serial(p, args.baud, timeout=1)
                        port = p
                        print("[serial] reconnected on %s." % p)
                    except Exception:
                        ser = None
                continue
            if not raw:
                if plot:
                    plot.maybe_draw()
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            out = stamp_line(line, not args.no_timestamp)
            if not args.quiet:
                print(out)
            if fh:
                fh.write(out + "\n")
                fh.flush()
            nlines += 1
            if plot:
                row = parse_row(line)
                if row:
                    plot.add(*row)
                plot.maybe_draw()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        try:
            ser.close()
        except Exception:
            pass
        if fh:
            fh.close()
            print("Saved %d lines to %s" % (nlines, out_path))


if __name__ == "__main__":
    main()
