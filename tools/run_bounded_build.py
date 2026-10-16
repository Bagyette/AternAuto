"""Run Gradle and every child in a Windows Job Object with an aggregate memory ceiling."""

import argparse
import ctypes
from ctypes import wintypes as w
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


class Limits(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                ("flags", w.DWORD), ("minimum_ws", ctypes.c_size_t),
                ("maximum_ws", ctypes.c_size_t), ("active_limit", w.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]


class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in
                ["read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes"]]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [("basic", Limits), ("io", IoCounters), ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                ("peak_job", ctypes.c_size_t)]


class Startup(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR),
                ("title", w.LPWSTR), ("x", w.DWORD), ("y", w.DWORD),
                ("width", w.DWORD), ("height", w.DWORD), ("chars_x", w.DWORD),
                ("chars_y", w.DWORD), ("fill", w.DWORD), ("flags", w.DWORD),
                ("show", w.WORD), ("reserved_size", w.WORD), ("reserved_data", ctypes.c_void_p),
                ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE), ("pid", w.DWORD), ("tid", w.DWORD)]


class MemoryCounters(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [
        (name, ctypes.c_size_t) for name in ["peak_ws", "working_set", "peak_paged", "paged",
                                            "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private"]]


def run(command, log, ceiling):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    declarations = {
        "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        "QueryInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
        "CreateProcessW": ([w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL,
                            w.DWORD, ctypes.c_void_p, w.LPCWSTR, ctypes.POINTER(Startup),
                            ctypes.POINTER(ProcessInfo)], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "ResumeThread": ([w.HANDLE], w.DWORD),
        "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
        "GetExitCodeProcess": ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
        "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "K32GetProcessMemoryInfo": ([w.HANDLE, ctypes.POINTER(MemoryCounters), w.DWORD], w.BOOL),
    }
    for name, (arguments, result) in declarations.items():
        function = getattr(api, name)
        function.argtypes, function.restype = arguments, result

    def checked(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    job = checked(api.CreateJobObjectW(None, None))
    info = ProcessInfo()
    limits = ExtendedLimits()
    limits.basic.flags = 0x200 | 0x2000  # Aggregate committed memory + kill descendants on close.
    limits.job_memory = ceiling
    started = time.monotonic()
    peak_resident = 0
    try:
        checked(api.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        with log.open("wb") as output, open("NUL", "rb") as stdin, log.open("rb") as reader:
            output_handle = msvcrt.get_osfhandle(output.fileno())
            stdin_handle = msvcrt.get_osfhandle(stdin.fileno())
            os.set_handle_inheritable(output_handle, True)
            os.set_handle_inheritable(stdin_handle, True)
            startup = Startup()
            startup.cb, startup.flags = ctypes.sizeof(startup), 0x100
            startup.stdin, startup.stdout, startup.stderr = stdin_handle, output_handle, output_handle
            line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
            # Assign the suspended root before it can create a Gradle daemon or workers.
            checked(api.CreateProcessW(command[0], line, None, None, True,
                                       0x4 | 0x08000000, None, str(ROOT),
                                       ctypes.byref(startup), ctypes.byref(info)))
            if not api.AssignProcessToJobObject(job, info.process):
                api.TerminateProcess(info.process, 1)
                raise ctypes.WinError(ctypes.get_last_error())
            if api.ResumeThread(info.thread) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
            api.CloseHandle(info.thread)
            info.thread = None
            print(f"Build memory ceiling: {ceiling // 1048576} MiB (whole process tree)", flush=True)
            while True:
                members = ctypes.create_string_buffer(8 + 256 * ctypes.sizeof(ctypes.c_size_t))
                resident = 0
                if api.QueryInformationJobObject(job, 3, members, len(members), None):
                    count = ctypes.c_uint32.from_buffer(members, 4).value
                    for pid in (ctypes.c_size_t * count).from_buffer(members, 8):
                        process = api.OpenProcess(0x410, False, pid)
                        if process:
                            try:
                                counters = MemoryCounters()
                                counters.cb = ctypes.sizeof(counters)
                                if api.K32GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
                                    resident += counters.working_set
                            finally:
                                api.CloseHandle(process)
                peak_resident = max(peak_resident, resident)
                if resident > ceiling:
                    api.TerminateJobObject(job, 137)
                    print("Aggregate resident memory ceiling reached; stopping build.", flush=True)
                data = reader.read()
                if data:
                    sys.stdout.write(data.decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                if api.WaitForSingleObject(info.process, 500) == 0:
                    data = reader.read()
                    if data:
                        sys.stdout.write(data.decode("utf-8", errors="replace"))
                    break
            code = w.DWORD()
            checked(api.GetExitCodeProcess(info.process, ctypes.byref(code)))
            checked(api.QueryInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits), None))
            result = {"exitCode": code.value, "limitMiB": ceiling // 1048576,
                      "peakCommittedMiB": round(limits.peak_job / 1048576, 1),
                      "peakResidentMiB": round(peak_resident / 1048576, 1),
                      "elapsedSeconds": round(time.monotonic() - started, 1), "log": str(log)}
            log.with_suffix(".memory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print("\nBuild resource report: " + json.dumps(result), flush=True)
            return code.value
    finally:
        if info.thread:
            api.CloseHandle(info.thread)
        if info.process:
            api.CloseHandle(info.process)
        api.CloseHandle(job)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jdk", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--memory-mib", type=int, default=5632)
    parser.add_argument("tasks", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not 512 <= args.memory_mib <= 5632:
        parser.error("The configured total ceiling cannot exceed 5632 MiB (below 6 GB).")
    log = args.log.resolve()
    if not log.is_relative_to(ROOT):
        parser.error("Build logs must stay inside the workspace.")
    log.parent.mkdir(parents=True, exist_ok=True)
    sockets = ROOT / ".tools/sockets"
    sockets.mkdir(parents=True, exist_ok=True)
    temporary = ROOT / ".tools/tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
    os.environ["GRADLE_USER_HOME"] = str(ROOT / ".tools/gradle-home")
    os.environ["JAVA_HOME"] = str(args.jdk.resolve())
    prism_java = Path(os.environ["APPDATA"]) / "PrismLauncher/java"
    for major, runtime in [(17, "gamma"), (21, "delta"), (25, "epsilon")]:
        installation = prism_java / ("java-runtime-" + runtime)
        if (installation / "bin/javac.exe").is_file():
            os.environ["ATERNAUTO_JAVA" + str(major)] = str(installation)
    os.environ["JAVA_TOOL_OPTIONS"] = "-Djdk.net.unixdomain.tmpdir=" + sockets.as_posix()
    # MCPConfig hard-codes -Xms4G for some decompilers. This JVM variable is
    # processed after command-line flags, keeping those tools inside the job.
    os.environ["_JAVA_OPTIONS"] = "-Xms32m -Xmx2048m -XX:ActiveProcessorCount=2"
    os.environ["PATH"] = str(args.jdk.resolve() / "bin") + os.pathsep + os.environ["PATH"]
    command = [str(args.jdk.resolve() / "bin/java.exe"), "-Xms32m", "-Xmx192m",
               "-Dorg.gradle.appname=gradlew", "-classpath", str(ROOT / "gradle/wrapper/gradle-wrapper.jar"),
               "org.gradle.wrapper.GradleWrapperMain", *args.tasks,
               "--no-daemon", "--max-workers=1", "--no-parallel", "--console=plain"]
    with (ROOT / ".tools/build.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit("Another bounded build is already running; the shared memory budget is in use.")
        try:
            code = run(command, log, args.memory_mib * 1048576)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
