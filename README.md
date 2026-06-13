# Backroads4Me Home Assistant Add-ons — BETA

> # ⚠️ BETA TESTING REPOSITORY — NOT FOR PRODUCTION USE
>
> **This is NOT the LibreCoach add-on.** This repository contains **pre-release beta builds**
> intended only for testing. They may be unstable, contain bugs, break between updates, or
> change behavior without notice.
>
> **If you are a regular user, do NOT install from here.** Use the stable production
> repository instead: **[Backroads4Me/ha-addons](https://github.com/Backroads4Me/ha-addons)**.

To avoid any confusion with the production add-ons, every Docker image in this repository uses
the **`-beta`** suffix (e.g. `ghcr.io/backroads4me/amd64-librecoach-beta`). Beta add-ons install
**side by side** with their production counterparts — they do not replace or upgrade them — so a
beta build can never silently take over a working production install.

## Add-ons (beta)

- **[LibreCoach](./librecoach/README.md)** *(beta)*: For controlling and monitoring RV systems.
- **[CAN to MQTT Bridge](./can-mqtt-bridge/README.md)** *(beta)*: Initializes CAN interfaces and provides a bidirectional bridge to MQTT.

## Contributing

This repository uses a CLA for the LibreCoach add-on only. The CLA check is applied at the
repository level by CLA Assistant, so you may be prompted to sign even when contributing to other
add-ons. See `librecoach/CONTRIBUTING.md` for details.

## Installation (testers only)

Only add this repository if you intend to test pre-release builds. To add it to your Home
Assistant instance, click the button below:

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBackroads4Me%2Fha-addons-beta)
