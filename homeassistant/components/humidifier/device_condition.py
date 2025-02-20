"""Provide the device automations for Humidifier."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import toggle_entity
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_MODE,
    CONF_CONDITION,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import condition, config_validation as cv, entity_registry
from homeassistant.helpers.config_validation import DEVICE_CONDITION_BASE_SCHEMA
from homeassistant.helpers.entity import get_capability, get_supported_features
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN, const

TOGGLE_CONDITION = toggle_entity.CONDITION_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN}
)

MODE_CONDITION = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): "is_mode",
        vol.Required(ATTR_MODE): str,
    }
)

CONDITION_SCHEMA = vol.Any(TOGGLE_CONDITION, MODE_CONDITION)


async def async_get_conditions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device conditions for Humidifier devices."""
    registry = entity_registry.async_get(hass)
    conditions = await toggle_entity.async_get_conditions(hass, device_id, DOMAIN)

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        supported_features = get_supported_features(hass, entry.entity_id)

        if supported_features & const.HumidifierEntityFeature.MODES:
            conditions.append(
                {
                    CONF_CONDITION: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: "is_mode",
                }
            )

    return conditions


@callback
def async_condition_from_config(
    hass: HomeAssistant, config: ConfigType
) -> condition.ConditionCheckerType:
    """Create a function to test a device condition."""
    if config[CONF_TYPE] == "is_mode":
        attribute = ATTR_MODE
    else:
        return toggle_entity.async_condition_from_config(hass, config)

    def test_is_state(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
        """Test if an entity is a certain state."""
        state = hass.states.get(config[ATTR_ENTITY_ID])
        return (
            state is not None and state.attributes.get(attribute) == config[attribute]
        )

    return test_is_state


async def async_get_condition_capabilities(hass, config):
    """List condition capabilities."""
    condition_type = config[CONF_TYPE]

    fields = {}

    if condition_type == "is_mode":
        try:
            modes = (
                get_capability(hass, config[ATTR_ENTITY_ID], const.ATTR_AVAILABLE_MODES)
                or []
            )
        except HomeAssistantError:
            modes = []

        fields[vol.Required(ATTR_MODE)] = vol.In(modes)

        return {"extra_fields": vol.Schema(fields)}

    return await toggle_entity.async_get_condition_capabilities(hass, config)
