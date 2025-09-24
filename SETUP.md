# 🛠️ Thinkific-Downloader Setup Guide

This comprehensive guide walks you through installing and configuring Thinkific-Downloader with all its advanced features.

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Authentication Setup](#authentication-setup)
- [Configuration Options](#configuration-options)
- [First Run](#first-run)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## 💻 System Requirements

### **Minimum Requirements**
- **Python**: 3.8 or higher
- **OS**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM**: 512MB available
- **Storage**: 100MB for installation + space for downloads
- **Network**: Stable internet connection

### **Recommended Requirements**
- **Python**: 3.11 or higher
- **RAM**: 2GB+ available (for concurrent downloads)
- **Storage**: 1GB+ free space
- **CPU**: Multi-core processor (for parallel processing)

### **Optional Requirements**
- **FFmpeg**: For presentation slide merging (auto-installed in Docker)
- **Git**: For development and updates

---

## 🚀 Installation Methods

### **📦 Option 1: Clone Repository (Recommended)**

Get the latest version directly from GitHub:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/itskavin/Thinkific-Downloader.git
   cd Thinkific-Downloader
   ```

2. **Setup configuration**:
   ```bash
   cp .env.example .env
   # ⚠️ IMPORTANT: Follow ENV_SETUP.md for detailed authentication setup
   ```
   
   **🔧 [Complete Environment Setup Guide](ENV_SETUP.md)** - Step-by-step instructions for extracting authentication data
   
3. **Run with Docker** (Recommended):
   ```bash
   docker-compose up
   ```
   
   **Or run with Python**:
   ```bash
   pip install -r requirements.txt
   python thinkificdownloader.py
   ```

---

### **🐳 Option 2: Docker Only**

If you want to use Docker without cloning:

---

## 🔐 Authentication Setup

To download courses, you need to obtain authentication data from your browser.

### **Step 1: Access Your Course**
1. Open your browser (Chrome, Firefox, etc.)
2. Navigate to your Thinkific course
3. Log in with your credentials
4. Make sure you can access the course content

### **Step 2: Extract Authentication Data**

#### **Method A: Browser Developer Tools (Recommended)**

1. **Open Developer Tools**:
   - Press `F12` or `Ctrl+Shift+I` (Windows/Linux)
   - Press `Cmd+Option+I` (Mac)

2. **Go to Network Tab**:
   - Click the "Network" tab
   - Refresh the page (F5)

3. **Find API Request**:
   - Look for requests to your course domain
   - Click on any request to the course site
   - Go to "Headers" section

4. **Copy Required Headers**:
   - **Cookie**: Copy the entire `Cookie` header value
   - **Client-Date**: Copy the `Client-Date` header value

#### **Method B: Browser Extension (Alternative)**

Use extensions like "Header Editor" or "ModHeader" to view headers.

### **Step 3: Get Course URL**
Copy the full URL of your course from the browser address bar.

**Example**: `https://yourschool.thinkific.com/courses/your-course-name`

---

## ⚙️ Configuration Options

### **Environment Variables File (.env)**

Create a `.env` file in your project directory:

```env
# ===============================================
# REQUIRED AUTHENTICATION
# ===============================================
COURSE_LINK=https://yourschool.thinkific.com/courses/your-course
COOKIE_DATA=your-complete-cookie-string-here
CLIENT_DATE=your-client-date-here

# ===============================================
# BASIC SETTINGS
# ===============================================
VIDEO_DOWNLOAD_QUALITY=720p
OUTPUT_DIR=./downloads

# ===============================================
# ENHANCED FEATURES (New!)
# ===============================================
# Parallel Downloads (1-10, recommended: 2-3)
CONCURRENT_DOWNLOADS=3

# Retry Logic (1-10, recommended: 3-5)
RETRY_ATTEMPTS=3

# Download Delay (seconds, 0.5-5.0)
DOWNLOAD_DELAY=1.0

# Rate Limiting (MB/s, empty = unlimited)
# RATE_LIMIT_MB_S=5.0

# File Validation (true/false)
VALIDATE_DOWNLOADS=true

# Resume Partial Downloads (true/false)
RESUME_PARTIAL=true

# Atomic Resume/Backup System (always enabled)
# Download status is tracked in .download_status.json (atomic, cross-platform)
# A backup .download_status.json.bak is created automatically before each update

# Debug Mode (true/false)
DEBUG=false

# ===============================================
# ADVANCED SETTINGS
# ===============================================
# FFmpeg Presentation Merging (true/false)
FFMPEG_PRESENTATION_MERGE=false

# Download All Video Formats (true/false)
ALL_VIDEO_FORMATS=false

# Use Enhanced Downloader (true/false)
USE_ENHANCED_DOWNLOADER=true
```

### **Configuration Profiles**

#### **Conservative Profile** (Respectful, Slower)
```env
CONCURRENT_DOWNLOADS=1
RETRY_ATTEMPTS=2
DOWNLOAD_DELAY=3.0
RATE_LIMIT_MB_S=2.0
```

#### **Balanced Profile** (Default, Recommended)
```env
CONCURRENT_DOWNLOADS=3
RETRY_ATTEMPTS=3
DOWNLOAD_DELAY=1.0
# RATE_LIMIT_MB_S=  # Unlimited
```

#### **Aggressive Profile** (Fast, Higher Risk)
```env
CONCURRENT_DOWNLOADS=5
RETRY_ATTEMPTS=5
DOWNLOAD_DELAY=0.5
# Use with caution!
```

---

## 🏃‍♂️ First Run

### **Method 1: Using Environment File**
```bash
# Ensure .env file is configured
python -m thinkific_downloader
```

### **Method 2: Command Line**
```bash
python -m thinkific_downloader "https://your-course-url"
```

### **Method 3: Docker**
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/app/downloads \
  --env-file .env \
  kvnxo/thinkific-downloader:latest
```

### **Expected Output**
```
🚀 THINKIFIC DOWNLOADER - ENHANCED
📦 Python Enhanced Version
✨ Features: Parallel downloads, Smart skip, Progress monitoring
════════════════════════════════════════════════════════════════════
🌐 Fetching course data...
🚀 Initializing enhanced course processing...

📚 Course: Your Course Name | Progress: 0.0% (0/25 files) | Speed: 0.0 MB/s | ETA: Unknown

📊 Resume Status Summary
  ✅ 5 files already completed
  📥 2 files partially downloaded (will resume)
  ❌ 1 files previously failed (will retry)

📁 Files to download: 31
🔄 Parallel workers: 3
⚡ Enhanced features: Rate limiting, Resume, Validation

🎥 introduction.mp4 ████████████████████████████ 100% 156.2MB • 12.3MB/s • Complete
🔄 lesson-02.mp4 ████████████░░░░░░░░░░░░░░░░ 45% 89.1MB/198.4MB • 8.7MB/s • 0:00:12
⏳ lesson-03.pdf ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0% Queued
```

---

## 🐳 Docker Setup (Detailed)

### **Docker Compose Configuration**

Create a complete `docker-compose.yml`:

```yaml
version: '3.8'

services:
  thinkific-downloader:
    image: kvnxo/thinkific-downloader:latest
    container_name: thinkific-downloader
    
    # Volume mounts
    volumes:
      - ./downloads:/app/downloads          # Download directory
      - ./.env:/app/.env                   # Environment file
      - ./courses:/app/courses             # Course data (optional)
    
    # Environment variables (override .env)
    environment:
      # Authentication
      - COURSE_LINK=${COURSE_LINK}
      - COOKIE_DATA=${COOKIE_DATA}
      - CLIENT_DATE=${CLIENT_DATE}
      
      # Enhanced features
      - CONCURRENT_DOWNLOADS=3
      - RETRY_ATTEMPTS=3
      - VALIDATE_DOWNLOADS=true
      - RESUME_PARTIAL=true
      - USE_ENHANCED_DOWNLOADER=true
      
      # Optional
      - VIDEO_DOWNLOAD_QUALITY=720p
      - DEBUG=false
    
    # Resource limits (optional)
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    # Restart policy
    restart: "no"
    
    # Network mode (optional)
    network_mode: bridge
```

### **Docker Management Commands**

```bash
# Build and run
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Update image
docker-compose pull
docker-compose up --force-recreate

# Cleanup
docker-compose down --volumes --rmi all
```

---

## 🔧 Environment Variables Reference

### **Required Variables**
| Variable | Description | Example |
|----------|-------------|---------|
| `COURSE_LINK` | Course URL | `https://school.thinkific.com/courses/course-name` |
| `COOKIE_DATA` | Browser cookies | `sessionid=abc123; csrftoken=xyz789; ...` |
| `CLIENT_DATE` | Client date header | `Wed, 23 Sep 2025 10:30:00 GMT` |

### **Optional Variables**
| Variable | Default | Description |
|----------|---------|-------------|
| `CONCURRENT_DOWNLOADS` | `3` | Parallel download threads (1-10) |
| `RETRY_ATTEMPTS` | `3` | Number of retry attempts (1-10) |
| `VIDEO_DOWNLOAD_QUALITY` | `720p` | Video quality preference |
| `DOWNLOAD_DELAY` | `1.0` | Delay between downloads (seconds) |
| `RATE_LIMIT_MB_S` | _(unlimited)_ | Bandwidth limit in MB/s |
| `VALIDATE_DOWNLOADS` | `true` | Enable file validation |
| `RESUME_PARTIAL` | `true` | Resume incomplete downloads |
| `OUTPUT_DIR` | `./downloads` | Download directory |
| `DEBUG` | `false` | Enable debug logging |
| `USE_ENHANCED_DOWNLOADER` | `true` | Use enhanced features |

### **Advanced Variables**
| Variable | Default | Description |
|----------|---------|-------------|
| `ALL_VIDEO_FORMATS` | `false` | Download all video qualities |
| `FFMPEG_PRESENTATION_MERGE` | `false` | Merge presentation slides |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING) |

---

## 🚨 Troubleshooting

### **Common Issues**

#### **1. Authentication Errors**
```
❌ Cookie data and Client Date not set
```

**Solution**:
- Re-extract cookies from browser (they expire)
- Ensure `.env` file is in the correct directory
- Check for typos in variable names

#### **2. No Downloads Starting**
```
✅ All files already exist and are valid!
```

**Solutions**:
- Delete existing files to re-download
- Set `VALIDATE_DOWNLOADS=false` to skip validation
- Use `--force-redownload` flag (if available)

#### **3. Permission Errors**
```
❌ Current directory is not writable
```

**Solutions**:
- Run with appropriate permissions
- Change to a writable directory
- Fix directory permissions: `chmod 755 .`

#### **4. Network/Connection Issues**
```
❌ HTTP GET failed: Connection timeout
```

**Solutions**:
- Check internet connection
- Increase retry attempts: `RETRY_ATTEMPTS=5`
- Add download delay: `DOWNLOAD_DELAY=2.0`
- Use rate limiting: `RATE_LIMIT_MB_S=3.0`

#### **5. Missing Dependencies**
```
❌ Import "rich.console" could not be resolved
```

**Solutions**:
- Install dependencies: `pip install -r requirements.txt`
- Use Docker version (pre-configured)
- Reinstall package: `pip install -e . --force-reinstall`

### **Docker Issues**

#### **1. Container Won't Start**
```bash
# Check Docker status
docker ps -a

# View container logs
docker logs container-name

# Check image
docker images | grep thinkific
```

#### **2. Volume Mount Issues**
```bash
# Ensure directories exist
mkdir -p downloads

# Check permissions
ls -la downloads/

# Fix permissions (Linux/Mac)
sudo chown -R $(whoami):$(whoami) downloads/
```

#### **3. Environment File Not Found**
```bash
# Check file exists
ls -la .env

# Verify content
cat .env

# Mount explicitly
docker run -v $(pwd)/.env:/app/.env ...
```

### **Performance Issues**

#### **1. Slow Downloads**
- Increase concurrent downloads: `CONCURRENT_DOWNLOADS=5`
- Remove rate limiting: `# RATE_LIMIT_MB_S=`
- Reduce delay: `DOWNLOAD_DELAY=0.5`

#### **2. High Memory Usage**
- Decrease concurrent downloads: `CONCURRENT_DOWNLOADS=1`
- Set rate limiting: `RATE_LIMIT_MB_S=2.0`
- Use Docker resource limits

#### **3. Frequent Failures**
- Increase retry attempts: `RETRY_ATTEMPTS=5`
- Add delays: `DOWNLOAD_DELAY=2.0`
- Use conservative settings

### **Debug Mode**

Enable detailed logging:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

This provides detailed output for troubleshooting:
```
[DEBUG] HTTP GET: https://example.com/api/...
[DEBUG] Response headers: {'Content-Length': '1234', ...}
[DEBUG] Download progress: 50% (512KB/1MB)
[DEBUG] File validation: PASSED
```

---

## ✅ Verification

After setup, verify everything works:

### **1. Test Authentication**
```bash
# Should show course info without downloading
python -c "from thinkific_downloader.config import Settings; s=Settings.from_env(); print(f'✅ Auth OK for {s.client_date[:20]}...')"

## Resume/Backup System

**How does resume work?**
- The downloader automatically tracks download status in `.download_status.json`.
- Before updating, a backup `.download_status.json.bak` is created (atomic, safe).
- If interrupted, just rerun the downloader. It will resume partial downloads, skip completed files, and retry failed ones.
- No manual intervention needed.

**Is it safe on Windows, Mac, Linux?**
- Yes! The resume/backup system uses atomic file operations and works on all major platforms.

**Where is the status file stored?**
- In the current working directory (where you run the downloader).

**Can I delete the status file?**
- Yes, but you will lose resume progress. The backup file is for safety only.
```

### **2. Test Network Connection**
```bash
# Test basic connectivity
ping google.com

# Test course site
curl -I https://your-course-site.com
```

### **3. Test Download System**
```bash
# Dry run (if available)
python -m thinkific_downloader --dry-run

# Download single lesson (if available)
python -m thinkific_downloader --limit 1
```

### **4. Verify Output**
```bash
# Check downloads directory
ls -la downloads/

# Check logs (if enabled)
tail -f *.log
```

---

## 🎯 Next Steps

After successful setup:

1. **📚 Read**: [DEVELOPMENT.md](DEVELOPMENT.md) for advanced usage
2. **🔧 Configure**: Fine-tune settings for your use case
3. **📦 Backup**: Save your configuration for future use
4. **🚀 Run**: Start downloading your courses!

---

## 💡 Pro Tips

### **For Best Performance**:
- Use Docker for hassle-free experience
- Set `CONCURRENT_DOWNLOADS=3` for balanced performance
- Enable `VALIDATE_DOWNLOADS=true` for reliability
- Use `RESUME_PARTIAL=true` to handle interruptions

### **For Stability**:
- Keep `RETRY_ATTEMPTS=3` or higher
- Use conservative `DOWNLOAD_DELAY=1.0` or higher
- Set reasonable `RATE_LIMIT_MB_S` if needed

### **For Debugging**:
- Enable `DEBUG=true` when troubleshooting
- Check logs regularly
- Monitor system resources

---

**Need more help?** Check our [GitHub Issues](https://github.com/itskavin/Thinkific-Downloader/issues) or [Discussions](https://github.com/itskavin/Thinkific-Downloader/discussions) page!