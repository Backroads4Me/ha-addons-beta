# Backroads4Me Home Assistant Add-ons — BETA

> ## ⚠️ BETA TESTING REPOSITORY — NOT FOR PRODUCTION USE
>
> This repository publishes **pre-release LibreCoach builds** for deliberate testing. Beta
> builds may be unstable, contain bugs, or change behavior between updates.
>
> For normal use, install LibreCoach from the
> **[stable repository](https://github.com/Backroads4Me/ha-addons)** instead.

## Before testing

- Create a full Home Assistant backup.
- Uninstall the LibreCoach version you are leaving before installing another one, whether you
  are moving to the beta, back to stable, or between beta and alpha. Stopping it is not enough:
  every LibreCoach version turns on its own **Start on boot** when it runs, so after the next Home
  Assistant restart all installed versions start together and fight over the same Node-RED
  installation, CAN interface, and Home Assistant entities.
- Your settings carry over. Every fresh install copies the settings saved by the stable add-on,
  or, if you have never run stable, the ones saved by the last beta or alpha build.
- Read the [LibreCoach changelog](./librecoach/CHANGELOG.md) for the behavior under test.
- Expect to provide the beta version and relevant logs when reporting a problem.

Every image published by this repository uses the **`-beta`** suffix, such as
`ghcr.io/backroads4me/amd64-librecoach-beta`. A beta build does not replace or upgrade the stable
add-on automatically.

## Install the beta

Only add this repository if you intend to test a pre-release build:

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBackroads4Me%2Fha-addons-beta)

You can also add `https://github.com/Backroads4Me/ha-addons-beta` manually under Home Assistant's
add-on repositories. Install **LibreCoach** from **BETA TESTING: LibreCoach**, review its
configuration, and then start it once the version you are leaving is uninstalled.

## Report beta feedback

Open a [bug report](https://github.com/Backroads4Me/ha-addons-beta/issues/new?template=bug_report.yml)
or a [feature request](https://github.com/Backroads4Me/ha-addons-beta/issues/new?template=feature_request.yml).
Include the LibreCoach beta version, affected hardware, expected behavior, actual behavior, and
the relevant add-on or Node-RED logs.

## LibreCoach

The add-on overview is shared with the stable repository, so its installation
button points to stable. Use the beta installation link above for testing.

- [Add-on overview](./librecoach/README.md)
- [First-start and configuration notes](./librecoach/DOCS.md)
- [Changelog](./librecoach/CHANGELOG.md)

## Contributing

This repository uses a CLA for the LibreCoach add-on. See
[CONTRIBUTING.md](./librecoach/CONTRIBUTING.md) for details.
