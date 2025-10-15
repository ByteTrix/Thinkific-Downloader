#!/usr/bin/env python3
"""
Command line entry point for Thinkific Downloader and offline site generator.

Usage examples:
  python -m thinkific_downloader <course_url>
  python -m thinkific_downloader --json beginner-course.json
  python -m thinkific_downloader generate-site beginner-course.json --clean
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from thinkific_downloader.downloader import main as downloader_main
from thinkific_downloader.site_generator import (
    SiteGenerationError,
    generate_site,
    load_course,
)

# Note: keep console output lightweight so it mirrors existing downloader UX.


def _run_generate_site(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="thinkific_downloader generate-site",
        description="Validate downloaded Thinkific course assets and build an offline viewer.",
    )
    parser.add_argument(
        "metadata",
        help="Path to the course metadata JSON file (e.g., beginner-chess-mastery.json).",
    )
    parser.add_argument(
        "--downloads-dir",
        dest="downloads_dir",
        help="Override the downloads root directory (defaults to <metadata>/../downloads).",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Directory to write the generated site (defaults to downloads/<course-slug>/).",
    )
    parser.add_argument(
        "--assets-dirname",
        dest="assets_dirname",
        default="site-assets",
        help="Subdirectory name for bundled CSS/JS assets (default: site-assets).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previously generated site files before rendering.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate metadata and assets without writing any files.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress success output; errors will still be printed.",
    )

    args = parser.parse_args(argv)

    metadata_path = Path(args.metadata).expanduser()
    downloads_dir: Optional[Path] = None
    output_dir: Optional[Path] = None

    if args.downloads_dir:
        downloads_dir = Path(args.downloads_dir).expanduser()
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()

    try:
        if args.dry_run:
            load_course(metadata_path, downloads_root=downloads_dir)
            if not args.quiet:
                print("✅ Course assets validated (dry run).")
            return 0

        generated_index = generate_site(
            metadata_path,
            downloads_root=downloads_dir,
            output_dir=output_dir,
            clean=args.clean,
            assets_dirname=args.assets_dirname,
        )
        if not args.quiet:
            print(f"✅ Offline course generated: {generated_index}")
        return 0

    except SiteGenerationError as exc:
        print("✖ Site generation failed:")
        for error in exc.errors:
            print(f"  - {error}")
        return 1
    except FileNotFoundError as exc:
        print(f"✖ {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - unexpected edge cases
        print(f"✖ Unexpected error: {exc}")
        return 1


def main(argv: Optional[List[str]] = None) -> None:
    argv = argv or sys.argv
    if len(argv) > 1 and argv[1] in {"generate-site", "generate_site"}:
        exit_code = _run_generate_site(argv[2:])
        sys.exit(exit_code)

    # Fallback to the legacy downloader behaviour.
    downloader_main(argv)


if __name__ == "__main__":
    main(sys.argv)
