# =============================================================================
# lcd_1inch14.py  --  driver for the Waveshare Pico-LCD-1.14 (ST7789, 240x135).
#
# Provides class LCD_1inch14, a framebuf.FrameBuffer subclass, so the usual
# framebuf methods work directly:
#     .fill(c)  .pixel(x,y[,c])  .text(s,x,y,c)  .line(x0,y0,x1,y1,c)
#     .hline / .vline / .rect / .fill_rect ...  then .show() to push to panel.
#
# Pin map is the FIXED Waveshare HAT wiring:
#     SCK=GP10  MOSI=GP11  CS=GP9  DC=GP8  RST=GP12  BL=GP13   (SPI1)
#
# This is a clean-room ST7789 init equivalent to Waveshare's reference example.
# =============================================================================
from machine import Pin, SPI, PWM
import framebuf
import time

# Default HAT pins (match config.py)
_SCK = 10
_MOSI = 11
_CS = 9
_DC = 8
_RST = 12
_BL = 13

_WIDTH = 240
_HEIGHT = 135


class LCD_1inch14(framebuf.FrameBuffer):
    def __init__(self, sck=_SCK, mosi=_MOSI, cs=_CS, dc=_DC, rst=_RST, bl=_BL):
        self.width = _WIDTH
        self.height = _HEIGHT

        self.cs = Pin(cs, Pin.OUT)
        self.dc = Pin(dc, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.cs(1)
        self.dc(1)

        # SPI1 on the HAT pins. 1-bit polarity/phase 0, fast clock.
        self.spi = SPI(1, baudrate=20_000_000, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=None)

        # RGB565 framebuffer
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height,
                         framebuf.RGB565)

        # Backlight on (full). display.py may also PWM this pin; that's fine.
        self.bl = Pin(bl, Pin.OUT)
        self.bl(1)

        self.init_display()

    # ---- low-level ----
    def _cmd(self, c):
        self.cs(1); self.dc(0); self.cs(0)
        self.spi.write(bytearray([c]))
        self.cs(1)

    def _data(self, d):
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(bytearray([d]))
        self.cs(1)

    def init_display(self):
        # hardware reset
        self.rst(1); time.sleep_ms(50)
        self.rst(0); time.sleep_ms(50)
        self.rst(1); time.sleep_ms(50)

        self._cmd(0x36); self._data(0x70)   # MADCTL: landscape, 240x135
        self._cmd(0x3A); self._data(0x05)   # COLMOD: 16-bit/pixel (RGB565)

        # porch / power / gamma block (standard ST7789 values)
        self._cmd(0xB2)
        for v in (0x0C, 0x0C, 0x00, 0x33, 0x33):
            self._data(v)
        self._cmd(0xB7); self._data(0x35)
        self._cmd(0xBB); self._data(0x19)
        self._cmd(0xC0); self._data(0x2C)
        self._cmd(0xC2); self._data(0x01)
        self._cmd(0xC3); self._data(0x12)
        self._cmd(0xC4); self._data(0x20)
        self._cmd(0xC6); self._data(0x0F)
        self._cmd(0xD0)
        self._data(0xA4); self._data(0xA1)
        self._cmd(0xE0)
        for v in (0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F,
                  0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23):
            self._data(v)
        self._cmd(0xE1)
        for v in (0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F,
                  0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23):
            self._data(v)
        self._cmd(0x21)                      # inversion on (normal for this panel)
        self._cmd(0x11)                      # sleep out
        time.sleep_ms(120)
        self._cmd(0x29)                      # display on

    def _set_window(self):
        # 240x135 panel sits at a column/row offset inside the ST7789's RAM
        self._cmd(0x2A)                      # column addr
        self._data(0x00); self._data(0x28)
        self._data(0x01); self._data(0x17)   # 40 .. 279  (240 wide)
        self._cmd(0x2B)                      # row addr
        self._data(0x00); self._data(0x35)
        self._data(0x00); self._data(0xBB)   # 53 .. 187  (135 tall)
        self._cmd(0x2C)                      # write to RAM

    def show(self):
        self._set_window()
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)
