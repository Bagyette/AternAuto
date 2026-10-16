# Building AternAuto

The project uses one shared core, three loader modules, and Minecraft-specific
adapters in `versions/`. Gradle configuration and the wrapper are required build
files. Build caches, credentials and release binaries stay outside Git.

Use JDK 25 and Python 3.11 or newer. JDKs 8, 17 and 21 are also needed for the
corresponding Minecraft versions. The current dependency and launch tooling
targets Windows; runtime detection can reuse Prism's Java installations.

Compile, run unit checks and package all 34 JARs without launching Minecraft:

```text
python -B tools/run_bounded_build.py --jdk "C:/path/to/jdk-25" --log .tools/build.log assembleAll
```

The Python runner caps the whole process tree at 5632 MiB and uses one Gradle
worker. It invokes the Gradle wrapper directly; no PowerShell or batch launcher
is needed.

`buildAll` additionally runs all 49 offline client launch checks and creates the
public ZIP. Launch checks require a secondary 1920×1080 monitor and use isolated
offline accounts. They do not verify real-account authentication or a live
Aternos server startup. Use `assembleAll` for compilation alone.

Build structure and translation checks can be run separately:

```text
python -B -m unittest discover -s tools/tests -v
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module details and
[COMPATIBILITY_V2.md](COMPATIBILITY_V2.md) for exact loader versions.
