# Calibration procedure

How to calibrate your own build. There are three layers, and you only need as
many as you care about.

1. **Electrical setup** so the recovered resistance is right. One-time.
2. **Channel matching** so the two probes read the same value at rest. This is
   the precision-critical step and the easy one.
3. **Absolute calibration** so the readings are correct on a true scale.
   Optional, and only if you care about absolute accuracy.

The important thing to understand first: **for precision you do not need an
accurate reference thermometer at all.** You only need both probes at the same
temperature, which you can guarantee by bonding the two beads together. You never
have to know what that shared temperature actually is. See
[`error_budget.md`](error_budget.md) for why precision and accuracy are separate
here.

## 1. Electrical setup (one-time)

These make the resistance the firmware recovers match the real thermistor
resistance. Tolerances here largely cancel out in the matching step, but the
measurements are quick.

* Measure the excitation voltage at the bridge top node with a multimeter and
  put it in `config.V_EXC`.
* Measure each bridge resistor out of circuit (the top resistor and the two
  reference-leg resistors per channel) and enter them in `config.CH1_R_TOP`,
  `CH1_R_A`, `CH1_R_B`, and the `CH2_*` equivalents.

## 2. Match the two probes at rest (the precision trim)

The goal is that when both probes sit at the same temperature, A reads the same
as B, so the A-B difference channel sits at zero and a small real difference
shows up cleanly against it.

1. **Bring both probes to the same temperature.** Easiest first:
   * Bond the two beads in contact (twist or tape them together) and leave them
     in still air inside the enclosure.
   * Better, put both into one thermal mass, such as a metal block with two
     holes or a small sealed vial of water or oil, and let it sit insulated.
     Stir it, then leave it to settle.
   * Do this in the real operating configuration: same cable lengths, same
     enclosure, backlight at its normal setting. Anything that differs between
     the two channels and is not stable will show up as a false offset.
2. **Let it settle.** Watch the STATS page until it reads STABLE and the DELTA
   and AVERAGES pages show a flat A-B. This can take many minutes because of the
   thermal mass and the probes' own self-heating settling. Do not handle the
   probes while they settle.
3. **Read the steady difference.** On the AVERAGES page, read the long-window
   means of A and B and the dT value (dT = A - B). That dT is the offset to
   remove.
4. **Set the trim** in `config.py`. The offsets are added to the readings:
   * Split it evenly: `CH1_T_OFFSET = -dT/2` and `CH2_T_OFFSET = +dT/2`. This
     keeps both channels close to their average.
   * Or move one onto the other: `CH2_T_OFFSET = +dT` and `CH1_T_OFFSET = 0` if
     you would rather leave A as the trusted channel.
   * Sign check: if A reads higher than B then dT is positive, so you lower A
     and raise B.
5. **Reflash `config.py`, re-settle, and confirm** dT now sits near zero on the
   AVERAGES page. One pass is usually enough. Iterate once if a small residual
   remains.

Why a single point is enough: the two thermistors match to about 0.1 % in B and
0.3 % in R0, and the enclosure holds a narrow temperature range, so a single
offset keeps them matched across the whole operating window. The quality of the
match is then visible as the residual A-B sigma on the DELTA page, which is your
precision floor for the difference.

What this does not fix: slow drift over time, which is a thermal-design and
stability question that the Allan-deviation campaign quantifies, and absolute
accuracy, which is the next section.

## 3. Absolute calibration (optional)

If you also want the readings to be correct on a true temperature scale,
characterise each thermistor against a reference probe and fit the B-model, as
described in [`characterisation.md`](characterisation.md). That sets `CH*_B_VAL`
and `CH*_INTERCEPT` per channel. The matching trim from step 2 then sits on top
of it and still applies.

## Where each value lives in `config.py`

| Setting | What it does |
|---|---|
| `V_EXC` | measured excitation voltage |
| `CH*_R_TOP`, `CH*_R_A`, `CH*_R_B` | measured bridge resistors, set the recovered R |
| `CH*_B_VAL`, `CH*_INTERCEPT` (or `CH*_SH_*`) | the R-to-temperature model |
| `CH1_T_OFFSET`, `CH2_T_OFFSET` | the channel-matching trim from step 2 |
