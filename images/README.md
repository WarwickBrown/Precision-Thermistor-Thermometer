# Images

Photos and screenshots used in the documentation.

## System photos

| File | Shot |
|---|---|
| `system_overview.jpg` | finished instrument in its enclosure with both probe cables (README hero) |
| `lcd_live.jpg` | the soldered stripboard build (Pico W, ADS1115, probes), with the earlier UI on screen |
| `probes.jpg` | the two NTC probe leads (tinned inner conductors of the shielded cable) |

## Screen renders

Rendered from the firmware display layout (`firmware/display.py`) using the
panel's own 8x8 font, so they match what the LCD shows pixel for pixel. The
values are illustrative. These replace the earlier screen photos, which were of
the previous smaller-font UI.

| File | Page |
|---|---|
| `screen_live.png` | LIVE, both probes large: T, R, ΔT, rolling σ |
| `screen_averages.png` | AVERAGES, rolling means over a short and a long window |
| `screen_trend.png` | TREND, scrolling A/B temperature chart |
| `screen_delta.png` | DELTA, scrolling A−B difference |
| `screen_stats.png` | STATS, mean, σ, span, drift, STABLE/SETTLING flag |

## Enclosure

| File | View |
|---|---|
| `enclosure.jpg` | top / lid, with the LCD window and "Temperature Sensor" label |
| `enclosure_usb.jpg` | USB Type-B port side |
| `enclosure_aux.jpg` | AUX side with the labelled A / B probe jacks |
| `enclosure_back.jpg` | base, engraved with the repository URL |

The calibration workbook lives under
[`../docs/calibration/`](../docs/calibration/). A bath/UT71B setup photo and a
residuals plot can be added there later. See that folder's README.
