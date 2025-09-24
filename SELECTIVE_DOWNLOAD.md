# 🎯 Selective Download Guide

This guide explains how to download only specific lessons from a Thinkific course instead of downloading the entire course.

## Overview

The Thinkific Downloader supports selective downloads using a JSON configuration file that specifies exactly which lessons you want to download. This is useful when you only need certain chapters or want to avoid downloading large files you don't need.

## Methods Available

### Method 1: Using Environment Variable (Recommended)

1. **Create or obtain a course data JSON file** (see options below)
2. **Set the file path in your `.env` file:**
   ```bash
   COURSE_DATA_FILE="my-selective-lessons.json"
   ```
3. **Run the downloader:**
   ```bash
   python -m thinkific_downloader
   ```

### Method 2: Using Command Line Flag

You can specify the JSON file directly via command line:
```bash
python -m thinkific_downloader --json my-selective-lessons.json
```

### Method 3: Docker with Selective Downloads

```bash
# Set in your .env file
COURSE_DATA_FILE="selective-lessons.json"

# Run with Docker
docker-compose up
```

## Creating Your Selective JSON File

### Option A: From Existing Progress File

If you've already run the downloader once:

1. **Copy the generated progress file:**
   ```bash
   # Windows
   copy "downloads\\your-course-name\\.thinkific_progress.json" "selective-lessons.json"
   
   # Linux/Mac
   cp "downloads/your-course-name/.thinkific_progress.json" "selective-lessons.json"
   ```

2. **Edit the file** to remove unwanted lessons from the `download_tasks` array

3. **Keep the structure intact** - only modify the contents of the arrays

### Option B: Create from Scratch

Create a JSON file with this structure:

```json
{
  "analyzed_chapters": ["chapter_1", "chapter_3", "chapter_5"],
  "download_tasks": [
    {
      "url": "https://embed-ssl.wistia.com/deliveries/video-id-here.bin",
      "dest_path": "1. chapter-name\\1.lesson-name\\lesson-file.mp4",
      "content_type": "video"
    },
    {
      "url": "https://course-files.thinkific.com/document.pdf",
      "dest_path": "1. chapter-name\\2.document-lesson\\document.pdf",
      "content_type": "document"
    }
  ]
}
```

## Understanding the JSON Structure

### `analyzed_chapters`
- Array of chapter IDs that have been processed
- Format: `["chapter_1", "chapter_2", "chapter_N"]`
- Used to track which chapters have been analyzed

### `download_tasks`
Each task has three required fields:

- **`url`**: Direct download URL for the content
- **`dest_path`**: Local file path where content will be saved
- **`content_type`**: Type of content (`video`, `document`, `html`, `audio`)

## Content Types Supported

| Content Type | Description | File Extensions |
|--------------|-------------|-----------------|
| `video` | Video lessons (Wistia, MP4) | `.mp4`, `.mov`, `.avi` |
| `document` | PDF documents, slides | `.pdf`, `.ppt`, `.pptx` |
| `html` | Text lessons, notes | `.html` |
| `audio` | Audio files | `.mp3`, `.m4a`, `.wav` |

## Example Workflows

### Download Only Videos from Specific Chapters

1. Run the full download once to get the complete JSON
2. Copy the progress file to `videos-only.json`
3. Edit to keep only entries where `content_type` is `"video"`
4. Remove chapters you don't want from `analyzed_chapters`
5. Set `COURSE_DATA_FILE="videos-only.json"` in `.env`

### Download Only First 5 Lessons

1. Get the complete JSON file
2. Keep only the first 5 entries in `download_tasks`
3. Update `analyzed_chapters` to match
4. Use the modified file

### Skip Large Video Files

1. Edit the JSON to remove large video entries
2. Keep documents, text, and smaller videos
3. Use the filtered JSON for download

## Tips and Best Practices

### File Path Management
- Use forward slashes (`/`) or double backslashes (`\\\\`) in paths
- Ensure destination directories exist or will be created
- Keep the original folder structure for organization

### Performance Optimization
- Fewer tasks = faster completion
- Remove unnecessary content types to save bandwidth
- Use `CONCURRENT_DOWNLOADS=1` for selective downloads to avoid rate limiting

### Validation
- Ensure all URLs are accessible
- Verify file paths are valid for your operating system
- Test with a small subset first

## Troubleshooting

### "File not found" Error
```
COURSE_DATA_FILE env var not set.
```
**Solution:** Ensure the JSON file exists in the project root directory and the path in `.env` is correct.

### "Invalid JSON" Error
**Solution:** Validate your JSON syntax using an online JSON validator or text editor with JSON support.

### Missing Downloads
**Solution:** Check that the `url` fields in your JSON are still valid and accessible.

### Permission Errors
**Solution:** Ensure the destination directories are writable and you have sufficient disk space.

## Getting Help

- See [ENV_SETUP.md](ENV_SETUP.md) for authentication setup
- See [README.md](README.md) for general usage
- Enable `DEBUG=true` for detailed logging
- Check the generated progress files for examples of proper JSON structure