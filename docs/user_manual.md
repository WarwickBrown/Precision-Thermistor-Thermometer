# User manual

A short guide to running the thermometer day to day: what the screens show, what
the buttons do, how often it updates, and how to read the data on a connected
computer.

## Powering on

Plug the Pico into USB. The firmware (`main.py`) starts on its own.

* If the ADS1115 is not detected, the screen shows `Waiting for ADS1115...` and
  it keeps retrying. Check the I2C wiring if it sticks here.
* Once the ADC is found it runs a one-time self-check (reported over USB) and
  then shows the LIVE page. If a channel is railed it briefly shows
  `Bridge OUT OF RANGE`, which usually means a probe is unplugged or the range
  needs widening.

## How often it updates (read this first)

This is the thing that trips people up. The instrument takes one full reading per
**measurement cycle**, and the numbers on screen refresh once per cycle:

| Profile | Cycle | What it is for |
|---|---|---|
| **QUIET** | about every 5 seconds | the quiet, roughly 1 mK logging setup |
| **FAST** | about every 1 second | watching the screen and fast changes |

So in QUIET the readings update only every 5 seconds or so. Between cycles the
last reading simply stays on screen. That is normal, not a frozen device. If you
want the numbers to move quickly, switch to FAST (long-press the joystick, see
below) and a red **FAST** badge appears in the top right.

The buttons themselves respond immediately, during a measurement as well as
between them. The page also redraws the moment you press a button.

## The screens

Five pages. Move between them with **KEY A** (next) and **KEY B** (previous).

| Page | Shows |
|---|---|
| **LIVE** | Each probe in large type: temperature (°C, to 1 mK) and resistance (Ω). Below that the A-B difference (`dT`), the rolling noise (`sig`, in mK), a STABLE/SETTLING flag, and the cycle count. |
| **AVERAGES** | Per probe, the rolling mean over a long window (big) and a short window (small), plus the long-window noise (`sd`). Use this page when matching the probes (see calibration). |
| **TREND** | A scrolling chart of both temperatures, A in green and B in cyan, sharing an autoscaled axis. The hi/lo numbers are the axis range and the bottom number is the time span shown. |
| **DELTA** | A scrolling chart of A-B only. This is the most sensitive view because anything both probes share cancels out. |
| **STATS** | Per probe: mean (`u`), noise (`s`), min-to-max span, and drift rate. At the bottom, a large STABLE or SETTLING flag. |

STABLE means the recent noise has dropped below the settle threshold. SETTLING
means it is still moving.

## The controls

| Control | Action |
|---|---|
| **KEY A** | next page |
| **KEY B** | previous page |
| **Joystick LEFT / RIGHT** | previous / next page (backup for KEY A / KEY B) |
| **Joystick UP** | cycle the backlight: full, then dim, then off, then full |
| **Joystick DOWN** | reset the statistics, history, and min/max |
| **Joystick press (short tap)** | HOLD: freeze the charts and statistics so you can read them. The live numbers keep updating. Tap again to resume. A HOLD tag shows in the top right. |
| **Joystick press (long, about 1 second)** | switch the sampling profile between QUIET and FAST |

A couple of notes that match how it behaves:

* KEY A and KEY B are the most reliable way to change page. The joystick
  directions also work but are a little less positive.
* The backlight is a heat source close to the sensors, so turning it down or off
  with joystick UP is worth doing during a careful measurement.
* DOWN clears the running statistics and the chart history. Use it to start a
  fresh measurement window.

## Reading the data on a connected computer

Yes, the instrument streams its data out over the same USB cable. Each
measurement cycle it prints one line of CSV over USB serial (the Pico shows up as
a serial port, often named like `/dev/cu.usbmodem...` on macOS, `/dev/ttyACM0` on
Linux, or `COMx` on Windows). The baud rate does not matter for USB.

The columns are:

```
cycle, t_s, vdiff1_uv, r1_ohm, t1_c, vdiff2_uv, r2_ohm, t2_c, t_amb_c
```

Three ways to see it, easiest first:

1. **The capture tool (recommended).** From the repo on the computer:
   ```
   python tools/serial_logger.py            # auto-detects the Pico, saves to data/
   python tools/serial_logger.py --plot     # also shows a live chart
   ```
   It finds the port, echoes the stream, and saves a timestamped CSV in `data/`
   that you can then run through `tools/analyse_log.py`.
2. **Thonny.** The Shell pane shows the CSV stream live, because the Pico is
   printing to its console. Good for a quick look.
3. **Any serial terminal** (screen, PuTTY, minicom) opened on the Pico's port.

There is also a backup copy on the Pico itself. With `LOG_TO_FLASH` on (the
default) the same CSV is appended to `log.csv` in the Pico's flash, so a run
survives a USB unplug. Pull that file off with Thonny or
`mpremote cp :log.csv .`.

To turn the console stream on or off, set `LOG_TO_CONSOLE` in `config.py`. The
flash log is `LOG_TO_FLASH`.

## Quick troubleshooting

| Symptom | Cause and fix |
|---|---|
| Screen is dark | The backlight may be off. Press joystick UP to cycle it back to full. |
| Numbers only change every few seconds | That is the QUIET cycle. Long-press the joystick for FAST. |
| A page will not change | Use KEY A / KEY B, which are the most reliable. The joystick L/R are a backup. |
| Screen stuck on `Waiting for ADS1115` | The ADC is not on the I2C bus. Check SDA, SCL, power, ground, and the address pin. |
| `Bridge OUT OF RANGE` at start | A channel is railed, usually an unplugged or miswired probe, or the range is too small. See `config.py` (`MODE` / FSR). |
| A and B disagree at the same temperature | That is a matching offset. See [`calibration_procedure.md`](calibration_procedure.md). |

## Going further

* Matching the two probes and calibrating: [`calibration_procedure.md`](calibration_procedure.md).
* What the precision and accuracy actually are: [`error_budget.md`](error_budget.md).
* Analysing a logged run: [`../tools/README.md`](../tools/README.md).
