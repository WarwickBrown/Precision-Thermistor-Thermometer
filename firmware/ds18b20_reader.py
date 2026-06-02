# =============================================================================
# ds18b20_reader.py  --  thin wrapper over MicroPython's built-in onewire +
# ds18x20 modules (both ship with the Pico W firmware).
#
# Usage pattern matters: a DS18B20 12-bit conversion takes ~750 ms.  We do NOT
# block for that.  Instead: call start() once, and >=750 ms later call read().
# We fold that latency into the main loop's cycle period so it is free.
# =============================================================================
import machine
import onewire
import ds18x20


class DS18B20:
    def __init__(self, pin_num):
        self._ow = onewire.OneWire(machine.Pin(pin_num))
        self._ds = ds18x20.DS18X20(self._ow)
        self.roms = self._ds.scan()      # list of sensors found on the bus
        self._pending = False

    @property
    def present(self):
        return len(self.roms) > 0

    def start(self):
        """Kick off a conversion on all sensors (non-blocking)."""
        if self.present:
            self._ds.convert_temp()
            self._pending = True

    def read(self):
        """Return temperature in C of the first sensor, or None.
        Only valid >=750 ms after start()."""
        if not self.present or not self._pending:
            return None
        try:
            return self._ds.read_temp(self.roms[0])
        except Exception:
            return None
