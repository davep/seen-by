"""Image importer for the seen-by photoblog.

Reads JPEG images from the Photoblog Inbox in iCloud Drive, extracts EXIF
metadata (date taken and description), then:

  - Resizes and copies each image into content/attachments/yyyy/mm/dd/
  - Creates a matching Markdown post in content/posts/yyyy/mm/dd/

Run with:  uv run impimg
"""

import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS
from slugify import slugify

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

INBOX: Path = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Photoblog Inbox"
)

_REPO_ROOT: Path = Path(__file__).parent
_ATTACHMENTS_ROOT: Path = _REPO_ROOT / "content" / "attachments"
_POSTS_ROOT: Path = _REPO_ROOT / "content" / "posts"

# Maximum dimensions for resized images (preserves aspect ratio).
_MAX_SIZE: tuple[int, int] = (1024, 1024)

# ---------------------------------------------------------------------------
# Markdown template
# ---------------------------------------------------------------------------

_MARKDOWN_TEMPLATE = """\
---
title: "{title}"
category: Seen By Me 3
tags:
date: {date}
cover: {cover}
---

![{title}]({cover}#centre)
"""

# ---------------------------------------------------------------------------
# EXIF helpers
# ---------------------------------------------------------------------------


def _read_exif(image_path: Path) -> dict:
    """Return EXIF data from *image_path*, keyed by human-readable tag name."""
    with Image.open(image_path) as img:
        raw = img._getexif() or {}  # type: ignore[attr-defined]
    return {TAGS.get(tag, tag): value for tag, value in raw.items()}


def _date_taken(exif: dict) -> datetime | None:
    """Return the date the photo was taken, or *None* if unavailable."""
    date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _description(exif: dict) -> str:
    """Return the image description from EXIF data, decoded to a string."""
    value = exif.get("ImageDescription", "")
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value.strip()


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------


def _resize_and_save(src: Path, dst: Path) -> None:
    """Copy *src* to *dst* as a JPEG, resized to fit within *_MAX_SIZE*."""
    with Image.open(src) as img:
        img = img.convert("RGB")
        img.thumbnail(_MAX_SIZE, Image.LANCZOS)
        img.save(dst, format="JPEG", quality=95, optimize=True)


# ---------------------------------------------------------------------------
# Per-image import
# ---------------------------------------------------------------------------


def _import_image(image_path: Path) -> None:
    """Import a single JPEG image into the blog."""
    exif = _read_exif(image_path)

    date = _date_taken(exif)
    if date is None:
        print(
            f"Skipping {image_path.name}: no date found in EXIF data.",
            file=sys.stderr,
        )
        return

    desc = _description(exif)
    if not desc:
        print(
            f"Skipping {image_path.name}: no description found in EXIF data.",
            file=sys.stderr,
        )
        return

    slug = slugify(desc)
    date_path = f"{date.year}/{date.month:02d}/{date.day:02d}"

    # Create output directories.
    att_dir = _ATTACHMENTS_ROOT / date_path
    post_dir = _POSTS_ROOT / date_path
    att_dir.mkdir(parents=True, exist_ok=True)
    post_dir.mkdir(parents=True, exist_ok=True)

    # Resize and copy the image.
    img_filename = f"{slug}.jpeg"
    img_dst = att_dir / img_filename
    _resize_and_save(image_path, img_dst)

    # Build the /attachments/… path used inside Markdown.
    img_path = f"/attachments/{date_path}/{img_filename}"

    # Write the Markdown post.
    md_dst = post_dir / f"{slug}.md"
    md_dst.write_text(
        _MARKDOWN_TEMPLATE.format(title=desc, date=date.isoformat(), cover=img_path),
        encoding="utf-8",
    )

    print(f"Imported:  {image_path.name}")
    print(f"  Image:   {img_dst.relative_to(_REPO_ROOT)}")
    print(f"  Post:    {md_dst.relative_to(_REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the ``impimg`` tool."""
    if not INBOX.exists():
        print(f"Error: inbox not found:\n  {INBOX}", file=sys.stderr)
        sys.exit(1)

    images = sorted(p for p in INBOX.iterdir() if p.suffix.lower() in {".jpg", ".jpeg"})

    if not images:
        print(f"No JPEG images found in:\n  {INBOX}")
        return

    for image_path in images:
        _import_image(image_path)


if __name__ == "__main__":
    main()
