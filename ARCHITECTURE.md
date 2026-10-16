# One maintained codebase, multiple distribution JARs

## Java namespaces

All maintained Java code uses the `fr.bagyette.aternauto` base:

- `fr.bagyette.aternauto.common`: core and its unit tests.
- `fr.bagyette.aternauto.fabric`: Fabric bootstrap and tests.
- `fr.bagyette.aternauto.fabric.compat.<version>`: Minecraft bindings.
- `fr.bagyette.aternauto.fabric.mixin.<version>`: annotated Fabric Mixins only.
- `fr.bagyette.aternauto.forge`: existing Forge binding and transformer tests.
- `fr.bagyette.aternauto.neoforge.compat.<version>`: typed NeoForge bindings.
- `fr.bagyette.aternauto.testing.smoke`: offline launch harness.

Source directories, generated version classes, reflection names and Mixin metadata
follow the same namespaces. Historical version 1 binary verification utilities
retain the old binary names intentionally; version 1 JARs are not rewritten.

## Modules

- `common/`: Dawn authentication and startup protocol, request state, retry policy,
  statistics sender, 24 language catalogs and fallbacks, and credits. No Minecraft,
  Fabric, Forge, NeoForge or Mixin imports. Its tests need no loader compilation.
- `fabric/`: Fabric bootstrap, Mixin selection and Fabric-specific tests.
- `forge/`: Forge build aggregation.
- `neoforge/`: NeoForge build aggregation.
- `versions/`: typed Minecraft bindings, included as child projects of their
  loader. An existing compatible adapter can serve several Minecraft versions.
  These are internal adapters, not separately maintained products.

Dependency direction is adapters -> loader integration -> common. The common core
never depends on an adapter. Forge's transformer tests belong to its LaunchWrapper
adapter; Fabric's Mixin layout tests belong to Fabric.

`gradle/loader-adapters.gradle` defines shared build conventions. No adapter has
its own copied root build. All Fabric, Forge and NeoForge adapters use it.
`mod_version` in `gradle.properties` is the single version source. It generates
`BuildVersion.VERSION` and supplies loader metadata and artifact names.

## Complete build

The entry point is `gradlew.bat buildAll` (or `./gradlew buildAll`):

1. Check the 49-target contract, required features and available launch drivers.
2. Run common and loader-specific tests, and check Java formatting.
3. Compile the shared modules and required adapters.
4. Package the 34 declared artifact families from those outputs, checking shared
   entry conflicts, license and all 24 language catalogs. Each Fabric artifact declares
   only its actual supported target versions.
5. Launch every target against its packaged JAR, using offline test credentials.
   A successful process exit alone is insufficient: the expected screen must be
   rendered, a fresh pass marker recorded, and the tested JAR hash must match.
6. Audit the verified release and create `releases/AternAuto-2-all-loaders.zip`
   with the JARs, license, checksums, compatibility index and release notes.

`assembleAll` performs packaging without running Minecraft. `checkBuildStructure`
checks module boundaries and packaging behavior without compiling a mod.

The Windows `build.ps1` wrapper supplies the selected JDK and a project-local
socket directory for this machine's Java loopback issue, then invokes the same
`buildAll` task. It restores its environment on exit. `-Tasks buildPreview` builds
and packages the existing adapters in `releases/2-preview/` without claiming the
complete matrix. Its manifest records missing ports and features; the full release
preflight and launch verification remain strict.

`tools/run_bounded_build.py` starts the wrapper in a Windows Job Object before it
can spawn children. Aggregate committed memory is capped at 5632 MiB, below 6 GB;
resident memory is also monitored. Closing the job terminates remaining workers.
Gradle runs with one worker, no parallel project execution, a 2560 MiB heap, and
384 MiB heaps for tests and formatting. Logs and measured memory peaks are stored
under `.tools/`; Gradle caches and temporary files also stay in that directory.
Direct calls to `gradlew` do not apply the Windows process-tree memory ceiling.

## One target contract

`compatibility-v2.json` owns the target list, artifact families and required
features. A binding resolves to the actual `versions/*/version.json` descriptor;
its `features` list records the behavior implemented by that adapter and common
core. This is implementation readiness, not test evidence or compatibility.

The packager derives its inputs from this contract. It never discovers outputs
with a wildcard that could pick up an older release. It writes a manifest that
maps every target to exactly one artifact, with SHA-256 hashes.

All artifact families are staged before a release directory is created. An
existing release is preserved rather than silently overwritten.

## Automated launch verification

`tools/launch_matrix.py` creates a fresh isolated directory per run and target,
limits clients to 800 MiB, and records failures as failures, including missing
drivers. No previous pass marker can satisfy a new run. Reports are written under
`.tools/runtime-matrix/`; a complete report is copied into the release only when
every required target passes.

An optional `-PresumeLaunchReport=<local-report.json>` reuses completed checks
only when the tested JAR and current artifact have the same SHA-256, the original
successful exit is recorded, and its result file, 15-frame render marker and
secondary-monitor marker are still present. Missing, failed or changed binaries
are launched in fresh directories. The complete report retains the source run
for each reused result. The default `buildAll` checks every target afresh.

The Fabric driver is adapted from the previous rendered-screen smoke tests.
Forge and NeoForge use their exact official installers in a project-local test
installation. All drivers render at least 15 frames of the actual request screen,
then request a normal client shutdown. Test-only harness JARs remain outside the
release. GLFW windows are created hidden and positioned on the secondary 1080p
monitor before being shown; the old LWJGL 2 clients set their position before
window creation. Minecraft 26.3 uses an equivalent SDL hook. Clients are muted
and use offline, non-user credentials. Older Forge and Minecraft 1.16.5 tests
initiate the connection from the main menu because startup joining can wait for
a preliminary server ping or be disabled for an offline account.

These offline tests cover startup, class loading, Mixin application and request
screen rendering. They do not prove real Mojang/Dawn authentication, remote
server availability, or that an Aternos server reached the online state. Common
unit tests cover the protocol replies, timestamp encoding and retry timing.

## Current verification boundary

All 49 target adapters compile and the 34 full-release JARs passed their offline
launch checks. The release index and runtime report bind each successful check
to its exact JAR hash. The public ZIP is finalized only after all 49 pass.
Typed adapters use the game's Java generation; common and Fabric bootstrap remain
Java 8. Forge 26.x is compiled by JDK 25 with Java 21 bytecode and Mixin level 21,
because Forge's bundled Sponge Mixin does not recognize `JAVA_25`. Minecraft 26.x
still requires Java 25 to run. Version 1 releases and Prism instances are unchanged.

Forge 1.7.10–1.14.4 use native coremod/event bridges. Forge 1.16.5 uses a mapped
binary compile and production SRG remapping. Forge 1.18.2–1.20.1 and NeoForge
1.20.1 use the legacy ModDev binary pipeline and generated Mixin refmaps. Modern
NeoForge uses ModDev with recompilation disabled. Forge 1.21.x and 26.x compile
against official mapped vanilla binaries plus the exact loader's API libraries.
No pipeline needs to recompile the full Minecraft source tree. Retry lifecycle
and report contexts are maintained by the shared `ConnectionFlow`, with small
typed screen/tick/connection bridges in each adapter.
