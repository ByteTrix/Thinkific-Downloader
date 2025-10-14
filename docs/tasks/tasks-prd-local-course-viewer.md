# Local Course Viewer PRD – MVP Task List
Offline viewer generator that converts downloaded Thinkific courses into a local two-pane site. Plan derived from `docs/tasks/prd-local-course-viewer.md`.

## Relevant Files

- `thinkific_downloader/site_generator.py` - New module to parse course metadata, validate assets, and emit static HTML/CSS/JS.
- `thinkific_downloader/templates/base.html` - Template for the main layout (sidebar + main pane).
- `thinkific_downloader/templates/lesson.html` - Template partial used to render individual lesson payloads.
- `thinkific_downloader/static/viewer.css` - Bundled stylesheet for offline-friendly styling.
- `thinkific_downloader/static/viewer.js` - Client-side behavior for SPA-style navigation.
- `thinkific_downloader/__main__.py` - CLI entry point; extend to expose the site generation command.
- `thinkific_downloader/config.py` - Reuse settings utilities; ensure downloads path configuration hooks in here if needed.
- `README.md` - Document usage instructions for generating the offline site.

### Notes

- Keep static assets (CSS/JS) referenced with relative URLs so `file://` browsing works.
- Manual QA (spot-check of video playback and text rendering) is sufficient; automated tests are not required for this pass.

## Tasks

- [ ] 1. Implement course metadata parsing and validation for offline site generation.

- [ ] 1.1 Load the course JSON, map chapters to lessons, and preserve the ordering from Thinkific metadata.

- [ ] 1.2 Model lessons (video vs text) and attachments so downstream renderers know which assets to expect.

- [ ] 1.3 Verify every lesson folder exists under `downloads/<course-slug>/` and report missing media or HTML files before rendering.

- [ ] 1.4 Surface lesson metadata (titles, durations, descriptions) for template consumption.

- [ ] 2. Build static site generation templates, asset pipeline, and lesson rendering logic.

- [ ] 2.1 Create base layout and lesson partial templates for the two-pane interface.

- [ ] 2.2 Produce `viewer.css` with offline-friendly styling (handcrafted Tailwind-like utilities or custom rules).

- [ ] 2.3 Render video lessons with `<video controls>` pointing to local `.mp4` files and attach `<track>` captions when `.vtt` exists.

- [ ] 2.4 Inline HTML/text lesson content safely and list any downloadable attachments (PDFs, etc.) with relative links.

- [ ] 2.5 Write idempotent file output routines that place assets under `downloads/<course-slug>/` and optionally clear prior builds when `--clean` is passed.

- [ ] 3. Add client-side navigation behavior and accessibility polish for the generated site.

- [ ] 3.1 Implement `viewer.js` to swap lessons in the main pane without page reloads, updating the active state in the sidebar.

- [ ] 3.2 Default to the first lesson on load, and optionally sync selection with `location.hash` for deep linking.

- [ ] 3.3 Ensure video playback resets or pauses when switching lessons to avoid overlapping audio.

- [ ] 3.4 Provide keyboard navigation and ARIA labeling for sidebar items and focus management around the video element.

- [ ] 3.5 Display graceful fallback messaging if a media element fails to load.

- [ ] 4. Wire the generator into a CLI command with configuration options and regeneration handling.

- [ ] 4.1 Add a `generate-site` CLI entry point (e.g., `python -m thinkific_downloader generate-site <metadata.json>`).

- [ ] 4.2 Support flags for downloads root override, output subdirectory selection, dry-run validation, and `--clean`.

- [ ] 4.3 Align CLI logging with existing downloader tone (progress banners, validation warnings, success summary).

- [ ] 4.4 Exit with non-zero status when validation fails or generation encounters missing assets.
