"""Services for the SwitchBot integration."""

import contextlib
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

import switchbot

from homeassistant.components import bluetooth
from homeassistant.const import ATTR_DEVICE_ID, CONF_SENSOR_TYPE
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, service

from .const import DOMAIN, SupportedModels
from .coordinator import SwitchbotConfigEntry, SwitchbotDataUpdateCoordinator

SERVICE_ADD_PASSWORD = "add_password"
SERVICE_SET_WEATHER = "meter_pro_set_weather"
SERVICE_SET_EXTERNAL_SENSOR_MAC = "meter_pro_set_external_sensor_mac"

ATTR_PASSWORD = "password"
ATTR_ICON = "icon"
ATTR_MAC_ADDRESS = "mac_address"
ATTR_SLOT = "slot"

ICON_MAP = {
    "none": 0,
    "sunny": 1,
    "partly_cloudy": 2,
    "cloudy": 3,
    "rainy": 4,
    "pouring": 5,
    "heavy_rain": 5,
    "snowy": 6,
    "light_snow": 6,
    "heavy_snow": 7,
}

_PASSWORD_VALIDATOR = vol.All(cv.string, cv.matches_regex(r"^\d{6,12}$"))

SCHEMA_ADD_PASSWORD_SERVICE = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PASSWORD): _PASSWORD_VALIDATOR,
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_SET_WEATHER_SERVICE = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_ICON): vol.In(list(ICON_MAP.keys())),
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_SET_EXTERNAL_SENSOR_MAC_SERVICE = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_MAC_ADDRESS): cv.string,
        vol.Optional(ATTR_SLOT, default=1): vol.All(
            vol.Coerce(int), vol.In([1, 2])
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


@callback
def _async_get_switchbot_entry_for_device_id(
    hass: HomeAssistant, device_id: str
) -> SwitchbotConfigEntry:
    """Return the loaded SwitchBot config entry for a device id."""
    config_entry: SwitchbotConfigEntry
    _, config_entry = service.async_get_device_and_config_entry(hass, DOMAIN, device_id)
    return config_entry


def _is_supported_keypad(entry: SwitchbotConfigEntry) -> bool:
    """Return if the entry is a supported keypad model."""
    allowed_sensor_types = {
        SupportedModels.KEYPAD_VISION.value,
        SupportedModels.KEYPAD_VISION_PRO.value,
    }
    return entry.data.get(CONF_SENSOR_TYPE) in allowed_sensor_types


@callback
def _async_target(
    hass: HomeAssistant, device_id: str
) -> SwitchbotDataUpdateCoordinator:
    """Return coordinator for a single target device."""
    entry = _async_get_switchbot_entry_for_device_id(hass, device_id)
    if not _is_supported_keypad(entry):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_keypad_vision_device",
        )

    return entry.runtime_data


async def async_add_password(call: ServiceCall) -> None:
    """Add a password to a SwitchBot keypad device."""
    password: str = call.data[ATTR_PASSWORD]
    device_id = call.data[ATTR_DEVICE_ID]

    coordinator = _async_target(call.hass, device_id)

    await coordinator.device.add_password(password)


async def async_meter_pro_set_weather(call: ServiceCall) -> None:
    """Push weather condition icon to Meter Pro."""
    device_id: str = call.data[ATTR_DEVICE_ID]
    icon_str: str = call.data[ATTR_ICON]

    entry = _async_get_switchbot_entry_for_device_id(call.hass, device_id)
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, switchbot.SwitchbotMeterPro):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_meter_pro_device",
        )

    if call.hass:
        with contextlib.suppress(Exception):
            if ble_device := bluetooth.async_ble_device_from_address(
                call.hass, coordinator.ble_device.address, connectable=True
            ):
                coordinator.device._device = ble_device

    icon_val = ICON_MAP[icon_str]
    await coordinator.device.set_weather(
        icon=icon_val,
    )


async def async_meter_pro_set_external_sensor_mac(call: ServiceCall) -> None:
    """Configure external sensor MAC address slot on Meter Pro."""
    device_id: str = call.data[ATTR_DEVICE_ID]
    mac_address: str = call.data[ATTR_MAC_ADDRESS]
    slot: int = call.data.get(ATTR_SLOT, 1)

    entry = _async_get_switchbot_entry_for_device_id(call.hass, device_id)
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, switchbot.SwitchbotMeterPro):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_meter_pro_device",
        )

    if call.hass:
        with contextlib.suppress(Exception):
            if ble_device := bluetooth.async_ble_device_from_address(
                call.hass, coordinator.ble_device.address, connectable=True
            ):
                coordinator.device._device = ble_device

    await coordinator.device.set_external_sensor_mac(
        mac_address=mac_address,
        slot=slot,
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the SwitchBot integration."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_PASSWORD,
        async_add_password,
        schema=SCHEMA_ADD_PASSWORD_SERVICE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_WEATHER,
        async_meter_pro_set_weather,
        schema=SCHEMA_SET_WEATHER_SERVICE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EXTERNAL_SENSOR_MAC,
        async_meter_pro_set_external_sensor_mac,
        schema=SCHEMA_SET_EXTERNAL_SENSOR_MAC_SERVICE,
    )
