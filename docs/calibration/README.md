# Calibration data

Raw characterisation data and the fit for the two NTC probes. The full write-up
is in [`../characterisation.md`](../characterisation.md), and the derived
coefficients live in [`../../firmware/config.py`](../../firmware/config.py).

## Contents

| File | What it is |
|---|---|
| `V2_Thermistor_Measurement.xlsx` | master workbook: the (T, R) sweep, the B-model fit, and residuals |
| `sweep_raw.csv` *(optional)* | plain-text export of the (T, R) pairs, for tools that cannot read `.xlsx` |
| `residuals.png` *(optional)* | residuals-vs-temperature plot, if exported from the workbook |
| `setup.jpg` *(optional)* | photo of the water bath and UT71B reference during the sweep |

## (T, R) column format

Reference temperature in °C (UNI-T UT71B + K-type probe) paired with the
measured thermistor resistance in Ω. Only the points in the operating range are
used for the residual statistics. The bath extremes taken under non-equilibrium
settling are excluded, as explained in the write-up.
