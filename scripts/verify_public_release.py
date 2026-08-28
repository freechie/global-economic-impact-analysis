from __future__ import annotations

import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCANNED_SUFFIXES = {
    ".csv",
    ".ipynb",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
LEGACY_TERMS = (
    r"\bBloomberg\b",
    r"\bSIPRI\b",
    r"\bTIV\b",
    r"\bPX_LAST\b",
    r"\bField ID\b",
    r"\bField Mnemonic\b",
    r"\bArms Category\b",
    r"\bRank 1950-2022\b",
    r"\bGDP Country Name\b",
    r"\bCIBR\b",
    r"\bHACK\b",
    r"\bBUG\b",
    r"\bAEROBMTA Index\b",
    r"all_arms_exports\.csv",
    r"all_arms_imports\.csv",
    r"top_200_arms_exports\.csv",
    r"top_200_arms_imports\.csv",
    r"bloomberg_[a-z_]+\.csv",
    r"img/[A-Za-z0-9_.-]+\.png",
)
ALLOWED_FILES = {
    "scripts/verify_public_release.py",
    "tests/test_public_release.py",
}


def release_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        path
        for item in result.stdout.split(b"\0")
        if item and (path := ROOT / item.decode()).exists()
    ]


def scan() -> list[str]:
    problems = []
    for path in release_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(("data/processed/", "img/")):
            problems.append(f"{relative}: retained legacy artifact")
            continue
        if relative in ALLOWED_FILES:
            continue
        if path.name != "Makefile" and path.suffix not in SCANNED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in LEGACY_TERMS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                problems.append(
                    f"{relative}: contains denied legacy term {match.group(0)!r}"
                )
    return problems


def main() -> None:
    problems = scan()
    if problems:
        print("Public release verification failed:")
        print("\n".join(f"- {problem}" for problem in problems))
        raise SystemExit(1)
    print("Public release verification passed.")


if __name__ == "__main__":
    main()
