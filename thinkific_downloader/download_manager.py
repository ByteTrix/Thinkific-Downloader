import os
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.progress import Progress, TaskID, TextColumn, BarColumn, TimeRemainingColumn, TransferSpeedColumn, DownloadColumn
from rich.text import Text
from rich.progress import ProgressColumn

class CustomSpeedColumn(ProgressColumn):
    """Speed column that shows 'Queued' instead of '?'"""
    def render(self, task):
        if task.speed is None:
            return Text("Queued", style="dim")
        return Text(f"{task.speed:.1f} MB/s" if task.speed > 1 else f"{task.speed*1000:.0f} KB/s")

class CustomTimeColumn(ProgressColumn):
    """Time remaining column that shows 'Queued' instead of '-:--:--'"""
    def render(self, task):
        if task.time_remaining is None:
            return Text("Queued", style="dim")
        remaining = int(task.time_remaining)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        return Text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
from rich.console import Console
from .config import Settings
from .file_utils import filter_filename


class RateLimiter:
    """Token bucket rate limiter for controlling download speed."""

    def __init__(self, rate_limit_mb_s: Optional[float] = None):
        self.rate_limit_bytes_s = rate_limit_mb_s * 1024 * 1024 if rate_limit_mb_s else None
        self.tokens = 0.0
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self, size: int) -> float:
        """Acquire tokens for the given size. Returns sleep time if rate limited."""
        if not self.rate_limit_bytes_s:
            return 0.0

        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens += time_passed * self.rate_limit_bytes_s
            self.tokens = min(self.tokens, self.rate_limit_bytes_s)  # Cap at burst rate
            self.last_update = now

            if self.tokens >= size:
                self.tokens -= size
                return 0.0
            else:
                # Calculate wait time
                wait_time = (size - self.tokens) / self.rate_limit_bytes_s
                self.tokens = 0.0
                self.last_update = now + wait_time
                return wait_time


class DownloadSession:
    """Manages HTTP sessions with connection pooling and retry logic."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with proper configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.settings.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/javascript,*/*;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'x-requested-with': 'XMLHttpRequest',
            'x-thinkific-client-date': self.settings.client_date,
            'cookie': self.settings.cookie_data,
        })

        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with the session."""
        return self.session.get(url, timeout=60, **kwargs)

    def close(self):
        """Close the session."""
        self.session.close()


class FileValidator:
    """Handles file validation and integrity checks."""

    @staticmethod
    def calculate_checksum(file_path: Path, algorithm: str = 'md5') -> str:
        """Calculate file checksum."""
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def validate_file_size(file_path: Path, expected_size: Optional[int] = None) -> bool:
        """Validate file size if expected size is provided."""
        if expected_size is None:
            return True
        return file_path.stat().st_size == expected_size

    @staticmethod
    def is_file_complete(file_path: Path, expected_size: Optional[int] = None) -> bool:
        """Check if file appears to be complete."""
        if not file_path.exists():
            return False
        if expected_size is None:
            return True
        return file_path.stat().st_size == expected_size


class DownloadTask:
    """Represents a single download task."""

    def __init__(self, url: str, dest_path: Path, expected_size: Optional[int] = None,
                 checksum: Optional[str] = None, resume: bool = True):
        self.url = url
        self.dest_path = dest_path
        self.expected_size = expected_size
        self.checksum = checksum
        self.resume = resume
        self.downloaded_size = 0
        self.status = 'pending'
        self.error: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if download is complete."""
        if not self.dest_path.exists():
            return False
        if self.expected_size:
            return self.dest_path.stat().st_size == self.expected_size
        return True


class DownloadManager:
    """Manages parallel downloads with rate limiting, retries, and validation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = DownloadSession(settings)
        self.rate_limiter = RateLimiter(settings.rate_limit_mb_s)
        self.executor = ThreadPoolExecutor(max_workers=settings.concurrent_downloads)
        self.validator = FileValidator()
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.lock = threading.Lock()

    def download_file(self, url: str, dest_path: Path, expected_size: Optional[int] = None,
                     checksum: Optional[str] = None, show_progress: bool = True) -> bool:
        """Download a single file with all features enabled."""
        task = DownloadTask(url, dest_path, expected_size, checksum, self.settings.resume_partial)

        # Check if file already exists and is valid
        if task.is_complete() and self._validate_download(task):
            if self.settings.debug:
                print(f"File already exists and valid: {dest_path}")
            return True

        # Start download
        return self._download_single_file(task, show_progress)

    def download_files_parallel(self, tasks: List[DownloadTask],
                               progress_callback: Optional[Callable] = None) -> List[bool]:
        """Download multiple files in parallel with Rich progress display."""
        
        console = Console()
        
        # Create rich progress display
        progress = Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            CustomSpeedColumn(),
            "•",
            CustomTimeColumn(),
            console=console,
        )
        
        with progress:
            futures = []
            results = []
            task_progress_map = {}

            for task in tasks:
                # Check if already complete
                if task.is_complete() and self._validate_download(task):
                    results.append(True)
                    continue

                # Get expected size
                if task.expected_size is None:
                    task.expected_size = self._get_content_length(task.url)

                # Add progress task
                progress_task_id = progress.add_task(
                    "download",
                    filename=task.dest_path.name,
                    total=task.expected_size or 100
                )
                task_progress_map[id(task)] = progress_task_id

                # Submit download job
                future = self.executor.submit(self._download_with_rich_progress, task, progress, progress_task_id)
                futures.append((future, task, progress_task_id))

            # Wait for completion
            for future, task, progress_task_id in futures:
                try:
                    result = future.result()
                    results.append(result)
                    if progress_callback:
                        progress_callback(task, result)
                except Exception as e:
                    console.print(f"[red]Download failed for {task.dest_path}: {e}[/red]")
                    results.append(False)

        return results

    def _download_with_rich_progress(self, task: DownloadTask, progress, progress_task_id: int) -> bool:
        """Download a single file with Rich progress bar updates."""
        try:
            # Check for resume
            resume_pos = 0
            if task.resume and task.dest_path.exists():
                resume_pos = task.dest_path.stat().st_size
                if task.expected_size and resume_pos >= task.expected_size:
                    return self._validate_download(task)

            # Prepare headers for resume
            headers = {}
            if task.resume and resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'

            response = self.session.session.get(task.url, headers=headers, stream=True)
            response.raise_for_status()

            # Update progress bar with actual content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                total_size = int(content_length) + resume_pos
                if task.expected_size != total_size:
                    task.expected_size = total_size
                    progress.update(progress_task_id, total=total_size)

            mode = 'ab' if resume_pos > 0 else 'wb'
            downloaded = resume_pos

            with open(task.dest_path, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        # Rate limiting
                        sleep_time = self.rate_limiter.acquire(len(chunk))
                        if sleep_time > 0:
                            time.sleep(sleep_time)

                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update Rich progress bar
                        progress.update(progress_task_id, advance=len(chunk))

            # Download completed successfully
            task.status = 'completed'
            return self._validate_download(task)

        except Exception as e:
            task.status = 'failed'
            task.error = str(e)
            
            # Clean up partial file if not resuming
            if not task.resume and task.dest_path.exists():
                task.dest_path.unlink()
            
            return False

    def _download_single_file(self, task: DownloadTask, show_progress: bool = True) -> bool:
        """Download a single file with resume support."""
        try:
            # Get file size first
            if task.expected_size is None:
                task.expected_size = self._get_content_length(task.url)

            # Check for resume
            resume_pos = 0
            if task.resume and task.dest_path.exists():
                resume_pos = task.dest_path.stat().st_size
                if task.expected_size and resume_pos >= task.expected_size:
                    return self._validate_download(task)

            # Prepare headers for resume
            headers = {}
            if task.resume and resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'

            # Make request
            response = self.session.get(task.url, headers=headers, stream=True)
            response.raise_for_status()

            # Handle redirect
            if response.status_code == 302:
                redirect_url = response.headers.get('Location')
                if redirect_url:
                    response = self.session.get(redirect_url, headers=headers, stream=True)
                    response.raise_for_status()

            # Get actual content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                total_size = int(content_length) + resume_pos
                if task.expected_size is None:
                    task.expected_size = total_size

            mode = 'ab' if resume_pos > 0 else 'wb'
            downloaded = resume_pos

            # Progress bar
            if show_progress and task.expected_size:
                console = Console()
                console.print(f"[blue]Downloading {task.dest_path.name}...[/blue]")

            with open(task.dest_path, mode) as f:
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        # Rate limiting
                        sleep_time = self.rate_limiter.acquire(len(chunk))
                        if sleep_time > 0:
                            time.sleep(sleep_time)

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Only show speed updates if not in parallel mode (to avoid spam)
                        if downloaded % (1024 * 1024) == 0 and show_progress:  # Update every 1MB
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed
                                # Only print speed updates when show_progress is True (not in parallel mode)
                                pass  # Remove speed updates in parallel mode

            # Download completed successfully

            # Validate download
            task.status = 'completed'
            return self._validate_download(task)

        except Exception as e:
            task.status = 'failed'
            task.error = str(e)
            print(f"Download failed for {task.dest_path}: {e}")

            # Clean up partial file if not resuming
            if not task.resume and task.dest_path.exists():
                task.dest_path.unlink()

            return False

    def _get_content_length(self, url: str) -> Optional[int]:
        """Get content length from HEAD request."""
        try:
            response = self.session.session.head(url, timeout=30)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            return int(content_length) if content_length else None
        except:
            return None

    def _validate_download(self, task: DownloadTask) -> bool:
        """Validate downloaded file."""
        if not self.settings.validate_downloads:
            return True

        try:
            # Check file size
            if not self.validator.validate_file_size(task.dest_path, task.expected_size):
                print(f"Size validation failed for {task.dest_path}")
                return False

            # Check checksum if provided
            if task.checksum:
                actual_checksum = self.validator.calculate_checksum(task.dest_path)
                if actual_checksum != task.checksum:
                    print(f"Checksum validation failed for {task.dest_path}")
                    return False

            return True
        except Exception as e:
            print(f"Validation error for {task.dest_path}: {e}")
            return False

    def close(self):
        """Clean up resources."""
        self.session.close()
        self.executor.shutdown(wait=True)