# LibreCoach Documentation

## Configuration

### Settings UI (Sidebar)

Most operational settings are managed in the **LibreCoach** sidebar panel — click the LibreCoach icon in the Home Assistant sidebar.

| Setting                 | Description                                                                                  |
| :---------------------- | :------------------------------------------------------------------------------------------- |
| **Geo Bridge**          | Syncs your Home Assistant location, timezone, and elevation from a GPS device tracker.       |
| **Victron Integration** | Enable or disable Victron GX device support. Enabled by default.                             |
| **Micro-Air EasyTouch** | Enable Bluetooth thermostat integration. Requires your Micro-Air account email and password. |
| **Beta Testing**        | Enables experimental features still in development.                                          |

Settings saved here take effect after restarting the add-on.

### Add-on Configuration Tab

These settings are found under **Settings → Apps → LibreCoach → Configuration**. Most users will not need to make changes here.

| Option                       | Description                                                                                                                                        |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Allow Node-RED Overwrite** | Only used during first install. Must be enabled to allow LibreCoach to replace existing Node-RED flows. **This will delete your current flows.**   |
| **Preserve Node-RED Flow Customizations** | Preserves your customized Node-RED flows during add-on updates. System software and reference files still update normally.                         |
| **Enable Debug Logging**     | Enables verbose logging for troubleshooting. Leave off during normal use.                                                                          |
| **CAN Interface**            | The host network interface name for your CAN hardware.                                                                                             |
| **MQTT User / Password**     | Credentials used by the Vehicle Bridge and Node-RED to connect to Mosquitto. Defaults are set automatically — most users should leave these as-is. |

## MQTT

LibreCoach automatically configures MQTT to ensure seamless communication between the Vehicle Bridge and Node-RED.

- A dedicated `librecoach` user is created in Mosquitto on first install.
- Default credentials are pre-configured and can be changed in the Configuration tab if needed.
- MQTT topics (`can/raw`, `can/send`, `can/status`) and CAN bitrate (250 kbps) are fixed.

## Hardware Setup

LibreCoach connects to your RV's CAN bus through a CAN HAT or USB adapter on your Raspberry Pi.

1. Install your CAN adapter (e.g., Waveshare CAN HAT) on the Raspberry Pi.
2. Ensure the interface is active in the host OS (usually `can0`).
3. If the CAN hardware is missing, the Vehicle Bridge will log the error but the rest of the system — Node-RED, Settings UI, Geo Bridge — will still deploy successfully. This is useful for testing or resolving configuration issues.

## Troubleshooting

### "Installation aborted to protect existing flows"

LibreCoach detected existing Node-RED flows and is refusing to overwrite them.

1. Back up your existing flows if you want to keep them.
2. Go to **Settings → Apps → LibreCoach → Configuration**.
3. Toggle **Allow Node-RED Overwrite** on.
4. Click **Save**.
