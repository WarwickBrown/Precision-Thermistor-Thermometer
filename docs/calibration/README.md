# Calibration data

Raw characterisation data and the fit for the two NTC probes. The full write-up
is in [`../characterisation.md`](../characterisation.md); the derived
coefficients live in [`../../firmware/config.py`](../../firmware/config.py).

## Contents

| File | What it is |
|---|---|
| `V2_Thermistor_Measurement.xlsx` | master workbook: the (T, R) sweep, the B-model fit, and residuals |
| `sweep_raw.csv` *(optional)* | plain-text export of the (T, R) pairs, for tools that can't read `.xlsx` |
| `residuals.png` | residuals-vs-temperature plot embedded in the write-up |
| `setup.jpg` | photo of the water bath + UT71B reference during the sweep |

## (T, R) column format

Reference temperature in °C (UNI-T UT71B + K-type probe) paired with the
measured thermistor resistance in Ω. Only the 10–30 °C points are used for the
fit; bath extremes taken under non-equilibrium settling are excluded (see the
write-up for why).
