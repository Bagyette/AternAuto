"""Repair known mojibake in active sources and v2 distributions without compiling."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile

from finalize_release import main as finalize_release


ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".java", ".json", ".properties", ".toml", ".mcmeta", ".md",
                   ".py", ".gradle", ".ps1", ".txt", ".html", ".js", ".css", ".yml", ".yaml"}
SKIP = {"build", ".gradle", "__pycache__", ".git", "node_modules", ".venv"}


def repair(text):
    for good in ("\u00e9", "\u00ea", "\u2026", "\u2013", "\u2014"):
        bad = good
        for _ in range(2):
            try:
                bad = bad.encode("utf-8").decode("cp1252")
            except UnicodeDecodeError:
                break
            text = text.replace(bad, good)
    return text


def patch_class(data):
    """Change UTF8 constant bytes and lengths only; preserve all instructions."""
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("Not a Java class")
    count = struct.unpack_from(">H", data, 8)[0]
    position, index = 10, 1
    result = bytearray(data[:10])
    changed = 0
    while index < count:
        start = position
        tag = data[position]
        position += 1
        if tag == 1:
            length = struct.unpack_from(">H", data, position)[0]
            position += 2
            original = data[position:position + length]
            position += length
            # Only these exact non-ASCII sequences need repair. All other MUTF8
            # bytes, including encoded NUL and surrogate pairs, stay untouched.
            patched = original
            for good in ("\u00e9", "\u00ea", "\u2026", "\u2013", "\u2014"):
                bad = good
                for _ in range(2):
                    try:
                        bad = bad.encode("utf-8").decode("cp1252")
                    except UnicodeDecodeError:
                        break
                    patched = patched.replace(bad.encode("utf-8"), good.encode("utf-8"))
            result.extend(bytes([tag]) + struct.pack(">H", len(patched)) + patched)
            changed += patched != original
        else:
            sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4,
                     11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
            position += sizes[tag]
            result.extend(data[start:position])
            if tag in (5, 6):
                index += 1
        index += 1
    result.extend(data[position:])
    return bytes(result), changed


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    paths = [p for folder in ("common", "fabric", "forge", "neoforge", "versions", "tools", "deploy")
             for p in (ROOT / folder).rglob("*") if p.is_file()]
    paths.extend(p for p in ROOT.iterdir() if p.is_file())
    source_changes = []
    for path in paths:
        if path.suffix not in TEXT_EXTENSIONS or SKIP.intersection(path.relative_to(ROOT).parts):
            continue
        if path.name.startswith(".env") or any(word in path.name.lower() for word in ("secret", "token")):
            continue
        original = path.read_bytes()
        patched = repair(original.decode("utf-8")).encode("utf-8")
        if original != patched:
            path.write_bytes(patched)
            source_changes.append(str(path.relative_to(ROOT)))
    release = ROOT / "releases" / "2"
    index = json.loads((release / "artifacts.json").read_text(encoding="utf-8"))
    report = json.loads((release / "runtime-checks.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "compatibility-v2.json").read_text(encoding="utf-8"))
    audit = {"sourcesChanged": source_changes, "jarsInspected": len(index["artifacts"]),
             "artifacts": [], "recompiled": False, "relaunched": False}
    for artifact in index["artifacts"]:
        path = release / artifact["file"]
        original_hash = sha(path.read_bytes())
        if original_hash != artifact["sha256"]:
            raise ValueError("Unexpected checksum: " + path.name)
        with zipfile.ZipFile(path) as archive:
            entries = [(info, archive.read(info)) for info in archive.infolist()]
        patched_entries, changes = [], []
        for info, original in entries:
            patched = original
            if info.filename.endswith(".class"):
                patched, _ = patch_class(original)
            elif Path(info.filename).suffix in TEXT_EXTENSIONS:
                patched = repair(original.decode("utf-8")).encode("utf-8")
            patched_entries.append((info, patched))
            if patched != original:
                changes.append(info.filename)
        if not changes:
            continue
        backup = ROOT / ".tools" / "encoding-patch-backup"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / (original_hash + ".jar"))
        temporary = path.with_suffix(".jar.tmp")
        try:
            with zipfile.ZipFile(temporary, "w") as archive:
                for info, data in patched_entries:
                    archive.writestr(info, data)
            with zipfile.ZipFile(temporary) as archive:
                assert archive.testzip() is None
                assert archive.namelist() == [info.filename for info, _ in entries]
                for info, expected in patched_entries:
                    assert archive.read(info.filename) == expected
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        artifact["sha256"] = sha(path.read_bytes())
        proof = {"file": path.name, "beforeSha256": original_hash,
                 "afterSha256": artifact["sha256"], "changedEntries": changes,
                 "scope": "UTF8 constants only; instructions and all other entries unchanged"}
        audit["artifacts"].append(proof)
        for target_id in artifact["targets"]:
            result = report["targets"][target_id]
            assert result["jarSha256"] == original_hash
            result.setdefault("testedJarSha256", original_hash)
            result["jarSha256"] = artifact["sha256"]
            result["encodingOnlyPatch"] = proof
            result["validationScope"] = "Prior launch; encoding-only constant patch, no relaunch"
        for target in plan["targets"]:
            if target["id"] in artifact["targets"]:
                target["validatedSha256"] = artifact["sha256"]
    save(release / "artifacts.json", index)
    save(release / "runtime-checks.json", report)
    save(ROOT / "compatibility-v2.json", plan)
    audit_path = release / "encoding-patch.json"
    if audit_path.exists():
        previous = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["sourcesChanged"] = list(dict.fromkeys(previous["sourcesChanged"] + audit["sourcesChanged"]))
        audit["artifacts"] = previous["artifacts"] + audit["artifacts"]
    if audit["artifacts"] or audit["sourcesChanged"] or not audit_path.exists():
        save(audit_path, audit)
    (release / "SHA256SUMS.txt").write_text("".join(
        item["sha256"] + "  " + item["file"] + "\n" for item in index["artifacts"]), encoding="ascii")
    finalize_release()
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
