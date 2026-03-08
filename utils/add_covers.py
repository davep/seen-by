#!/usr/bin/env python3
"""Tool to add missing cover: frontmatter to blog post markdown files.

Reads each .md file below the posts/ subdirectory, looks for the image shown
in the post, and rewrites the file with a cover: frontmatter property pointing
at that same image (with any URL anchor such as #centre stripped).
"""

import re
import sys
from pathlib import Path

# Matches a Markdown image: ![alt text](/some/path.jpeg) or with an anchor like #centre
_IMAGE_PATTERN = re.compile(r"!\[.*?\]\((/[^)]+)\)")


def _strip_anchor(url: str) -> str:
    """Remove any anchor fragment (#...) from a URL."""
    return url.split("#")[0]


def _find_image_url(body: str) -> str | None:
    """Return the first image URL found in *body*, with any anchor stripped."""
    match = _IMAGE_PATTERN.search(body)
    if match:
        return _strip_anchor(match.group(1))
    return None


def add_cover(path: Path) -> bool:
    """Add a cover: property to *path* if one is not already present.

    Returns True if the file was modified, False otherwise.
    """
    content = path.read_text(encoding="utf-8")

    # Must start with a YAML frontmatter block
    if not content.startswith("---\n"):
        return False

    lines = content.split("\n")

    # Find the closing --- of the frontmatter block (first --- after line 0)
    closing_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return False

    # Skip files that already carry a cover: property
    frontmatter_lines = lines[1:closing_idx]
    if any(line.startswith("cover:") for line in frontmatter_lines):
        return False

    # Find the image URL in the body (everything after the closing ---)
    body = "\n".join(lines[closing_idx + 1 :])
    image_url = _find_image_url(body)
    if image_url is None:
        return False

    # Insert cover: immediately before the closing ---
    lines.insert(closing_idx, f"cover: {image_url}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> None:
    posts_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("content/posts")

    if not posts_dir.exists():
        print(f"error: directory not found: {posts_dir}", file=sys.stderr)
        sys.exit(1)

    modified = 0
    skipped = 0
    for md_file in sorted(posts_dir.rglob("*.md")):
        if add_cover(md_file):
            print(f"updated: {md_file}")
            modified += 1
        else:
            skipped += 1

    print(f"\n{modified} file(s) updated, {skipped} file(s) skipped.")


if __name__ == "__main__":
    main()
