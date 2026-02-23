import asyncio
import json
import logging
import os
from pathlib import Path

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONFIG_PATH
from .bridge import BleBridgeManager

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up LibreCoach BLE from configuration.yaml."""
    _LOGGER.info("LibreCoach BLE integration loading")

    # Read config written by the add-on
    try:
        def _read_config():
            path = Path(CONFIG_PATH)
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8")

        conf_text = await hass.async_add_executor_job(_read_config)

        if conf_text is None:
             _LOGGER.warning("Config file not found at %s — add-on may not have started yet", CONFIG_PATH)
             return True

        conf = json.loads(conf_text)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _LOGGER.warning("Config file error: %s", exc)
        return True

    _LOGGER.info("Config loaded: microair_enabled=%s, addon_slug=%s",
                 conf.get("microair_enabled"), conf.get("addon_slug"))

    # Start monitoring task for suicide check (delayed)
    addon_slug = conf.get("addon_slug")
    if addon_slug:
        hass.async_create_task(_monitor_addon_status(hass, addon_slug))

    if not conf.get("microair_enabled"):
        _LOGGER.info("MicroAir disabled in add-on config")
        # Clear locked device address so it rediscovers on re-enable
        if conf.get("locked_devices"):
            conf.pop("locked_devices", None)

            def _write_cleared():
                Path(CONFIG_PATH).write_text(json.dumps(conf))

            try:
                await hass.async_add_executor_job(_write_cleared)
                _LOGGER.info("Cleared locked device addresses")
            except Exception as exc:
                _LOGGER.debug("Failed to clear locked devices: %s", exc)
        return True

    manager = BleBridgeManager(hass, conf)
    hass.data[DOMAIN] = manager

    # Start after HA is fully running (Bluetooth + MQTT ready)
    async def _start_bridge(event=None):
        _LOGGER.info("Starting BLE bridge (homeassistant_started fired)")
        await manager.start()
        _LOGGER.info("BLE bridge started — listening for MicroAir advertisements")

    hass.bus.async_listen_once("homeassistant_started", _start_bridge)
    _LOGGER.info("BLE bridge will start when Home Assistant is fully loaded")

    return True

async def _monitor_addon_status(hass: HomeAssistant, slug: str):
    """Monitor add-on status and perform cleanup if uninstalled.

    Uses the Supervisor REST API directly to avoid dependency on internal
    HA Python APIs (is_hassio, hass.components.hassio) that change between releases.
    """
    # Wait for HA to fully start and Add-ons to initialize
    await asyncio.sleep(120)

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        _LOGGER.warning("No SUPERVISOR_TOKEN — not running on HA OS. Cannot verify add-on status.")
        return

    supervisor = os.environ.get("SUPERVISOR", "http://supervisor")
    headers = {"Authorization": f"Bearer {token}"}
    session = async_get_clientsession(hass)
    timeout = aiohttp.ClientTimeout(total=10)

    max_retries = 3
    retry_delay = 30
    confirmed_missing = 0

    for attempt in range(max_retries):
        try:
            # Source 1: Check individual add-on info
            is_in_info = False
            async with session.get(
                f"{supervisor}/addons/{slug}/info",
                headers=headers, timeout=timeout
            ) as resp:
                if resp.status == 200:
                    is_in_info = True

            # Source 2: Check the full installed add-ons list
            is_in_list = False
            async with session.get(
                f"{supervisor}/addons",
                headers=headers, timeout=timeout
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    addons = data.get("data", {}).get("addons", [])
                    is_in_list = any(a.get("slug") == slug for a in addons)

            if is_in_info or is_in_list:
                _LOGGER.debug("LibreCoach add-on (%s) verified present.", slug)
                return

            _LOGGER.warning("LibreCoach add-on (%s) not found in Double-Lock check (Attempt %d/%d).", slug, attempt + 1, max_retries)
            confirmed_missing += 1
        except Exception as exc:
            _LOGGER.debug("Double-Lock check error (Attempt %d/%d): %s", attempt + 1, max_retries, exc)

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

    # 2. Cleanup configuration.yaml and marker file
    config_yaml = hass.config.path("configuration.yaml")
    
    def _do_file_cleanup():
        try:
            content = Path(config_yaml).read_text(encoding="utf-8")
            lines = content.splitlines()
            new_lines = [l for l in lines if not l.strip().startswith("librecoach_ble:")]
            if len(lines) != len(new_lines):
                Path(config_yaml).write_text("\n".join(new_lines), encoding="utf-8")
            Path(CONFIG_PATH).unlink(missing_ok=True)
            return True
        except Exception as exc:
            return exc
            
    result = await hass.async_add_executor_job(_do_file_cleanup)
    if result is True:
        _LOGGER.info("Removed 'librecoach_ble:' from configuration.yaml and deleted marker file")
    else:
        _LOGGER.error("Failed to clean up files: %s", result)

    # Note: As per HA standards and best practices, we avoid deleting 
    # the custom_component files themselves during runtime.

async def async_unload(hass: HomeAssistant) -> bool:
    """Unload the integration."""
    manager = hass.data.get(DOMAIN)
    if manager:
        await manager.stop()
    return True
