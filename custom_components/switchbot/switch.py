"""Support for Switchbot bot."""

import abc
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any, override

import switchbot

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import AIRPURIFIER_BASIC_MODELS, AIRPURIFIER_TABLE_MODELS, DOMAIN
from .coordinator import SwitchbotConfigEntry, SwitchbotDataUpdateCoordinator
from .entity import (
    SwitchbotConnectionPolledEntity,
    SwitchbotEntity,
    SwitchbotSwitchedEntity,
    exception_handler,
)


@dataclass(frozen=True, kw_only=True)
class SwitchbotSwitchEntityDescription(SwitchEntityDescription):
    """Describes a Switchbot switch entity."""

    is_on_fn: Callable[[switchbot.SwitchbotDevice], bool | None]
    turn_on_fn: Callable[[switchbot.SwitchbotDevice], Awaitable[Any]]
    turn_off_fn: Callable[[switchbot.SwitchbotDevice], Awaitable[Any]]


AIRPURIFIER_BASIC_SWITCHES: tuple[SwitchbotSwitchEntityDescription, ...] = (
    SwitchbotSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        device_class=SwitchDeviceClass.SWITCH,
        is_on_fn=lambda device: device.is_child_lock_on(),
        turn_on_fn=lambda device: device.open_child_lock(),
        turn_off_fn=lambda device: device.close_child_lock(),
    ),
)

AIRPURIFIER_TABLE_SWITCHES: tuple[SwitchbotSwitchEntityDescription, ...] = (
    *AIRPURIFIER_BASIC_SWITCHES,
    SwitchbotSwitchEntityDescription(
        key="wireless_charging",
        translation_key="wireless_charging",
        device_class=SwitchDeviceClass.SWITCH,
        is_on_fn=lambda device: device.is_wireless_charging_on(),
        turn_on_fn=lambda device: device.open_wireless_charging(),
        turn_off_fn=lambda device: device.close_wireless_charging(),
    ),
)

CIRCULATOR_FAN_PRO_SWITCHES: tuple[SwitchbotSwitchEntityDescription, ...] = (
    SwitchbotSwitchEntityDescription(
        key="vertical_oscillation",
        translation_key="vertical_oscillation",
        device_class=SwitchDeviceClass.SWITCH,
        is_on_fn=lambda device: device.get_vertical_oscillating_state(),
        turn_on_fn=lambda device: device.set_vertical_oscillation(True),
        turn_off_fn=lambda device: device.set_vertical_oscillation(False),
    ),
)

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Switchbot based on a config entry."""
    coordinator = entry.runtime_data

    if isinstance(coordinator.device, switchbot.SwitchbotRelaySwitch2PM):
        entries = [
            SwitchbotMultiChannelSwitch(coordinator, channel)
            for channel in range(1, coordinator.device.channel + 1)
        ]
        async_add_entities(entries)
    elif coordinator.model in AIRPURIFIER_BASIC_MODELS:
        async_add_entities(
            [
                SwitchbotGenericSwitch(coordinator, desc)
                for desc in AIRPURIFIER_BASIC_SWITCHES
            ]
        )
    elif coordinator.model in AIRPURIFIER_TABLE_MODELS:
        async_add_entities(
            [
                SwitchbotGenericSwitch(coordinator, desc)
                for desc in AIRPURIFIER_TABLE_SWITCHES
            ]
        )
    elif isinstance(coordinator.device, switchbot.SwitchbotStandingFan):
        async_add_entities(
            [
                SwitchbotFanHorizontalOscillationSwitch(coordinator),
                SwitchbotFanVerticalOscillationSwitch(coordinator),
            ]
        )
    elif isinstance(coordinator.device, switchbot.SwitchbotCirculatorFanPro):
        async_add_entities(
            SwitchbotGenericSwitch(coordinator, desc)
            for desc in CIRCULATOR_FAN_PRO_SWITCHES
        )
    elif isinstance(coordinator.device, switchbot.SwitchbotMeterPro):
        meter_switches: list[SwitchEntity] = [
            SwitchBotMeterProBatteryIndicatorSwitch(coordinator),
            SwitchBotMeterProDisplayDataSourceSwitch(coordinator),
            SwitchBotMeterProButtonToggleUnitSwitch(coordinator),
            SwitchBotMeterProButtonToggleDataSourceSwitch(coordinator),
        ]
        if isinstance(coordinator.device, switchbot.SwitchbotMeterProCO2):
            meter_switches.append(SwitchBotMeterProCO2BuzzerSoundSwitch(coordinator))
        async_add_entities(meter_switches)
    else:
        async_add_entities([SwitchBotSwitch(coordinator)])


class SwitchbotGenericSwitch(SwitchbotSwitchedEntity, SwitchEntity):
    """Representation of a Switchbot switch controlled via entity description."""

    entity_description: SwitchbotSwitchEntityDescription
    _device: switchbot.SwitchbotDevice

    def __init__(
        self,
        coordinator: SwitchbotDataUpdateCoordinator,
        description: SwitchbotSwitchEntityDescription,
    ) -> None:
        """Initialize the Switchbot generic switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.base_unique_id}-{description.key}"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self.entity_description.is_on_fn(self._device)

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        _LOGGER.debug(
            "Turning on %s for %s", self.entity_description.key, self._address
        )
        await self.entity_description.turn_on_fn(self._device)
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        _LOGGER.debug(
            "Turning off %s for %s", self.entity_description.key, self._address
        )
        await self.entity_description.turn_off_fn(self._device)
        self.async_write_ha_state()


class SwitchBotSwitch(SwitchbotSwitchedEntity, SwitchEntity, RestoreEntity):
    """Representation of a Switchbot switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "bot"
    _attr_name = None
    _device: switchbot.Switchbot

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the Switchbot."""
        super().__init__(coordinator)
        self._attr_is_on = False

    @override
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        if not (last_state := await self.async_get_last_state()):
            return
        self._attr_is_on = last_state.state == STATE_ON
        self._last_run_success = last_state.attributes.get("last_run_success")

    @property
    @override
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        return not self._device.switch_mode()

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if not self._device.switch_mode():
            return self._attr_is_on
        return self._device.is_on()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            **super().extra_state_attributes,
            "switch_mode": self._device.switch_mode(),
        }


class SwitchbotMultiChannelSwitch(SwitchbotSwitchedEntity, SwitchEntity):
    """Representation of a Switchbot multi-channel switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _device: switchbot.Switchbot
    _attr_name = None

    def __init__(
        self, coordinator: SwitchbotDataUpdateCoordinator, channel: int
    ) -> None:
        """Initialize the Switchbot."""
        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.base_unique_id}-{channel}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.base_unique_id}-channel-{channel}")},
            manufacturer="SwitchBot",
            model_id="RelaySwitch2PM",
            name=f"{coordinator.device_name} Channel {channel}",
        )

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self._device.is_on(self._channel)

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        _LOGGER.debug(
            "Turn Switchbot device on %s, channel %d", self._address, self._channel
        )
        await self._device.turn_on(self._channel)
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        _LOGGER.debug(
            "Turn Switchbot device off %s, channel %d", self._address, self._channel
        )
        await self._device.turn_off(self._channel)
        self.async_write_ha_state()


class SwitchbotFanOscillationSwitch(SwitchbotSwitchedEntity, SwitchEntity, abc.ABC):
    """Base class for fan oscillation switch entities."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _device: switchbot.SwitchbotStandingFan

    @property
    @abc.abstractmethod
    @override
    def is_on(self) -> bool | None:
        """Return true if oscillation is active."""

    @abc.abstractmethod
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable oscillation."""

    @abc.abstractmethod
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable oscillation."""


class SwitchbotFanHorizontalOscillationSwitch(SwitchbotFanOscillationSwitch):
    """Switch entity for fan horizontal (left-right) oscillation."""

    _attr_translation_key = "horizontal_oscillation"

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the horizontal oscillation switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-horizontal-oscillation"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if horizontal oscillation is active."""
        return self._device.get_horizontal_oscillating_state()

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable horizontal oscillation."""
        await self._device.set_horizontal_oscillation(True)
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable horizontal oscillation."""
        await self._device.set_horizontal_oscillation(False)
        self.async_write_ha_state()


class SwitchbotFanVerticalOscillationSwitch(SwitchbotFanOscillationSwitch):
    """Switch entity for fan vertical (up-down) oscillation."""

    _attr_translation_key = "vertical_oscillation"

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the vertical oscillation switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-vertical-oscillation"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if vertical oscillation is active."""
        return self._device.get_vertical_oscillating_state()

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable vertical oscillation."""
        await self._device.set_vertical_oscillation(True)
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable vertical oscillation."""
        await self._device.set_vertical_oscillation(False)
        self.async_write_ha_state()


class SwitchBotMeterProBatteryIndicatorSwitch(
    SwitchbotEntity, SwitchEntity, RestoreEntity
):
    """Representation of a Switchbot Meter Pro battery indicator toggle switch."""

    _device: switchbot.SwitchbotMeterPro
    _attr_translation_key = "battery_indicator"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the battery indicator switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-battery_indicator"
        self._attr_is_on = True

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Show battery indicator on screen."""
        await self._device.show_battery_level(True)
        self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Hide battery indicator on screen."""
        await self._device.show_battery_level(False)
        self._attr_is_on = False
        self.async_write_ha_state()


class SwitchBotMeterProCO2BuzzerSoundSwitch(
    SwitchbotConnectionPolledEntity, SwitchEntity, RestoreEntity
):
    """Representation of a Switchbot Meter Pro CO2 buzzer audible alarm switch."""

    _device: switchbot.SwitchbotMeterProCO2
    _attr_translation_key = "buzzer_sound"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the buzzer sound switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-buzzer_sound"
        self._attr_is_on = True

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON

    @override
    async def _async_read_value(self) -> None:
        """Fetch alert sound status from device."""
        sound = await self._device.get_alert_sound()
        self._attr_is_on = sound["sound_on"]

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable audible buzzer on alarm."""
        await self._device.set_alert_sound(sound_on=True, volume=3)
        self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable audible buzzer on alarm (flash only)."""
        await self._device.set_alert_sound(sound_on=False, volume=3)
        self._attr_is_on = False
        self.async_write_ha_state()


class SwitchBotMeterProDisplayDataSourceSwitch(
    SwitchbotEntity, SwitchEntity, RestoreEntity
):
    """Representation of a Switchbot Meter Pro IN/OUT sensor toggle switch."""

    _device: switchbot.SwitchbotMeterPro
    _attr_translation_key = "display_data_source"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the display data source switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-display_data_source"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch display to outdoor sensor."""
        await self._device.set_display_data_source(outdoor=True)
        self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch display to indoor sensor."""
        await self._device.set_display_data_source(outdoor=False)
        self._attr_is_on = False
        self.async_write_ha_state()


class SwitchBotMeterProButtonToggleUnitSwitch(
    SwitchbotConnectionPolledEntity, SwitchEntity, RestoreEntity
):
    """Switch to enable/disable toggling temperature unit via top physical button."""

    _device: switchbot.SwitchbotMeterPro
    _attr_translation_key = "button_toggle_unit"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-button_toggle_unit"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON
            self._device._button_change_unit = self._attr_is_on

    @override
    async def _async_read_value(self) -> None:
        """Fetch button function behavior from device."""
        btn = await self._device.get_button_function()
        self._attr_is_on = btn["change_unit"]
        self._device._button_change_unit = self._attr_is_on

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable toggling unit on top button."""
        await self._device.set_button_toggle_unit(True)
        self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable toggling unit on top button."""
        await self._device.set_button_toggle_unit(False)
        self._attr_is_on = False
        self.async_write_ha_state()


class SwitchBotMeterProButtonToggleDataSourceSwitch(
    SwitchbotConnectionPolledEntity, SwitchEntity, RestoreEntity
):
    """Switch to enable/disable toggling data source via top physical button."""

    _device: switchbot.SwitchbotMeterPro
    _attr_translation_key = "button_toggle_data_source"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: SwitchbotDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-button_toggle_data_source"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == STATE_ON
            self._device._button_change_data_source = self._attr_is_on

    @override
    async def _async_read_value(self) -> None:
        """Fetch button function behavior from device."""
        btn = await self._device.get_button_function()
        self._attr_is_on = btn["change_data_source"]
        self._device._button_change_data_source = self._attr_is_on

    @exception_handler
    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable toggling data source on top button."""
        await self._device.set_button_toggle_data_source(True)
        self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable toggling data source on top button."""
        await self._device.set_button_toggle_data_source(False)
        self._attr_is_on = False
        self.async_write_ha_state()
