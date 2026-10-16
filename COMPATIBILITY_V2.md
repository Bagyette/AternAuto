# AternAuto 2 compatibility targets

All 49 requested combinations are mandatory, including every plus sign
in the supplied table. Loader availability is not mod compatibility.

All 49 targets compile into 34 JARs and passed offline client launch checks.
`releases/2/artifacts.json` and `runtime-checks.json` record the exact tested JAR
hashes. Validation covers loader startup, required class/Mixin loading and the
actual AternAuto request screen, not live-account server startup.
The table pins the loader builds used for compilation and launch verification.

| Minecraft | Fabric | Forge | NeoForge | Java |
| --- | --- | --- | --- | --- |
| 1.7.10 | — | Verified (1.7.10-10.13.4.1614-1.7.10) | — | 8 |
| 1.8.9 | — | Verified (1.8.9-11.15.1.2318-1.8.9) | — | 8 |
| 1.12.2 | — | Verified (1.12.2-14.23.5.2864) | — | 8 |
| 1.14.4 | Verified (0.19.5) | Verified (1.14.4-28.2.30) | — | 8 |
| 1.16.5 | Verified (0.19.5) | Verified (1.16.5-36.2.42) | — | 8 |
| 1.18.2 | Verified (0.19.5) | Verified (1.18.2-40.3.12) | — | 17 |
| 1.19.2 | Verified (0.19.5) | Verified (1.19.2-43.5.2) | — | 17 |
| 1.19.4 | Verified (0.19.5) | Verified (1.19.4-45.4.5) | — | 17 |
| 1.20.1 | Verified (0.19.5) | Verified (1.20.1-47.4.28) | Verified (1.20.1-47.1.106) | 17 |
| 1.21.1 | Verified (0.19.5) | Verified (1.21.1-52.1.20) | Verified (21.1.262) | 21 |
| 1.21.4 | Verified (0.19.5) | Verified (1.21.4-54.1.22) | Verified (21.4.161) | 21 |
| 1.21.8 | Verified (0.19.5) | Verified (1.21.8-58.1.26) | Verified (21.8.57) | 21 |
| 1.21.9 | Verified (0.19.5) | Verified (1.21.9-59.0.5) | Verified (21.9.16-beta) | 21 |
| 1.21.10 | Verified (0.19.5) | Verified (1.21.10-60.1.18) | Verified (21.10.64) | 21 |
| 1.21.11 | Verified (0.19.5) | Verified (1.21.11-61.2.4) | Verified (21.11.48) | 21 |
| 26.1 | Verified (0.19.5) | Verified (26.1-62.0.9) | Verified (26.1.0.19-beta) | 25 |
| 26.1.1 | Verified (0.19.5) | Verified (26.1.1-63.0.2) | Verified (26.1.1.15-beta) | 25 |
| 26.1.2 | Verified (0.19.5) | Verified (26.1.2-64.1.5) | Verified (26.1.2.122) | 25 |
| 26.2 | Verified (0.19.5) | Verified (26.2-65.1.5) | Verified (26.2.0.93) | 25 |
| 26.3 | Verified (0.19.5) | Verified (26.3-66.0.12) | Verified (26.3.0.83) | 25 |

## Artifact plan

Families share an artifact only where their actual bindings can coexist.
An artifact is not ready for publication until every claimed target is validated.

- `forge-1.7.10`: 1.7.10.
- `forge-launchwrapper`: 1.8.9, 1.12.2.
- `fabric-legacy`: 1.14.4, 1.16.5.
- `forge-1.14.4`: 1.14.4.
- `forge-1.16.5`: 1.16.5.
- `fabric-modern`: 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.21.1, 1.21.4, 1.21.8, 1.21.9, 1.21.10, 1.21.11.
- `forge-1.18.2`: 1.18.2.
- `forge-1.19.2`: 1.19.2.
- `forge-1.19.4`: 1.19.4.
- `forge-1.20.1`: 1.20.1.
- `neoforge-1.20.1`: 1.20.1.
- `forge-1.21.1`: 1.21.1.
- `neoforge-1.21.1`: 1.21.1.
- `forge-1.21.4`: 1.21.4.
- `neoforge-1.21.4`: 1.21.4.
- `forge-1.21.8`: 1.21.8.
- `neoforge-1.21.8`: 1.21.8.
- `forge-1.21.9`: 1.21.9.
- `neoforge-1.21.9`: 1.21.9.
- `forge-1.21.10`: 1.21.10.
- `neoforge-1.21.10`: 1.21.10.
- `forge-1.21.11`: 1.21.11.
- `neoforge-1.21.11`: 1.21.11.
- `fabric-26`: 26.1, 26.1.1, 26.1.2, 26.2, 26.3.
- `forge-26.1`: 26.1.
- `neoforge-26.1`: 26.1.
- `forge-26.1.1`: 26.1.1.
- `neoforge-26.1.1`: 26.1.1.
- `forge-26.1.2`: 26.1.2.
- `neoforge-26.1.2`: 26.1.2.
- `forge-26.2`: 26.2.
- `neoforge-26.2`: 26.2.
- `forge-26.3`: 26.3.
- `neoforge-26.3`: 26.3.

Forge 1.7.10 has its own FML generation. NeoForge 1.20.1 uses the
older `net.neoforged:forge` artifact, not the modern NeoForge artifact.
The initial plan deliberately separates other Forge/NeoForge versions.
Shared artifacts can replace them after validation, without changing the targets.

Every target must include autostart, exactly one reset retry after 35 client
ticks, confirmed-start telemetry, all 24 language catalogs and regional fallbacks,
the requested credit, and the license. Server-version compatibility remains
a separate requirement; the client mod does not translate Minecraft protocols.
