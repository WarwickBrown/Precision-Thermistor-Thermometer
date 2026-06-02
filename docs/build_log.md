# Build log

Chronological bring-up, including the debugging dead-ends — kept because they're
the most useful part for anyone reproducing the work.

## 1. Front-end design

Differential half-bridge per probe; ADS1115 at PGA = 16 for 0.21 mK/LSB. Bridge
maths and resolution verified by round-trip simulation before any hardware.

## 2. Single-channel breadboard bring-up

* First run with nothing wired: I²C scan empty, as expected. Added a
  wait-for-ADC loop so a missing board no longer crashes the session.
* With the ADS1115 wired: `0x48` found, self-check ran.
* **Dead-end #1 — readings pinned at 100 kΩ, not tracking.** The thermistor's
  resistance changed at the jack but not in the readings. Cause: the diagnostic
  script was reading the AIN0–AIN1 pair while the bridge was wired to AIN2–AIN3.
  The ADS1115 has two differential pairs; the MUX bits select between them. Fix:
  point the MUX at the correct pair. (Confirmed differential mode was correct
  all along — it was just the wrong pair.)
* After the fix: resistance tracked finger-pinch up/down correctly. Front-end
  proven.

## 3. Connectors

TRS audio jacks used as thermistor connectors (Tip = sense node, Ring = GND,
Sleeve = shield grounded at the board end only). The thin inner conductors of
aux cable are **enamelled** — they must be tinned/scraped before they make
contact, which initially looked like a broken cable.

## 4. Two-channel (Option C)

Both probes on independent differential pairs: CH1 = AIN0−AIN1,
CH2 = AIN2−AIN3. Thermistor A → CH1, B → CH2 (so each matches its calibration
coefficients).

## 5. Pulsed excitation attempt — abandoned

* Built a high-side PMOS switch on the excitation rail.
* **Dead-end #2 — bridge dead with the PMOS in circuit.** Drain stuck at 0 V.
  Gate measured swinging 3.3 V ↔ 1.6 V, never reaching 0 V. Cause: the
  two-resistor gate "drive" was actually a passive divider that floats the gate
  to its midpoint; it cannot pull a high-side PMOS gate to 0 V.
* Switched to direct GPIO gate drive (active-low). Gate then swung fully; the
  PMOS conducted.
* **But:** the only available PMOS was an **IRFD9024**, a standard-threshold
  part. At −3.3 V V_GS it only partially enhances, dropping ~0.38 V with a
  temperature-dependent resistance. Decision: **remove the switch, run
  continuous excitation.** Self-heating becomes a constant, calibrated-out
  offset — cleaner than a drifting switch. Pulsing can return later with a
  logic-level PMOS.

## 6. Thermistor characterisation

UT71B sweep, B-model fit over 10–30 °C. Coefficients entered in config; firmware
conversion verified against the fit's own predictions.

## 7. Soldered to stripboard

* Added RC input filters and star grounding.
* **Dead-end #3 — huge readings after soldering.** Self-check showed Vdiff ≈
  −1.59 V on both channels (should be tens of mV). A software sign-invert turned
  it positive but the *magnitude* stayed ~1.59 V → the real fault was not a sign
  swap but a node sitting near a rail (a mis-wired or open input on the soldered
  board, found by measuring each AIN pin to GND). Lesson: a large differential
  means a node isn't at a divider midpoint — measure the pins before touching
  firmware.

## 8. Multi-page UI

LIVE / TREND / DELTA / STATS pages, joystick navigation, backlight control,
rolling σ and drift, STABLE/SETTLING flag. Logic verified in a desktop
simulation with mocked hardware.

## Next

* Formal stability / Allan-deviation campaign (breadboard vs soldered, with and
  without the RC filters) — the measurement the whole PoC hinges on.
* 3D-printed enclosure.
* Decide 16-bit-sufficient vs ADS1220.
