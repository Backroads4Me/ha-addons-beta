import asyncio
import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONFIG_PATH
from .bridge import BleBridgeManager

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up LibreCoach BLE from configuration.yaml."""
    # Read config written by the add-on
    try:
        if not Path(CONFIG_PATH).exists():
             _LOGGER.debug("LibreCoach BLE config marker not found. Cleanup might have run or add-on not yet started.")
             return True
        conf = json.loads(Path(CONFIG_PATH).read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _LOGGER.debug("LibreCoach BLE config error: %s", exc)
        return True

    # Start monitoring task for suicide check (delayed)
    addon_slug = conf.get("addon_slug")
    if addon_slug:
        hass.async_create_task(_monitor_addon_status(hass, addon_slug))

    if not conf.get("microair_enabled"):
        _LOGGER.info("LibreCoach BLE: MicroAir disabled in add-on config")
        # Clear locked device address so it rediscovers on re-enable
        if conf.get("locked_devices"):
            conf.pop("locked_devices", None)
            try:
                Path(CONFIG_PATH).write_text(json.dumps(conf))
                _LOGGER.info("Cleared locked device addresses")
            except Exception as exc:
                _LOGGER.debug("Failed to clear locked devices: %s", exc)
        return True

    manager = BleBridgeManager(hass, conf)
    hass.data[DOMAIN] = manager

    # Start after HA is fully running (Bluetooth + MQTT ready)
    async def _start_bridge(event=None):
        await manager.start()
        _LOGGER.info("LibreCoach BLE bridge started")

    hass.bus.async_listen_once("homeassistant_started", _start_bridge)

    return True

async def _monitor_addon_status(hass: HomeAssistant, slug: str):
    """Monitor add-on status and perform cleanup if uninstalled."""
    # Wait for HA to fully start and Add-ons to initialize
    await asyncio.sleep(120)

    max_retries = 3
    retry_delay = 30
    confirmed_missing = 0

    for attempt in range(max_retries):
        try:
            hassio = hass.components.hassio

            # Source 1: Check individual add-on info
            addon_info = await hassio.async_get_addon_info(slug)

            # Source 2: Check the full add-on list
            addons_list = await hassio.async_get_addons_list()
            installed_slugs = [a.get("slug") for a in addons_list.get("addons", [])] if addons_list else []

            # Double-Lock Condition:
            # 1. Info must be missing (None or 404 handled by hassio)
            # 2. Slug must be missing from the full list
            is_in_info = addon_info is not None
            is_in_list = slug in installed_slugs

            if is_in_info or is_in_list:
                _LOGGER.debug("LibreCoach add-on (%s) verified present (Info: %s, List: %s). Monitoring finished.", slug, is_in_info, is_in_list)
                return

            _LOGGER.warning("LibreCoach add-on (%s) not found in Double-Lock check (Attempt %d/%d).", slug, attempt + 1, max_retries)
            confirmed_missing += 1
        except Exception as exc:
            _LOGGER.debug("Double-Lock check encountered an error (Attempt %d/%d): %s", attempt + 1, max_retries, exc)

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    # Destructive cleanup ONLY if every retry definitively confirmed the add-on is missing.
    # If any attempt errored (ambiguous), fail-safe by stopping the bridge without cleanup.
    if confirmed_missing == max_retries:
        await _perform_self_cleanup(hass, slug)
    else:
        _LOGGER.error("Double-Lock: Could not confirm %s is installed after %d retries. Aborting bridge for safety.", slug, max_retries)
        manager = hass.data.get(DOMAIN)
        if manager:
            await manager.stop()

async def _perform_self_cleanup(hass: HomeAssistant, slug: str):
    """Clean up configuration if original add-on is gone."""
    _LOGGER.critical("Automated Cleanup: Removing LibreCoach BLE configuration as add-on is no longer installed")
    
    # 1. Notify User
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "LibreCoach BLE: Automated Cleanup",
            "message": (
                f"The LibreCoach add-on ({slug}) was uninstalled. "
                "The accompanying Bluetooth integration has automatically removed its entry from configuration.yaml. "
                "The integration will be completely gone following the next Home Assistant restart."
            ),
            "notification_id": "librecoach_ble_cleanup",
        }
    )

    # 2. Cleanup configuration.yaml
    config_yaml = hass.config.path("configuration.yaml")
    try:
        content = Path(config_yaml).read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = [l for l in lines if not l.strip().startswith("librecoach_ble:")]
        if len(lines) != len(new_lines):
            Path(config_yaml).write_text("\n".join(new_lines), encoding="utf-8")
            _LOGGER.info("Removed 'librecoach_ble:' from configuration.yaml")
    except Exception as exc:
        _LOGGER.error("Failed to clean up configuration.yaml: %s", exc)

    # 3. Remove config marker file
    try:
        Path(CONFIG_PATH).unlink(missing_ok=True)
        _LOGGER.debug("Removed config marker file")
    except Exception:
        pass

    # Note: As per HA standards and best practices, we avoid deleting 
    # the custom_component files themselves during runtime.

async def async_unload(hass: HomeAssistant) -> bool:
    """Unload the integration."""
    manager = hass.data.get(DOMAIN)
    if manager:
        await manager.stop()
    return True
