"""Stage CPython plus its ELF dependencies without copying the build OS.

Runs only in the trusted Linux build stage. Preserve Debian status metadata for
each copied library so vulnerability scanners retain package/version evidence.
"""
import fnmatch
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path("/runtime-root")
# Interactive terminal/Tk features, UUID1's optional native helper, and CPython
# test extensions are unused by this web app. uuid4 works with os.urandom.
EXCLUDED = ["site-packages", "ensurepip", "idlelib", "tkinter", "turtledemo",
            "test", "tests", "__pycache__", "_curses*.so", "readline*.so",
            "_tkinter*.so", "_uuid*.so", "_test*.so"]
# The distroless cc base supplies its own matched loader/glibc/C++ runtime.
BASE_LIBRARIES = {"libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0",
                  "librt.so.1", "libutil.so.1", "libresolv.so.2", "libanl.so.1",
                  "libgcc_s.so.1", "libstdc++.so.6"}


def ignore(_directory, names):
    return [name for name in names if any(fnmatch.fnmatch(name, p) for p in EXCLUDED)]


def main():
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("Review the runtime staging recipe before changing Python versions")
    python_root = ROOT / "usr/local"
    (python_root / "bin").mkdir(parents=True)
    (python_root / "lib").mkdir()
    shutil.copy2("/usr/local/bin/python3.13", python_root / "bin/python3.13")
    (python_root / "bin/python3").symlink_to("python3.13")
    (ROOT / "usr/bin").mkdir(parents=True)
    (ROOT / "usr/bin/python3").symlink_to("/usr/local/bin/python3")
    shutil.copytree("/usr/local/lib/python3.13", python_root / "lib/python3.13", ignore=ignore, symlinks=True)
    for source in Path("/usr/local/lib").glob("libpython3.13.so*"):
        shutil.copy2(source, python_root / "lib" / source.name, follow_symlinks=False)

    libraries = {}
    binaries = [python_root / "bin/python3.13"]
    binaries += list((python_root / "lib").rglob("*.so*"))
    binaries += list(Path("/opt/python").rglob("*.so*"))
    for binary in binaries:
        result = subprocess.run(["ldd", str(binary)], text=True, capture_output=True, check=True)
        if "not found" in result.stdout:
            raise RuntimeError(f"Unresolved shared library for {binary}: {result.stdout}")
        for line in result.stdout.splitlines():
            match = re.match(r"\s*(?:\S+\s+=>\s+)?(/\S+)", line)
            if not match:
                continue
            source = Path(match[1])
            if source.name in BASE_LIBRARIES or source.name.startswith("ld-linux"):
                continue
            if str(source).startswith(("/usr/local/", str(ROOT) + "/")):
                continue
            if source.name in libraries and source.resolve() != libraries[source.name].resolve():
                raise RuntimeError(f"Conflicting library paths: {source.name}")
            libraries[source.name] = source

    lib_directory = ROOT / "opt/runtime-libs"
    status_directory = ROOT / "var/lib/dpkg/status.d"
    lib_directory.mkdir(parents=True)
    status_directory.mkdir(parents=True)
    packages = set()
    for name, source in sorted(libraries.items()):
        shutil.copy2(source.resolve(), lib_directory / name)
        ownership = subprocess.check_output(["dpkg-query", "-S", str(source.resolve())], text=True)
        package = ownership.split(": ", 1)[0]
        status = subprocess.check_output(["dpkg-query", "-s", package], text=True)
        # Use the binary-package name, including multi-arch suffix, as the file key.
        (status_directory / package).write_text(status)
        packages.add(package)
    inventory = {"python": sys.version.split()[0], "copied_libraries": sorted(libraries),
                 "copied_debian_packages": sorted(packages), "excluded_features": EXCLUDED}
    inventory_dir = python_root / "share/fpl-runtime"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
