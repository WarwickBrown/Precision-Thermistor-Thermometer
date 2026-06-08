# Logged runs

CSV captures from the instrument go here.

Columns: cycle, t_s, vdiff1_uv, r1_ohm, t1_c, vdiff2_uv, r2_ohm, t2_c, t_amb_c

`t_s` is seconds since the firmware started. Captures made with
`tools/serial_logger.py` append one more column, `host_time`, which is the host
computer's wall-clock time per row for matching against other data.
