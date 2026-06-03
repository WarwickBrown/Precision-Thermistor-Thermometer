#!/usr/bin/env python3
# =============================================================================
# analyse_log.py  --  stability analysis for The Box thermistor logger.
#
# Reads the CSV produced by the Pico (log.csv, or console capture) and reports:
#   * per-channel statistics (mean, sigma, peak-to-peak, drift)
#   * the A-B difference channel (common-mode-cancelled)
#   * the OVERLAPPING ALLAN DEVIATION vs averaging time tau
#
# The Allan deviation is the key plot: it shows how much your reading improves
# as you average for longer, and the tau at which drift starts to dominate
# (the minimum of the curve = best achievable stability and the optimal
# averaging time). This is the number that answers "is 16-bit enough?".
#
# Runs on a normal computer (not the Pico). Requires numpy + matplotlib:
#     pip install numpy matplotlib
#
# Usage:
#     python analyse_log.py log.csv
#     python analyse_log.py log.csv --settle-min 10      # drop first 10 minutes
#     python analyse_log.py log.csv --col t1_c           # analyse one column
#     python analyse_log.py log.csv --out stability.png
# =============================================================================
import argparse
import sys
import numpy as np

CSV_COLUMNS = ["cycle", "t_s", "vdiff1_uv", "r1_ohm", "t1_c",
               "vdiff2_uv", "r2_ohm", "t2_c", "t_amb_c"]


def load_csv(path):
    """Robust loader: skips the header and any non-data lines (e.g. [loop]...)."""
    rows = []
    with open(path) as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith("[") or ln.startswith("cycle"):
                continue
            parts = ln.split(",")
            if len(parts) < 8:
                continue
            try:
                rows.append([float(p) if p != "" else np.nan
                             for p in parts[:9]])
            except ValueError:
                continue
    if not rows:
        sys.exit("No data rows parsed from %s" % path)
    # pad short rows (missing t_amb) to 9 columns
    width = max(len(r) for r in rows)
    for r in rows:
        r += [np.nan] * (width - len(r))
    arr = np.array(rows, dtype=float)
    return {CSV_COLUMNS[i]: arr[:, i] for i in range(min(width, len(CSV_COLUMNS)))}


def basic_stats(x, tau0):
    """Return dict of mean, sigma, p-p, drift (per hour) for a 1-D series."""
    x = x[~np.isnan(x)]
    if x.size < 2:
        return None
    n = x.size
    mean = float(np.mean(x))
    sigma = float(np.std(x, ddof=1))
    pp = float(np.ptp(x))
    # linear drift via least-squares slope over the record
    t = np.arange(n) * tau0
    slope = np.polyfit(t, x, 1)[0]          # units per second
    drift_per_hr = slope * 3600.0
    return {"n": n, "mean": mean, "sigma": sigma, "pp": pp,
            "drift_per_hr": drift_per_hr, "minutes": n * tau0 / 60.0}


def overlapping_adev(y, tau0):
    """Overlapping Allan deviation of a series of direct readings y.

    Treats y as frequency-like data, converts to phase by cumulative sum, and
    applies the standard overlapping ADEV estimator. Returns (taus, adev, err).
    """
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    N = y.size
    if N < 4:
        return np.array([]), np.array([]), np.array([])
    # phase data (length N+1)
    x = np.concatenate([[0.0], np.cumsum(y)]) * tau0
    taus, adevs, errs = [], [], []
    m = 1
    m_max = (N - 1) // 2
    while m <= m_max:
        tau = m * tau0
        d = x[2 * m:] - 2 * x[m:-m] + x[:-2 * m]
        n = d.size
        if n < 1:
            break
        avar = np.sum(d * d) / (2.0 * tau * tau * n)
        adev = np.sqrt(avar)
        taus.append(tau)
        adevs.append(adev)
        errs.append(adev / np.sqrt(n))      # rough 1-sigma confidence
        m = max(m + 1, int(np.ceil(m * 1.3)))   # ~log-spaced
    return np.array(taus), np.array(adevs), np.array(errs)


def fmt_mk(v):
    """Format a temperature value in mK with sign."""
    return "{:+.2f} mK".format(v * 1000.0)


def main():
    ap = argparse.ArgumentParser(description="Stability / Allan-deviation analysis")
    ap.add_argument("csv", help="log.csv from the Pico")
    ap.add_argument("--settle-min", type=float, default=0.0,
                    help="discard the first N minutes (warm-up)")
    ap.add_argument("--col", default=None,
                    help="analyse a single column (e.g. t1_c); default = all temps")
    ap.add_argument("--tau0", type=float, default=None,
                    help="sample period in s (default: auto from t_s column)")
    ap.add_argument("--out", default="stability.png", help="output plot file")
    ap.add_argument("--no-plot", action="store_true", help="stats only, no plot")
    args = ap.parse_args()

    data = load_csv(args.csv)

    # sample period
    if args.tau0:
        tau0 = args.tau0
    elif "t_s" in data and np.sum(~np.isnan(data["t_s"])) > 2:
        dt = np.diff(data["t_s"][~np.isnan(data["t_s"])])
        tau0 = float(np.median(dt))
    else:
        tau0 = 5.0
    print("Sample period tau0 = %.2f s  (%d rows)" % (tau0, len(data["cycle"])))

    # settle trim
    if args.settle_min > 0:
        drop = int(args.settle_min * 60.0 / tau0)
        for k in data:
            data[k] = data[k][drop:]
        print("Discarded first %.1f min (%d rows) as warm-up." % (args.settle_min, drop))

    # which columns
    if args.col:
        cols = [args.col]
    else:
        cols = ["t1_c", "t2_c"]
    # difference channel
    have_delta = ("t1_c" in data and "t2_c" in data and not args.col)
    if have_delta:
        delta = data["t1_c"] - data["t2_c"]

    # ---- statistics ----
    print("\n================  STATISTICS  ================")
    label = {"t1_c": "Probe A", "t2_c": "Probe B"}
    for c in cols:
        if c not in data:
            continue
        s = basic_stats(data[c], tau0)
        if not s:
            continue
        print("\n%s  (%s, %.1f min, n=%d)" % (label.get(c, c), c, s["minutes"], s["n"]))
        print("  mean      : %.4f C" % s["mean"])
        print("  sigma     : %s  (%.4f C)" % (fmt_mk(s["sigma"]), s["sigma"]))
        print("  peak-peak : %s" % fmt_mk(s["pp"]))
        print("  drift     : %s / hour" % fmt_mk(s["drift_per_hr"]))

    if have_delta:
        s = basic_stats(delta, tau0)
        if s:
            print("\nA - B difference  (common-mode cancelled)")
            print("  mean      : %.4f C" % s["mean"])
            print("  sigma     : %s" % fmt_mk(s["sigma"]))
            print("  peak-peak : %s" % fmt_mk(s["pp"]))
            print("  drift     : %s / hour" % fmt_mk(s["drift_per_hr"]))

    # ---- Allan deviation ----
    print("\n================  ALLAN DEVIATION  ================")
    adev_sets = {}
    series = list(cols)
    for c in series:
        if c in data:
            taus, ad, er = overlapping_adev(data[c], tau0)
            if taus.size:
                adev_sets[label.get(c, c)] = (taus, ad, er)
    if have_delta:
        taus, ad, er = overlapping_adev(delta, tau0)
        if taus.size:
            adev_sets["A - B"] = (taus, ad, er)

    for name, (taus, ad, er) in adev_sets.items():
        i = int(np.argmin(ad))
        print("\n%s:" % name)
        print("  ADEV @ tau=%.0fs (1 sample) : %s" % (taus[0], fmt_mk(ad[0])))
        print("  best ADEV                  : %s  at tau=%.0f s (%.1f min)"
              % (fmt_mk(ad[i]), taus[i], taus[i] / 60.0))
        print("  -> optimal averaging time  : ~%.0f s" % taus[i])

    # ---- plots ----
    if args.no_plot:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("\n(matplotlib unavailable: %s -- skipping plot)" % e)
        return

    fig, (axT, axA) = plt.subplots(2, 1, figsize=(9, 9))

    tmin = np.arange(len(data["t1_c"])) * tau0 / 60.0 if "t1_c" in data else None
    for c, col in (("t1_c", "tab:green"), ("t2_c", "tab:cyan")):
        if c in data:
            t = np.arange(len(data[c])) * tau0 / 60.0
            axT.plot(t, data[c], color=col, lw=0.8, label=label.get(c, c))
    axT.set_xlabel("time (min)")
    axT.set_ylabel("temperature (C)")
    axT.set_title("Time series")
    axT.legend(loc="best", fontsize=8)
    axT.grid(alpha=0.3)

    for name, (taus, ad, er) in adev_sets.items():
        axA.errorbar(taus, ad * 1000.0, yerr=er * 1000.0, marker="o",
                     ms=3, lw=0.9, capsize=2, label=name)
    axA.set_xscale("log")
    axA.set_yscale("log")
    axA.set_xlabel("averaging time tau (s)")
    axA.set_ylabel("Allan deviation (mK)")
    axA.set_title("Overlapping Allan deviation")
    axA.grid(alpha=0.3, which="both")
    axA.legend(loc="best", fontsize=8)

    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print("\nSaved plot -> %s" % args.out)


if __name__ == "__main__":
    main()