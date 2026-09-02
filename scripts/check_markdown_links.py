"""Validate that local Markdown links resolve to tracked repository files."""

from __future__ import annotations

import pathlib
import re
import subprocess
from urllib.parse import unquote, urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = {"http", "https", "mailto"}


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return {
        item.decode("utf-8").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    # Local links in this repository do not use titles or spaces in paths.
    return target.split(maxsplit=1)[0]


def main() -> int:
    tracked = tracked_files()
    markdown_files = sorted(
        ROOT / relative
        for relative in tracked
        if pathlib.PurePosixPath(relative).suffix.lower() == ".md"
    )
    failures: list[str] = []
    checked = 0

    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = link_target(match.group(1))
            if not target or target.startswith("#"):
                continue

            parsed = urlsplit(target)
            if parsed.scheme.lower() in EXTERNAL_SCHEMES:
                continue
            if parsed.scheme:
                failures.append(f"{markdown.relative_to(ROOT)}: unsupported link scheme: {target}")
                continue

            local_path = unquote(parsed.path)
            if not local_path:
                continue
            candidate = (markdown.parent / local_path).resolve()
            try:
                relative = candidate.relative_to(ROOT).as_posix()
            except ValueError:
                failures.append(f"{markdown.relative_to(ROOT)}: link leaves repository: {target}")
                continue

            checked += 1
            if not candidate.is_file():
                failures.append(f"{markdown.relative_to(ROOT)}: missing file: {target}")
            elif relative not in tracked:
                failures.append(f"{markdown.relative_to(ROOT)}: untracked target: {target}")

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(f"Markdown link check passed: {checked} local links across {len(markdown_files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
