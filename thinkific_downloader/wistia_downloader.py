import json
import os
import re
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests

from .file_utils import filter_filename
# Local imports inside functions to avoid circular dependency during module import

# Handles video proxy and wistia direct downloads

WISTIA_JSON_URL = "https://fast.wistia.com/embed/medias/{id}.json"

VIDEO_PROXY_JSONP_ID_PATTERN = re.compile(r"medias/(\w+)\.jsonp")
DEFAULT_SUBTITLE_EXTENSION = "vtt"
_LANGUAGE_SANITIZE_PATTERN = re.compile(r'[^A-Za-z0-9\-]+')


def _normalize_wistia_track_url(url: Optional[str]) -> Optional[str]:
    """Normalize Wistia caption track URLs to absolute HTTPS URLs."""
    if not url or not isinstance(url, str):
        return None

    normalized = url.strip()
    if not normalized:
        return None

    if normalized.startswith('//'):
        normalized = f"https:{normalized}"
    elif normalized.startswith('/'):
        normalized = f"https://fast.wistia.com{normalized}"
    elif not re.match(r'^https?://', normalized, re.IGNORECASE):
        normalized = f"https://fast.wistia.com/{normalized.lstrip('/')}"

    return normalized


def _build_caption_url(hashed_id: Optional[str], language: Optional[str], extension: Optional[str] = None) -> Optional[str]:
    """Construct a Wistia caption URL when only hashedId and language are available."""
    if not hashed_id or not language:
        return None

    ext = (extension or DEFAULT_SUBTITLE_EXTENSION).lstrip('.') or DEFAULT_SUBTITLE_EXTENSION
    return f"https://fast.wistia.com/embed/captions/{hashed_id}.{ext}?language={language}"


def _infer_track_extension(url: str, fallback: str = DEFAULT_SUBTITLE_EXTENSION) -> str:
    """Infer file extension from track URL."""
    try:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix
        if suffix:
            return suffix.lstrip('.').lower() or fallback
    except (AttributeError, TypeError):
        pass
    return fallback


def extract_wistia_subtitle_tracks(media: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """Extract subtitle/caption track metadata from Wistia media JSON."""
    if not isinstance(media, dict):
        return []

    hashed_id = media.get('hashedId') or media.get('hashed_id')
    tracks: List[Dict[str, Optional[str]]] = []

    def add_track(url: Optional[str], language: Optional[str], label: Optional[str], ext: Optional[str]):
        normalized = _normalize_wistia_track_url(url)
        if not normalized and hashed_id and language:
            normalized = _build_caption_url(hashed_id, language, ext)
        if not normalized:
            return
        tracks.append({
            'url': normalized,
            'language': language,
            'label': label,
            'ext': (ext or '').lstrip('.') or None
        })

    def collect_from_captions(caption_items: Optional[Iterable[Dict[str, Any]]]):
        for track in caption_items or []:
            if not isinstance(track, dict):
                continue
            add_track(
                track.get('url') or track.get('src'),
                track.get('language') or track.get('lang'),
                track.get('languageName') or track.get('label') or track.get('name'),
                track.get('ext')
            )

    def collect_from_text_tracks(track_items: Optional[Iterable[Dict[str, Any]]], label_keys: Iterable[str]):
        label_key_order = tuple(label_keys)
        for track in track_items or []:
            if not isinstance(track, dict):
                continue
            language = track.get('language') or track.get('lang')
            label = next((track.get(key) for key in label_key_order if track.get(key)), None)
            sources = track.get('sources') or []
            if sources:
                for source in sources:
                    if not isinstance(source, dict):
                        continue
                    add_track(
                        source.get('url') or source.get('src'),
                        language,
                        label,
                        source.get('ext') or track.get('ext')
                    )
            else:
                add_track(
                    track.get('url') or track.get('src'),
                    language,
                    label,
                    track.get('ext')
                )

    def collect_from_assets(asset_items: Optional[Iterable[Dict[str, Any]]]):
        subtitle_flags = {'caption', 'captions', 'subtitle', 'subtitles'}
        for asset in asset_items or []:
            if not isinstance(asset, dict):
                continue
            asset_type = (asset.get('type') or '').lower()
            asset_kind = (asset.get('kind') or '').lower()
            if asset_type in subtitle_flags or asset_kind in subtitle_flags:
                add_track(
                    asset.get('url') or asset.get('src'),
                    asset.get('language') or asset.get('lang'),
                    asset.get('display_name') or asset.get('name'),
                    asset.get('ext')
                )

    def collect_from_transcripts(transcripts: Optional[Iterable[Dict[str, Any]]]):
        if not hashed_id:
            return
        for transcript in transcripts or []:
            if not isinstance(transcript, dict) or not transcript.get('hasCaptions'):
                continue
            language = (
                transcript.get('language')
                or transcript.get('wistiaLanguageCode')
                or transcript.get('bcp47LanguageTag')
            )
            if not language:
                continue
            add_track(
                _build_caption_url(hashed_id, language, DEFAULT_SUBTITLE_EXTENSION),
                language,
                transcript.get('name') or transcript.get('familyName') or language,
                DEFAULT_SUBTITLE_EXTENSION
            )

    collect_from_captions(media.get('captions'))
    collect_from_text_tracks(media.get('text_tracks'), ('name', 'label'))
    collect_from_text_tracks(media.get('textTracks'), ('name', 'label', 'title'))
    collect_from_assets(media.get('assets'))
    collect_from_transcripts(media.get('availableTranscripts'))

    unique_tracks: Dict[str, Dict[str, Optional[str]]] = {}
    for track in tracks:
        url = track['url']
        if not url:
            continue
        if url not in unique_tracks:
            unique_tracks[url] = track
        else:
            existing = unique_tracks[url]
            # Prefer track data that includes language/label/ext
            if not existing.get('language') and track.get('language'):
                existing['language'] = track['language']
            if not existing.get('label') and track.get('label'):
                existing['label'] = track['label']
            if not existing.get('ext') and track.get('ext'):
                existing['ext'] = track['ext']

    return list(unique_tracks.values())


def build_wistia_subtitle_tasks(
    media: Dict[str, Any],
    dest_dir: Path,
    video_base_name: str,
    settings: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Construct subtitle download task dicts for a Wistia media object."""
    if not isinstance(dest_dir, Path):
        dest_dir = Path(dest_dir)

    if settings and not getattr(settings, 'subtitle_download_enabled', True):
        return []

    tracks = extract_wistia_subtitle_tracks(media)
    if not tracks:
        return []

    base_name = Path(video_base_name).stem
    if not base_name:
        fallback_name = media.get('name') or media.get('hashedId') or 'captions'
        base_name = filter_filename(str(fallback_name))
    else:
        base_name = filter_filename(base_name)

    if not base_name:
        base_name = "captions"

    tasks: List[Dict[str, Any]] = []
    counter = 1
    for track in tracks:
        url = track.get('url')
        if not url:
            continue

        ext = (track.get('ext') or _infer_track_extension(url)).lstrip('.').lower() or DEFAULT_SUBTITLE_EXTENSION
        language_raw = track.get('language') or track.get('label')
        if isinstance(language_raw, str):
            language_part = _LANGUAGE_SANITIZE_PATTERN.sub('-', language_raw).strip('-')
        else:
            language_part = ''

        if not language_part:
            language_part = 'captions' if counter == 1 else f"captions-{counter}"

        subtitle_filename = filter_filename(f"{base_name}.{language_part}.{ext}")
        if not subtitle_filename:
            subtitle_filename = filter_filename(f"{base_name}.captions-{counter}.{ext}")

        tasks.append({
            'url': url,
            'dest_path': dest_dir / subtitle_filename,
            'content_type': 'subtitle',
            'label': track.get('label'),
            'language': track.get('language'),
        })
        counter += 1

    return tasks


def video_downloader_videoproxy(video_url: str, file_name: str, quality: str = "720p"):
    from .downloader import http_get  # delayed import
    video_html_frame = http_get(video_url)  # JSONP wrapper
    match = VIDEO_PROXY_JSONP_ID_PATTERN.search(video_html_frame)
    if match:
        wistia_id = match.group(1)
        video_downloader_wistia(wistia_id, file_name, quality)


def video_downloader_wistia(wistia_id: str, file_name: Optional[str] = None, quality: str = "720p"):
    """Download a Wistia video by ID.

    Handles compressed (brotli/deflate/gzip) responses and retries with reduced headers
    if the Thinkific-auth style request fails or returns compressed binary that isn't
    automatically decompressed by urllib. Falls back to selecting first asset if
    desired quality not present.
    """
    from .downloader import DOWNLOAD_MANAGER  # delayed import

    if not DOWNLOAD_MANAGER:
        from .downloader import init_settings
        init_settings()

    json_url = WISTIA_JSON_URL.format(id=wistia_id)

    def fetch_raw(simple: bool = False) -> Optional[str]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Accept': 'application/json,text/javascript,*/*;q=0.9',
        }
        # If simple, don't advertise brotli to get plain JSON (some hosts still send br randomly)
        if not simple:
            headers['Accept-Encoding'] = 'gzip, deflate, br'
        else:
            headers['Accept-Encoding'] = 'gzip, deflate'

        try:
            resp = requests.get(json_url, headers=headers, timeout=30)

            # Handle compressed response data
            data = resp.content
            encoding = resp.headers.get('Content-Encoding', '')

            if 'br' in encoding:
                try:
                    import brotli  # type: ignore
                    raw_decoded = brotli.decompress(data)
                except Exception:
                    # Attempt python's built-in zlib alt decompress for brotli mislabels (rare)
                    try:
                        raw_decoded = zlib.decompress(data)
                    except Exception:
                        return None
            elif 'gzip' in encoding:
                raw_decoded = zlib.decompress(data, 16 + zlib.MAX_WBITS)
            elif 'deflate' in encoding:
                # deflate can be raw or zlib-wrapped
                try:
                    raw_decoded = zlib.decompress(data)
                except zlib.error:
                    raw_decoded = zlib.decompress(data, -zlib.MAX_WBITS)
            else:
                try:
                    return data.decode('utf-8')
                except Exception:
                    return data.decode('latin-1', errors='replace')

            return raw_decoded.decode('utf-8', errors='replace')

        except Exception as e:
            print(f"Wistia fetch error ({'simple' if simple else 'full'} headers): {e}")
            return None

    # First attempt with reduced headers (simpler) to avoid binary JSON issues
    raw = fetch_raw(simple=True)
    if not raw:
        # Retry with full encoding acceptance
        raw = fetch_raw(simple=False)
    if not raw:
        print("Failed to fetch Wistia JSON after retries.")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        from .downloader import SETTINGS  # Import here to avoid circular import
        if SETTINGS and SETTINGS.debug:
            print("Failed to decode Wistia JSON. First 120 chars:", raw[:120])
        return

    media = data.get('media') or {}
    assets = media.get('assets') or []
    if not assets:
        from .downloader import SETTINGS  # Import here to avoid circular import
        if SETTINGS and SETTINGS.debug:
            print("No assets in Wistia response.")
        return
    all_formats_flag = os.getenv('ALL_VIDEO_FORMATS', 'false').lower() in ('1','true','yes','on')

    def infer_ext(asset: dict) -> str:
        ct = (asset.get('content_type') or '').lower()
        url = asset.get('url') or ''
        
        # Check URL path for extension
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_ext = Path(parsed.path).suffix.lower()
        if path_ext in ['.mp4', '.webm', '.m3u8', '.ogg', '.mov', '.avi', '.mkv']:
            return path_ext
            
        # Check content type
        if '.m3u8' in url or 'application/vnd.apple.mpegurl' in ct or 'application/x-mpegURL' in ct:
            return '.m3u8'
        if '.mp4' in url or 'mp4' in ct or 'video/mp4' in ct:
            return '.mp4'
        if '.webm' in url or 'webm' in ct or 'video/webm' in ct:
            return '.webm'
        if '.ogg' in url or '.ogv' in url or 'ogg' in ct or 'video/ogg' in ct:
            return '.ogg'
        if '.mov' in url or 'video/quicktime' in ct:
            return '.mov'
        if 'video/' in ct:
            return '.mp4'  # Default fallback for video content
        
        # If no extension detected, default to .mp4 for video assets
        return '.mp4'

    resolved_base = filter_filename(file_name if file_name else media.get('name') or wistia_id)
    current_dir = Path.cwd()

    if all_formats_flag:
        print(f"Downloading all available Wistia assets for {resolved_base}")
        from .downloader import DOWNLOAD_MANAGER  # local import inside to avoid circular earlier
        if not DOWNLOAD_MANAGER:
            from .downloader import init_settings
            init_settings()
        seen: List[str] = []
        for asset in assets:
            a_url = asset.get('url')
            if not a_url or a_url in seen:
                continue
            seen.append(a_url)
            display = asset.get('display_name') or asset.get('type') or 'asset'
            ext = infer_ext(asset)
            # Ensure we always have an extension
            if not ext:
                ext = '.mp4'
            # For different resolutions append display name
            out_name = resolved_base
            if display and display.lower() != 'original':
                out_name = f"{resolved_base}-{filter_filename(display)}"
            if not out_name.endswith(ext):
                out_name += ext
            print(f"Asset: {display} -> {a_url}")
            if DOWNLOAD_MANAGER:
                DOWNLOAD_MANAGER.download_file(a_url, Path(filter_filename(out_name)))
            else:
                print("Download manager not initialized")
        from .downloader import SETTINGS, add_download_task
        subtitle_tasks = build_wistia_subtitle_tasks(media, current_dir, resolved_base, SETTINGS)
        for task in subtitle_tasks:
            print(f"   [Subs] Queued subtitles: {task['dest_path'].name}")
            add_download_task(task['url'], task['dest_path'], task.get('content_type', 'subtitle'))
        return

    # Single quality path
    selected = None
    for asset in assets:
        if asset.get('display_name') == quality:
            selected = asset; break
    if not selected:
        # choose highest width mp4/webm
        candidates = [a for a in assets if a.get('url') and infer_ext(a) in ('.mp4', '.webm')]
        if candidates:
            candidates.sort(key=lambda a: a.get('width') or 0, reverse=True)
            selected = candidates[0]
    if not selected:
        selected = assets[0]
        print('Video quality not found. Using first available asset.')
    video_url = selected.get('url')
    if not video_url:
        print('Selected Wistia asset missing URL.'); return
    ext = infer_ext(selected)
    # Ensure we always have an extension
    if not ext:
        ext = '.mp4'  # Default fallback
    resolved_name = resolved_base + (ext if not resolved_base.endswith(ext) else '')
    print(f"URL : {video_url}\nFile Name : {resolved_name}")
    
    # Queue video for parallel download with absolute path to current directory
    from .downloader import SETTINGS, add_download_task
    full_path = current_dir / resolved_name  # Create absolute path
    add_download_task(video_url, full_path, "video")
    subtitle_tasks = build_wistia_subtitle_tasks(media, current_dir, resolved_name, SETTINGS)
    for task in subtitle_tasks:
        print(f"   [Subs] Queued subtitles: {task['dest_path'].name}")
        add_download_task(task['url'], task['dest_path'], task.get('content_type', 'subtitle'))
