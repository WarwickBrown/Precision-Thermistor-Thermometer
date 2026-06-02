# Design notes

The reasoning behind the circuit and firmware choices. This is the "why," not
the "how" — see the README for usage and `build_log.md` for the chronological
bring-up.

## Goal

Determine how much temperature resolution a commodity **16-bit ADS1115** can
deliver in a thermistor bridge, before committing to a 24-bit ADS1220. The
worry: a 24-bit part may not yield usable extra bits once real-world noise is
accounted for, so the cheaper option is validated first.

## Sensor choice: 100 kΩ NTC

* High resistance ⇒ lead and contact resistance are negligible. A 1 m cable at
  ~0.2 Ω is ~2 ppm of a 100 kΩ sensor, so no Kelvin/4-wire sensing is needed.
* Large dR/dT: ≈ −4400 Ω/K near 25 °C (B ≈ 3820 K), giving strong sensitivity.

## Topology: differential half-bridge

Each probe sits in a half-bridge; the ADC reads the difference between the
sense node and a reference node.

```
dV/dT ≈ (V_exc / 4) · (B / T²) ≈ V_exc · 11.1 mV/K
      ≈ 36.6 mV/K at V_exc = 3.3 V
```

Reading differentially (AINP − AINN) rather than single-ended:

* rejects excitation-supply noise as common-mode,
* keeps the signal near 0 V at balance so PGA = 16 (±0.256 V) can be used,
* uses the ADS1115's full ±32768 signed range.

## Noise / resolution budget

| Quantity | Value |
|---|---|
| LSB at PGA = 16 | 7.81 µV |
| ADS1115 input-referred noise (8 SPS) | ~2 µV RMS |
| Bridge sensitivity | 36.6 mV/K |
| **Resolution** | **0.21 mK / LSB** |
| **Noise floor (single sample)** | **~55 µK RMS** |
| Span at PGA = 16 | ±7 K around balance |

So resolution and white-noise floor are comfortably sub-mK; the real limits are
**self-heating, reference-resistor drift, and layout/EMI**, addressed below.

## Excitation: continuous DC (pulsing deferred)

Pulsed excitation was planned to cut thermistor self-heating, switched by a
high-side PMOS. The only available PMOS was an **IRFD9024 — a standard-threshold
part, not logic-level**. At 3.3 V gate drive it never fully enhances, sitting in
its linear region with a large, temperature-dependent on-resistance. That would
inject drift into V_exc that mimics a temperature signal — worse for precision
than the problem it solves.

Decision: **run continuous excitation.** Self-heating (~27 mK at 3.3 V across the
sense leg) is a *constant* offset that calibration absorbs; it only harms
precision if the dissipation-to-environment coupling fluctuates, which it does
not inside the still air of the enclosure. Pulsing can be revisited later with a
proper logic-level PMOS. To reduce self-heating passively without a switch, a
series dropper resistor can lower V_exc (~10× less dissipation at ~1 V) at the
cost of some sensitivity.

## Ratiometric-ish reference

The bridge is excited from the Pico's filtered `ADC_VREF` pin (or 3V3). The
ADS1115 has a fixed internal reference, so the measurement is not fully
ratiometric — true ratiometric operation (external VREF tied to excitation) is
a reason to move to the ADS1220 later.

## Front-end filtering

A differential RC filter sits at each ADC input: 1 kΩ in series per line + a
100 nF differential cap across the pair (optional 10 nF common-mode caps to
ground). Corner ≈ 800 Hz — far above the thermal signal bandwidth, far below
mains hum / RF / digital switching. The 1 kΩ is kept small so the ADS1115's
finite PGA input impedance (~700 kΩ at PGA = 16) introduces only a fraction of a
percent of (calibrated-out) scale error; larger series R would interact badly
with the switched-cap input.

## Grounding

Star ground: analog returns (bridge bottoms, ADC GND, decoupling, filter caps)
on one strip; digital returns (Pico, LCD, I²C) on another; the two joined by a
single jumper at the ADS1115 GND pin. On stripboard, strip resistance (~5 mΩ /
30 mm) means shared digital return current would inject µV-level errors into the
analog reference — hence the separation.

## Calibration model

A two-parameter B-model over 10–30 °C is used rather than full-range
Steinhart-Hart: it gives better residuals in the operating window (the
extreme-temperature bath points were taken under non-equilibrium conditions and
added scatter) and inverts trivially. Both models are implemented in
`bridge.py`; `config.TEMP_MODEL` selects between them.

## Verification

The bridge inverse-maths and resolution were checked by round-trip simulation
(pick a true NTC resistance → compute the differential voltage the ADC would
see → run it back through the firmware maths → confirm recovery). The firmware's
B-model and Steinhart-Hart conversions were checked against the characterisation
spreadsheet's own predicted temperatures and matched to the third decimal.
