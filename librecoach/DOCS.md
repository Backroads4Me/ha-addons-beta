# LibreCoach Documentation

## Concept: The "System" vs. The "Add-on"

It is important to distinguish between **LibreCoach (The System)** and this **Add-on**.

### 1. The LibreCoach System

This is the "App" and final product. It is a collection of services (Mosquitto, Node-RED, and the Vehicle Bridge) that run in the background to control your RV.

- **Status:** Always Running.
- **Control:** Via Home Assistant Dashboards and highly customizable.
- **Composition:** The unified system formed by the sum of all installed components.

### 2. This LibreCoach Add-on

This is the system orchestrator and bridge. It ensures the System is installed and configured, handles the Settings UI, and actively runs the `vehicle_bridge` service.

- **Status:** Runs continuously in the background.
- **Function:** It installs missing components, updates Node-RED flows, hosts the LibreCoach Settings UI sidebar, and runs the Vehicle Bridge (handling CAN bus, Micro-Air Bluetooth, and Geo Bridge updates).

## Updating LibreCoach

If you have automatic updates enabled in Home Assistant, updates are applied automatically. When a new version is installed, HAOS restarts the addon, which re-runs the orchestrator with the updated code.

## Configuration

### Core Settings (Add-on Config)

The following core settings are managed in the Home Assistant Add-on **Configuration** tab:

| Option                                                      | Type    | Default | Description                                                                                                                                                                                     |
| :---------------------------------------------------------- | :------ | :------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CAN Interface`                                             | String  | `can0`  | The host network interface name for your CAN hardware (e.g., `can0`, `vcan0`).                                                                                                                  |
| `Enable Debug Logging`                                      | Boolean | `false` | Enables verbose logging of API calls and setup steps. Use only for troubleshooting.                                                                                                             |
| `Allow Node-RED Overwrite (Initial install config only)`    | Boolean | `false` | **DANGER:** Only used during first install. If Node-RED is already installed, this must be `true` to allow LibreCoach to delete your existing flows and install the LibreCoach system.          |
| `Prevent Flow Updates (Referenced at every update)`         | Boolean | `false` | **SAFETY:** If `true`, LibreCoach will never update your Node-RED flows when the add-on is updated. Use this if you have customized your flows and want to prevent them from being overwritten. |

### Settings UI (Sidebar)

Most operational settings—including Bluetooth tracking, Geo Bridge, and solar configuration—have moved to the new **Settings UI**.
You can access this by clicking **LibreCoach** in the Home Assistant sidebar.

## Automated Settings

LibreCoach automatically handles MQTT credentials to ensure seamless communication between the bridge and the automation flows.

- **MQTT Topics**: Defaults to `can/raw`, `can/send`, and `can/status`.
- **Authentication**: LibreCoach creates a dedicated `librecoach` user in Mosquitto automatically.

## Hardware Setup

LibreCoach primarily utilizes a physical connection to your RV's CAN bus.

1.  Install your CAN HAT/Adapter (e.g., Waveshare CAN HAT) on your Raspberry Pi.
2.  Ensure the interface is active in the host OS (usually `can0`).
3.  **Note:** The internal Vehicle Bridge will fail to initialize CAN if the hardware is missing, but the orchestrator will still successfully deploy the rest of the software stack (useful for testing or resolving configuration errors).

## Troubleshooting

### Protect Your Flows

If you have spent time customizing your LibreCoach flows and want to ensure a future update doesn't wipe them out:

1.  Go to the **Configuration** tab.
2.  Toggle **Prevent Flow Updates (Referenced at every update)** to `true`.
3.  Scroll down and click **Save**.

Future updates will still update the system software (Vehicle Bridge, Python scripts), but your Node-RED flows will remain untouched.

### "Installation aborted to protect existing flows"

**Reason:** You have Node-RED installed, and LibreCoach is refusing to delete your work.
**Fix:**

1.  Backup your existing flows if you want to keep them.
2.  Go to the **Configuration** tab.
3.  Toggle **Allow Node-RED Overwrite (Initial install config only)** to `true`.
4.  Scroll down and click **Save**.

### Using Node-RED Independently

If you wish to stop LibreCoach from managing Node-RED:

1.  Uninstall the **LibreCoach** add-on.
2.  Go to the **Node-RED** add-on configuration tab.
3.  Just above the "Show unused optional configuration options" toggle you should see:

    `bash /share/.librecoach/init-nodered.sh` &#x2716;

4.  Click the &#x2716; to delete the entry and then click save.

### Uninstalling the Bluetooth Integration

Because Home Assistant add-ons cannot automatically remove files from your `/config` directory during uninstallation, you should clean up the Bluetooth integration **before** uninstalling the add-on:

1.  Open the **LibreCoach** sidebar settings (Ingress UI).
2.  Toggle **Enable Micro-Air EasyTouch Thermostat** to **OFF**.
3.  Click **Save Settings**.
4.  **Restart** the LibreCoach add-on.
5.  Wait for the add-on logs to confirm the autonomous cleanup of the integration.
6.  (Optional) Restart Home Assistant to fully remove the integration from memory.
7.  Now you can safely uninstall the **LibreCoach** add-on.

If you have already uninstalled the add-on, you must manually delete the `/config/custom_components/librecoach_ble` folder and remove the `librecoach_ble:` line from your `configuration.yaml` (or rely on the automated cleanup if you reinstall).
