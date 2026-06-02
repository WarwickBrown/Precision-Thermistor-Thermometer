# Precision Thermistor Thermometer

A two-channel, sub-10-millikelvin-class temperature **measurement and logging
instrument** built around a Raspberry Pi Pico W and a 16-bit ADS1115 ADC, using
matched 100 kΩ NTC thermistors in differential Wheatstone half-bridges.

It was developed as the instrumentation for **"The Box"** — a passively
temperature-stabilised enclosure for a photonic reservoir-computing experiment,
where a multimode fibre acts as the nonlinear mixing medium and its refractive
index (and therefore the computation) is temperature-sensitive. Characterising
and controlling that thermal environment is what this instrument is for.

> **Status:** working two-channel prototype on soldered stripboard. Thermistors
> characterised; live UI complete; rigorous stability (Allan-deviation)
> characterisation and the 3D-printed enclosure are in progress. See
> [Project status](#project-status).

---

## Why this design

The goal was to find out, cheaply, **how much temperature resolution is
actually achievable with a commodity 16-bit ADC** before committing to a more
complex (and more expensive) 24-bit sigma-delta design (ADS1220). Rather than
assume the 24-bit part is necessary, this project proves out the 16-bit approach
end-to-end and measures its real noise floor.

Key design decisions and the reasoning behind them are documented in
[`docs/design_notes.md`](docs/design_notes.md).

---

## How it works

```
            +3V3 (or ADC_VREF)
                 │
     ┌───────────┴───────────┐         (one half-bridge per channel)
     │                       │
    R_a (100k)              R_top (100k)
     │                       │
   NODE_A ───► AINP        NODE_B ───► AINN     ADS1115 reads (AINP − AINN)
     │                       │                  differentially, PGA-amplified
    R_b (100k)              NTC (100k, on cable)
     │                       │
    GND                     GND
```

* Each thermistor sits in its own **differential half-bridge**. The bridge
  output is ~0 V at balance (≈25 °C), so the ADC's smallest range (±0.256 V,
  PGA = 16) can be used for maximum resolution around the operating point.
* The ADS1115 has two differential pairs, so **two probes** are read:
  channel 1 = AIN0−AIN1, channel 2 = AIN2−AIN3.
* Resistance is recovered from the measured differential voltage, then
  converted to temperature via a **narrow-range B-model** fit (see
  [Calibration](#calibration)).
* A Waveshare Pico-LCD-1.14 provides a **multi-page live UI**; readings also
  stream as CSV over USB serial for logging.

### Resolution (theoretical)

| Quantity | Value |
|---|---|
| Bridge sensitivity (V_exc = 3.3 V) | ≈ 36.6 mV/K |
| ADS1115 LSB at PGA = 16 (±0.256 V) | 7.81 µV |
| **Resolution** | **≈ 0.21 mK / LSB** |
| Usable span at PGA = 16 | ≈ ±7 K around bridge balance |

These figures are derived and verified by round-trip simulation in
[`docs/design_notes.md`](docs/design_notes.md).

---

## Measured performance

> Numbers marked _(prelim.)_ are early bench observations, not yet a rigorous
> characterisation. The formal stability campaign is the next milestone.

| Metric | Value | Notes |
|---|---|---|
| Single-shot noise, settled (breadboard) | ~±4 mK p-p _(prelim., eyeballed)_ | continuous excitation, no RC filter |
| Rolling σ (32-sample), simulated 3 mK input | ~2.4 mK | sanity check of stats pipeline |
| Thermistor B-value match (A vs B) | 0.1 % | 3816.6 K vs 3820.8 K |
| Thermistor R₀ match (A vs B) | 0.3 % | ~99.9 kΩ vs ~99.6 kΩ at 25 °C |
| Absolute accuracy | ~0.1 °C | limited by reference probe (UNI-T UT71B) |
| **Stability / Allan deviation (Veroboard)** | **TODO** | formal logged campaign pending |

A note on _accuracy vs precision_: the ~0.1 °C absolute figure is set by the
reference thermometer used during calibration. The instrument's **relative
stability** — the quantity that matters for thermal control — is far better and
is what the Allan-deviation campaign will quantify.

---

## Repository layout

```
the-box-thermometer/
├── README.md                 ← this file
├── LICENSE
├── firmware/                 ← MicroPython for the Pico W
│   ├── config.py             ← all tunable constants live here
│   ├── ads1115.py            ← minimal differential ADS1115 driver
│   ├── bridge.py             ← bridge maths + B-model / Steinhart-Hart
│   ├── ds18b20_reader.py     ← optional 1-Wire ambient sensor
│   ├── display.py            ← multi-page LCD UI (joystick-navigated)
│   ├── main.py               ← measurement loop
│   ├── test_single.py        ← single-channel bring-up diagnostic
│   └── test_pmos.py          ← excitation-switch polarity diagnostic
├── hardware/
│   ├── schematic_bridge.png  ← bridge + ADC front-end
│   ├── netlist.md            ← full from-to netlist
│   └── bom.md                ← bill of materials
├── docs/
│   ├── design_notes.md       ← design rationale + noise budget
│   ├── characterisation.md   ← thermistor calibration write-up
│   └── build_log.md          ← chronological bring-up / debugging notes
├── enclosure/
│   └── README.md             ← 3D-printed cover (STL to be added)
├── data/                     ← logged runs (CSV)
└── images/                   ← photos, screenshots
```

---

## Quick start

1. Flash **MicroPython for the Pico W** (`.uf2` from micropython.org).
2. Copy everything in [`firmware/`](firmware/) to the Pico's root, plus
   Waveshare's `lcd_1inch14.py` driver (from the Waveshare wiki for the
   Pico-LCD-1.14).
3. Edit [`firmware/config.py`](firmware/config.py): set your measured excitation
   voltage, resistor values, and thermistor coefficients.
4. Reset the Pico. `main.py` runs automatically; readings appear on the LCD and
   as CSV over USB serial.

Bring-up diagnostics (`test_single.py`, `test_pmos.py`) are documented in
[`docs/build_log.md`](docs/build_log.md).

---

## The display

Four pages, cycled with the joystick **LEFT / RIGHT**:

| Page | Shows |
|---|---|
| **LIVE** | Both probes: temperature, resistance, ΔT, rolling σ |
| **TREND** | Scrolling chart of A and B temperature (shared autoscale) |
| **DELTA** | Scrolling chart of A−B (common-mode-cancelled, most sensitive) |
| **STATS** | Mean, σ, min–max span, drift rate, STABLE/SETTLING flag |

Buttons: **KEY A** cycles backlight (full → dim → off — useful because the
backlight is a heat source near the sensors); **KEY B** resets statistics;
**joystick press** toggles a hold/freeze.

---

## Calibration

Thermistors are characterised individually against a UNI-T UT71B reference, then
fitted with a two-parameter B-model over the 10–30 °C operating window:

```
T(°C) = B / (ln R − intercept) − 273.15
```

| Probe | B (K) | intercept | R₀ @ 25 °C |
|---|---|---|---|
| A (NTC-01) | 3816.56 | −1.288504 | ~99.9 kΩ |
| B (NTC-02) | 3820.82 | −1.306170 | ~99.6 kΩ |

Full method and residuals: [`docs/characterisation.md`](docs/characterisation.md).

---

## Project status

- [x] Differential bridge + ADS1115 front-end designed and simulated
- [x] Single-channel bring-up on breadboard
- [x] Two-channel (Option C) differential operation
- [x] Thermistor characterisation (B-model)
- [x] Soldered onto stripboard with RC input filters + star ground
- [x] Multi-page LCD UI
- [ ] Formal stability / Allan-deviation campaign (breadboard vs soldered)
- [ ] 3D-printed enclosure (STL)
- [ ] Decision: is 16-bit sufficient, or move to ADS1220?

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built as instrumentation for a photonic reservoir-computing experiment.
Firmware and circuit developed iteratively on the bench; see
[`docs/build_log.md`](docs/build_log.md) for the full bring-up story including
the debugging dead-ends (they're educational).
