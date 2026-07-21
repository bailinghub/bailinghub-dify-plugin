from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path, PurePosixPath

ALLOWED_ROOTS = {
    ".difyignore",
    "CHANGELOG.md",
    "LICENSE",
    "PRIVACY.md",
    "README.md",
    "_assets",
    "main.py",
    "manifest.yaml",
    "provider",
    "pyproject.toml",
    "readme",
    "requirements.txt",
    "tools",
}
REQUIRED_FILES = {
    "PRIVACY.md",
    "README.md",
    "_assets/icon.svg",
    "main.py",
    "manifest.yaml",
    "provider/bailinghub.py",
    "provider/bailinghub.yaml",
    "requirements.txt",
}
FORBIDDEN_PARTS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "docs",
    "scripts",
    "tests",
}
FORBIDDEN_NAMES = {
    ".gitignore",
    ".python-version",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "uv.lock",
}
FORBIDDEN_SUFFIXES = {
    ".bin",
    ".dll",
    ".dylib",
    ".exe",
    ".log",
    ".p12",
    ".pem",
    ".pyc",
    ".pyo",
    ".so",
}


def check_package(package: Path) -> None:
    if not package.is_file():
        raise AssertionError(f"package not found: {package}")

    with zipfile.ZipFile(package) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = {item.filename for item in members}

        missing = REQUIRED_FILES - names
        if missing:
            raise AssertionError(f"missing required package files: {sorted(missing)}")

        for item in members:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise AssertionError(f"unsafe package path: {item.filename}")
            if FORBIDDEN_PARTS.intersection(path.parts):
                raise AssertionError(f"forbidden development state: {item.filename}")
            if path.name in FORBIDDEN_NAMES or path.name.startswith(".env"):
                raise AssertionError(f"forbidden package file: {item.filename}")
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise AssertionError(f"forbidden binary or sensitive file: {item.filename}")
            if not path.parts or path.parts[0] not in ALLOWED_ROOTS:
                raise AssertionError(f"non-runtime package entry: {item.filename}")

            mode = (item.external_attr >> 16) & 0o777
            if mode & 0o111:
                raise AssertionError(f"executable file is not allowed: {item.filename}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a Dify plugin package before release.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()

    try:
        check_package(args.package)
    except (AssertionError, OSError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"PASS: {args.package} contains only approved runtime and Marketplace files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
