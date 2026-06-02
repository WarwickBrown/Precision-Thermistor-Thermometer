# =============================================================================
# test_pmos.py  --  determine PMOS switch polarity empirically.
#
# Does NOT touch I2C or the ADC. Just toggles GP22 every 3 seconds and tells
# you what state it is driving. Put your multimeter (DC volts) between the
# PMOS DRAIN (top of bridge) and GND, and watch which GP22 level gives 3.3 V.
#
#   GP22 level that produces ~3.3 V at the drain = "bridge ON" level.
#   - If drain is 3.3 V when GP22 is HIGH  -> you are ACTIVE-HIGH -> PULSE_ACTIVE_LOW=False
#   - If drain is 3.3 V when GP22 is LOW   -> you are ACTIVE-LOW  -> PULSE_ACTIVE_LOW=True
#   - If drain is 3.3 V in BOTH or NEITHER -> wiring fault (see notes printed).
# =============================================================================
from machine import Pin
import time

PIN_PULSE = 22
pulse = Pin(PIN_PULSE, Pin.OUT)

print("Toggling GP22 every 3 s. Measure DRAIN (top of bridge) to GND.")
print("Note which GP22 level gives ~3.3 V at the drain.\n")

state = 0
while True:
    pulse.value(state)
    print("GP22 = %s   <-- measure drain now" % ("HIGH (3.3V)" if state else "LOW (0V)"))
    state ^= 1
    time.sleep(3)
