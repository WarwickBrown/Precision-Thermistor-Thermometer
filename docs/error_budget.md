# Theoretical accuracy and precision

This is the error budget for the instrument: where the numbers in the README
come from, and what limits each of them. It answers two separate questions that
are easy to confuse.

* **Accuracy** is how close a reading is to the true temperature on an absolute
  scale. For this instrument it is set almost entirely by the reference probe
  used during calibration, not by the electronics.
* **Precision** (resolution and short-term stability) is how small a *change* the
  instrument can resolve. This is what matters for thermal control, and it is far
  finer than the accuracy.

All figures below are derived from the design and the component datasheets. They
are the targets the formal Allan-deviation campaign will confirm or correct on
real hardware. That measurement is still pending.

## Headline numbers

| Quantity | Value | Set by |
|---|---|---|
| Resolution | ≈ 0.21 mK / LSB | ADC LSB ÷ bridge sensitivity |
| Single-sample precision | ≈ 0.085 mK RMS | ADC noise + quantisation |
| Averaged precision (QUIET, 16×) | ≈ 0.02 mK RMS | white noise ÷ √N |
| Averaged precision (FAST, 4×) | ≈ 0.04 mK RMS | white noise ÷ √N |
| Absolute accuracy | ≈ 0.1 °C | UNI-T UT71B reference probe |

The gap between precision (tens of µK) and accuracy (about 0.1 °C) is roughly a
factor of a thousand. That gap is the whole point. This is a precision relative
thermometer, not an accurate absolute one.

## Where the resolution comes from

The half-bridge sensitivity is

```
S = dVdiff/dT = V_exc · B / (4 · T²)  ≈ 35 to 37 mV/K
```

at V_exc = 3.3 V, B ≈ 3820 K, near 25 °C. The ADS1115 at PGA = 16 (±0.256 V)
has an LSB of

```
LSB = 2 · 0.256 V / 65536 = 7.81 µV
```

so one LSB is `7.81 µV / 36 mV/K ≈ 0.21 mK`. The sensitivity falls slowly as the
probe moves away from 25 °C, so the resolution is best near the bridge balance
point and degrades gently towards the edges of the ±7 K usable span.

## Random noise (sets short-term precision)

These are uncorrelated sample to sample, so averaging N samples reduces them by
√N. The firmware does this in both profiles (16 averages in QUIET, 4 in FAST).

| Source | Per sample | Notes |
|---|---|---|
| ADC input-referred noise (~2 µV RMS at 8 SPS) | ≈ 56 µK | dominant white-noise term |
| Quantisation (LSB / √12) | ≈ 64 µK | inherent to a 16-bit conversion |
| Johnson noise of the 100 kΩ arms (~5 Hz ENBW) | ≈ 3 µK | well below the ADC floor |
| **Combined single sample** | **≈ 85 µK RMS** | root-sum-square of the above |
| Combined after 16× averaging (QUIET) | ≈ 21 µK | the ~1 mK profile has headroom to spare |
| Combined after 4× averaging (FAST) | ≈ 43 µK | still sub-0.1 mK |

Averaging only helps until drift takes over. The point where it stops helping,
and the best stability the instrument actually reaches, is exactly what the
overlapping Allan deviation in `tools/analyse_log.py` measures.

## Systematic and drift terms

These do not average away. Most are either constant (and so removed by
calibration) or slow drift that only matters over minutes to hours.

| Source | Magnitude | Affects | Constant or drift |
|---|---|---|---|
| Excitation (V_exc) noise and drift | rejected near balance | precision | the differential bridge cancels it as common-mode |
| Reference-resistor tolerance | calibrated out | accuracy | the resistors are measured and entered in `config.py` |
| Reference-resistor tempco (10 to 50 ppm/°C) | ≈ 0.2 to 1.2 mK per °C of *ambient* change | precision/drift | drift, largely cancelled in the A−B channel |
| ADC gain error (±0.15 % typ) | ≈ 1.5 mK per K of offset from balance | accuracy | near-constant, a scale error |
| ADC integral non-linearity (±1 LSB) | ≈ 0.21 mK | accuracy | near-constant |
| Self-heating of the NTC (~27 µW) | ≈ 27 mK offset | accuracy | constant in still air, calibrated out |
| Lead and contact resistance (~0.2 Ω) | ≈ 0.05 mK | accuracy | constant, negligible at 100 kΩ |
| B-model fit residual | ≈ 0.1 °C absolute | accuracy | set by the reference probe, not the slope |

The reference-resistor tempco is the main thing standing between the instrument
and microkelvin stability. A change in the ambient around the bridge resistors
shifts the balance point by `α · T² / B` per degree, which is about 0.6 mK per °C
for an ordinary 25 ppm/°C resistor. This is why the design keeps the reference
cluster isothermal and away from the LCD backlight, and why low-tempco resistors
are worth using.

## Why the differential design helps twice

* **Within a channel,** reading `AINP − AINN` makes excitation-supply noise a
  common-mode signal that the bridge rejects. Near balance the residual
  sensitivity to V_exc is close to zero.
* **Across channels,** the A−B difference cancels anything both probes see in
  common: shared ambient drift, shared resistor tempco, shared self-heating
  coupling. That is why A−B is the most stable channel and the best place to look
  for a small real signal against a drifting background.

## Measured so far (first calibration run)

A bonded-probe run in a temperature-controlled box gives the first real numbers
to set against the budget above (full write-up in
[`calibration/calibration_run_results.md`](calibration/calibration_run_results.md)):

| Quantity | Measured | Notes |
|---|---|---|
| Resolution | 0.21 mK/LSB | as designed |
| Single-channel noise (1σ, single sample) | ~0.4 to 0.6 mK | drift removed via successive differences (A ~0.6, B ~0.4), versus an as-measured Allan of ~0.8 mK inflated by box drift |
| Differential A−B stability | ~0.5 to 0.8 mK (Allan) | drift cancels, the real floor reached |
| Absolute accuracy | ~0.1 °C | reference-limited, unchanged by matching |

The single-channel noise is the short-term scatter once the box's own drift is
removed (the successive-difference estimate, which matches the A−B Allan
deviation to better than 0.01 mK). The raw single-channel Allan deviation on this
run was ~0.8 mK only because the box was still drifting.

**Used independently** (each probe as its own absolute thermometer), a channel
has a single-sample repeatability of about half a millikelvin, but its absolute
reading is only good to ~0.1 °C and its longer-term stability is set by ambient
and reference-resistor drift, not by ADC noise. **Used differentially** (A−B),
the common-mode rejection removes that drift and the pair reaches the
sub-millikelvin floor. This run did not pin the single-channel noise floor on its
own, because the box was still drifting, so the true single-channel floor sits
somewhere between the differential result and the theoretical ~85 µK and needs a
stabilised run to measure.

## Verification status

The resolution and the noise floor were checked by round-trip simulation (see
[`design_notes.md`](design_notes.md)). The remaining empirical milestone is the
overlapping Allan deviation of a long, deliberately stabilised run, which will
pin the absolute single-channel stability. Until then, treat the per-channel
precision targets above as design figures, confirmed only at the differential
level by the calibration run.
