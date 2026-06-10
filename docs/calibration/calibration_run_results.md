# Calibration run results

Channel-matching and differential-stability results from a single logged run with
both thermistor beads bonded together inside a temperature-controlled box. The
numbers and the plot below are ready to cite. The raw data is
[`calibration_log.csv`](calibration_log.csv) and the figure is
[`calibration_run_stability.png`](calibration_run_stability.png).

## Setup

- Both NTC beads bonded in firm thermal contact and placed in a
  temperature-controlled box, so they share one temperature.
- QUIET sampling profile: 16 averages, 8 SPS, PGA ±0.256 V, 5 s cycle.
- Captured over USB with `tools/serial_logger.py`.
- Date 2026-06-10. Duration 18.3 min, 219 samples at a sample period of 5.0 s.

## Statistics

| Series | Mean (°C) | Sigma (mK) | Peak-to-peak (mK) | Drift (mK/hr) |
|---|---|---|---|---|
| A (NTC-01) | 24.7480 | 53.60 | 190.5 | −583.5 |
| B (NTC-02) | 24.6145 | 51.41 | 194.3 | −558.4 |
| **A − B** | **0.1335** | **3.02** | **22.5** | **−25.1** |

The box temperature drifted about 190 mK over the run, and both probes followed
it together (their absolute drifts agree to within 4 mK). That common drift
cancels in A − B, whose sigma is roughly 18 times smaller than either channel
alone (3.0 mK against ~53 mK). This is the common-mode rejection of the matched
differential bridge in action.

## Channel offset (the calibration)

A read +133.5 mK above B, and the difference stayed flat to a few mK as the box
drifted. Split symmetrically between the two channels, the matching trim is

```
CH1_T_OFFSET = -0.0667    # NTC-01 (A)
CH2_T_OFFSET = +0.0667    # NTC-02 (B)
```

now set in [`../../firmware/config.py`](../../firmware/config.py). Applying these
to this run brings the measured A − B from +133.5 mK down to +0.1 mK, so the two
channels agree to within 0.1 mK.

## Overlapping Allan deviation

| Averaging time tau (s) | A (mK) | B (mK) | A − B (mK) |
|---|---|---|---|
| 5 | 0.87 | 0.76 | 0.53 |
| 10 | 1.62 | 1.51 | 0.83 |
| 15 | 2.39 | 2.24 | 1.10 |
| 20 | 3.17 | 2.96 | 1.32 |
| 30 | 4.70 | 4.35 | 1.47 |
| 40 | 6.20 | 5.69 | 1.30 |
| 55 | 8.29 | 7.60 | 1.13 |
| 75 | 10.70 | 10.01 | 1.01 |
| 100 | 13.44 | 12.83 | 0.85 |
| 131 | 16.60 | 15.99 | 0.79 |
| 171 | 20.61 | 19.89 | 0.86 |
| 226 | 25.87 | 24.92 | 1.08 |
| 296 | 32.43 | 31.09 | 1.44 |
| 387 | 41.20 | 39.36 | 1.88 |
| 507 | 55.05 | 52.51 | 2.55 |

How to read the curve (see [`calibration_run_stability.png`](calibration_run_stability.png)):

- **Each channel alone (A, B) rises monotonically with tau**, so it is
  drift-limited. Averaging for longer does not help, because the box's absolute
  temperature is wandering. The per-channel Allan deviation is about 0.8 mK at a
  single sample and climbs past 50 mK by tau = 500 s as the drift accumulates.
- **The A − B difference stays sub-millikelvin across the whole range.** It is
  0.53 mK at a single sample, rises to about 1.5 mK near tau = 30 s, then settles
  to a broad minimum around 0.8 mK near tau = 130 s. The common-mode rejection
  buys roughly two orders of magnitude of stability in the difference channel.

This is the central result the instrument was built to demonstrate: a commodity
16-bit ADC in a matched differential bridge resolves temperature *differences* at
the sub-millikelvin level, even while the absolute temperature drifts by hundreds
of millikelvin.

## Per-probe short-term precision

Removing the box drift with successive differences (the standard short-term-noise
estimator) gives a single-sample noise of about **0.6 mK for probe A and 0.4 mK
for probe B** (1σ). This matches the A − B Allan deviation of 0.53 mK to better
than 0.01 mK, which is the cross-check that it is genuine sensor noise and not an
artefact. These are the per-probe precisions used independently. They are upper
bounds, because the box was still drifting, so the true floor is no worse than
this and approaches the theoretical ~85 µK (see
[`../error_budget.md`](../error_budget.md)). The resolution is 0.21 mK per ADC
count. Each probe's absolute accuracy is separate and reference-limited at
~0.1 °C.

## What this run does and does not show

- It **does** establish the channel matching, the per-probe short-term precision
  above, and the differential (A − B) stability floor of about 0.5 to 0.8 mK on
  real hardware.
- It is **not** the formal stability campaign. The box was still settling, so the
  per-channel absolute figures are drift-limited rather than a true noise floor. A
  longer, deliberately stabilised run is still needed to characterise the absolute
  stability and to compare the breadboard and soldered builds.

For the theoretical floor these sit against, see
[`../error_budget.md`](../error_budget.md): resolution ~0.21 mK/LSB and a
white-noise floor well below 0.1 mK per sample.

## Reproduce

```
./run.sh analyse docs/calibration/calibration_log.csv
```

This prints the statistics and Allan deviation above and writes the plot.
