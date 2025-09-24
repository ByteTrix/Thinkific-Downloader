# Thinkific Downloader - AI Agent Instructions

## Architecture Overview

This is a modern Python 3.8+ application that downloads educational content from Thinkific-based learning platforms. The architecture follows a modular design with clear separation of concerns:

- **Entry Points**: `thinkificdownloader.py` (legacy) and `python -m thinkific_downloader` (preferred)
- **Core Engine**: `thinkific_downloader/downloader.py` - main orchestrator with global state management
- **Specialized Downloaders**: `wistia_downloader.py` for Wistia video content, standard HTTP for other media
- **Download Management**: `download_manager.py` with parallel processing, rate limiting, and resume capabilities
- **Configuration**: Environment-driven via `.env` files with `config.py` handling validation

## Critical Developer Workflows

### Running the Application
```bash
# Preferred modern approach
python -m thinkific_downloader

# Legacy approach (still supported)
python thinkificdownloader.py

# Docker deployment
docker-compose up
```

### Environment Setup
- **Authentication is MANDATORY** - requires `COOKIE_DATA` and `CLIENT_DATE` from browser DevTools
- Configuration lives in `.env` files (workspace root takes precedence over package directory)
- See `ENV_SETUP.md` for detailed browser cookie extraction process
- Missing auth data causes immediate `SystemExit` with clear error message

### Package Management
- Minimal dependencies: `requests`, `rich`, `tqdm` (see `requirements.txt`)
- Optional extras: `brotli` support, `beautifulsoup4` for enhanced parsing
- Multi-stage Docker build optimizes for Alpine Linux + FFmpeg

## Project-Specific Patterns

### Global State Management
The `downloader.py` module uses globals to mirror PHP-style behavior:
```python
# Critical singletons initialized in init_settings()
SETTINGS: Optional[Settings] = None
DOWNLOAD_MANAGER: Optional[DownloadManager] = None
COURSE_CONTENTS: List[Dict[str, Any]] = []
```

### Authentication Headers Pattern
All HTTP requests use consistent Thinkific-compatible headers:
```python
# Standard auth header pattern used throughout
request_headers = {
    'x-thinkific-client-date': SETTINGS.client_date,
    'cookie': SETTINGS.cookie_data,
    'User-Agent': USER_AGENT,  # Chrome-based UA string
}
```

### Filename Sanitization
File naming follows strict cross-platform rules via `file_utils.py`:
- Reserved characters (`<>:"/\|?*`) replaced with hyphens
- Unicode escapes properly decoded
- UTF-8 byte limits enforced (255 bytes max)
- Filename beautification (lowercase, dash consolidation)

### Progress Monitoring
Rich terminal UI with custom columns for download status:
- `QueuedSpeedColumn` shows "Queued" instead of unrealistic speeds
- `QueuedTimeColumn` handles pending downloads gracefully
- Progress state persists across application restarts

## Integration Points

### Wistia Video Processing
Special handling for Wistia-hosted videos via regex extraction:
```python
# Extract Wistia ID from JSONP URLs
VIDEO_PROXY_JSONP_ID_PATTERN = re.compile(r"medias/(\w+)\.jsonp")
```
- Supports compressed responses (brotli/gzip/deflate)
- Falls back to first available quality if requested quality unavailable
- Quality options: 720p (default), 1080p, etc.

### Rate Limiting & Concurrency
Token bucket rate limiter prevents server overload:
- Configurable concurrent downloads (default: 3 threads)
- Exponential backoff with jitter for failed requests
- Optional bandwidth limiting via `RATE_LIMIT_MB_S`

### Resume Functionality
Atomic progress tracking across application restarts:
- Download state persisted in JSON files
- Cross-platform safe backup system
- Partial download detection and continuation

## Docker Considerations

- Multi-stage build (builder + runtime) for minimal image size
- Non-root user (`thinkific`) for security
- FFmpeg included for presentation merging when `FFMPEG_PRESENTATION_MERGE=true`
- Volume mounting for persistent downloads: `./downloads:/app/downloads`

## Key Configuration Options

Essential `.env` variables (see `.env.example`):
- `COURSE_LINK`: Target course URL
- `COOKIE_DATA`: Browser session cookies (required)
- `CLIENT_DATE`: API timestamp (required)
- `CONCURRENT_DOWNLOADS`: Parallel download threads (1-10)
- `VIDEO_DOWNLOAD_QUALITY`: Preferred video quality
- `RESUME_PARTIAL`: Enable download resumption (default: true)

## Testing & Debugging

- Set `DEBUG=true` for verbose logging
- Progress validation via Rich UI real-time monitoring
- File integrity checking with size/checksum validation
- Network retry logic automatically handles transient failures