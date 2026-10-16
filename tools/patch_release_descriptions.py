"""Patch public descriptions without compiling or launching Minecraft."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import tomllib
import zipfile

from finalize_release import main as finalize_release


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = "Start your Aternos server when connecting from Minecraft."
DESCRIPTORS = {"fabric.mod.json", "META-INF/mods.toml", "META-INF/neoforge.mods.toml"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_descriptor(name, data):
    text = data.decode("utf-8")
    if name == "fabric.mod.json":
        parsed = json.loads(text)
        if parsed["description"] == DESCRIPTION:
            return data
        parsed["description"] = DESCRIPTION
        return (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return re.sub(r'^description\s*=\s*"[^"\n]*"',
                  'description="' + DESCRIPTION + '"', text,
                  flags=re.MULTILINE).encode("utf-8")


def main():
    release = ROOT / "releases" / "2"
    index_path = release / "artifacts.json"
    report_path = release / "runtime-checks.json"
    plan_path = ROOT / "compatibility-v2.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    audit_path = release / "description-patch.json"
    audit = (json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists()
             else {"description": DESCRIPTION, "recompiled": False, "relaunched": False,
                   "artifacts": []})
    backup = ROOT / ".tools" / "description-patch-backup"
    backup.mkdir(parents=True, exist_ok=True)
    source_count = 0
    for directory in (ROOT / "fabric", ROOT / "versions"):
        for path in directory.glob("**/src/main/resources/*"):
            candidates = [path] if path.is_file() else list(path.glob("*.toml"))
            for candidate in candidates:
                name = candidate.relative_to(candidate.parents[0]).as_posix()
                if candidate.parent.name == "META-INF":
                    name = "META-INF/" + candidate.name
                if name not in DESCRIPTORS:
                    continue
                before = candidate.read_bytes()
                after = patch_descriptor(name, before)
                if after != before:
                    candidate.write_bytes(after)
                    source_count += 1
    generator = ROOT / "tools" / "generate_adapters.py"
    before = generator.read_text(encoding="utf-8")
    after, matches = re.subn(r'"description": "[^"\n]*"',
                            '"description": "' + DESCRIPTION + '"', before)
    if not matches:
        raise ValueError("Generator description was not found")
    if after != before:
        generator.write_text(after, encoding="utf-8", newline="\n")
        source_count += 1
    changed_count = 0
    for artifact in index["artifacts"]:
        path = release / artifact["file"]
        original_hash = digest(path.read_bytes())
        if original_hash != artifact["sha256"]:
            raise ValueError("Unexpected original checksum: " + path.name)
        with zipfile.ZipFile(path) as archive:
            entries = [(item, archive.read(item)) for item in archive.infolist()]
        if len(entries) != len({item.filename for item, _ in entries}):
            raise ValueError("Duplicate archive entries")
        patched = [(item, patch_descriptor(item.filename, data)
                    if item.filename in DESCRIPTORS else data) for item, data in entries]
        changed = [item.filename for (item, old), (_, new) in zip(entries, patched)
                   if old != new]
        if changed:
            backup_path = backup / (original_hash + ".jar")
            if not backup_path.exists():
                shutil.copy2(path, backup_path)
            temporary = path.with_suffix(".jar.tmp")
            try:
                with zipfile.ZipFile(temporary, "w") as archive:
                    for item, data in patched:
                        archive.writestr(item, data)
                with zipfile.ZipFile(temporary) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("Invalid patched ZIP")
                    for item, old in entries:
                        new = archive.read(item.filename)
                        if item.filename not in changed and old != new:
                            raise ValueError("Unexpected payload change: " + item.filename)
                        if item.filename in changed:
                            if item.filename == "fabric.mod.json":
                                original = json.loads(old)
                                original["description"] = DESCRIPTION
                                current = json.loads(new)
                            else:
                                original = tomllib.loads(old.decode("utf-8"))
                                original["mods"][0]["description"] = DESCRIPTION
                                current = tomllib.loads(new.decode("utf-8"))
                            if current != original:
                                raise ValueError("Unexpected metadata change")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            new_hash = digest(path.read_bytes())
            artifact["sha256"] = new_hash
            proof = {"file": path.name, "beforeSha256": original_hash,
                     "afterSha256": new_hash, "changedEntries": changed,
                     "allOtherEntriesIdentical": True}
            audit["artifacts"].append(proof)
            for target_id in artifact["targets"]:
                result = report["targets"][target_id]
                if result["jarSha256"] != original_hash:
                    raise ValueError("Unexpected runtime evidence checksum")
                result["testedJarSha256"] = original_hash
                result["jarSha256"] = new_hash
                result["metadataOnlyPatch"] = proof
                result["validationScope"] = "Prior launch; description-only patch verified by entry comparison"
            changed_count += 1
        for target in plan["targets"]:
            if target["id"] in artifact["targets"]:
                target["validatedSha256"] = artifact["sha256"]
    write_json(index_path, index)
    write_json(report_path, report)
    write_json(plan_path, plan)
    write_json(audit_path, audit)
    (release / "SHA256SUMS.txt").write_text("".join(
        item["sha256"] + "  " + item["file"] + "\n" for item in index["artifacts"]),
        encoding="ascii")
    finalize_release()
    print(json.dumps({"sourcesChanged": source_count, "jarsInspected": len(index["artifacts"]),
                      "jarsChanged": changed_count, "otherEntriesIdentical": True,
                      "recompiled": False, "relaunched": False}))


if __name__ == "__main__":
    main()
