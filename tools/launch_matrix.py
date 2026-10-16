"""Run every required target against its exact distribution and collect fresh evidence."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import uuid

from distributions_v2 import ROOT, release_version


def reusable_result(result, artifact, directory):
    """Reuse observed evidence only while its exact tested binary is unchanged."""
    if not (result.get("passed") and result.get("exit") == 0
            and result.get("result") == "REQUEST_SCREEN_RENDERED"
            and result.get("jarSha256") == artifact["sha256"]
            and result.get("marker") and result.get("secondaryMonitor")):
        return False
    try:
        if (directory / "result.txt").read_text().strip() != "REQUEST_SCREEN_RENDERED":
            return False
        console = (directory / "console.log").read_text(encoding="utf-8", errors="replace")
        frames = re.search(r"ATERN_SMOKE_PASS renderedFrames=(\d+)", console)
        if frames is None or int(frames[1]) < 15 or "ATERN_SMOKE_WINDOW_1080P" not in console:
            return False
        tested = directory / "mods" / artifact["file"]
        return hashlib.sha256(tested.read_bytes()).hexdigest() == artifact["sha256"]
    except (OSError, ValueError):
        return False


def validate_artifact_index(plan, index, directory):
    expected = {target["id"] for target in plan["targets"]}
    actual = []
    for artifact in index["artifacts"]:
        path = (directory / artifact["file"]).resolve()
        if path.parent != directory.resolve():
            raise ValueError("Unexpected artifact path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("Artifact changed after packaging: " + artifact["file"])
        actual.extend(artifact["targets"])
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("Packaged artifact index does not cover all 49 targets exactly once")


def load_driver(loader):
    if loader not in {"fabric", "forge", "neoforge"}:
        raise ValueError("Launch driver not ported: " + loader)
    path = ROOT / ("tools/runtime_smoke/run.py" if loader == "fabric" else "tools/runtime_smoke/native.py")
    spec = importlib.util.spec_from_file_location(loader + "_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if loader == "fabric":
        return module.run
    def run(version, jar, directory):
        plan = json.loads((ROOT / "compatibility-v2.json").read_text())
        target = next(target for target in plan["targets"]
                      if target["loader"] == loader and target["minecraft"] == version)
        return module.run(target, jar, directory)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="Comma-separated subset of the fully packaged matrix")
    parser.add_argument("--resume", type=Path, help="Reuse verified unchanged JARs from an earlier matrix report")
    args = parser.parse_args()
    version = release_version()
    directory = ROOT / "releases" / version
    plan = json.loads((ROOT / "compatibility-v2.json").read_text())
    index = json.loads((directory / "artifacts.json").read_text())
    if str(index["version"]) != version:
        raise ValueError("Artifact version differs from the Gradle version")
    validate_artifact_index(plan, index, directory)
    index["runtimeVerified"] = False
    index["complete"] = False
    (directory / "artifacts.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    requested = set(args.target.split(",")) if args.target else None
    if requested and requested - {target["id"] for target in plan["targets"]}:
        raise ValueError("Unknown targets: " + ", ".join(sorted(requested)))
    targets = [target for target in plan["targets"]
               if requested is None or target["id"] in requested]
    if not targets:
        raise ValueError("Unknown target: " + str(args.target))
    previous = {}
    if args.resume:
        resume_path = args.resume.resolve()
        if not resume_path.is_relative_to((ROOT / ".tools/runtime-matrix").resolve()):
            raise ValueError("Resume evidence must be a local runtime-matrix report")
        previous = json.loads(resume_path.read_text())
        if str(previous.get("version")) != version:
            raise ValueError("Cannot reuse evidence from another release")
    run_directory = ROOT / ".tools/runtime-matrix" / uuid.uuid4().hex
    run_directory.mkdir(parents=True)
    report = {"version": version, "complete": False, "targets": {}}
    failed = False
    for target in targets:
        artifact = next(entry for entry in index["artifacts"] if target["id"] in entry["targets"])
        earlier = previous.get("targets", {}).get(target["id"], {})
        evidence_run = earlier.get("evidenceRun", args.resume.parent.name if args.resume else "")
        if re.fullmatch(r"[a-f0-9]{32}", evidence_run):
            evidence = ROOT / ".tools/runtime-matrix" / evidence_run / target["id"]
            if reusable_result(earlier, artifact, evidence):
                report["targets"][target["id"]] = {**earlier, "evidenceRun": evidence_run}
                print(target["id"], "PASS (verified unchanged JAR)", flush=True)
                (run_directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                continue
        try:
            driver = load_driver(target["loader"])
            result = driver(target["minecraft"], directory / artifact["file"],
                            run_directory / target["id"])
            passed = (result["exit"] == 0 and result["result"] == "REQUEST_SCREEN_RENDERED"
                      and result["marker"] and result.get("secondaryMonitor", False)
                      and result["jarSha256"] == artifact["sha256"])
            report["targets"][target["id"]] = {"passed": passed, "evidenceRun": run_directory.name, **result}
        except Exception as error:
            passed = False
            report["targets"][target["id"]] = {"passed": False, "error": str(error)}
        failed |= not passed
        print(target["id"], "PASS" if passed else "FAIL", flush=True)
        (run_directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["complete"] = not failed and len(targets) == len(plan["targets"])
    (run_directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["complete"]:
        (directory / "runtime-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        index["runtimeVerified"] = True
        index["complete"] = True
        (directory / "artifacts.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print("Report:", run_directory / "report.json")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
