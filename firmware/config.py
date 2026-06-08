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
PIN_SDA      = 0          # GP0 -> ADS1115 SDA
PIN_SCL      = 1          # GP1 -> ADS1115 SCL
I2C_FREQ     = 400_000    # 400 kHz standard fast-mode
ADS_ADDR     = 0x48       # ADDR pin tied to GND -> 0x48

# Input-polarity correction. A warm-the-probe test showed the NTC resistance
# rising when heated, but it must fall, so the earlier inversion was backwards.
# The board is in fact wired correctly (node A on AINP, node B on AINN). The
# static room-temperature match that set these True was a false positive: a
# plausible resistance sitting on an inverted slope. Flags off give the correct
# slope. Set True only if the inputs are physically swapped.
INVERT_CH1   = False
INVERT_CH2   = False

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
V_EXC        = 3.284      # measured at the bridge top node
R_TOP        = None       # per-channel overrides used instead (see below)
R_A          = None
R_B          = None

# Per-channel overrides (once you measure each resistor, fill these in).
# Leave as None to fall back to the shared values above.
CH1_R_TOP = 100_510.0     # R2  (measured, out of circuit)
CH1_R_A   = 99_140.0      # R1
CH1_R_B   = 99_120.0      # R3
CH2_R_TOP = 99_730.0      # R6
CH2_R_A   = 99_100.0      # R4
CH2_R_B   = 99_110.0      # R5

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

# --- Per-channel temperature trim (deg C), added after conversion ---
# Use these to MATCH the two probes at rest. Put both probes at the same
# temperature (bond the beads together), let them settle, read the steady A-B on
# the AVERAGES screen, then split that difference between the two offsets so it
# goes to zero. Offsets are added, so if A reads high, lower CH1 and/or raise
# CH2. Leave at 0.0 for no trim. See docs/calibration_procedure.md.
CH1_T_OFFSET = 0.0
CH2_T_OFFSET = 0.0

# -----------------------------------------------------------------------------
# 7. Sampling / averaging  --  two switchable profiles
#
#   The instrument carries two sampling profiles and can switch between them at
#   runtime without a reflash (long-press the joystick button). MODE picks which
#   profile is active at boot. Tune either profile below.
#
#   QUIET : quiet, full-resolution logging profile (the ~1 mK setup):
#           16 averages, 8 SPS, PGA +-0.256 V, 5 s cycle.
#   FAST  : fast, responsive real-time profile for watching the screen:
#           4 averages, 32 SPS, PGA +-2.048 V, 1 s cycle.
#
#   PGA note: +-0.256 V gives 0.21 mK/LSB but only spans ~+-7 K around bridge
#   balance. The FAST profile widens the PGA to +-2.048 V so a fast-changing or
#   off-balance probe cannot clip, at the cost of resolution.
# -----------------------------------------------------------------------------
MODE = 'logging'           # boot profile: 'logging' (QUIET) or 'live' (FAST)

PROFILE_QUIET = {"name": "QUIET", "n_avg": 16, "datarate": 8,  "fsr": 0.256, "period_s": 5.0}
PROFILE_FAST  = {"name": "FAST",  "n_avg": 4,  "datarate": 32, "fsr": 2.048, "period_s": 1.0}

# Flat names derived from the boot profile. Kept so code that reads config.N_AVG
# etc. still works; runtime switching happens through sampling.py.
_BOOT = PROFILE_FAST if MODE == 'live' else PROFILE_QUIET
N_AVG          = _BOOT["n_avg"]
ADS_DATARATE   = _BOOT["datarate"]
ADS_FSR        = _BOOT["fsr"]
CYCLE_PERIOD_S = _BOOT["period_s"]

# -----------------------------------------------------------------------------
# 8. Logging
# -----------------------------------------------------------------------------
LOG_TO_CONSOLE = True       # print CSV lines over USB serial
LOG_TO_FLASH   = True       # also append CSV to a file on the Pico's flash
LOG_FILENAME   = "log.csv"  # written to the Pico root
LOG_MAX_BYTES  = 1_000_000  # stop appending past this size (protects the flash)

# -----------------------------------------------------------------------------
# 9. Backlight
# -----------------------------------------------------------------------------
BACKLIGHT_ON_BOOT = True    # set False to start with the screen backlight off
                            # (also toggled live with joystick UP)
