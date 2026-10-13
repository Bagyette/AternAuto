"""Ensure rendered smoke-test adapters match the exact classes in the final JAR."""

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ["1.18.2", "1.19.4", "1.20.1", "1.21.1", "1.21.9", "1.21.10", "1.21.11",
            "26.1", "26.1.1", "26.1.2", "26.2", "26.3"]
final_jar = ROOT / "releases/1/AternAuto-1-fabric-multiversion.jar"
report = {"jarSha256": hashlib.sha256(final_jar.read_bytes()).hexdigest(), "heapMiB": 800,
          "session": "offline test account; no Aternos start request", "versions": {}}
with zipfile.ZipFile(final_jar) as final:
    index = json.loads(final.read("aternauto-adapters.json"))
    for version in VERSIONS:
        directory = ROOT / ".tools/runtime-smoke" / version
        result = (directory / "result.txt").read_text().strip()
        assert result == "REQUEST_SCREEN_RENDERED", (version, result)
        log = (directory / "console.log").read_text(encoding="utf-8", errors="replace")
        assert "ATERN_SMOKE_PASS" in log
        suffix = index[version]["package"] + "/"
        prefixes = ("fr/autoaternos/", "fr/bagyette/aternauto/compat/" + suffix,
                    "fr/bagyette/aternauto/mixin/" + suffix)
        count = 0
        with zipfile.ZipFile(directory / "mods/AternAuto-1-fabric-multiversion.jar") as tested:
            for name in final.namelist():
                if name.endswith(".class") and name.startswith(prefixes):
                    assert final.read(name) == tested.read(name), (version, "Untested class changed", name)
                    count += 1
        report["versions"][version] = {"result": "passed", "classesMatched": count,
            "onboardingContinue": "ATERN_SMOKE_CONTINUE" in log}
(ROOT / "releases/1/runtime-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("12 Minecraft runtime checks verified against the final packaged classes.")
