"""
Utilities for turning a downloaded Thinkific course into an offline static website.

This module currently focuses on:
1. Parsing course metadata JSON files and validating that the associated local assets
   (videos, text lessons, attachments) exist.
2. Rendering a basic two-pane static site (HTML + CSS + JS stubs) that can be opened
   directly from the filesystem.

Further CLI plumbing and richer client-side behaviour will be added in subsequent steps.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
from string import Template
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote

from .file_utils import filter_filename

# File categorisation helpers
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm"}
CAPTION_EXTENSIONS = {".vtt", ".srt"}
TEXT_EXTENSIONS = {".html", ".htm"}
IGNORED_FILENAMES = {".ds_store"}

LESSON_SUFFIX_PATTERN = re.compile(r"[._-](lesson|text)$", re.IGNORECASE)
NUMERIC_PREFIX_PATTERN = re.compile(r"^\d+\.?\s*")


class SiteGenerationError(Exception):
    """Collects validation failures encountered during site generation."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        message = "Site generation encountered issues:\n" + "\n".join(f"- {err}" for err in self.errors)
        super().__init__(message)


@dataclass
class LessonAssets:
    """Represents the local files associated with a lesson."""

    videos: List[Path] = field(default_factory=list)
    captions: List[Path] = field(default_factory=list)
    html_file: Optional[Path] = None
    attachments: List[Path] = field(default_factory=list)


@dataclass
class Lesson:
    """Course lesson enriched with local filesystem references."""

    id: int
    name: str
    slug: str
    position: int
    chapter_id: int
    lesson_type: str  # "video" or "text"
    display_name: str
    duration_seconds: Optional[int]
    description: Optional[str]
    directory: Path
    assets: LessonAssets = field(default_factory=LessonAssets)

    @property
    def is_video(self) -> bool:
        return self.lesson_type == "video"

    @property
    def is_text(self) -> bool:
        return self.lesson_type == "text"


@dataclass
class Chapter:
    """A Thinkific chapter containing lessons."""

    id: int
    name: str
    position: int
    directory: Path
    lessons: List[Lesson] = field(default_factory=list)


@dataclass
class Course:
    """Top-level course representation ready for rendering."""

    id: int
    name: str
    slug: str
    output_dir: Path
    metadata_path: Path
    landing_page_url: Optional[str]
    chapters: List[Chapter] = field(default_factory=list)

    def iter_lessons(self) -> Iterable[Lesson]:
        for chapter in self.chapters:
            yield from chapter.lessons

    @property
    def first_lesson(self) -> Optional[Lesson]:
        for chapter in self.chapters:
            if chapter.lessons:
                return chapter.lessons[0]
        return None


def load_course(metadata_path: Path | str, downloads_root: Path | str | None = None) -> Course:
    """
    Load course metadata and validate the presence of corresponding local assets.

    :param metadata_path: Path to the Thinkific course JSON dump.
    :param downloads_root: Optional override for the downloads directory root.
    :returns: Course model containing chapters, lessons, and asset references.
    :raises SiteGenerationError: if required assets are missing or structure mismatches are detected.
    """
    metadata_path = Path(metadata_path)
    if downloads_root is None:
        downloads_root = metadata_path.parent / "downloads"
    downloads_root = Path(downloads_root)

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with metadata_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    course_info = data.get("course") or {}
    course_slug = course_info.get("slug")
    if not course_slug:
        raise SiteGenerationError(["Course slug missing from metadata."])

    course_dir = downloads_root / course_slug

    errors: List[str] = []
    if not course_dir.exists():
        errors.append(f"Course directory not found: {course_dir}")

    contents_map: Dict[int, Dict] = {content["id"]: content for content in data.get("contents", [])}
    chapters: List[Chapter] = []

    for chapter_data in sorted(data.get("chapters", []), key=lambda c: c.get("position", 0)):
        chapter_id = chapter_data.get("id")
        chapter_name = chapter_data.get("name", f"Chapter {chapter_id}")
        chapter_position = chapter_data.get("position", 0)
        chapter_dir_name = f"{chapter_position + 1}. {filter_filename(chapter_name)}"
        chapter_dir = course_dir / chapter_dir_name

        if not chapter_dir.exists():
            errors.append(
                f"Missing chapter directory for '{chapter_name}' (expected '{chapter_dir_name}')"
            )
            continue

        chapter = Chapter(
            id=chapter_id,
            name=chapter_name,
            position=chapter_position,
            directory=chapter_dir,
            lessons=[],
        )

        lesson_dirs = sorted(
            [entry for entry in chapter_dir.iterdir() if entry.is_dir()],
            key=lambda path: path.name.lower(),
        )
        claimed_dirs: set[Path] = set()

        lesson_ids = chapter_data.get("content_ids", [])
        lessons_for_chapter = [
            contents_map.get(lesson_id) for lesson_id in lesson_ids if contents_map.get(lesson_id)
        ]
        lessons_for_chapter.sort(key=lambda lesson: lesson.get("position", 0))

        for index, lesson_data in enumerate(lessons_for_chapter):
            content_type = lesson_data.get("contentable_type")
            if content_type not in {"Lesson", "HtmlItem"}:
                # Ignore unsupported content types (quizzes, surveys, etc.) for now.
                continue

            lesson_name = lesson_data.get("name", f"Lesson {lesson_data.get('id')}")
            lesson_kind = _classify_lesson_type(lesson_data)

            lesson_dir = _find_lesson_directory(
                lesson_dirs=lesson_dirs,
                claimed_dirs=claimed_dirs,
                lesson_name=lesson_name,
                lesson_index=index,
            )

            if lesson_dir is None:
                errors.append(
                    f"Missing lesson directory for '{lesson_name}' in chapter '{chapter_name}'"
                )
                continue

            assets = _scan_lesson_assets(lesson_dir)

            if lesson_kind == "video" and not assets.videos:
                errors.append(
                    f"Video files not found for lesson '{lesson_name}' at {lesson_dir}"
                )
            if lesson_kind == "text" and assets.html_file is None:
                errors.append(
                    f"HTML content not found for text lesson '{lesson_name}' at {lesson_dir}"
                )

            duration_seconds = _extract_duration_seconds(lesson_data)
            description = _extract_description(lesson_data)

            lesson = Lesson(
                id=lesson_data.get("id"),
                name=lesson_name,
                slug=lesson_data.get("slug", filter_filename(lesson_name)),
                position=lesson_data.get("position", index),
                chapter_id=chapter_id,
                lesson_type=lesson_kind,
                display_name=lesson_data.get("display_name", lesson_kind.title()),
                duration_seconds=duration_seconds,
                description=description,
                directory=lesson_dir,
                assets=assets,
            )
            chapter.lessons.append(lesson)

        chapters.append(chapter)

    if not chapters:
        errors.append("No chapters discovered in metadata.")

    total_lessons = sum(len(chapter.lessons) for chapter in chapters)
    if total_lessons == 0:
        errors.append("No lessons were successfully mapped to local directories.")

    if errors:
        raise SiteGenerationError(errors)

    return Course(
        id=course_info.get("id"),
        name=course_info.get("name", "Thinkific Course"),
        slug=course_slug,
        output_dir=course_dir,
        metadata_path=metadata_path,
        landing_page_url=course_info.get("landing_page_url"),
        chapters=chapters,
    )


def generate_site(
    metadata_path: Path | str,
    downloads_root: Path | str | None = None,
    output_dir: Path | str | None = None,
    *,
    clean: bool = False,
    assets_dirname: str = "site-assets",
) -> Path:
    """
    High-level helper that loads a course and renders the static site.

    :returns: Path to the generated index.html file.
    """
    course = load_course(metadata_path, downloads_root=downloads_root)
    target_dir = Path(output_dir) if output_dir else course.output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    _render_course(
        course=course,
        output_dir=target_dir,
        clean=clean,
        assets_dirname=assets_dirname,
    )
    return target_dir / "index.html"


def _render_course(course: Course, output_dir: Path, *, clean: bool, assets_dirname: str) -> None:
    """Render HTML/CSS/JS assets for a course."""
    templates_dir = Path(__file__).with_name("templates")
    static_dir = Path(__file__).with_name("static")

    assets_dir = output_dir / assets_dirname

    if clean and assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    if clean:
        index_path = output_dir / "index.html"
        if index_path.exists():
            index_path.unlink()

    # Copy static assets
    (assets_dir / "viewer.css").write_text(
        (static_dir / "viewer.css").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (assets_dir / "viewer.js").write_text(
        (static_dir / "viewer.js").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    # Prepare template fragments
    base_template = Template((templates_dir / "base.html").read_text(encoding="utf-8"))
    lesson_template = Template((templates_dir / "lesson.html").read_text(encoding="utf-8"))

    sidebar_html = _render_sidebar(course)
    lesson_templates_html, initial_lesson_html = _render_lessons(
        course=course,
        lesson_template=lesson_template,
        output_dir=output_dir,
    )

    course_payload = _build_course_payload(course)

    subtitle_html = ""
    if course.landing_page_url:
        subtitle_html = f'<p class="course-link">Original: <a href="{html_escape(course.landing_page_url)}">{html_escape(course.landing_page_url)}</a></p>'

    index_html = base_template.substitute(
        title=html_escape(course.name),
        subtitle=subtitle_html,
        sidebar=sidebar_html,
        initial_lesson=initial_lesson_html,
        lesson_templates=lesson_templates_html,
        course_json=json.dumps(course_payload, ensure_ascii=False),
        css_path=f"{assets_dirname}/viewer.css",
        js_path=f"{assets_dirname}/viewer.js",
    )

    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    manifest = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "course": {
            "id": course.id,
            "name": course.name,
            "slug": course.slug,
        },
        "files": [
            "index.html",
            f"{assets_dirname}/viewer.css",
            f"{assets_dirname}/viewer.js",
        ],
        "lessons": [
            {
                "id": lesson.id,
                "name": lesson.name,
                "type": lesson.lesson_type,
                "directory": str(lesson.directory.relative_to(output_dir)),
            }
            for lesson in course.iter_lessons()
        ],
    }
    (assets_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _render_sidebar(course: Course) -> str:
    """Create the sidebar navigation markup."""
    lines: List[str] = [
        '<nav class="sidebar-nav" aria-label="Course navigation">',
    ]
    active_lesson_id = course.first_lesson.id if course.first_lesson else None

    for chapter in course.chapters:
        lines.append(
            f'  <section class="sidebar-chapter" data-chapter-id="{chapter.id}">'
        )
        lines.append(f'    <h2 class="chapter-title">{html_escape(chapter.name)}</h2>')
        lines.append('    <ol class="lesson-list">')
        for lesson in chapter.lessons:
            is_active = " is-active" if lesson.id == active_lesson_id else ""
            lines.append(
                "      <li>"
                f'<button type="button" class="lesson-link{is_active}" '
                f'data-lesson-id="{lesson.id}" data-lesson-type="{lesson.lesson_type}">'
                f"{html_escape(lesson.name)}</button>"
                "</li>"
            )
        lines.append("    </ol>")
        lines.append("  </section>")
    lines.append("</nav>")
    return "\n".join(lines)


def _render_lessons(
    course: Course,
    lesson_template: Template,
    output_dir: Path,
) -> Tuple[str, str]:
    """Render lesson templates and return (templates_html, initial_lesson_html)."""
    templates: List[str] = ['<div id="lesson-templates" hidden>']
    initial_html = ""
    first_lesson_id = course.first_lesson.id if course.first_lesson else None

    for lesson in course.iter_lessons():
        lesson_html = _render_lesson(
            lesson=lesson,
            template=lesson_template,
            output_dir=output_dir,
        )
        templates.append(
            f'<template id="lesson-template-{lesson.id}">{lesson_html}</template>'
        )
        if lesson.id == first_lesson_id and not initial_html:
            initial_html = lesson_html

    templates.append("</div>")
    return "\n".join(templates), initial_html


def _render_lesson(lesson: Lesson, template: Template, output_dir: Path) -> str:
    """Render a single lesson section."""
    body_html = _render_lesson_body(lesson, output_dir)
    attachments_html = _render_attachments(lesson, output_dir)

    meta_fragments: List[str] = []
    if lesson.duration_seconds:
        meta_fragments.append(
            f'<span class="lesson-duration">{_format_duration(lesson.duration_seconds)}</span>'
        )
    if lesson.description:
        meta_fragments.append(
            f'<p class="lesson-description">{html_escape(lesson.description)}</p>'
        )
    lesson_meta = ""
    if meta_fragments:
        lesson_meta = '<div class="lesson-meta">' + "".join(meta_fragments) + "</div>"

    return template.substitute(
        lesson_id=lesson.id,
        lesson_type=lesson.lesson_type,
        lesson_title=html_escape(lesson.name),
        lesson_meta=lesson_meta,
        lesson_body=body_html,
        attachments=attachments_html,
    )


def _render_lesson_body(lesson: Lesson, output_dir: Path) -> str:
    """Generate the primary lesson content markup."""
    if lesson.is_video and lesson.assets.videos:
        video_sources = []
        for video_path in lesson.assets.videos:
            rel_url = _relative_url(video_path, output_dir)
            video_sources.append(f'<source src="{rel_url}" type="video/mp4">')

        caption_tracks = []
        for idx, caption in enumerate(lesson.assets.captions):
            srclang, label = _guess_caption_language(caption)
            default_attr = " default" if idx == 0 else ""
            caption_src = _build_caption_data_uri(caption)
            caption_tracks.append(
                f'<track src="{caption_src}" kind="subtitles" srclang="{srclang}" label="{label}"{default_attr}>'
            )

        return (
            '<div class="video-wrapper">'
            '<video class="lesson-video" controls preload="metadata">'
            + "".join(video_sources)
            + "".join(caption_tracks)
            + "Sorry, your browser does not support embedded videos."
            "</video>"
            "</div>"
        )

    if lesson.is_text and lesson.assets.html_file:
        html_content = lesson.assets.html_file.read_text(encoding="utf-8")
        return f'<article class="lesson-article">{html_content}</article>'

    return (
        '<div class="lesson-unavailable">'
        "<p>This lesson type is not yet supported for offline viewing.</p>"
        "</div>"
    )


def _render_attachments(lesson: Lesson, output_dir: Path) -> str:
    """Render lesson attachment links, if any."""
    if not lesson.assets.attachments:
        return ""

    items = []
    for attachment in lesson.assets.attachments:
        rel_url = _relative_url(attachment, output_dir)
        items.append(
            f'<li><a class="attachment-link" href="{rel_url}" download>{html_escape(attachment.name)}</a></li>'
        )
    return (
        '<section class="lesson-attachments">'
        "<h3>Downloads</h3>"
        "<ul>"
        + "".join(items)
        + "</ul>"
        "</section>"
    )


def _build_course_payload(course: Course) -> Dict:
    """Build a lightweight JSON payload for client-side consumption."""
    payload = {
        "id": course.id,
        "name": course.name,
        "slug": course.slug,
        "chapters": [],
    }
    for chapter in course.chapters:
        payload["chapters"].append(
            {
                "id": chapter.id,
                "name": chapter.name,
                "lessons": [
                    {
                        "id": lesson.id,
                        "name": lesson.name,
                        "type": lesson.lesson_type,
                    }
                    for lesson in chapter.lessons
                ],
            }
        )
    return payload


def _classify_lesson_type(lesson_data: Dict) -> str:
    """Normalise lesson type labels from metadata."""
    label = (
        lesson_data.get("lesson_type_label")
        or lesson_data.get("display_name")
        or ""
    ).lower()
    content_type = (lesson_data.get("contentable_type") or "").lower()
    if "video" in label:
        return "video"
    if "text" in label or "html" in label or content_type == "htmlitem":
        return "text"
    if content_type == "lesson":
        return "video"
    return "other"


def _find_lesson_directory(
    lesson_dirs: List[Path],
    claimed_dirs: set[Path],
    lesson_name: str,
    lesson_index: int,
) -> Optional[Path]:
    """Find the best matching directory for a lesson by name and order."""
    target_key = _normalise_dir_key(lesson_name)

    # First pass: exact match on the normalised directory name.
    for directory in lesson_dirs:
        if directory in claimed_dirs:
            continue
        if _normalise_existing_dir(directory.name) == target_key:
            claimed_dirs.add(directory)
            return directory

    # Second pass: substring overlap.
    for directory in lesson_dirs:
        if directory in claimed_dirs:
            continue
        existing_key = _normalise_existing_dir(directory.name)
        if target_key in existing_key or existing_key in target_key:
            claimed_dirs.add(directory)
            return directory

    # Fallback: choose by ordering to keep generation moving.
    for directory in lesson_dirs:
        if directory not in claimed_dirs:
            claimed_dirs.add(directory)
            return directory

    return None


def _normalise_existing_dir(name: str) -> str:
    """Normalise an existing directory name down to its semantic slug."""
    name = NUMERIC_PREFIX_PATTERN.sub("", name)
    name = LESSON_SUFFIX_PATTERN.sub("", name)
    return filter_filename(name)


def _normalise_dir_key(name: str) -> str:
    """Normalise metadata lesson names to align with directory naming conventions."""
    return filter_filename(name)


def _scan_lesson_assets(lesson_dir: Path) -> LessonAssets:
    """Inspect a lesson directory and categorise its files."""
    videos: List[Path] = []
    captions: List[Path] = []
    html_files: List[Path] = []
    attachments: List[Path] = []

    for file_path in sorted(lesson_dir.iterdir(), key=lambda p: p.name.lower()):
        if not file_path.is_file():
            continue
        if file_path.name.lower() in IGNORED_FILENAMES:
            continue

        suffix = file_path.suffix.lower()
        if suffix in VIDEO_EXTENSIONS:
            videos.append(file_path)
            continue
        if suffix in CAPTION_EXTENSIONS:
            captions.append(file_path)
            continue
        if suffix in TEXT_EXTENSIONS:
            html_files.append(file_path)
            continue

        attachments.append(file_path)

    primary_html = html_files[0] if html_files else None
    # Treat additional HTML files as attachments to keep them accessible.
    for extra_html in html_files[1:]:
        attachments.append(extra_html)

    return LessonAssets(
        videos=videos,
        captions=captions,
        html_file=primary_html,
        attachments=attachments,
    )


def _relative_url(path: Path, base: Path) -> str:
    """Convert an absolute path to a file:// friendly relative URL."""
    try:
        relative_path = path.relative_to(base)
    except ValueError:
        relative_path = path
    return quote(str(relative_path).replace("\\", "/"))


def _guess_caption_language(path: Path) -> Tuple[str, str]:
    """Heuristically derive subtitle metadata from the filename."""
    stem = path.stem
    if "." in stem:
        lang = stem.split(".")[-1]
    else:
        lang = "en"
    lang = lang.lower()

    canonical = _map_language_code(lang)
    label = canonical.upper()
    lang = canonical

    return lang, label


def _map_language_code(lang: str) -> str:
    """Map common language fragments to two-letter ISO codes."""
    language_map = {
        "eng": "en",
        "english": "en",
        "en-us": "en",
        "en-gb": "en",
        "es": "es",
        "spa": "es",
        "spanish": "es",
        "fr": "fr",
        "fre": "fr",
        "fra": "fr",
        "french": "fr",
        "de": "de",
        "ger": "de",
        "deu": "de",
        "german": "de",
        "it": "it",
        "ita": "it",
        "italian": "it",
        "pt": "pt",
        "por": "pt",
        "pt-br": "pt",
        "pt-pt": "pt",
        "portuguese": "pt",
        "ru": "ru",
        "rus": "ru",
        "russian": "ru",
        "zh": "zh",
        "chi": "zh",
        "zho": "zh",
        "chinese": "zh",
    }

    if lang in language_map:
        return language_map[lang]
    if len(lang) > 2:
        return lang[:2]
    if not lang:
        return "en"
    return lang


def _build_caption_data_uri(path: Path) -> str:
    """Embed caption file content into a data URI to avoid file:// origin issues."""
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:text/vtt;base64,{encoded}"


def _format_duration(seconds: int | float) -> str:
    """Render a human-friendly duration string."""
    total_seconds = int(float(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def _extract_duration_seconds(lesson_data: Dict) -> Optional[int]:
    """Extract duration from metadata when available."""
    meta = lesson_data.get("meta_data") or {}
    duration = meta.get("duration_in_seconds")
    if duration is None:
        return None
    try:
        return int(float(duration))
    except (TypeError, ValueError):
        return None


def _extract_description(lesson_data: Dict) -> Optional[str]:
    """Pull optional description fields from lesson metadata."""
    return (
        lesson_data.get("description")
        or (lesson_data.get("meta_data") or {}).get("description")
        or None
    )


__all__ = [
    "Course",
    "Chapter",
    "Lesson",
    "LessonAssets",
    "SiteGenerationError",
    "generate_site",
    "load_course",
]
