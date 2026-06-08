# Tools

Off-Pico helpers that run on a normal computer rather than on the
microcontroller. Install their dependencies once with:

```
pip install -r tools/requirements.txt
```

## `serial_logger.py`

Captures the CSV the firmware streams over USB serial straight onto the host
computer. It auto-detects the Pico's serial port, echoes the stream to the
screen, and saves it to a timestamped file in `data/` that you can then feed to
`analyse_log.py`. With `--plot` it also draws a live temperature chart. Needs
`pyserial` (and `matplotlib` only for `--plot`).

```
python tools/serial_logger.py                 # auto-detect port, save to data/
python tools/serial_logger.py --list          # list serial ports and exit
python tools/serial_logger.py --port COM5     # choose the port yourself
python tools/serial_logger.py --plot          # also draw a live chart
python tools/serial_logger.py --out run1.csv  # choose the output file
python tools/serial_logger.py --no-file       # echo only, do not save
```

This complements the on-Pico flash log. The flash log survives a USB
disconnect, while the serial capture is the easy way to pull a long run onto the
computer in real time.

## `analyse_log.py`

Stability analysis for the CSV the firmware produces (`log.csv`, a flash dump,
or a `serial_logger.py` capture). It reports per-channel statistics, the
common-mode-cancelled A-B difference channel, and the overlapping Allan
deviation against averaging time tau. The minimum of that curve answers the
project's central question, "is 16-bit enough?". Needs `numpy` and `matplotlib`.

```
python tools/analyse_log.py log.csv                 # stats + Allan plot -> stability.png
python tools/analyse_log.py log.csv --settle-min 10 # drop the first 10 min (warm-up)
python tools/analyse_log.py log.csv --col t1_c      # analyse a single column
python tools/analyse_log.py log.csv --no-plot       # stats only
```

The expected CSV columns are:

```
cycle, t_s, vdiff1_uv, r1_ohm, t1_c, vdiff2_uv, r2_ohm, t2_c, t_amb_c
```
