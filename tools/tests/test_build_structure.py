"""Check build boundaries and packaging without compiling any Minecraft mod."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from distributions_v2 import LANGUAGES, binding, families, merge_entries, package, preflight, write_artifact
from launch_matrix import reusable_result, validate_artifact_index


class BuildStructureTest(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "compatibility-v2.json").read_text())
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".tools")
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_complete_target_contract_has_34_artifacts_and_49_targets(self):
        targets = self.plan["targets"]
        self.assertEqual(49, len({entry["id"] for entry in targets}))
        self.assertEqual({"fabric": 17, "forge": 20, "neoforge": 12}, {
            loader: sum(entry["loader"] == loader for entry in targets)
            for loader in ["fabric", "forge", "neoforge"]})
        self.assertEqual(34, len(families(self.plan)))

    def test_common_has_no_minecraft_or_loader_import(self):
        forbidden = ["net.minecraft", "net.fabricmc", "net.minecraftforge",
                     "net.neoforged", "org.spongepowered"]
        for path in (ROOT / "common/src/main/java").rglob("*.java"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("import "):
                    self.assertFalse(any(value in line for value in forbidden), str(path))
        common_build = (ROOT / "common/build.gradle").read_text()
        self.assertNotIn(":forge", common_build)
        self.assertNotIn(":fabric", common_build)

    def test_java_packages_use_the_project_namespace_and_matching_paths(self):
        sources = []
        for directory in ["common", "fabric", "forge", "neoforge", "versions", "tools/runtime_smoke/src"]:
            sources.extend(path for path in (ROOT / directory).rglob("*.java")
                           if "build" not in path.relative_to(ROOT).parts)
        self.assertTrue(sources)
        for path in sources:
            text = path.read_text(encoding="utf-8")
            package = re.search(r"^package ([\w.]+);", text, re.MULTILINE)
            self.assertIsNotNone(package, str(path))
            namespace = package.group(1)
            self.assertTrue(namespace.startswith("fr.bagyette.aternauto."), str(path))
            self.assertTrue(path.parent.as_posix().endswith(namespace.replace(".", "/")), str(path))
            self.assertNotRegex(text, r"fr[./]autoaternos")
        metadata = json.loads((ROOT / "fabric/src/main/resources/aternauto.mixins.json").read_text())
        self.assertEqual("fr.bagyette.aternauto.fabric.AdapterPlugin", metadata["plugin"])
        self.assertEqual("fr.bagyette.aternauto.fabric.mixin", metadata["package"])

    def test_alias_versions_share_one_adapter_project(self):
        targets = {entry["id"]: entry for entry in self.plan["targets"]}
        self.assertEqual(binding(targets["fabric-1.21.9"])["project"],
                         binding(targets["fabric-1.21.10"])["project"])
        self.assertEqual(binding(targets["forge-1.8.9"])["project"],
                         binding(targets["forge-1.12.2"])["project"])
        self.assertEqual(binding(targets["fabric-26.1"])["project"],
                         binding(targets["fabric-26.1.2"])["project"])

    def test_unported_targets_block_the_complete_release(self):
        def missing_adapter(target, root=ROOT):
            return None if target["id"] == "fabric-1.19.2" else binding(target, root)
        with patch("distributions_v2.binding", side_effect=missing_adapter):
            errors = preflight(self.plan)
        self.assertTrue(any("fabric-1.19.2: adapter not ported" in error for error in errors))
        with patch("distributions_v2.RUNTIME_DRIVERS", {"fabric"}):
            errors = preflight(self.plan)
        self.assertTrue(any("forge-1.8.9" in error and "launch driver" in error for error in errors))

    def test_shared_entry_conflict_is_an_error(self):
        inputs = []
        for index, content in enumerate([b"first", b"different"]):
            path = self.directory / (str(index) + ".zip")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("shared.txt", content)
            inputs.append(path)
        with self.assertRaisesRegex(ValueError, "Conflicting shared entry"):
            merge_entries(inputs)

    def test_forge_loader_manifest_is_preserved(self):
        inputs = []
        expected = b"Manifest-Version: 1.0\r\nFMLCorePlugin: example.Plugin\r\n\r\n"
        for index, manifest in enumerate([b"Manifest-Version: 1.0\r\n\r\n", expected]):
            path = self.directory / (str(index) + ".zip")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("META-INF/MANIFEST.MF", manifest)
            inputs.append(path)
        self.assertEqual(expected, merge_entries(inputs)["META-INF/MANIFEST.MF"])

    def test_fabric_artifact_advertises_only_its_own_versions(self):
        languages = {f"assets/aternauto/lang/{language}.properties": b"test=value"
                     for language in LANGUAGES}
        entries = {**languages, "fabric.mod.json": json.dumps({"version": "old", "depends": {}}).encode(),
                   "aternauto-adapters.json": json.dumps({"1.14.4": {}, "26.3": {}}).encode()}
        target = next(entry for entry in self.plan["targets"] if entry["id"] == "fabric-1.14.4")
        output = self.directory / "artifact.zip"
        write_artifact(output, [target], entries, "2", b"license")
        with zipfile.ZipFile(output) as archive:
            metadata = json.loads(archive.read("fabric.mod.json"))
            self.assertEqual(["1.14.4"], metadata["depends"]["minecraft"])
            self.assertEqual("2", metadata["version"])
            self.assertEqual({"1.14.4"}, set(json.loads(archive.read("aternauto-adapters.json"))))
            self.assertEqual(b"license", archive.read("LICENSE"))

    def test_packaged_artifacts_are_reproducible(self):
        entries = {f"assets/aternauto/lang/{language}.properties": b"key=value"
                   for language in LANGUAGES}
        target = {"loader": "forge", "minecraft": "1.7.10"}
        outputs = [self.directory / "first.jar", self.directory / "second.jar"]
        for output in outputs:
            write_artifact(output, [target], entries, "2", b"license")
        self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())

    def test_loader_metadata_limits_the_minecraft_version_and_registers_neoforge_mixins(self):
        import tomllib
        for target in self.plan["targets"]:
            if target["loader"] == "fabric" or target["minecraft"] in {"1.7.10", "1.8.9", "1.12.2"}:
                continue
            adapter = binding(target)
            resources = ROOT / adapter["directory"] / "src/main/resources"
            modern_neo = target["loader"] == "neoforge" and target["minecraft"] != "1.20.1"
            filename = "neoforge.mods.toml" if modern_neo else "mods.toml"
            metadata = tomllib.loads((resources / "META-INF" / filename).read_text())
            pack = json.loads((resources / "pack.mcmeta").read_text())["pack"]
            self.assertGreater(pack["pack_format"], 0)
            self.assertEqual("${version}", metadata["mods"][0]["version"])
            minecraft = next(entry for entry in metadata["dependencies"]["aternauto"]
                             if entry["modId"] == "minecraft")
            self.assertEqual("[" + target["minecraft"] + "]", minecraft["versionRange"])
            if modern_neo:
                self.assertEqual("aternauto.loader.mixins.json", metadata["mixins"][0]["config"])

    def test_changed_or_duplicate_runtime_artifacts_are_rejected(self):
        output = self.directory / "artifact.zip"
        output.write_bytes(b"fixture")
        targets = [{"id": "fabric-1.21.11"}]
        artifact = {"file": output.name, "targets": ["fabric-1.21.11"],
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
        index = {"artifacts": [artifact]}
        validate_artifact_index({"targets": targets}, index, self.directory)
        artifact["targets"].append("fabric-1.21.11")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_artifact_index({"targets": targets}, index, self.directory)
        artifact["targets"].pop()
        output.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed after packaging"):
            validate_artifact_index({"targets": targets}, index, self.directory)

    def test_launch_evidence_requires_the_same_binary_and_observed_render_and_monitor_markers(self):
        mods = self.directory / "mods"
        mods.mkdir()
        binary = mods / "release.jar"
        binary.write_bytes(b"tested distribution")
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        artifact = {"file": binary.name, "sha256": digest}
        result = {"passed": True, "exit": 0, "result": "REQUEST_SCREEN_RENDERED",
                  "jarSha256": digest, "marker": True, "secondaryMonitor": True}
        (self.directory / "result.txt").write_text("REQUEST_SCREEN_RENDERED\n")
        console = self.directory / "console.log"
        console.write_text("ATERN_SMOKE_WINDOW_1080P\nATERN_SMOKE_PASS renderedFrames=15\n")
        self.assertTrue(reusable_result(result, artifact, self.directory))
        binary.write_bytes(b"changed distribution")
        self.assertFalse(reusable_result(result, artifact, self.directory))
        binary.write_bytes(b"tested distribution")
        console.write_text("ATERN_SMOKE_PASS renderedFrames=15\n")
        self.assertFalse(reusable_result(result, artifact, self.directory))
        console.write_text("ATERN_SMOKE_WINDOW_1080P\nATERN_SMOKE_PASS renderedFrames=14\n")
        self.assertFalse(reusable_result(result, artifact, self.directory))

    def test_preview_excludes_unported_targets_and_cannot_replace_a_complete_release(self):
        for relative in ["gradle.properties", "LICENSE",
                         "fabric/src/main/resources/aternauto-adapters.json",
                         "versions/fabric-1.14.4/version.json"]:
            destination = self.directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        spec = self.directory / "versions/fabric-1.14.4/version.json"
        descriptor = json.loads(spec.read_text())
        descriptor["features"] = [feature for feature in descriptor["features"]
                                  if feature != "single-reset-retry-35-ticks"]
        spec.write_text(json.dumps(descriptor), encoding="utf-8")
        targets = [target for target in self.plan["targets"]
                   if target["id"] in {"fabric-1.14.4", "fabric-1.19.2"}]
        plan = {**self.plan, "targets": targets}
        fixture = self.directory / "input.jar"
        with zipfile.ZipFile(fixture, "w") as archive:
            archive.writestr("fabric.mod.json", json.dumps({"depends": {}}))
            archive.writestr("aternauto-adapters.json", json.dumps({"1.14.4": {}}))
            for language in LANGUAGES:
                archive.writestr(f"assets/aternauto/lang/{language}.properties", "key=value")
        with patch("distributions_v2.artifact_inputs", return_value=[fixture]):
            package(plan, self.directory, preview=True)
        directory = self.directory / "releases/2-preview"
        index = json.loads((directory / "artifacts.json").read_text())
        self.assertTrue(index["preview"])
        self.assertFalse(index["complete"])
        self.assertEqual(["fabric-1.19.2"], index["missingTargets"])
        self.assertIn("single-reset-retry-35-ticks", index["missingFeatures"]["fabric-1.14.4"])
        self.assertEqual(["fabric-1.14.4"], index["artifacts"][0]["targets"])
        with self.assertRaisesRegex(ValueError, "Incomplete release"):
            package(plan, self.directory)
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_artifact_index(plan, index, directory)
        self.assertFalse((self.directory / "releases/2").exists())


if __name__ == "__main__":
    unittest.main()
