# AternAuto 2

Join your Aternos or exaroton server normally. AternAuto requests startup through
Dawn's service, then resumes the connection when the request is accepted. An
official Minecraft account and the server's startup permission are required.

## Changes

- Fabric, Forge and NeoForge distributions cover 49 loader/version combinations,
  from Minecraft 1.7.10 to 26.3. Pick the JAR for your loader and Minecraft version
  using the included `artifacts.json`; install only one AternAuto JAR.
- After an accepted startup request, an exact connection-reset failure triggers
  one silent reconnect after 35 client ticks. A second failure shows the normal
  Minecraft disconnect screen. Cancelling also cancels the pending retry.
- Startup requests can be cancelled or skipped with **Connect anyway**. Repeated
  clicks do not send duplicate startup requests.
- The interface follows Minecraft's language, with 24 translations and regional
  fallbacks, including separate Brazilian Portuguese and Traditional Chinese.
- An optional **Report problem** screen explains the report contents before
  sending. Reports include mod names and versions, the server address and port,
  environment versions, the error and the full User-Agent. They are sent to
  Discord through AternAuto's reporting service only after confirmation.
- Each instance stores a randomly selected User-Agent index in
  `config/aternauto/uatu`. Invalid or missing files are regenerated.
- Newly accepted server starts contribute to an always-active public counter.
  The request contains only AternAuto's version and an encoded timestamp.
  Already-running responses and rejected startup requests are not counted.

Statistics: <https://aa.bagyette.fr/telemetry>. Data information:
<https://aa.bagyette.fr/privacy>.

This is a client mod. It does not bypass permissions or translate Minecraft
protocols: your client must still be compatible with the server. Availability
depends on Dawn's online API. Automated launch verification covers loading and
request-screen rendering with the exact release JARs; it does not guarantee live
server startup or compatibility with every other mod.

Made by Bagyette0 (`bagyette.fr` on Discord). Licensed under the included
Bagyette Custom License (BCL-1.0).
