# AternAuto

AternAuto requests startup when you join an Aternos or exaroton server from Minecraft. Put the mod in your instance's `mods` folder and connect to your server as usual. You do not need the Dawn launcher or Fabric API.

The mod pauses the connection while it verifies your Minecraft session and sends the startup request. If the request is accepted, Minecraft resumes connecting. If it fails, the screen shows the reason and lets you connect anyway or cancel.

## Before you connect

You need an official Minecraft account signed in through your launcher, and permission to start the server. AternAuto does not bypass access controls, queues, or the server's auto-start settings.

An accepted request does not mean the server is ready. You may enter Aternos's waiting lobby or need to reconnect once startup finishes. After an accepted startup request, AternAuto silently retries one exact connection-reset failure after 35 client ticks. A second failure shows Minecraft's normal error. Your Minecraft version must match the server to enter the world.

## Choose your download

| Loader | Supported Minecraft versions |
| --- | --- |
| Fabric | 26.3, 26.2, 26.1.2, 26.1.1, 26.1, 1.21.11, 1.21.10, 1.21.9, 1.21.8, 1.21.4, 1.21.1, 1.20.1, 1.19.4, 1.19.2, 1.18.2, 1.16.5, 1.14.4 |
| Forge | All Fabric versions above, plus 1.12.2, 1.8.9 and 1.7.10 |
| NeoForge | 26.3, 26.2, 26.1.2, 26.1.1, 26.1, 1.21.11, 1.21.10, 1.21.9, 1.21.8, 1.21.4, 1.21.1 and 1.20.1 |

Version 2 has 34 distribution JARs covering these 49 combinations. Choose the file matching both your loader and Minecraft version; `releases/2/artifacts.json` gives the exact mapping and SHA-256 checksums. Fabric uses three families (legacy, modern and 26); Forge 1.8.9/1.12.2 share one JAR. Other Forge and NeoForge versions have separate JARs. This is a client mod; do not install it on the server. Remove older AternAuto or `auto-aternos-start` copies first, and do not combine it with Dawn or Feather. Release readiness is recorded by `complete` and `runtimeVerified` in the artifact index; compilation alone is not launch validation.

## Languages

Version 2 includes 24 languages: English, French, German, Spanish, Brazilian Portuguese, Portuguese, Russian, Italian, Polish, Turkish, Japanese, Simplified Chinese, Dutch, Korean, Ukrainian, Traditional Chinese, Indonesian, Vietnamese, Hindi, Arabic, Czech, Romanian, Swedish and Hungarian. The interface follows Minecraft's selected language. Regional variants use their base language, including Canadian French and Mexican Spanish. Brazilian Portuguese remains separate. Chinese Hans/Hant scripts take precedence over region; Taiwan, Hong Kong and Macao use Traditional Chinese when no script is specified. The legacy Indonesian `in` code maps to `id`. Unsupported languages fall back to English. Catalogs are read explicitly as UTF-8. Font coverage and text shaping still depend on the Minecraft client, especially on old releases.

## Service and privacy

AternAuto uses Dawn's online API to request startup. It works without the launcher, but still depends on that service being available. It supports addresses ending in `.aternos.me` or `.exaroton.me`; custom domains are not supported.

Your Minecraft access token is sent only to Mojang's session service. Dawn receives your Minecraft username, a session-verification challenge, and the server address. AternAuto keeps tokens in memory during the request and does not save or log them.

A startup counter is always active. When Dawn confirms a newly accepted start (HTTP 202 and `alreadyInProgress: false`), the mod sends only its version and an encoded current timestamp to `https://aa.bagyette.fr/ping`. Already-running responses and failed requests are not counted. Sending happens in the background and cannot block joining. The receiving server necessarily sees the network connection's IP address; the counter payload contains no player name or server address. Public statistics and data information are available at [aa.bagyette.fr](https://aa.bagyette.fr/telemetry) and its [privacy page](https://aa.bagyette.fr/privacy).

For selected failures, an optional **Report problem** button opens a consent screen before anything is sent. A report includes AternAuto/Minecraft/Java and loader versions, OS, mod names and versions, the target server address and port, the classified error, HTTP status if applicable, and the full User-Agent. Reports go through `https://aa.bagyette.fr/issue/dscwh/` to Discord. They contain no account token, player UUID, full log or mod JAR. Cancelling the screen sends nothing.

Each instance keeps its randomly selected User-Agent index (1–30) in `config/aternauto/uatu`. Missing, invalid or out-of-range values are regenerated. The selection does not use your Minecraft username or UUID.

Made by Bagyette0. Discord: **bagyette.fr**.

Released under the **Bagyette Custom License (BCL-1.0)**. Free use and free redistribution of the complete, unmodified mod are allowed under its conditions. Publishing modified versions, selling the mod, and removing the author credit are not allowed. See the included `LICENSE` for the full terms.

## Source and build

This repository contains the shared request code and the Minecraft adapters. Java sources follow the Google Java Style Guide.

Build requirements: JDK 25, Python 3.11 or newer, and network access for dependencies. On Windows,
run `./build.ps1 -JdkDirectory <path-to-JDK-25> -Tasks buildAll` to compile,
test, package and launch-check the full matrix into `releases/2/`. The wrapper limits all build processes
together to 5632 MiB, with one Gradle worker and no parallel project execution.
JDKs 8, 17 and 21 are also needed for the corresponding client generations. The launch checks use isolated offline test accounts, muted clients and the secondary 1920×1080 monitor; they fail if that monitor is unavailable. `assembleAll` packages without game launches. Direct Gradle invocation does not apply the Windows process-tree memory limit.

The startup protocol uses `api.dawn.gg/v2/minecraft/server-id`, Mojang's session join endpoint, `api.dawn.gg/v2/minecraft/has-joined`, and `api.dawn.gg/v2/aternos/auto-start`. Requests have timeouts and do not follow HTTP redirects.

The launch report checks the exact packaged JAR hash, loader initialization, Mixin application and rendering of the AternAuto request screen. Offline checks do not establish successful real-account authentication, actual server startup or compatibility with every other mod. Those boundaries also apply when all launch checks pass.

## Maintenance

Version 2 uses one shared core and three loader modules. The requested 49-target
matrix and build architecture are documented in [COMPATIBILITY_V2.md](COMPATIBILITY_V2.md)
and [ARCHITECTURE.md](ARCHITECTURE.md). Shared logic lives in `common/`; loader and
version adapters supply Minecraft-specific UI and connection hooks. There are no
34 independent copies of the startup protocol to maintain.
