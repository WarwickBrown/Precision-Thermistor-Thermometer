# =============================================================================
# config.py  --  ALL tunable values live here.
#
# This is the ONLY file that differs between the breadboard build and the
# final Veroboard build.  Debug everything on the breadboard, then for the
# Veroboard you only revisit the marked sections (pins / timing / calibration).
# =============================================================================

# -----------------------------------------------------------------------------
# 1. I2C / ADS1115
# -----------------------------------------------------------------------------
I2C_ID       = 0          # Pico I2C0 peripheral
PIN_SDA      = 0          # GP0  -> ADS1115 SDA
PIN_SCL      = 1          # GP1  -> ADS1115 SCL
I2C_FREQ     = 400_000    # 400 kHz standard fast-mode
ADS_ADDR     = 0x48       # ADDR pin tied to GND -> 0x48

# Input-polarity correction. The bridge inputs were soldered with AINP/AINN
# swapped (node B on the even pin instead of node A), giving large NEGATIVE
# Vdiff. These flags negate each channel in software to compensate.
# Set back to False if you ever rewire the inputs the right way round.
INVERT_CH1   = True
INVERT_CH2   = True

# -----------------------------------------------------------------------------
# 2. Pulsed-excitation switch (PMOS high-side)
#    GP22 LOW  = bridge ON   (PMOS conducting)
#    GP22 HIGH = bridge OFF
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 2. Bridge excitation
#
#    USE_PULSED_EXCITATION = False  -> bridge tops wired straight to 3V3 (or a
#    series-dropper resistor).  No switch.  GP22 is not used.  Self-heating is a
#    constant offset that calibrates out -- correct choice without a logic-level
#    PMOS.  Set True only if a proper logic-level PMOS switch is fitted.
# -----------------------------------------------------------------------------
USE_PULSED_EXCITATION = False
PIN_PULSE        = 22         # GP22 -> PMOS gate (only used if pulsed)
PULSE_ACTIVE_LOW = False      # only relevant if USE_PULSED_EXCITATION = True
SETTLE_MS        = 50         # settle wait before converting (used in both modes)
OFF_SETTLE_MS    = 50         # (pulsed mode only)

# -----------------------------------------------------------------------------
# 3. DS18B20 (1-Wire)
# -----------------------------------------------------------------------------
PIN_ONEWIRE  = 4          # GP4 -> DS18B20 DQ (with 4k7 pull-up to 3V3)
USE_DS18B20  = False      # set False if probe not plugged in

# -----------------------------------------------------------------------------
# 4. LCD (Waveshare Pico-LCD-1.14, ST7789).  Pins fixed by the HAT.
# -----------------------------------------------------------------------------
USE_LCD      = True
PIN_LCD_SCK  = 10
PIN_LCD_MOSI = 11
PIN_LCD_CS   = 9
PIN_LCD_DC   = 8
PIN_LCD_RST  = 12
PIN_LCD_BL   = 13
LCD_SPI_ID   = 1

# Joystick + buttons on the Pico-LCD-1.14 HAT (active-low, internal pull-ups)
PIN_JOY_UP    = 2
PIN_JOY_DOWN  = 18
PIN_JOY_LEFT  = 16
PIN_JOY_RIGHT = 20
PIN_JOY_CTRL  = 3
PIN_KEY_A     = 15
PIN_KEY_B     = 17

# Display behaviour
DISPLAY_BYTESWAP = True    # flip if on-screen colours look wrong (RGB565 order)
LABEL_A      = "A"         # rename to "IN" / "FIBRE" / etc. as you like
LABEL_B      = "B"         # rename to "OUT" / "AIR" / etc.
STATS_WINDOW = 32          # samples used for rolling mean / sigma
SETTLE_SIGMA_MK = 5.0      # rolling sigma below this (mK) => "STABLE"

# -----------------------------------------------------------------------------
# 5. Bridge electrical model
#
#    Half-bridge per channel:
#         V_EXC --- R_top --- NODE_B --- NTC --- GND      (sense leg)
#         V_EXC --- R_a   --- NODE_A --- R_b  --- GND      (reference leg)
#    ADC reads  Vdiff = V(NODE_A) - V(NODE_B)   (AINP - AINN)
#
#    With all reference resistors equal to R_REF and excitation V_EXC:
#         V(NODE_A) = V_EXC * R_b / (R_a + R_b)      (fixed, = V_EXC/2 if equal)
#         V(NODE_B) = V_EXC * NTC / (R_top + NTC)
#    Solve the measured Vdiff for NTC.  Because the ADS1115 is *ratiometric-ish*
#    only (internal ref), we still need V_EXC numerically -- measure it once with
#    your multimeter and put it here.
# -----------------------------------------------------------------------------
V_EXC        = 3.30       # MEASURE THIS with the UT71B at the bridge top node.
R_TOP        = 100_000.0  # series resistor above the NTC (R2 / R6)   <-- measure!
R_A          = 100_000.0  # reference leg upper resistor (R1 / R4)    <-- measure!
R_B          = 100_000.0  # reference leg lower resistor (R3 / R5)    <-- measure!

# Per-channel overrides (once you measure each resistor, fill these in).
# Leave as None to fall back to the shared values above.
CH1_R_TOP = None
CH1_R_A   = None
CH1_R_B   = None
CH2_R_TOP = None
CH2_R_A   = None
CH2_R_B   = None

# -----------------------------------------------------------------------------
# 6. Thermistor calibration   (from V2_Thermistor_Measurement.xlsx)
#
#    TEMP_MODEL selects the conversion:
#      'bmodel' -> 2-param B-model, narrow-range fit (RECOMMENDED, ~0.10C RMS)
#                  T_C = B / (ln R - intercept) - 273.15
#      'sh'     -> 3-param Steinhart-Hart, full-range fit (~0.27C RMS)
#                  1/T = A + B*ln R + C*(ln R)^3
#
#    NOTE: the residual RMS above is the *accuracy* floor set by the UT71B
#    reference probe (~0.1C resolution).  It is NOT your relative stability /
#    precision, which is far better and is what The Box actually needs.
# -----------------------------------------------------------------------------
TEMP_MODEL = 'bmodel'

# --- B-model narrow-range coefficients (NTC-01 = CH1, NTC-02 = CH2) ---
CH1_B_VAL     = 3816.564267
CH1_INTERCEPT = -1.288503865
CH2_B_VAL     = 3820.824309
CH2_INTERCEPT = -1.306170354

# --- Full-range Steinhart-Hart coefficients (fallback if TEMP_MODEL='sh') ---
CH1_SH_A = 0.0008259969752
CH1_SH_B = 0.0001987447054
CH1_SH_C = 0.0000001568288742
CH2_SH_A = 0.0008454762978
CH2_SH_B = 0.0001953817084
CH2_SH_C = 0.0000001702921204

# -----------------------------------------------------------------------------
# 7. Sampling / averaging
# -----------------------------------------------------------------------------
N_AVG        = 16         # ADS1115 samples averaged per channel per cycle
ADS_DATARATE = 8          # SPS. 8 = slowest = quietest = best 50/60Hz rejection
ADS_FSR      = 2.048      # PGA full-scale (V). Options: 6.144 4.096 2.048
                          # 1.024 0.512 0.256. Wide = safe/coarse, narrow = fine.
                          # Drop to 0.256 only once readings sit well inside range.
CYCLE_PERIOD_S = 5.0      # total time between measurement cycles (incl. cooldown)

# -----------------------------------------------------------------------------
# 8. Logging
# -----------------------------------------------------------------------------
LOG_TO_CONSOLE = True     # print CSV lines over USB serial
