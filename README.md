# Ubuntu Touch for moto g play 2024 (fogona)

Halium 13 / Ubuntu Touch 24.04 port for the Motorola moto g play 2024
(XT2413, SM6225 "bengal", GKI 5.15, Android 13 vendor).

- `configs/stock-fogona.config`: `/proc/config.gz` from the stock firmware (U1TFS34.100-35-14-1-14).
- `configs/halium.config`: options Halium / Ubuntu Touch need on top of stock.
- `.github/workflows/kernel.yml`: builds the kernel from Motorola's
  `MMI-U1TFS34.100-35-14-1-21` tag with AOSP clang r450784e.

## TODO

- **Battery safety:** test phone runs on a 4.20 V-max LiPo with no thermistor/ID.
  Stock DT charges to 4.50-4.53 V. Done: `tools/patch_charging_dtbo.py` caps every
  charge voltage in the `dtbo` overlays at 4200 mV and drops 10 W FFC; flashed to
  `dtbo_a` and verified (`voltage_max` = 4200000). 
