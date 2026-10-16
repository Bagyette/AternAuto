"""Prepare only UI language/font assets, entirely inside the local workspace."""

import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / ".tools/runtime-assets"


def prepare(version, prism):
    game = json.loads((ROOT / ".tools" / ("minecraft-" + version + ".json")).read_text())
    metadata = game["assetIndex"]
    index = ASSETS / "indexes" / (metadata["id"] + ".json")
    index.parent.mkdir(parents=True, exist_ok=True)
    if not index.is_file():
        cached = prism / "assets/indexes" / index.name
        if cached.is_file() and hashlib.sha1(cached.read_bytes()).hexdigest() == metadata["sha1"]:
            shutil.copy2(cached, index)
        else:
            with urllib.request.urlopen(metadata["url"], timeout=30) as response:
                content = response.read()
            if hashlib.sha1(content).hexdigest() != metadata["sha1"]:
                raise ValueError("Asset index checksum mismatch")
            index.write_bytes(content)
    data = json.loads(index.read_text())
    selected = {name: item for name, item in data["objects"].items() if "/sounds/" not in name}

    def obtain(entry):
        name, item = entry
        digest = item["hash"]
        relative = Path(digest[:2]) / digest
        path = ASSETS / "objects" / relative
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            cached = prism / "assets/objects" / relative
            if cached.is_file() and hashlib.sha1(cached.read_bytes()).hexdigest() == digest:
                shutil.copy2(cached, path)
            else:
                with urllib.request.urlopen("https://resources.download.minecraft.net/" + relative.as_posix(), timeout=30) as response:
                    content = response.read()
                if hashlib.sha1(content).hexdigest() != digest:
                    raise ValueError("UI asset checksum mismatch: " + name)
                path.write_bytes(content)
        if data.get("virtual"):
            destination = ASSETS / "virtual" / metadata["id"] / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(path, destination)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(obtain, selected.items()))
    return ASSETS, metadata["id"], data.get("virtual", False)
