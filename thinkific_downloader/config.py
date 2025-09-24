import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Look for .env in the current working directory first, then package directory as fallback
ENV_FILE = Path.cwd() / '.env' if (Path.cwd() / '.env').exists() else Path(__file__).parent / '.env'


def load_env(file_path: Path = ENV_FILE):
    """Load environment variables from .env file if it exists, otherwise skip gracefully"""
    if file_path.exists():
        with file_path.open('r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                name, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                os.environ[name.strip()] = value
    # If .env doesn't exist, environment variables can still be set externally


@dataclass
class Settings:
    client_date: str
    cookie_data: str
    video_download_quality: str = '720p'
    ffmpeg_presentation_merge: bool = False
    output_dir: str = './downloads'  # Default to downloads directory
    # Enhanced downloader settings
    concurrent_downloads: int = 3
    retry_attempts: int = 3
    rate_limit_mb_s: Optional[float] = None
    download_delay: float = 1.0
    validate_downloads: bool = True
    resume_partial: bool = True
    debug: bool = False
    course_name: str = "Course"

    @classmethod
    def from_env(cls):
        load_env()
        
        # Required authentication
        client_date = os.getenv('CLIENT_DATE', '')
        cookie_data = os.getenv('COOKIE_DATA', '')
        
        # Basic settings with matching defaults to .env.example
        video_download_quality = os.getenv('VIDEO_DOWNLOAD_QUALITY', '720p')
        output_dir = os.getenv('OUTPUT_DIR', './downloads')
        
        # Advanced settings
        ffmpeg_flag_raw = os.getenv('FFMPEG_PRESENTATION_MERGE', 'false').lower()
        ffmpeg_merge = ffmpeg_flag_raw in ('1', 'true', 'yes', 'on')
        
        # Enhanced downloader settings with matching defaults
        concurrent_downloads = int(os.getenv('CONCURRENT_DOWNLOADS', '3'))
        retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
        download_delay = float(os.getenv('DOWNLOAD_DELAY', '1.0'))
        
        # Rate limiting - empty string or 0 means unlimited
        rate_limit_env = os.getenv('RATE_LIMIT_MB_S', '')
        rate_limit_mb_s = float(rate_limit_env) if rate_limit_env and rate_limit_env != '0' else None
        
        # Feature toggles
        validate_downloads = os.getenv('VALIDATE_DOWNLOADS', 'true').lower() in ('1', 'true', 'yes', 'on')
        resume_partial = os.getenv('RESUME_PARTIAL', 'true').lower() in ('1', 'true', 'yes', 'on')
        debug = os.getenv('DEBUG', 'false').lower() in ('1', 'true', 'yes', 'on')
        
        # Validation
        if not client_date or not cookie_data:
            raise SystemExit('Cookie data and Client Date not set. Use the ReadMe file first before using this script.')
            
        # Basic directory permissions check
        cwd = Path.cwd()
        if not os.access(cwd, os.W_OK):
            raise SystemExit('Current directory is not writable.')
        return cls(
            client_date=client_date, 
            cookie_data=cookie_data, 
            video_download_quality=video_download_quality,
            output_dir=output_dir,
            ffmpeg_presentation_merge=ffmpeg_merge,
            concurrent_downloads=concurrent_downloads,
            retry_attempts=retry_attempts,
            rate_limit_mb_s=rate_limit_mb_s,
            download_delay=download_delay,
            validate_downloads=validate_downloads,
            resume_partial=resume_partial,
            debug=debug
        )
