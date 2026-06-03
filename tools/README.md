# Tools

Off-Pico helpers that run on a normal computer (not on the microcontroller).

## `analyse_log.py`

Stability analysis for the CSV the firmware produces (`log.csv`, or a console
capture). It reports per-channel statistics, the common-mode-cancelled **A−B**
difference channel, and the **overlapping Allan deviation** vs averaging time τ
— the curve whose minimum answers the project's central question, *"is 16-bit
enough?"*.

```
pip install numpy matplotlib

python tools/analyse_log.py log.csv                 # stats + Allan plot -> stability.png
python tools/analyse_log.py log.csv --settle-min 10 # drop the first 10 min (warm-up)
python tools/analyse_log.py log.csv --col t1_c      # analyse a single column
python tools/analyse_log.py log.csv --no-plot       # stats only
```

The expected CSV columns are:

```
cycle, t_s, vdiff1_uv, r1_ohm, t1_c, vdiff2_uv, r2_ohm, t2_c, t_amb_c
```
