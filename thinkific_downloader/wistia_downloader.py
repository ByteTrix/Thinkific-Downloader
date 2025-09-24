import json
import re
import urllib.request
import zlib
from typing import Optional, List
from pathlib import Path
import os
from .file_utils import filter_filename
from .download_manager import DownloadManager
# Local imports inside functions to avoid circular dependency during module import

# Handles video proxy and wistia direct downloads

WISTIA_JSON_URL = "https://fast.wistia.com/embed/medias/{id}.json"

VIDEO_PROXY_JSONP_ID_PATTERN = re.compile(r"medias/(\w+)\.jsonp")


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
        req = urllib.request.Request(json_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_bytes = resp.read()
                encoding = resp.headers.get('Content-Encoding', '')
                if 'br' in encoding:
                    try:
                        import brotli  # type: ignore
                        raw_decoded = brotli.decompress(raw_bytes)
                    except Exception:
                        # Attempt python's built-in zlib alt decompress for brotli mislabels (rare)
                        try:
                            raw_decoded = zlib.decompress(raw_bytes)
                        except Exception:
                            return None
                elif 'gzip' in encoding:
                    raw_decoded = zlib.decompress(raw_bytes, 16 + zlib.MAX_WBITS)
                elif 'deflate' in encoding:
                    # deflate can be raw or zlib-wrapped
                    try:
                        raw_decoded = zlib.decompress(raw_bytes)
                    except zlib.error:
                        raw_decoded = zlib.decompress(raw_bytes, -zlib.MAX_WBITS)
                else:
                    try:
                        return raw_bytes.decode('utf-8')
                    except Exception:
                        return raw_bytes.decode('latin-1', errors='replace')
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
        print("Failed to decode Wistia JSON. First 120 chars:", raw[:120])
        return

    media = data.get('media') or {}
    assets = media.get('assets') or []
    if not assets:
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
    from .downloader import add_download_task
    current_dir = Path.cwd()  # Capture current working directory
    full_path = current_dir / resolved_name  # Create absolute path
    add_download_task(video_url, full_path, "video")
