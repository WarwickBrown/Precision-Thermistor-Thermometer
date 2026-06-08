# =============================================================================
# main.py  --  The Box temperature-sensor PoC.  Runs on the Pico W.
#
# Cycle:  pulse bridge ON -> settle -> read CH1 & CH2 differentially ->
#         pulse OFF -> convert to R and T -> read DS18B20 -> update LCD ->
#         log CSV -> sleep for the rest of the cycle period.
#
# Files this depends on (copy all to the Pico):
#   config.py  ads1115.py  bridge.py  ds18b20_reader.py  display.py
#   (and, for the screen, Waveshare's lcd_1inch14.py)
# =============================================================================
from machine import Pin, I2C
import time

import config
from ads1115 import ADS1115
from bridge import Channel
import display
import sampling

# Optional DS18B20
ds = None
if config.USE_DS18B20:
    try:
        from ds18b20_reader import DS18B20
        ds = DS18B20(config.PIN_ONEWIRE)
        if not ds.present:
            print("[ds18b20] no sensor found on bus; continuing without it.")
            ds = None
    except Exception as e:
        print("[ds18b20] init failed (%s); continuing without it." % e)
        ds = None


def _pick(override, default):
    return default if override is None else override


_CSV_HEADER = ("cycle,t_s,vdiff1_uv,r1_ohm,t1_c,"
               "vdiff2_uv,r2_ohm,t2_c,t_amb_c")


def _flash_log_init():
    """Open the flash log for appending; write a header if the file is new.
    Returns an open file handle, or None if logging to flash is off/failed."""
    if not config.LOG_TO_FLASH:
        return None
    try:
        import os
        new = True
        try:
            if os.stat(config.LOG_FILENAME)[6] > 0:   # size > 0 => existing
                new = False
        except OSError:
            new = True
        fh = open(config.LOG_FILENAME, "a")
        if new:
            fh.write(_CSV_HEADER + "\n")
            fh.flush()
        return fh
    except Exception as e:
        print("[flash] logging disabled (%s)" % e)
        return None


def _flash_size():
    try:
        import os
        return os.stat(config.LOG_FILENAME)[6]
    except Exception:
        return 0


def build_channels():
    ch1 = Channel(
        "CH1", config.V_EXC,
        _pick(config.CH1_R_TOP, config.R_TOP),
        _pick(config.CH1_R_A,   config.R_A),
        _pick(config.CH1_R_B,   config.R_B),
        model=config.TEMP_MODEL,
        b_val=config.CH1_B_VAL, intercept=config.CH1_INTERCEPT,
        sh_a=config.CH1_SH_A, sh_b=config.CH1_SH_B, sh_c=config.CH1_SH_C,
        t_offset=config.CH1_T_OFFSET)
    ch2 = Channel(
        "CH2", config.V_EXC,
        _pick(config.CH2_R_TOP, config.R_TOP),
        _pick(config.CH2_R_A,   config.R_A),
        _pick(config.CH2_R_B,   config.R_B),
        model=config.TEMP_MODEL,
        b_val=config.CH2_B_VAL, intercept=config.CH2_INTERCEPT,
        sh_a=config.CH2_SH_A, sh_b=config.CH2_SH_B, sh_c=config.CH2_SH_C,
        t_offset=config.CH2_T_OFFSET)
    return ch1, ch2


def bridge_on(pulse_pin):
    if not config.USE_PULSED_EXCITATION or pulse_pin is None:
        return                      # continuous excitation: always on, nothing to do
    pulse_pin.value(0 if config.PULSE_ACTIVE_LOW else 1)


def bridge_off(pulse_pin):
    if not config.USE_PULSED_EXCITATION or pulse_pin is None:
        return                      # continuous excitation: leave bridge powered
    pulse_pin.value(1 if config.PULSE_ACTIVE_LOW else 0)


def main():
    # --- bring up hardware ---
    i2c = I2C(config.I2C_ID,
              sda=Pin(config.PIN_SDA),
              scl=Pin(config.PIN_SCL),
              freq=config.I2C_FREQ)

    found = i2c.scan()
    print("[i2c] devices:", [hex(a) for a in found])

    # --- wait (don't crash) until the ADS1115 actually appears on the bus ---
    # Lets you hot-wire the board and have it pick up without re-running.
    if config.USE_PULSED_EXCITATION:
        pulse = Pin(config.PIN_PULSE, Pin.OUT)
        pulse.value(1 if config.PULSE_ACTIVE_LOW else 0)   # bridge OFF before we have `adc`
    else:
        pulse = None                                       # continuous: no switch

    while config.ADS_ADDR not in i2c.scan():
        print("[i2c] waiting for ADS1115 @ 0x%02x ... "
              "(check SDA/SCL, VDD, GND, pull-ups, ADDR->GND)" % config.ADS_ADDR)
        display.message("Waiting for", "ADS1115...")
        time.sleep(1)
    print("[i2c] ADS1115 found.")

    active_prof = sampling.current()
    adc = ADS1115(i2c, addr=config.ADS_ADDR,
                  fsr=active_prof["fsr"], datarate=active_prof["datarate"])
    adc.invert_ch1 = config.INVERT_CH1
    adc.invert_ch2 = config.INVERT_CH2

    bridge_off(pulse)            # start with bridge de-energised
    ch1, ch2 = build_channels()

    # --- one-shot startup self-check: energise, read both channels, report ---
    # Wrapped so a transient I2C glitch reports instead of crashing the session.
    print("[selfcheck] energising bridge for range check...")
    try:
        bridge_on(pulse)
        time.sleep_ms(config.SETTLE_MS)
        sv1 = adc.read_diff(1)
        sv2 = adc.read_diff(2)
        bridge_off(pulse)
        for name, sv in (("CH1", sv1), ("CH2", sv2)):
            status = "CLIPPING - check NTC R or PGA" if adc.near_clip(sv) else "in range"
            print("[selfcheck] %s Vdiff = %+.4f V  (%s)" % (name, sv, status))
        if adc.near_clip(sv1) or adc.near_clip(sv2):
            display.message("Bridge OUT OF", "RANGE - see USB")
            time.sleep(2)
    except OSError as e:
        bridge_off(pulse)
        print("[selfcheck] I2C error during self-check (%s); "
              "continuing into main loop." % e)

    # CSV header over USB serial
    if config.LOG_TO_CONSOLE:
        print(_CSV_HEADER)

    # Flash log (append mode; survives USB disconnect)
    flash = _flash_log_init()
    flash_full = False
    if flash:
        print("[flash] logging to %s" % config.LOG_FILENAME)

    cycle = 0
    consecutive_errs = 0
    t_start = time.ticks_ms()

    while True:
        cycle_t0 = time.ticks_ms()

        # --- apply a live QUIET/FAST profile switch requested from the display ---
        prof = sampling.current()
        if prof is not active_prof:
            try:
                adc.reconfigure(fsr=prof["fsr"], datarate=prof["datarate"])
                active_prof = prof
                print("[mode] %s: %d avg, %d SPS, +-%.3f V, %.1f s cycle"
                      % (prof["name"], prof["n_avg"], prof["datarate"],
                         prof["fsr"], prof["period_s"]))
            except OSError as e:
                print("[mode] reconfigure failed (%s); keeping previous." % e)

        # Kick off DS18B20 conversion early so its 750 ms overlaps our work.
        if ds:
            ds.start()

        # --- energise bridge and let it settle ---
        bridge_on(pulse)
        time.sleep_ms(config.SETTLE_MS)

        # --- read both differential channels (averaged) ---
        try:
            v1, _ = adc.read_diff_avg(1, prof["n_avg"])
            v2, _ = adc.read_diff_avg(2, prof["n_avg"])
            consecutive_errs = 0
        except OSError as e:
            bridge_off(pulse)
            consecutive_errs += 1
            print("[loop] I2C error (%s) on cycle %d (x%d); skipping."
                  % (e, cycle, consecutive_errs))
            # After several straight failures, try to re-init the bus once.
            if consecutive_errs in (5, 20, 50):
                print("[loop] attempting I2C bus re-init...")
                try:
                    i2c.init(scl=Pin(config.PIN_SCL), sda=Pin(config.PIN_SDA),
                             freq=config.I2C_FREQ)
                except Exception as ie:
                    print("[loop] re-init failed (%s)" % ie)
            time.sleep(1)
            continue

        # --- de-energise bridge (minimise self-heating) ---
        bridge_off(pulse)

        # --- convert ---
        r1, t1 = ch1.convert(v1)
        r2, t2 = ch2.convert(v2)

        # --- ambient (result of the conversion we started at top of loop) ---
        t_amb = None
        if ds:
            # ensure the 750 ms conversion has definitely finished
            elapsed = time.ticks_diff(time.ticks_ms(), cycle_t0)
            if elapsed < 800:
                time.sleep_ms(800 - elapsed)
            t_amb = ds.read()

        # --- display: push new data, then poll UI during cooldown ---
        display.push(t1, r1, t2, r2, t_amb, cycle)

        # --- build the CSV line once ---
        t_s = time.ticks_diff(time.ticks_ms(), t_start) / 1000.0
        def f(x, nd=3):
            return "" if x is None else ("{:.%df}" % nd).format(x)
        line = "{},{:.1f},{},{},{},{},{},{},{}".format(
            cycle, t_s,
            f(v1 * 1e6, 1), f(r1, 1), f(t1, 4),
            f(v2 * 1e6, 1), f(r2, 1), f(t2, 4),
            f(t_amb, 3))

        if config.LOG_TO_CONSOLE:
            print(line)

        if flash and not flash_full:
            try:
                flash.write(line + "\n")
                flash.flush()                      # flush so a reset keeps data
                if _flash_size() >= config.LOG_MAX_BYTES:
                    flash_full = True
                    print("[flash] %s reached %d bytes; stopping flash log."
                          % (config.LOG_FILENAME, config.LOG_MAX_BYTES))
            except Exception as e:
                print("[flash] write error (%s); disabling flash log." % e)
                flash = None

        cycle += 1

        # --- responsive cooldown: poll joystick / redraw ~25 Hz until next cycle ---
        deadline = time.ticks_add(cycle_t0, int(prof["period_s"] * 1000))
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            display.tick()
            time.sleep_ms(40)


if __name__ == "__main__":
    main()
