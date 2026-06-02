# Bill of materials

| Ref | Part | Value / spec | Notes |
|---|---|---|---|
| U1 | ADS1115 breakout | 16-bit I²C ADC | Adafruit 1085 or clone; on-board I²C pull-ups |
| U2 | Raspberry Pi Pico W | RP2040 + wireless | |
| LCD1 | Waveshare Pico-LCD-1.14 V2 | 240×135 ST7789, joystick + 2 keys | stacks on Pico header |
| R1,R2,R3 | Resistor | 100 kΩ, 0.1 %, ≤25 ppm/K, thin-film | bridge 1; same reel/batch |
| R4,R5,R6 | Resistor | 100 kΩ, 0.1 %, ≤25 ppm/K, thin-film | bridge 2; same reel/batch |
| TH1 (A) | NTC thermistor | ~100 kΩ @ 25 °C, B ≈ 3817 K | characterised; on cable |
| TH2 (B) | NTC thermistor | ~100 kΩ @ 25 °C, B ≈ 3821 K | characterised; on cable |
| R_filt1–4 | Resistor | 1 kΩ, 1 %, thin-film | RC filter series, in signal path |
| C_diff1,2 | Capacitor | 100 nF, C0G/NP0 | RC filter differential, across AIN pairs |
| C_cm1–4 | Capacitor | 10 nF, C0G/NP0 | RC filter common-mode (optional) |
| C1 | Capacitor | 100 nF, X7R | ADS1115 decoupling, at VDD pin |
| C2 | Capacitor | 10 µF, X7R/X5R | bulk decoupling on rail |
| J1,J2 | TRS audio jack | 3.5 mm or 6.35 mm, **gold** contacts | thermistor connectors; label distinctly |
| — | Stripboard (Veroboard) | — | analog + digital sections, star ground |
| — | Shielded twisted-pair cable | mic cable or similar | jack ↔ thermistor runs |

### Not populated (design-time options)

| Ref | Part | Why omitted |
|---|---|---|
| Q1 | Logic-level PMOS | pulsed-excitation switch; deferred — only a non-logic-level IRFD9024 was available, so continuous excitation is used instead |
| R_g1,R_g2 | 10 kΩ | PMOS gate drive (only if Q1 fitted) |
| U3 | DS18B20 | ambient 1-Wire sensor; planned addition (GP4 + 4.7 kΩ pull-up) |

### Calibration / test equipment

| Item | Use |
|---|---|
| UNI-T UT71B multimeter + K-type probe | thermistor characterisation reference |
