from pathlib import Path
import re


def main() -> None:
    root = Path("output")
    if not root.exists():
        return

    # New format: {category}_{mode}_{image}_{timestamp}.docx
    new_pattern = re.compile(
        r"^(?P<category>.+?)_(?:full|incremental)_(?:img|noimg)_(?P<ts>\d{8}_\d{6})\.docx$"
    )
    # Legacy format: {category}_{timestamp}.docx
    old_pattern = re.compile(r"^(?P<category>.+?)_(?P<ts>\d{8}_\d{6})\.docx$")
    category_groups: dict[str, list[tuple[str, Path]]] = {}

    for path in root.glob("*.docx"):
        match = new_pattern.match(path.name)
        if not match:
            match = old_pattern.match(path.name)
        if not match:
            continue
        category = match.group("category")
        timestamp = match.group("ts")
        category_groups.setdefault(category, []).append((timestamp, path))

    # Keep latest 3 docs for each category separately.
    for _, items in category_groups.items():
        items.sort(key=lambda x: x[0], reverse=True)
        for _, path in items[3:]:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()