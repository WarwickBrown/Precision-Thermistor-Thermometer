# Netlist (from-to)

Two-channel differential bridge (Option C), continuous excitation, breakout
ADS1115, RC input filters, audio-jack thermistor connectors. Each row is a net;
nets with >2 endpoints span multiple rows.

> Excitation switch (PMOS) is **not** populated — bridge tops wired directly to
> the excitation rail. See `docs/design_notes.md` for why.

## Power / excitation

| Net | From | To |
|---|---|---|
| +3V3 | Pico 3V3(OUT) pin 36 | ADS1115 VDD |
| +3V3 | Pico 3V3(OUT) pin 36 | C1, C2 (decoupling) |
| V_EXC | Pico ADC_VREF pin 35 (or 3V3) | R1, R2 tops (bridge 1) |
| V_EXC | Pico ADC_VREF pin 35 (or 3V3) | R4, R6 tops (bridge 2) |

## Bridge 1 → channel 1 (Thermistor A)

| Net | From | To |
|---|---|---|
| NODE_A1 | R1 / R3 midpoint | R_filt1 → AIN0 |
| NODE_B1 | R2 / J1-Tip midpoint | R_filt2 → AIN1 |
| GND | R3 bottom | analog GND |
| GND | J1 Ring | analog GND |
| GND | J1 Sleeve (shield, board end only) | analog GND |

## Bridge 2 → channel 2 (Thermistor B)

| Net | From | To |
|---|---|---|
| NODE_A2 | R4 / R5 midpoint | R_filt3 → AIN2 |
| NODE_B2 | R6 / J2-Tip midpoint | R_filt4 → AIN3 |
| GND | R5 bottom | analog GND |
| GND | J2 Ring | analog GND |
| GND | J2 Sleeve | analog GND |

## RC input filter (per channel)

| Net | From | To |
|---|---|---|
| AIN0 | R_filt1 (1k) | ADS1115 AIN0; C_diff1 one side |
| AIN1 | R_filt2 (1k) | ADS1115 AIN1; C_diff1 other side |
| AIN2 | R_filt3 (1k) | ADS1115 AIN2; C_diff2 one side |
| AIN3 | R_filt4 (1k) | ADS1115 AIN3; C_diff2 other side |

C_diff (100 nF) across each input pair, at the IC. Optional C_cm (10 nF) from
each AIN pin to analog GND.

## I²C / control

| Net | From | To |
|---|---|---|
| SDA | ADS1115 SDA | Pico GP0 |
| SCL | ADS1115 SCL | Pico GP1 |
| ADDR | ADS1115 ADDR | GND (address 0x48) |
| (ALRT) | ADS1115 ALERT/RDY | Pico GP14 (optional DRDY) |

## Ground

Star point: single jumper from digital GND strip to analog GND strip at the
ADS1115 GND pin. Analog strip carries bridge bottoms, jack returns, decoupling
and filter-cap grounds, ADS1115 GND. Digital strip carries Pico + LCD grounds.
Pico AGND (pin 33) is the tidy landing point for the analog star.

## LCD (Waveshare Pico-LCD-1.14 HAT)

Stacks on the Pico header. Uses GP8–GP13 (SPI + DC/CS/RST/BL), and
GP2/3/15/16/17/18/20 for joystick + keys. Grounds via the header to the Pico
ground plane (digital side of the star).
