import os
import re
import sys
import json
import gzip
import time
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional
from urllib.parse import urlparse, parse_qs
import urllib.request

from .config import Settings, load_env
from .file_utils import filter_filename, unicode_decode
from tqdm import tqdm

# Globals to mirror PHP behavior
ROOT_PROJECT_DIR = Path.cwd()
COURSE_CONTENTS: List[Dict[str, Any]] = []
SETTINGS: Optional[Settings] = None
BASE_HOST: Optional[str] = None

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36'


def init_settings():
    global SETTINGS
    if SETTINGS is None:
        SETTINGS = Settings.from_env()


def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> str:
    init_settings()
    if SETTINGS is None:
        raise RuntimeError("Settings not initialized")
    request_headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'x-requested-with': 'XMLHttpRequest',
        'x-thinkific-client-date': SETTINGS.client_date,
        'cookie': SETTINGS.cookie_data,
        'User-Agent': USER_AGENT,
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        encoding = resp.headers.get('Content-Encoding', '')
        if 'gzip' in encoding:
            data = gzip.decompress(data)
        return data.decode('utf-8', errors='replace')


def download_file_redirect(url: str, file_name: Optional[str] = None):
    # Simulate PHP fdownload behavior (follow redirect manually)
    init_settings()
    if SETTINGS is None:
        raise RuntimeError("Settings not initialized")
    request_headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'x-requested-with': 'XMLHttpRequest',
        'x-thinkific-client-date': SETTINGS.client_date,
        'cookie': SETTINGS.cookie_data,
        'User-Agent': USER_AGENT,
    }
    req = urllib.request.Request(url, headers=request_headers)
    # We allow redirect to capture final URL
    with urllib.request.urlopen(req) as resp:
        final_url = resp.geturl()
    parsed = urlparse(final_url)
    fname = os.path.basename(parsed.path)
    qs = parse_qs(parsed.query)
    if 'filename' in qs:
        fname = qs['filename'][0]
    if file_name:
        # Preserve extension
        ext = os.path.splitext(fname)[1]
        fname = f"{file_name}{ext}"
    fname = filter_filename(fname)
    if Path(fname).exists():
        return
    download_file_chunked(final_url, fname)


def download_file_chunked(src_url: str, dst_name: str, chunk_mb: int = 1):
    if Path(dst_name).exists():
        return
    init_settings()
    if SETTINGS is None:
        raise RuntimeError("Settings not initialized")
    request_headers = {
        'Accept-Encoding': 'identity',  # streaming
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'x-requested-with': 'XMLHttpRequest',
        'x-thinkific-client-date': SETTINGS.client_date,
        'cookie': SETTINGS.cookie_data,
        'User-Agent': USER_AGENT,
    }
    req = urllib.request.Request(src_url, headers=request_headers)
    
    try:
        with urllib.request.urlopen(req) as resp:
            # Get file size for progress bar
            content_length = resp.headers.get('Content-Length')
            total_size = int(content_length) if content_length else None
            
            chunk_bytes = chunk_mb * 1024 * 1024
            
            # Create progress bar
            with tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Downloading {Path(dst_name).name}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            ) as pbar:
                
                with open(dst_name, 'wb') as out:
                    start_time = time.time()
                    downloaded = 0
                    
                    while True:
                        chunk = resp.read(chunk_bytes)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress bar
                        pbar.update(len(chunk))
                        
                        # Calculate and display speed every few chunks
                        if downloaded % (chunk_bytes * 5) == 0:  # Update speed every 5MB
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed
                                pbar.set_postfix({'speed': f'{speed/1024/1024:.2f} MB/s'})
                    
                    # Final speed calculation
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = downloaded / elapsed
                        print(f"Download completed: {downloaded/1024/1024:.2f} MB in {elapsed:.2f}s (avg: {speed/1024/1024:.2f} MB/s)")
    
    except Exception as e:
        print(f"Download failed for {dst_name}: {e}")
        # Clean up partial file
        if Path(dst_name).exists():
            Path(dst_name).unlink()


def init_course(data: Dict[str, Any]):
    global COURSE_CONTENTS, ROOT_PROJECT_DIR, BASE_HOST
    course_name = filter_filename(data['course']['name'])
    prev_dir = Path.cwd()
    ROOT_PROJECT_DIR = prev_dir
    course_dir = Path(course_name)
    course_dir.mkdir(exist_ok=True)
    os.chdir(course_dir)
    COURSE_CONTENTS = data['contents']
    # Derive base host from landing_page_url if available
    landing = data['course'].get('landing_page_url')
    if landing:
        BASE_HOST = urlparse(landing).hostname
    create_chap_folders(data)
    os.chdir(prev_dir)


def create_chap_folders(data: Dict[str, Any]):
    for i, chapter in enumerate(data.get('chapters', []), start=1):
        chap_folder_name = f"{i}. {filter_filename(chapter['name'])}"
        Path(chap_folder_name).mkdir(exist_ok=True)
        prev_dir = Path.cwd()
        os.chdir(chap_folder_name)
        chapterwise_download(chapter['content_ids'])
        os.chdir(prev_dir)


# Patterns reused
VIDEOPROXY_PATTERN = re.compile(r"https://platform.thinkific.com/videoproxy/v1/play/[a-zA-Z0-9]+")
MP3_PATTERN = re.compile(r"https://[^\"']+\.mp3")
WISTIA_PATTERN = re.compile(r"(?:\w+\.)?(?:wistia\.(?:com|net)|wi\.st)/(?:medias|embed(?:/(?:iframe|medias))?)/([a-zA-Z0-9]+)")
VIDEOPROXY_IN_HTML_PATTERN = re.compile(r"https://platform\.thinkific\.com/videoproxy/v1/play/[a-zA-Z0-9]+")
MP3_IN_HTML_PATTERN = re.compile(r"https://[^\"']+\.mp3")


def api_get(endpoint: str) -> Optional[Dict[str, Any]]:
    """Helper to GET a course_player API resource using BASE_HOST and return JSON dict."""
    if not BASE_HOST:
        print('Base host unknown; cannot call API:', endpoint)
        return None
    url = f"https://{BASE_HOST}{endpoint}"
    print(f"[API] Fetching: {url}")
    try:
        raw = http_get(url)
        print(f"[API] Response (first 200 chars): {raw[:200]}")
        return json.loads(raw)
    except Exception as e:
        print(f"API GET failed {endpoint}: {e}")
        return None


def chapterwise_download(content_ids: Iterable[Any]):
    from .wistia_downloader import video_downloader_wistia, video_downloader_videoproxy  # local import
    global COURSE_CONTENTS, SETTINGS, ROOT_PROJECT_DIR
    index = 1
    for content_id in content_ids:
        match = next((c for c in COURSE_CONTENTS if c['id'] == content_id), None)
        if not match:
            print(f"[SKIP] No content found for id {content_id}")
            index += 1
            continue
        ctype = match.get('contentable_type') or match.get('default_lesson_type_label')
        print(f"[INFO] Processing content id {content_id} type {ctype} name {match.get('name')}")
        
        # HTML Item (Notes)
        if ctype == 'HtmlItem':
            fname = filter_filename(f"{match['slug']}.html")
            if Path(fname).exists():
                print("File already exists, skipping")
                index += 1
                continue
            dc = filter_filename(f"{index}. {match['name']} Text")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']}")
            j = api_get(f"/api/course_player/v2/html_items/{match['contentable']}")
            if j:
                html_text = j.get('html_item', {}).get('html_text', '')
                decoded = unicode_decode(html_text)
                
                # Extract videoproxy links
                videoproxy_matches = VIDEOPROXY_PATTERN.findall(decoded)
                if videoproxy_matches:
                    print("Found Videoproxy in HTML Item")
                    for video_url in set(videoproxy_matches):
                        video_downloader_videoproxy(video_url, filter_filename(match['name']), SETTINGS.video_download_quality if SETTINGS else '720p')
                
                # Extract MP3 audio files 
                mp3_matches = MP3_PATTERN.findall(decoded)
                if mp3_matches:
                    print("Found Audios in HTML Item")
                    for audio_url in set(mp3_matches):
                        audio_name = filter_filename(Path(urlparse(audio_url).path).name)
                        download_file_chunked(audio_url, audio_name)
                
                # Extract Wistia videos
                wistia_matches = WISTIA_PATTERN.findall(decoded)
                if wistia_matches:
                    print("Found Wistia Videos in HTML Item")
                    for wistia_id in set(wistia_matches):
                        video_downloader_wistia(wistia_id, filter_filename(match['name']), SETTINGS.video_download_quality if SETTINGS else '720p')
                
                # Save HTML content to file  
                fname = fname.replace(" ", "-")  # PHP replaces spaces with dashes
                Path(fname).write_text(decoded, encoding='utf-8', errors='replace')
            os.chdir(prev)
            index += 1
            continue

        # Multimedia (iframe)
        if match.get('default_lesson_type_label') == 'Multimedia':
            dc = filter_filename(f"{index}. {match['name']} Multimedia")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']}")
            j = api_get(f"/api/course_player/v2/iframes/{match['contentable']}")
            file_contents = ''
            if j:
                src_url = unicode_decode(j.get('iframe', {}).get('source_url') or '')
                # PHP logic: if URL contains .md, .html, or ends with /, try to fetch content
                if re.search(r"(\.md|\.html|/)$", src_url):
                    try:
                        file_contents = http_get(src_url)
                    except Exception:
                        print("Not a valid documents, continuing")
                        file_contents = src_url
                else:
                    file_contents = src_url
                
                # Download attached files
                if j.get('download_files'):
                    for download_file in j['download_files']:
                        download_file_name = filter_filename(download_file.get('label') or 'file')
                        download_file_url = download_file.get('download_url')
                        if download_file_url:
                            download_file_chunked(download_file_url, download_file_name)
            
            # Save to HTML file (PHP logic)
            fname = f"{match['name']}.html"
            fname = re.sub(r"[^A-Za-z0-9\_\-\. \?]", '', fname)  # PHP filename sanitization
            fname = filter_filename(fname)
            Path(fname).write_text(file_contents, encoding='utf-8', errors='replace')
            os.chdir(prev)
            index += 1
            continue

        # Lesson (videos + html + attachments)
        if ctype == 'Lesson':
            dc = filter_filename(f"{index}. {match['name']} Lesson")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            vname = filter_filename(match['name'])
            print(f"Downloading Video : {vname}")
            j = api_get(f"/api/course_player/v2/lessons/{match['contentable']}")
            if j:
                videos = j.get('videos') or []
                if not videos:
                    print('No Lesson Videos found for', vname)
                else:
                    for video in videos:
                        storage = video.get('storage_location')
                        identifier = video.get('identifier')
                        if storage == 'wistia' and identifier:
                            video_downloader_wistia(identifier, vname, SETTINGS.video_download_quality if SETTINGS else '720p')
                        elif storage == 'videoproxy' and identifier:
                            video_downloader_videoproxy(f"https://platform.thinkific.com/videoproxy/v1/play/{identifier}", vname, SETTINGS.video_download_quality if SETTINGS else '720p')
                        else:
                            print(f"Unknown video storage location. Trying Native Method for {vname}")
                            direct = video.get('url')
                            if direct:
                                download_file_redirect(direct, vname)
                
                # Save lesson HTML content if exists (PHP logic)
                lesson_info = j.get('lesson', {})
                html_text = lesson_info.get('html_text') if isinstance(lesson_info, dict) else None
                if html_text and html_text.strip():  # PHP checks if not empty
                    print(f"Saving HTML Text for {vname}")
                    html_filename = f"{vname}.html"
                    Path(html_filename).write_text(html_text, encoding='utf-8', errors='replace')
                
                # Download attached files
                for dlf in j.get('download_files', []) or []:
                    download_file_name = filter_filename(dlf.get('label') or 'file')
                    download_file_url = dlf.get('download_url')
                    if download_file_url:
                        download_file_chunked(download_file_url, download_file_name)
            os.chdir(prev); index += 1; continue

        # Pdf
        if ctype == 'Pdf':
            dc = filter_filename(f"{index}. {match['name']}")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']} (PDF)")
            j = api_get(f"/api/course_player/v2/pdfs/{match['contentable']}")
            if j:
                pdf = j.get('pdf', {})
                pdf_url = pdf.get('url')
                if pdf_url:
                    fname = filter_filename(Path(urlparse(pdf_url).path).name)
                    download_file_chunked(pdf_url, fname)
            os.chdir(prev); index += 1; continue

        # Download (shared files)
        if ctype == 'Download':
            dc = filter_filename(f"{index}. {match['name']}")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']} (Files)")
            j = api_get(f"/api/course_player/v2/downloads/{match['contentable']}")
            if j:
                for dlf in j.get('download_files', []) or []:
                    label = filter_filename(dlf.get('label') or 'file')
                    url = dlf.get('download_url')
                    if url:
                        download_file_chunked(url, label)
            os.chdir(prev); index += 1; continue

        # Audio
        if ctype == 'Audio':
            dc = filter_filename(f"{index}. {match['name']}")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']} (Audio)")
            j = api_get(f"/api/course_player/v2/audio/{match['contentable']}")
            if j:
                audio = j.get('audio', {})
                audio_url = audio.get('url')
                if audio_url:
                    fname = filter_filename(Path(urlparse(audio_url).path).name)
                    download_file_chunked(audio_url, fname)
            os.chdir(prev); index += 1; continue

        # Presentation
        if ctype == 'Presentation':
            dc = filter_filename(f"{index}. {match['name']}")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            print(f"Downloading {match['name']} (Presentation)")
            j = api_get(f"/api/course_player/v2/presentations/{match['contentable']}")
            if j:
                pres = j.get('presentation', {})
                pdf_url = pres.get('source_file_url')
                pdf_name = filter_filename(pres.get('source_file_name') or 'slides.pdf')
                if pdf_url:
                    download_file_chunked(pdf_url, pdf_name)
                # Optional merging if ffmpeg available and flag is set
                merge_flag = SETTINGS.ffmpeg_presentation_merge if SETTINGS else False
                if merge_flag:
                    # Detect ffmpeg availability
                    from shutil import which
                    if which('ffmpeg') is None:
                        print('ffmpeg not found in PATH; skipping merge. Install ffmpeg or disable flag.')
                    else:
                        items = j.get('presentation_items') or []
                        # Download images & audio (with position prefix) first
                        print('Downloading slide images/audio for merge')
                        for it in items:
                            pos = it.get('position')
                            img_url = it.get('image_file_url')
                            aud_url = it.get('audio_file_url')
                            if img_url:
                                download_file_chunked('https:' + img_url if img_url.startswith('//') else img_url,
                                                      filter_filename(f"{pos}{it.get('image_file_name','slide.png')}") )
                            if aud_url:
                                download_file_chunked('https:' + aud_url if aud_url.startswith('//') else aud_url,
                                                      filter_filename(f"{pos}{it.get('audio_file_name','audio.m4a')}") )
                        # Build per-slide videos
                        print('Merging slides to per-slide videos')
                        list_entries = []
                        for it in items:
                            pos = it.get('position')
                            img_name = filter_filename(f"{pos}{it.get('image_file_name','slide.png')}")
                            aud_name = filter_filename(f"{pos}{it.get('audio_file_name','audio.m4a')}") if it.get('audio_file_url') else None
                            slide_video = filter_filename(f"{pos}-slide.mp4")
                            if Path(slide_video).exists():
                                list_entries.append(slide_video)
                                continue
                            # Build ffmpeg command
                            if aud_name and Path(aud_name).exists():
                                cmd = f'ffmpeg -r 1 -loop 1 -y -i "{img_name}" -i "{aud_name}" -c:a copy -r 1 -vcodec libx264 -shortest "{slide_video}" -hide_banner -loglevel error'
                            else:
                                cmd = f'ffmpeg -r 1 -loop 1 -t 5 -y -i "{img_name}" -f lavfi -i anullsrc -c:a aac -r 1 -vcodec libx264 -shortest "{slide_video}" -hide_banner -loglevel error'
                            print(cmd)
                            os.system(cmd)
                            if Path(slide_video).exists():
                                list_entries.append(slide_video)
                        if list_entries:
                            # Write list.txt
                            with open('list.txt','w', encoding='utf-8') as lf:
                                for f in list_entries:
                                    lf.write(f"file '{f}'\n")
                            merged_name = filter_filename(f"{match['contentable']}-{match['name']}-merged.mp4")
                            if not Path(merged_name).exists():
                                concat_cmd = f'ffmpeg -n -f concat -safe 0 -i list.txt -c copy "{merged_name}" -hide_banner'
                                print(concat_cmd)
                                os.system(concat_cmd)
                            # Clean intermediates
                            for f in list_entries:
                                try:
                                    Path(f).unlink()
                                except Exception:
                                    pass
                            try:
                                Path('list.txt').unlink()
                            except Exception:
                                pass
                            # Remove slide assets (images/audio)
                            for it in items:
                                pos = it.get('position')
                                img_name = filter_filename(f"{pos}{it.get('image_file_name','slide.png')}")
                                if Path(img_name).exists():
                                    try: Path(img_name).unlink()
                                    except Exception: pass
                                if it.get('audio_file_url'):
                                    aud_name = filter_filename(f"{pos}{it.get('audio_file_name','audio.m4a')}")
                                    if Path(aud_name).exists():
                                        try: Path(aud_name).unlink()
                                        except Exception: pass
            os.chdir(prev); index += 1; continue

        # Quiz
        if ctype == 'Quiz':
            print(f"Downloading {match['name']}")
            dc = filter_filename(f"{index}. {match['name']} Quiz")
            Path(dc).mkdir(exist_ok=True)
            prev = Path.cwd(); os.chdir(dc)
            fname = filter_filename(f"{match['name']} Answers.html")
            qname = filter_filename(f"{match['name']} Questions.html")
            
            result = api_get(f"/api/course_player/v2/quizzes/{match['contentable']}")
            if result:
                file_contents_with_answers = "<h3 style='color: red;'>Answers of this Quiz are marked in RED </h3>"
                file_contents_with_questions = ""
                
                # Process questions (PHP logic)
                for qs in result.get("questions", []):
                    choice = 'A'
                    position = qs.get("position", 0) + 1  # PHP increments position by 1
                    prompt = unicode_decode(qs.get("prompt", ""))
                    explanation = unicode_decode(qs.get("text_explanation", ""))
                    
                    file_contents_with_answers += f"{position}) <strong>{prompt}</strong> Explanation: {explanation}<br><br>"
                    
                    # Extract embedded Wistia videos from prompt (PHP logic)
                    wistia_matches = WISTIA_PATTERN.findall(prompt)
                    if wistia_matches:
                        for wistia_match in set(wistia_matches):
                            video_downloader_wistia(wistia_match, f"QA Video {position}", SETTINGS.video_download_quality if SETTINGS else '720p')
                    
                    file_contents_with_questions += f"{position}) <strong>{prompt}</strong><br><br>"
                    
                    # Process choices for this question
                    for ch in result.get("choices", []):
                        if ch.get("question_id") == qs.get("id"):
                            try:
                                import base64
                                ans = base64.b64decode(ch.get("credited", "")).decode('utf-8', 'ignore')
                                ans = re.sub(r'\d', '', ans)  # Remove digits
                            except Exception:
                                ans = ""
                            
                            choice_text = unicode_decode(ch.get("text", ""))
                            if ans == "true":
                                file_contents_with_questions += f"{choice}) {choice_text}<br>"
                                file_contents_with_answers += f"<em style='color: red;'>{choice}) {choice_text}</em><br>"
                            else:
                                file_contents_with_questions += f"{choice}) {choice_text}<br>"
                                file_contents_with_answers += f"{choice}) {choice_text}<br>"
                            
                            choice = chr(ord(choice) + 1)  # Increment choice letter
                    
                    file_contents_with_questions += "<br>"
                    file_contents_with_answers += "<br>"
                
                # Write both files (PHP logic)
                Path(qname).write_text(file_contents_with_questions, encoding='utf-8', errors='replace')
                Path(fname).write_text(file_contents_with_answers, encoding='utf-8', errors='replace')
            
            os.chdir(prev)
            index += 1
            continue

        # Assignment (placeholder - currently planned)
        if ctype == 'Assignment':
            print(f"Assignment content type not yet implemented: {match['name']}")
            index += 1
            continue

        # Survey (placeholder - currently planned)
        if ctype == 'Survey':
            print(f"Survey content type not yet implemented: {match['name']}")
            index += 1
            continue
        
        index += 1


def handler(course_url: str):
    """Fetch course JSON and initialize folder structure."""
    raw = http_get(course_url)
    data = json.loads(raw)
    if 'error' in data:
        print(data['error'])
        return
    parsed = urlparse(course_url)
    course_file = Path(parsed.path).name + '.json'
    Path(course_file).write_text(raw, encoding='utf-8')
    init_course(data)


def main(argv: List[str]):
    print("THINKIFIC DOWNLOADER\nPython Port (Core)\nAuthor: Ported by Assistant\n")
    # Ensure .env is loaded before checking COURSE_URL/COURSE_LINK
    try:
        load_env()
    except FileNotFoundError:
        pass  # proceed; Settings.from_env() will raise later if critical vars missing
    # Accept legacy/alternate env var names: COURSE_URL or COURSE_LINK
    course_url_env_primary = os.getenv('COURSE_URL')
    course_url_env_alt = os.getenv('COURSE_LINK')
    effective_course_url_env = course_url_env_primary or course_url_env_alt

    if ('--json' in argv and len(argv) > 2) or os.getenv('COURSE_DATA_FILE'):
        if '--json' in argv:
            json_path = Path(argv[argv.index('--json') + 1])
            if not json_path.exists():
                print(f"File not found: {json_path}")
                return
            print('Using Custom Metadata File for course data.')
            data = json.loads(json_path.read_text(encoding='utf-8'))
        else:
            course_data_file = os.getenv('COURSE_DATA_FILE')
            if not course_data_file:
                print('COURSE_DATA_FILE env var not set.')
                return
            json_path = Path(course_data_file)
            if not json_path.exists():
                print(f"File not found: {json_path}")
                return
            print('Loading Custom Metadata File from env for course data.')
            data = json.loads(json_path.read_text(encoding='utf-8'))
        init_course(data)
    elif len(argv) > 1:
        course_url = argv[1]
        handler(course_url)
    else:
        if effective_course_url_env:
            print(f"Using course url from env: { 'COURSE_URL' if course_url_env_primary else 'COURSE_LINK' }")
            handler(effective_course_url_env)
        else:
            print('No course URL resolved.')
            print('Usage for using course url: python thinkidownloader3.py <course_url>')
            print('Or set COURSE_URL=... (fallback: COURSE_LINK=...) in .env')
            print('Usage for selective download: python thinkidownloader3.py --json <course.json>')


if __name__ == '__main__':
    main(sys.argv)