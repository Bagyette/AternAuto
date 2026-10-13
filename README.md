# AternAuto

AternAuto requests startup when you join an Aternos or exaroton server from Minecraft. Put the mod in your instance's `mods` folder and connect to your server as usual. You do not need the Dawn launcher or Fabric API.

The mod pauses the connection while it verifies your Minecraft session and sends the startup request. If the request is accepted, Minecraft resumes connecting. If it fails, the screen shows the reason and lets you connect anyway or cancel.

## Before you connect

You need an official Minecraft account signed in through your launcher, and permission to start the server. AternAuto does not bypass access controls, queues, or the server's auto-start settings.

An accepted request does not mean the server is ready. You may enter Aternos's waiting lobby or need to reconnect once startup finishes. If you get a connection reset, try connecting again. Your Minecraft version must match the server to enter the world.

## Choose your download

| Loader | Supported Minecraft versions |
| --- | --- |
| Fabric | 26.3, 26.2, 26.1.2, 26.1.1, 26.1, 1.21.11, 1.21.10, 1.21.9, 1.21.1, 1.20.1, 1.19.4, 1.18.2, 1.16.5, 1.14.4 |
| Forge | 1.12.2, 1.8.9 |

Each download is one JAR for all the versions listed in its row. Install only the file for your loader. This is a client mod; do not install it on the server. Remove the older `auto-aternos-start` mod before installing AternAuto, and do not combine it with Dawn or Feather.

## Languages

English, French, German, Spanish, Brazilian Portuguese, Portuguese, Russian, and Italian. The interface follows Minecraft's selected language. Regional variants use the corresponding translation: Canadian French uses French, British English uses English, and Mexican Spanish uses Spanish. Brazilian Portuguese has its own translation. Unsupported languages fall back to English.

## Service and privacy

AternAuto uses Dawn's online API to request startup. It works without the launcher, but still depends on that service being available. It supports addresses ending in `.aternos.me` or `.exaroton.me`; custom domains are not supported.

Your Minecraft access token is sent only to Mojang's session service. Dawn receives your Minecraft username, a session-verification challenge, and the server address. AternAuto keeps tokens in memory during the request and does not save or log them.

Made by Bagyette0. Discord: **bagyette.fr**.

Released under the **Bagyette Custom License (BCL-1.0)**. Free use and free redistribution of the complete, unmodified mod are allowed under its conditions. Publishing modified versions, selling the mod, and removing the author credit are not allowed. See the included `LICENSE` for the full terms.

## Source and build

This repository contains the shared request code and the Minecraft adapters. Java sources follow the Google Java Style Guide.

Build requirements: JDK 25, Python 3, and network access for dependencies. On Windows, run `build.ps1 -JdkDirectory <path-to-JDK-25>`. Build output is placed in `releases/1/`.

The startup protocol uses `api.dawn.gg/v2/minecraft/server-id`, Mojang's session join endpoint, `api.dawn.gg/v2/minecraft/has-joined`, and `api.dawn.gg/v2/aternos/auto-start`. Requests have timeouts and do not follow HTTP redirects.

The pre-localization builds were launched in Prism across all 16 declared versions. Minecraft 1.21.11 entered a live server; 1.8.9 loaded and attempted the connection, but its captured window was blank. The language update was compiled without rerunning gameplay tests. Historical reports are not a validation of the current binary.
