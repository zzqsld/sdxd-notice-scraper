from pathlib import Path
import re


def main() -> None:
    root = Path("output")
    if not root.exists():
        return

    pattern = re.compile(r"_(\d{8}_\d{6})\.docx$")
    groups: dict[str, list[Path]] = {}

    for path in root.glob("*.docx"):
        match = pattern.search(path.name)
        if not match:
            continue
        groups.setdefault(match.group(1), []).append(path)

    latest_groups = set(sorted(groups, reverse=True)[:3])
    for timestamp, paths in groups.items():
        if timestamp not in latest_groups:
            for path in paths:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()