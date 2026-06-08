# =============================================================================
# sampling.py  --  runtime-switchable sampling profile (QUIET vs FAST).
#
# One shared piece of state for the whole program. main.py reads current() once
# per cycle and reconfigures the ADC and loop period when the profile changes.
# display.py flips the profile on a long-press of the joystick button and uses
# period_s() for its time-axis maths. The initial profile follows config.MODE.
#
# A profile is a dict: {"name", "n_avg", "datarate", "fsr", "period_s"}.
# =============================================================================
import config


def _initial():
    if config.MODE == 'live':
        return dict(config.PROFILE_FAST)
    return dict(config.PROFILE_QUIET)


_state = {"profile": _initial()}


def current():
    """Return the active profile dict. The identity of the returned object only
    changes when toggle() is called, so callers can detect a switch with `is`."""
    return _state["profile"]


def is_fast():
    return _state["profile"]["name"] == config.PROFILE_FAST["name"]


def toggle():
    """Switch QUIET <-> FAST and return the new profile."""
    _state["profile"] = dict(config.PROFILE_QUIET if is_fast()
                             else config.PROFILE_FAST)
    return _state["profile"]


def period_s():
    return _state["profile"]["period_s"]
