# Thermistor characterisation

Both NTC thermistors were characterised before installation in the bridge, so
the R(T) curve is a property of the sensor alone and transfers to any downstream
circuit.

This is the absolute calibration. If you only want the two channels to agree at
rest (relative precision), you do not need this at all. See
[`calibration_procedure.md`](calibration_procedure.md) for the simpler matching
trim.

## Method

* **Reference:** UNI-T UT71B multimeter with its K-type thermocouple probe. The
  thermistor bead and the thermocouple tip were thermally coupled so they saw
  the same temperature.
* **Sweep:** a slowly cooling water bath provided a range of temperatures. The
  thermistor resistance and reference temperature were recorded as pairs once
  the rate of change was slow enough for both sensors to track together.
* **Fit window:** the model is fit to the settled middle of the sweep (roughly
  5 to 40 °C), and the residuals are then evaluated over the 10–30 °C operating
  range. The points at the cold and hot extremes were taken while the bath was
  still ramping, so they were excluded. They degraded the fit without
  representing the operating point.

## Model

Two-parameter B-model:

```
1/T = 1/T₀ + (1/B)·ln(R/R₀)     ⇔     T(°C) = B / (ln R − intercept) − 273.15
```

## Results

| Probe | B (K) | intercept | R₀ @ 25 °C | fit R² |
|---|---|---|---|---|
| A (NTC-01) | 3816.564 | −1.288504 | ~99.9 kΩ | ≥ 0.9996 |
| B (NTC-02) | 3820.824 | −1.306170 | ~99.6 kΩ | ≥ 0.9996 |

The two devices are closely matched, with B-values within 0.1 % and R₀ within
0.3 %. That is valuable for a two-channel differential instrument because both
channels then behave alike, and their difference (A−B) is especially clean.

The full sweep, the fit, and the residuals are in the workbook
[`calibration/V2_Thermistor_Measurement.xlsx`](calibration/V2_Thermistor_Measurement.xlsx).

## Accuracy vs precision

The residual RMS of the fit (about 0.1 °C) is the absolute accuracy floor, and
it is set by the UT71B thermocouple's resolution and absolute accuracy rather
than by the instrument's noise. The instrument's relative stability, meaning its
ability to detect small changes in temperature, is far finer and is limited by
ADC noise and bridge drift in the millikelvin range. The two figures describe
different things and should not be conflated.

## Files

* [`calibration/`](calibration/) holds the raw (T, R) sweep data, the fit
  workbook `V2_Thermistor_Measurement.xlsx`, and the residuals plot.
* Coefficients are entered in [`../firmware/config.py`](../firmware/config.py).
