# AternAuto 2

**AternAuto 2** requests Aternos server startup when you connect from Minecraft.
Client mod for Fabric, Forge and NeoForge, with 24 interface languages. It also
automatically retries one “Connection reset” error after a startup request.

No Dawn Launcher or Fabric API required. Install the mod on your client, connect
to your Aternos or exaroton server, and AternAuto handles the startup request.

**[Download AternAuto 2](https://aa.bagyette.fr/download)** ·
[GitHub release](https://github.com/Bagyette/AternAuto/releases/tag/2) ·
[CurseForge](https://www.curseforge.com/minecraft/mc-mods/aternauto)

## Supported versions

| Loader | Supported Minecraft versions |
| --- | --- |
| **Fabric** | 1.14.4, 1.16.5, 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.21.1, 1.21.4, 1.21.8, 1.21.9, 1.21.10, 1.21.11, 26.1, 26.1.1, 26.1.2, 26.2, 26.3 |
| **Forge** | 1.7.10, 1.8.9, 1.12.2, 1.14.4, 1.16.5, 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.21.1, 1.21.4, 1.21.8, 1.21.9, 1.21.10, 1.21.11, 26.1, 26.1.1, 26.1.2, 26.2, 26.3 |
| **NeoForge** | 1.20.1, 1.21.1, 1.21.4, 1.21.8, 1.21.9, 1.21.10, 1.21.11, 26.1, 26.1.1, 26.1.2, 26.2, 26.3 |

**Client-side only.** The interface follows Minecraft's language, including
regional variants, and falls back to English when a translation is unavailable.

## Installation

1. Download the JAR matching your loader and Minecraft version.
2. Put **one AternAuto JAR** in your instance's `mods` folder. Remove older copies.
3. Join your server as usual with an official Minecraft account signed in.

Use a `.aternos.me` or `.exaroton.me` address; custom domains are not supported.
Do not combine AternAuto with Dawn or Feather.

**Note:** You must have permission to start the server. AternAuto does not bypass
restrictions, queues or startup delays. A confirmed request does not mean the
server is ready, and you may need to reconnect once it is. Your Minecraft version
must also be compatible with the server.

## Statistics and problem reports

Version 2 includes an always-active startup counter. It sends only the mod version
and a timestamp when Dawn confirms a new startup request. Already-running servers
and refused requests are not counted. [Statistics](https://aa.bagyette.fr/telemetry).

Problem reports are optional: review the information and confirm before sending.
They include your technical environment, mod names and versions, error details,
User-Agent and server address with its port. No full logs or JARs are uploaded.
[Privacy notice](https://aa.bagyette.fr/privacy).

## Development

[Build instructions](docs/BUILD.md) · [Changelog](docs/RELEASE_NOTES_2.md) ·
[Report an issue](https://github.com/Bagyette/AternAuto/issues)

Created by **Bagyette0**. Discord: **bagyette.fr**.
Released under the [Bagyette Custom License (BCL-1.0)](LICENSE).
