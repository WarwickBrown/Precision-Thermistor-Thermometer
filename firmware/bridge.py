# =============================================================================
# bridge.py  --  half-bridge maths + Steinhart-Hart conversion.
#
# Model (per channel):
#   Reference leg:  V_EXC -- R_a -- NODE_A -- R_b -- GND
#   Sense leg:      V_EXC -- R_top -- NODE_B -- NTC -- GND
#   ADC measures:   Vdiff = V(NODE_A) - V(NODE_B)     (AINP - AINN)
#
#   V(NODE_A) = V_EXC * R_b / (R_a + R_b)
#   V(NODE_B) = V_EXC * NTC / (R_top + NTC)
#   => V(NODE_B) = V(NODE_A) - Vdiff
#   => solve for NTC:
#        let Vb = V(NODE_A) - Vdiff
#        NTC = R_top * Vb / (V_EXC - Vb)
# =============================================================================
import math


def resistance_from_vdiff(vdiff, v_exc, r_top, r_a, r_b):
    """Return NTC resistance (ohms) from the measured differential voltage."""
    v_node_a = v_exc * r_b / (r_a + r_b)
    v_node_b = v_node_a - vdiff
    # guard against division blow-up if something is miswired
    denom = v_exc - v_node_b
    if denom <= 0 or v_node_b <= 0:
        return None
    return r_top * v_node_b / denom


def steinhart_hart(resistance, a, b, c):
    """Return temperature in Celsius from resistance + S-H coefficients."""
    if resistance is None or resistance <= 0:
        return None
    ln_r = math.log(resistance)
    inv_t = a + b * ln_r + c * ln_r * ln_r * ln_r
    if inv_t <= 0:
        return None
    return (1.0 / inv_t) - 273.15


def b_model(resistance, b, intercept):
    """Return temperature in Celsius from the 2-parameter B-model.
    T_C = B / (ln R - intercept) - 273.15
    (narrow-range fit from the characterisation spreadsheet)."""
    if resistance is None or resistance <= 0:
        return None
    denom = math.log(resistance) - intercept
    if denom == 0:
        return None
    return (b / denom) - 273.15


class Channel:
    """Bundles the electrical + calibration constants for one bridge channel.

    model = 'bmodel' uses (b_val, intercept)  [recommended, narrow-range fit]
    model = 'sh'     uses (sh_a, sh_b, sh_c)   [full-range Steinhart-Hart]
    """
    def __init__(self, name, v_exc, r_top, r_a, r_b,
                 model='bmodel',
                 b_val=None, intercept=None,
                 sh_a=None, sh_b=None, sh_c=None):
        self.name = name
        self.v_exc = v_exc
        self.r_top = r_top
        self.r_a = r_a
        self.r_b = r_b
        self.model = model
        self.b_val = b_val
        self.intercept = intercept
        self.sh_a = sh_a
        self.sh_b = sh_b
        self.sh_c = sh_c

    def convert(self, vdiff):
        """Return (resistance_ohms, temperature_C)."""
        r = resistance_from_vdiff(vdiff, self.v_exc, self.r_top,
                                  self.r_a, self.r_b)
        if self.model == 'sh':
            t = steinhart_hart(r, self.sh_a, self.sh_b, self.sh_c)
        else:
            t = b_model(r, self.b_val, self.intercept)
        return r, t
