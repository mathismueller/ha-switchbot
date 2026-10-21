"""Select platform for SwitchBot."""

from datetime import timedelta
import logging
from typing import override

import switchbot
from switchbot import NightLightState

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SwitchbotConfigEntry, SwitchbotDataUpdateCoordinator
from .entity import SwitchbotConnectionPolledEntity, SwitchbotEntity, exception_handler

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0

SCAN_INTERVAL = timedelta(days=7)
TIME_FORMAT_12H = "12h"
TIME_FORMAT_24H = "24h"
TIME_FORMAT_OPTIONS = [TIME_FORMAT_12H, TIME_FORMAT_24H]

DATE_FORMAT_MM_DD = "mm_dd"
DATE_FORMAT_DD_MM = "dd_mm"
DATE_FORMAT_OPTIONS = [DATE_FORMAT_MM_DD, DATE_FORMAT_DD_MM]

BUTTON_FN_REFRESH = "refresh_only"
BUTTON_FN_UNIT = "toggle_unit"
BUTTON_FN_DATA_SOURCE = "toggle_data_source"
BUTTON_FUNCTION_OPTIONS = [BUTTON_FN_REFRESH, BUTTON_FN_UNIT, BUTTON_FN_DATA_SOURCE]

BUZZER_VOL_LOW = "low"
BUZZER_VOL_MEDIUM = "medium"
BUZZER_VOL_HIGH = "high"
BUZZER_VOLUME_OPTIONS = [BUZZER_VOL_LOW, BUZZER_VOL_MEDIUM, BUZZER_VOL_HIGH]

INTERVAL_5M = "5m"
INTERVAL_10M = "10m"
INTERVAL_30M = "30m"
CO2_INTERVAL_OPTIONS = [INTERVAL_5M, INTERVAL_10M, INTERVAL_30M]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SwitchBot select platform."""
    coordinator = entry.runtime_data

    if isinstance(coordinator.device, switchbot.SwitchbotMeterPro):
        entities: list[SelectEntity] = [
            SwitchBotMeterProCO2TimeFormatSelect(coordinator),
            SwitchBotMeterProDateFormatSelect(coordinator),
            SwitchBotMeterProButtonFunctionSelect(coordinator),
        ]
        if isinstance(coordinator.device, switchbot.SwitchbotMeterProCO2):
            entities.extend(
                [
                    SwitchBotMeterProCO2BuzzerVolumeSelect(coordinator),
                    SwitchBotMeterProCO2UpdateIntervalSelect(coordinator),
                ]
            )
        async_add_entities(entities)
    elif isinstance(coordinator.device, switchbot.SwitchbotStandingFan):
        async_add_entities([SwitchBotStandingFanNightLightSelect(coordinator)])


class SwitchBotMeterProCO2TimeFormatSelect(
    SwitchbotConnectionPolledEntity, SelectEntity
):
    """Select entity to set time display format on Meter Pro CO2."""

    _device: switchbot.SwitchbotMeterProCO2
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "time_format"
    _attr_options = TIME_FORMAT_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_time_format"

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Change the time display format."""
        _LOGGER.debug("Setting time format to %s for %s", option, self._address)
        is_12h_mode = option == TIME_FORMAT_12H
        await self._device.set_time_display_format(is_12h_mode)
        self._attr_current_option = option
        self.async_write_ha_state()

    @override
    async def _async_read_value(self) -> None:
        """Fetch the latest time format from the device."""
        device_time = await self._device.get_datetime()
        self._attr_current_option = (
            TIME_FORMAT_12H if device_time["12h_mode"] else TIME_FORMAT_24H
        )


class SwitchBotMeterProDateFormatSelect(SwitchbotConnectionPolledEntity, SelectEntity):
    """Select entity to set date display format on Meter Pro."""

    _device: switchbot.SwitchbotMeterPro
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "date_format"
    _attr_options = DATE_FORMAT_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_date_format"

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Change the date display format."""
        is_month_first = option == DATE_FORMAT_MM_DD
        await self._device.set_date_display_format(is_month_first)
        self._attr_current_option = option
        self.async_write_ha_state()

    @override
    async def _async_read_value(self) -> None:
        """Default date format."""
        if self._attr_current_option is None:
            self._attr_current_option = DATE_FORMAT_MM_DD


class SwitchBotMeterProButtonFunctionSelect(
    SwitchbotConnectionPolledEntity, SelectEntity
):
    """Select entity to set the top physical button behavior on Meter Pro."""

    _device: switchbot.SwitchbotMeterPro
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "button_function"
    _attr_options = BUTTON_FUNCTION_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_button_function"

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Change the top physical button behavior."""
        change_unit = option == BUTTON_FN_UNIT
        change_data_source = option == BUTTON_FN_DATA_SOURCE
        await self._device.set_button_function(change_unit, change_data_source)
        self._attr_current_option = option
        self.async_write_ha_state()

    @override
    async def _async_read_value(self) -> None:
        """Default button function."""
        if self._attr_current_option is None:
            self._attr_current_option = BUTTON_FN_REFRESH


class SwitchBotMeterProCO2BuzzerVolumeSelect(
    SwitchbotConnectionPolledEntity, SelectEntity
):
    """Select entity to set buzzer volume on Meter Pro CO2."""

    _device: switchbot.SwitchbotMeterProCO2
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "buzzer_volume"
    _attr_options = BUZZER_VOLUME_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_buzzer_volume"

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Change the buzzer volume."""
        vol_map = {BUZZER_VOL_LOW: 2, BUZZER_VOL_MEDIUM: 3, BUZZER_VOL_HIGH: 4}
        await self._device.set_alert_sound(sound_on=True, volume=vol_map[option])
        self._attr_current_option = option
        self.async_write_ha_state()

    @override
    async def _async_read_value(self) -> None:
        """Default buzzer volume."""
        if self._attr_current_option is None:
            self._attr_current_option = BUZZER_VOL_MEDIUM


class SwitchBotMeterProCO2UpdateIntervalSelect(
    SwitchbotConnectionPolledEntity, SelectEntity
):
    """Select entity to set CO2 update interval on Meter Pro CO2."""

    _device: switchbot.SwitchbotMeterProCO2
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "co2_update_interval"
    _attr_options = CO2_INTERVAL_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_co2_update_interval"

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Change the CO2 measurement update interval."""
        sec_map = {INTERVAL_5M: 300, INTERVAL_10M: 600, INTERVAL_30M: 1800}
        await self._device.set_co2_update_interval(sec_map[option])
        self._attr_current_option = option
        self.async_write_ha_state()

    @override
    async def _async_read_value(self) -> None:
        """Fetch active CO2 update interval."""
        sec = await self._device.get_co2_update_interval()
        if sec == 300:
            self._attr_current_option = INTERVAL_5M
        elif sec == 600:
            self._attr_current_option = INTERVAL_10M
        elif sec == 1800:
            self._attr_current_option = INTERVAL_30M


NIGHT_LIGHT_OFF = "off"
NIGHT_LIGHT_BRIGHT = "bright"
NIGHT_LIGHT_SOFT = "soft"
NIGHT_LIGHT_OPTIONS = [NIGHT_LIGHT_OFF, NIGHT_LIGHT_SOFT, NIGHT_LIGHT_BRIGHT]
NIGHT_LIGHT_TO_STATE: dict[str, NightLightState] = {
    NIGHT_LIGHT_OFF: NightLightState.OFF,
    NIGHT_LIGHT_SOFT: NightLightState.LEVEL_2,
    NIGHT_LIGHT_BRIGHT: NightLightState.LEVEL_1,
}
NIGHT_LIGHT_FROM_STATE: dict[int, str] = {
    state.value: option for option, state in NIGHT_LIGHT_TO_STATE.items()
}


class SwitchBotStandingFanNightLightSelect(SwitchbotEntity, SelectEntity):
    """Select entity for night light on Standing Fan."""

    _device: switchbot.SwitchbotStandingFan
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "night_light"
    _attr_options = NIGHT_LIGHT_OPTIONS

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}_night_light"

    @property
    @override
    def current_option(self) -> str | None:
        """Return current night light state."""
        state = self._device.get_night_light_state()
        if state is None:
            return None
        return NIGHT_LIGHT_FROM_STATE.get(state)

    @exception_handler
    @override
    async def async_select_option(self, option: str) -> None:
        """Set night light state."""
        await self._device.set_night_light(NIGHT_LIGHT_TO_STATE[option])
        self.async_write_ha_state()
