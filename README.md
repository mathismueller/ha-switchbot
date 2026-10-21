# SwitchBot Bluetooth (Enhanced) for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

An enhanced custom component for **SwitchBot Bluetooth** devices in Home Assistant, featuring complete reverse-engineered control and entity support for the **SwitchBot Meter Pro** (`WoTHP`) and **SwitchBot Meter Pro CO2** (`WoTHPc`).

This integration is a direct drop-in replacement for the core Home Assistant `switchbot` integration. It seamlessly integrates with your existing devices without needing re-pairing, and works natively through **ESPHome Active Bluetooth Proxies** and local Bluetooth adapters.

---

## 🌟 Enhanced Capabilities for Meter Pro & Meter Pro CO2

### 1. Switches (`switch`)
* **Battery Indicator Glyph (`switch.battery_indicator`)**: Toggle whether the physical battery gauge icon appears on the physical LCD display.
* **Buzzer Alarm Sound (`switch.buzzer_sound`)**: Toggle between audible buzzer alarm and silent screen flashing when environmental thresholds are breached.

### 2. Selects (`select`)
* **Time Display Format (`select.time_format`)**: Switch between `12h` (AM/PM) and `24h` clock modes.
* **Date Display Format (`select.date_format`)**: Switch between Month/Day (`MM/DD`) and Day/Month (`DD/MM`).
* **Top Button Behavior (`select.button_function`)**: Configure the physical hardware button on top of the device:
  * `Refresh only` (default)
  * `Toggle ℃ / ℉`
  * `Toggle Indoor / Outdoor Data Source`
* **Buzzer Volume (`select.buzzer_volume`)**: Set alarm volume (`Low`, `Medium`, `High`).
* **CO2 Measurement Interval (`select.co2_update_interval`)**: Configure background sampling interval (`5m`, `10m`, `30m`).

### 3. Numbers (`number`)
* **Comfort Temperature Thresholds**:
  * `number.comfort_cold`: Lower temperature threshold for `COMFORT` status (°C, 0.5°C step).
  * `number.comfort_hot`: Upper temperature threshold for `COMFORT` status (°C, 0.5°C step).
* **Comfort Humidity Thresholds**:
  * `number.comfort_dry`: Lower humidity threshold before display segments show `DRY` (%).
  * `number.comfort_wet`: Upper humidity threshold before display segments show `WET` (%).
* **CO2 Air Quality Thresholds**:
  * `number.co2_threshold_good`: Boundary between Good (Green) and Moderate (Orange) air quality (ppm).
  * `number.co2_threshold_moderate`: Boundary between Moderate (Orange) and Poor (Red) air quality (ppm).
* **Sensor Calibration Offsets**:
  * `number.temperature_offset`: Hardware temperature calibration offset (-10.0 to +10.0 °C).
  * `number.humidity_offset`: Hardware relative humidity calibration offset (-30 to +30 %).
* **Time Display Offset (`number.display_time_offset`)**: Adjust local time display offset.

### 4. Buttons (`button`)
* **Sync Date and Time (`button.sync_datetime`)**: Immediately synchronize the hardware real-time clock to Home Assistant UTC time.
* **Force CO2 Measurement (`button.force_co2_measurement`)**: Trigger an immediate, fresh NDIR CO2 sensor measurement regardless of the sleep interval.
* **Calibrate CO2 Sensor (`button.calibrate_co2`)**: Start the 5-minute automated CO2 sensor recalibration routine (place device in ventilated outdoor air first).

### 5. Actions / Services (`service`)
* **`switchbot.meter_pro_set_weather`**: Push current local weather forecast and external temperature/humidity to the Meter Pro LCD header.
  ```yaml
  action: switchbot.meter_pro_set_weather
  data:
    device_id: YOUR_METER_PRO_DEVICE_ID
    icon: rainy # Options: sunny, partly_cloudy, cloudy, rainy, heavy_snow, snowy, light_snow, none
    temperature: 14.5
    humidity: 82
  ```

---

## 📦 Installation

### Via HACS (Recommended)
1. Open Home Assistant $\rightarrow$ **HACS** $\rightarrow$ **Integrations**.
2. Click the three dots in the top right corner $\rightarrow$ **Custom repositories**.
3. Add this repository URL, category: **Integration**.
4. Click **Download**, then restart Home Assistant.

### Manual Installation
1. Copy the `custom_components/switchbot/` folder into your Home Assistant configuration directory (`<config_dir>/custom_components/switchbot/`).
2. Restart Home Assistant.

---

## 📡 Bluetooth Proxy & Gateway Compatibility
* **ESPHome Bluetooth Proxies**: Fully supported with `active: true` configured on your ESP32 proxies. Home Assistant communicates with the device bidirectionally over GATT anywhere within range of your ESPHome nodes.
* **No Official Hub Required**: All configuration, weather push, comfort triggers, buzzer controls, and calibration run 100% locally over Bluetooth without requiring a SwitchBot Hub or cloud connection.

---

## 🤝 Acknowledgments & Credits

This project builds directly upon the incredible foundational work of the Home Assistant and SwitchBot open-source communities:

* **[Home Assistant Core](https://github.com/home-assistant/core)**:
  This custom component is derived from the official `switchbot` core integration. Huge credit to the original integration authors and code owners:
  * Daniel Hjelseth Høyer ([@danielhiversen](https://github.com/danielhiversen))
  * [@RenierM26](https://github.com/RenierM26)
  * [@murtas](https://github.com/murtas)
  * [@Eloston](https://github.com/Eloston)
  * [@dsypniewski](https://github.com/dsypniewski)
  * [@zerzhang](https://github.com/zerzhang)
  * And all Home Assistant community contributors.

* **[pySwitchbot](https://github.com/sblibs/pySwitchbot)**:
  All low-level BLE communication, packet parsing, and GATT command execution rely on `pySwitchbot`, originally authored by Daniel Hjelseth Høyer and maintained by the SwitchBot library contributors. Our Meter Pro and Meter Pro CO2 protocol implementations extend this library directly.

---

## 📄 License

This project is licensed under the **Apache License 2.0** — in full compatibility and continuity with Home Assistant Core. See the [LICENSE](LICENSE) file for complete details.

Copyright © 2013-2026 The Home Assistant Authors and `ha-switchbot` contributors.
