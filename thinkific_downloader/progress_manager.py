import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, TaskID, TextColumn, BarColumn, TimeRemainingColumn, TransferSpeedColumn, DownloadColumn
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

console = Console()

class ProgressDisplay:
    """Manages rich progress display for downloads."""
    
    def __init__(self):
        self.progress = Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•", 
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
            transient=True
        )
        self.tasks: Dict[str, TaskID] = {}
        
    def add_task(self, filename: str, total_size: Optional[int] = None) -> TaskID:
        """Add a download task to the progress display."""
        task_id = self.progress.add_task(
            "download",
            filename=filename,
            total=total_size
        )
        self.tasks[filename] = task_id
        return task_id
    
    def update_task(self, filename: str, advance: int = 0, **kwargs):
        """Update progress for a specific task."""
        if filename in self.tasks:
            self.progress.update(self.tasks[filename], advance=advance, **kwargs)
    
    def complete_task(self, filename: str):
        """Mark a task as completed."""
        if filename in self.tasks:
            self.progress.update(self.tasks[filename], completed=True)
    
    def start(self):
        """Start the progress display."""
        self.progress.start()
        
    def stop(self):
        """Stop the progress display."""
        self.progress.stop()


class ContentProcessor:
    """Handles content processing with cleaner output."""
    
    def __init__(self):
        self.processed_items = []
        self.download_queue = []
        
    def process_content_item(self, item: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Process a content item and collect download tasks."""
        content_type = item.get('contentable_type') or item.get('default_lesson_type_label', 'Unknown')
        name = item.get('name', 'Untitled')
        
        # Create a clean summary
        summary = {
            'index': index,
            'name': name,
            'type': content_type,
            'files': [],
            'status': 'pending'
        }
        
        # Log the processing
        console.print(f"[cyan]📋 Processing:[/cyan] {content_type} - {name}", style="dim")
        
        # Collect files to download based on content type
        files_to_download = self._get_files_for_content_type(item, content_type)
        summary['files'] = files_to_download
        
        # Add to download queue
        self.download_queue.extend(files_to_download)
        
        self.processed_items.append(summary)
        return summary
    
    def _get_files_for_content_type(self, item: Dict[str, Any], content_type: str) -> List[Dict[str, Any]]:
        """Get list of files to download for a specific content type."""
        files = []
        
        if content_type == 'Lesson':
            # Video files
            files.append({
                'type': 'video',
                'url': f"wistia:{item.get('contentable')}",  # Placeholder
                'filename': f"{item.get('name', 'video')}.mp4",
                'size_estimate': '100-500MB'
            })
            
        elif content_type == 'Pdf':
            files.append({
                'type': 'pdf',
                'url': f"pdf:{item.get('contentable')}",  # Placeholder
                'filename': f"{item.get('name', 'document')}.pdf",
                'size_estimate': '1-10MB'
            })
            
        elif content_type == 'HtmlItem':
            files.append({
                'type': 'html',
                'url': f"html:{item.get('contentable')}",  # Placeholder
                'filename': f"{item.get('name', 'content')}.html",
                'size_estimate': '<1MB'
            })
            
        elif content_type == 'Audio':
            files.append({
                'type': 'audio',
                'url': f"audio:{item.get('contentable')}",  # Placeholder
                'filename': f"{item.get('name', 'audio')}.mp3",
                'size_estimate': '5-50MB'
            })
            
        return files
    
    def print_summary(self):
        """Print a summary of all processed content."""
        if not self.processed_items:
            console.print("[yellow]No content items processed[/yellow]")
            return
            
        # Create summary panel
        summary_text = Text()
        summary_text.append("📊 Content Summary\n", style="bold cyan")
        
        type_counts = {}
        total_files = 0
        
        for item in self.processed_items:
            content_type = item['type']
            type_counts[content_type] = type_counts.get(content_type, 0) + 1
            total_files += len(item['files'])
        
        summary_text.append(f"Total Items: {len(self.processed_items)}\n", style="white")
        summary_text.append(f"Total Files: {total_files}\n", style="white")
        summary_text.append("\nContent Types:\n", style="bold white")
        
        for content_type, count in type_counts.items():
            emoji = self._get_type_emoji(content_type)
            summary_text.append(f"  {emoji} {content_type}: {count}\n", style="green")
        
        panel = Panel(summary_text, title="Processing Summary", border_style="blue")
        console.print(panel)
    
    def _get_type_emoji(self, content_type: str) -> str:
        """Get emoji for content type."""
        emoji_map = {
            'Lesson': '🎥',
            'Pdf': '📄',
            'HtmlItem': '📝',
            'Audio': '🎵',
            'Quiz': '📝',
            'Download': '📁',
            'Presentation': '🎨',
            'Multimedia': '🖼️'
        }
        return emoji_map.get(content_type, '📋')


def print_banner():
    """Print a clean banner."""
    banner_text = Text()
    banner_text.append("🚀 THINKIFIC DOWNLOADER\n", style="bold cyan")
    banner_text.append("Enhanced with Parallel Downloads & Rich UI\n", style="green")
    
    panel = Panel(
        banner_text, 
        title="Starting Download", 
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)


def print_download_start_banner(total_files: int, parallel_workers: int):
    """Print banner before starting downloads."""
    info_text = Text()
    info_text.append(f"📁 Files to download: {total_files}\n", style="white")
    info_text.append(f"🔄 Parallel workers: {parallel_workers}\n", style="white")
    info_text.append(f"⚡ Enhanced features: Rate limiting, Resume, Validation\n", style="green")
    
    panel = Panel(
        info_text,
        title="Download Configuration",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)


def print_completion_summary(successful: int, failed: int, total_time: float):
    """Print completion summary."""
    status_text = Text()
    
    if failed == 0:
        status_text.append("🎉 All downloads completed successfully!\n", style="bold green")
    else:
        status_text.append(f"⚠️  Downloads completed with {failed} failures\n", style="bold yellow")
    
    status_text.append(f"✅ Successful: {successful}\n", style="green")
    status_text.append(f"❌ Failed: {failed}\n", style="red" if failed > 0 else "dim")
    status_text.append(f"⏱️  Total time: {total_time:.1f}s\n", style="blue")
    
    panel = Panel(
        status_text,
        title="Download Complete",
        border_style="green" if failed == 0 else "yellow",
        padding=(1, 2)
    )
    console.print(panel)