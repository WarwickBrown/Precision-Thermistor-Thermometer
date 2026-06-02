# =============================================================================
# test_single.py  --  ONE-CHANNEL diagnostic. Standalone, no other files needed.
#
# Circuit (no PMOS, no DS18B20, no second channel):
#   +3V3 --- R1(100k) --- NODE_A --- R3(100k) --- GND     (reference leg)
#   +3V3 --- R2(100k) --- NODE_B --- NTC(jack) -- GND      (sense leg)
#   ADS1115:  AIN0 = NODE_A,  AIN1 = NODE_B,  reads AIN0-AIN1 differentially.
#
# Upload just this file. In Thonny, open it and press Run.
# It prints raw counts, the differential voltage, the reconstructed NODE_B
# voltage, and the back-calculated NTC resistance, ~1 per second.
#
# WHAT GOOD LOOKS LIKE:
#   - With a ~110k thermistor at room temp: Vdiff ~ -0.15 V, R_ntc ~ 110k.
#   - Pinch the thermistor: R_ntc should fall by several kohm and recover.
#   - If R_ntc sits pinned near 100k and barely moves, the thermistor is NOT
#     in circuit (jack/solder fault) -- that is the bug we are hunting.
# =============================================================================
from machine import Pin, I2C
import time

# ---- EDIT THESE IF NEEDED -------------------------------------------------
PIN_SDA  = 0
PIN_SCL  = 1
ADS_ADDR = 0x48
V_EXC    = 3.30        # measure at the bridge top with your UT71B and update
R_TOP    = 100_000.0   # R2  (measure & update)
R_A      = 100_000.0   # R1  (measure & update)
R_B      = 100_000.0   # R3  (measure & update)
FSR      = 2.048       # <-- start WIDE so nothing clips while diagnosing
DATARATE = 8
# ---------------------------------------------------------------------------

# ADS1115 register constants
_REG_CONV   = 0x00
_REG_CONFIG = 0x01
_OS_SINGLE  = 0x8000
_MUX_0_1    = 0x0000           # AINP=AIN0, AINN=AIN1
_MUX_2_3    = 0x3000           # AINP=AIN2, AINN=AIN3
_MODE_SINGLE = 0x0100
_COMP_OFF   = 0x0003

# ---- SELECT WHICH DIFFERENTIAL PAIR YOUR BRIDGE IS WIRED TO ----
# You wired the bridge to AIN2 / AIN3, so use _MUX_2_3.
# If you move the wires to AIN0 / AIN1, change this back to _MUX_0_1.
MUX_SELECT = _MUX_2_3
_PGA = {6.144:0x0000, 4.096:0x0200, 2.048:0x0400,
        1.024:0x0600, 0.512:0x0800, 0.256:0x0A00}
_DR  = {8:0x0000, 16:0x0020, 32:0x0040, 64:0x0060,
        128:0x0080, 250:0x00A0, 475:0x00C0, 860:0x00E0}
_CONV_MS = {8:135, 16:70, 32:36, 64:20, 128:12, 250:8, 475:5, 860:4}

i2c = I2C(0, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL), freq=400_000)
print("[i2c] scan:", [hex(a) for a in i2c.scan()])

lsb = (2.0 * FSR) / 65536.0

def read_diff():
    cfg = (_OS_SINGLE | MUX_SELECT | _PGA[FSR] | _MODE_SINGLE |
           _DR[DATARATE] | _COMP_OFF)
    i2c.writeto_mem(ADS_ADDR, _REG_CONFIG, bytes([(cfg>>8)&0xFF, cfg&0xFF]))
    time.sleep_ms(_CONV_MS[DATARATE])
    raw = i2c.readfrom_mem(ADS_ADDR, _REG_CONV, 2)
    val = (raw[0]<<8) | raw[1]
    if val & 0x8000:
        val -= 1<<16
    return val

def resistance_from_vdiff(vdiff):
    v_a = V_EXC * R_B / (R_A + R_B)     # reference node (fixed)
    v_b = v_a - vdiff                   # sense node
    denom = V_EXC - v_b
    if denom <= 0 or v_b <= 0:
        return None
    return R_TOP * v_b / denom

print("PGA = +-%.3f V, LSB = %.2f uV" % (FSR, lsb*1e6))
print("count, vdiff_mV, v_nodeB_mV, R_ntc_ohm")

v_ref_a = V_EXC * R_B / (R_A + R_B)

while True:
    counts = read_diff()
    vdiff = counts * lsb
    v_b = v_ref_a - vdiff
    r = resistance_from_vdiff(vdiff)
    r_str = "OPEN/RAIL" if r is None else "%.1f" % r
    print("%6d, %8.3f, %9.2f, %s" % (counts, vdiff*1000, v_b*1000, r_str))
    time.sleep(1)
