# Local Course Viewer PRD

## 1. Introduction / Overview
Create a Python-based generator that turns a downloaded Thinkific course into a self-contained static website for offline consumption. The script should read the provided course metadata JSON (e.g., `beginner-chess-mastery.json`) and the corresponding assets already stored under `downloads/<course-slug>/`, validate that everything needed is present, and produce an easy-to-navigate two-pane interface. The generated site must work when opened directly from the filesystem (no server) and allow a learner to browse chapters, play videos, and read text lessons completely offline.

## 2. Goals
- Provide a one-command workflow that accepts a Thinkific course metadata JSON file and emits an offline-ready static site in the matching `downloads/<course-slug>/` directory.
- Mirror the course hierarchy (chapters → lessons) in a left-hand navigation tree with quick access to each lesson.
- Render lesson content appropriately in the main pane: embedded video playback (with captions) for video lessons, and readable formatted text for HTML lessons.
- Package all required assets (CSS, JS, fonts) locally so the experience works without network access.

## 3. User Stories
1. **As a learner traveling without reliable internet**, I want to open `downloads/<course>/index.html` and continue the course offline, so I can make use of the content anywhere.
2. **As a downloader maintainer**, I want the generator to fail fast if lesson assets are missing, so I can fix gaps before distributing the course dump.
3. **As a learner**, I want to jump between lessons quickly using a chapter tree, so I can find specific topics without scrolling through a long page.
4. **As a learner**, I want video lessons to include captions when available, so I can follow along in noisy environments.
5. **As a learner**, I want links to attachments (e.g., PDFs) surfaced with each lesson, so I can access supporting materials.

## 4. Functional Requirements
1. **CLI entrypoint**  
   - Provide a Python command (e.g., `python -m thinkific_downloader.generate_site <metadata.json>`) that accepts at minimum: path to the metadata JSON, optional `--downloads-dir` override (default `downloads/`), and optional `--output-subdir` name (default the course slug).
2. **Metadata ingestion and validation**  
   - Parse the JSON and confirm required keys exist (`course.slug`, `chapters`, `contents`).  
   - Build an in-memory course model linking chapters to lesson content via IDs.  
   - Emit actionable errors when the JSON structure is unexpected.
3. **Asset validation**  
   - Locate the base course folder at `downloads/<course-slug>/` (configurable via CLI).  
   - For each lesson, verify the expected asset directory exists (matching lesson slug or already-downloaded folder naming).  
   - Confirm that required primary assets exist: `.mp4` for videos, `.html` for text lessons, plus optional assets (`.vtt`, PDFs, images).  
   - Surface a consolidated report of missing assets before generation.
4. **Output structure**  
   - Generate a static site rooted at `downloads/<course-slug>/index.html`.  
   - Place shared assets under a subfolder (e.g., `downloads/<course-slug>/site-assets/`) containing CSS, JS, icons, and fonts (if any).  
   - Preserve or reuse existing lesson folders; do not modify original media files.
5. **Navigation UI**  
   - Render an always-expanded chapter list in the left sidebar reflecting chapter order (`position`) without collapse/expand controls.  
   - List lessons within each chapter in order, distinguishing lesson types (video vs text) with an icon or label.  
   - Highlight the currently selected lesson and keep the selection in sync when switching content.
6. **Lesson rendering**  
   - For video lessons, embed the local `.mp4` via `<video controls>` and attach `<track>` elements for available `.vtt` caption files when the browser supports them; if caption injection fails, continue without blocking playback.  
   - Display lesson metadata such as title, duration (when provided by JSON), and any description or summary from the metadata.  
   - For text lessons, inline the HTML content into the page at build time (e.g., inject sanitized markup into a template or embed via `<template>` tags) so it can render without runtime network/file fetches.  
   - Detect and list downloadable attachments (e.g., `.pdf`, `.zip`, `.png`) beneath the main content with relative links.
7. **Client-side behavior**  
   - Implement navigation without full page reloads (SPA feel) using vanilla JS so switching lessons updates the main pane dynamically.  
   - Ensure initialization logic selects the first lesson by default and updates the URL hash (optional) for deep linking when feasible offline.  
   - Handle malformed content gracefully (show fallback message if media fails to load).
8. **Styling and layout**  
   - Deliver a responsive layout (desktop optimized, mobile acceptable) using locally bundled CSS. Tailwind utility classes may be mimicked via a pre-generated static CSS file, but no CDN links or build steps at runtime.  
   - Provide a dark-on-light theme with sufficient contrast, clear typography, and distinct section headers.
9. **Accessibility**  
   - Ensure keyboard navigation can move between sidebar items and activate lessons.  
   - Include labels for screen readers on navigation controls and video players.
10. **Build idempotency**  
    - Regeneration should overwrite previously generated site assets deterministically without duplicating content or leaving stale files.  
    - Provide a `--clean` flag to remove prior generated files before rebuild if necessary.

## 5. Non-Goals (Out of Scope)
- Tracking learner progress, bookmarking, or syncing state across sessions.
- Hosting or serving the site via a backend server or adding authentication.  
- Building or bundling third-party tooling beyond Python standard libraries (no Node/Tailwind build pipeline).  
- Streaming remote media; all content must remain local.

## 6. Design Considerations
- Keep the HTML/CSS/JS footprint small; consider hand-crafted CSS or a precompiled utility stylesheet shipped with the generator to approximate Tailwind ergonomics offline.  
- Use semantic HTML to ensure screen readers work as expected.  
- Anticipate long chapter/lesson names and ensure they truncate or wrap gracefully in the sidebar.  
- Consider providing optional keyboard shortcuts for previous/next lesson navigation to improve usability.

## 7. Technical Considerations
- Leverage existing project structure (`thinkific_downloader` package) for command wiring if possible.  
- Use Python templating (e.g., `jinja2`) only if already available in dependencies; otherwise, rely on standard-library templating (`string.Template`) or manual composition.  
- Handle file paths with `pathlib` to simplify cross-platform compatibility.  
- Guard against browser security limitations when opening `file://` URLs by embedding lesson content directly or via data attributes instead of runtime `fetch` calls.  
- Ensure generated HTML references assets using relative paths (no absolute `/` paths).  
- Provide unit coverage for JSON parsing and asset discovery logic, and add an integration smoke test that generates the sample course site into a temp directory.

## 8. Success Metrics
- Opening `downloads/<course-slug>/index.html` in a modern browser renders the full navigation tree within 2 seconds on the sample course.  
- 100% of lessons in `beginner-chess-mastery` are reachable and display the correct content type offline.  
- Generation script returns a non-zero exit code when any required lesson asset is missing.  
- Manual QA confirms video playback with captions works for at least one lesson that ships `.vtt` files.

## 9. Open Questions
- None at this time.
