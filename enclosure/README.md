# Enclosure

3D-printed cover for the instrument (Pico + LCD + stripboard).

## To be added

- [ ] `cover.stl` — printable enclosure / lid
- [ ] source CAD (Fusion 360) or STEP export
- [ ] print settings (material, layer height, infill)
- [ ] photo of the printed result

## Design considerations (for when the STL is made)

- **LCD on the lid**, board inside — keeps the screen visible while the sensors
  stay enclosed. The LCD likely needs a 40-pin ribbon extension off the Pico
  rather than stacking directly, so the board can sit separately.
- **Backlight heat:** the LCD backlight is the largest local heat source. Keep
  it physically away from the thermistor cable entries, and note the firmware
  can dim/disable the backlight (KEY A) during sensitive runs.
- **Cable pass-throughs** for the two thermistor leads (audio jacks) and USB.
- **Don't enclose the reference-resistor cluster** with the warm digital
  section — thermal gradients across the bridge resistors appear as measurement
  error.
