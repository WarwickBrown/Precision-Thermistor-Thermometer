# =============================================================================
# ads1115.py  --  minimal, self-contained ADS1115 driver (MicroPython).
#
# No external dependencies.  Single-shot differential reads only, which is all
# this project needs.  Written against the TI ADS1115 datasheet (SBAS444).
# =============================================================================
from machine import I2C
import time

# Register pointers
_REG_CONV   = 0x00
_REG_CONFIG = 0x01

# Config register bit fields (see datasheet Table 8)
_OS_SINGLE  = 0x8000   # write 1 = start a single conversion

# MUX[14:12] -- differential pairs
_MUX_0_1    = 0x0000   # AINP=AIN0, AINN=AIN1   (bridge channel 1)
_MUX_2_3    = 0x3000   # AINP=AIN2, AINN=AIN3   (bridge channel 2)
# (single-ended ones, not used here, kept for reference)
_MUX_0_G    = 0x4000
_MUX_1_G    = 0x5000
_MUX_2_G    = 0x6000
_MUX_3_G    = 0x7000

# PGA[11:9] -- full-scale range. We want the SMALLEST range our signal fits in.
_PGA = {
    6.144: 0x0000,
    4.096: 0x0200,
    2.048: 0x0400,
    1.024: 0x0600,
    0.512: 0x0800,
    0.256: 0x0A00,
}

_MODE_SINGLE = 0x0100  # single-shot

# DR[7:5] -- data rate (samples/sec)
_DR = {
    8:   0x0000,
    16:  0x0020,
    32:  0x0040,
    64:  0x0060,
    128: 0x0080,
    250: 0x00A0,
    475: 0x00C0,
    860: 0x00E0,
}

# Comparator: disabled
_COMP_OFF = 0x0003

# Conversion-time lookup (ms) per data rate, with margin
_CONV_MS = {8: 135, 16: 70, 32: 36, 64: 20, 128: 12,
            250: 8, 475: 5, 860: 4}


class ADS1115:
    def __init__(self, i2c, addr=0x48, fsr=0.256, datarate=8):
        self.i2c = i2c
        self.addr = addr
        if fsr not in _PGA:
            raise ValueError("Unsupported FSR %s" % fsr)
        if datarate not in _DR:
            raise ValueError("Unsupported data rate %s" % datarate)
        self.fsr = fsr
        self.datarate = datarate
        self._lsb = (2.0 * fsr) / 65536.0   # volts per LSB (differential)
        self._conv_ms = _CONV_MS[datarate]

    def reconfigure(self, fsr=None, datarate=None):
        """Change PGA full-scale range and/or data rate at runtime. Used by the
        live QUIET/FAST sampling-profile switch."""
        if fsr is not None:
            if fsr not in _PGA:
                raise ValueError("Unsupported FSR %s" % fsr)
            self.fsr = fsr
            self._lsb = (2.0 * fsr) / 65536.0
        if datarate is not None:
            if datarate not in _DR:
                raise ValueError("Unsupported data rate %s" % datarate)
            self.datarate = datarate
            self._conv_ms = _CONV_MS[datarate]

    def _write_config(self, cfg):
        self.i2c.writeto_mem(self.addr, _REG_CONFIG,
                             bytes([(cfg >> 8) & 0xFF, cfg & 0xFF]))

    def _read_conv(self):
        raw = self.i2c.readfrom_mem(self.addr, _REG_CONV, 2)
        val = (raw[0] << 8) | raw[1]
        if val & 0x8000:           # two's-complement negative
            val -= 1 << 16
        return val

    def read_diff(self, channel):
        """channel 1 -> AIN0-AIN1, channel 2 -> AIN2-AIN3. Returns volts."""
        if channel == 1:
            mux = _MUX_0_1
        elif channel == 2:
            mux = _MUX_2_3
        else:
            raise ValueError("channel must be 1 or 2")

        cfg = (_OS_SINGLE | mux | _PGA[self.fsr] |
               _MODE_SINGLE | _DR[self.datarate] | _COMP_OFF)
        self._write_config(cfg)
        time.sleep_ms(self._conv_ms)
        v = self._read_conv() * self._lsb
        # Per-channel input-polarity correction (set if AINP/AINN wired swapped)
        if channel == 1 and getattr(self, 'invert_ch1', False):
            v = -v
        if channel == 2 and getattr(self, 'invert_ch2', False):
            v = -v
        return v

    def read_diff_avg(self, channel, n):
        """Average n single-shot differential reads. Returns (mean_v, raw_list)."""
        acc = 0.0
        samples = []
        for _ in range(n):
            v = self.read_diff(channel)
            acc += v
            samples.append(v)
        return acc / n, samples

    def near_clip(self, vdiff):
        """True if a reading is within 2% of the full-scale rails (likely clipping)."""
        return abs(vdiff) > 0.98 * self.fsr
