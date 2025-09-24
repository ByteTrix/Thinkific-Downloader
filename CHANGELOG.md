# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-09-24

### 🚀 Major Features Added
- **Enhanced Download Manager**: Complete rewrite with improved timeout handling and better error recovery
- **AI Agent Documentation**: Comprehensive `.github/copilot-instructions.md` for AI coding assistance
- **Selective Download Guide**: Detailed `SELECTIVE_DOWNLOAD.md` with multiple methods for downloading specific lessons
- **Resume-First Architecture**: Improved resume functionality with atomic progress tracking

### 🐛 Critical Bug Fixes
- **Fixed Gzip Decompression Error**: Resolved `http_get()` function attempting manual decompression when requests auto-handles it
- **Download Timeout Issues**: Improved session timeout handling from 60s to (30s connect, 300s read) for large files (1GB+)
- **Completion Summary Bug**: Fixed incorrect parameter passing in completion reports showing wrong success/failure counts
- **URL Encoding**: Fixed special character handling in URLs and file paths
- **File Validation**: Enhanced media file validation with proper size and integrity checks

### 🎨 User Experience Improvements
- **Conditional Debug Logging**: Debug output now only shows when `DEBUG=true` in environment variables
- **Rich Terminal UI**: Enhanced progress bars with queued status handling and realistic speed calculations
- **Better Error Messages**: Clearer error reporting with actionable troubleshooting steps
- **Clean Output**: Reduced verbose logging for production use while maintaining debug capabilities

### 📚 Documentation Enhancements
- **Environment Setup Guide**: Comprehensive `ENV_SETUP.md` with browser cookie extraction steps
- **Development Guide**: Added `DEVELOPMENT.md` for contributors
- **AI Agent Instructions**: Detailed architectural guide for automated code assistance
- **Selective Downloads**: Complete guide for downloading specific lessons instead of entire courses
- **Updated README**: Improved structure with better navigation and clearer setup instructions

### ⚡ Performance Optimizations
- **Parallel Download Engine**: Enhanced multi-threaded downloads with intelligent task queuing
- **Rate Limiting**: Configurable bandwidth limiting to respect server resources
- **Memory Efficiency**: Optimized streaming downloads for large files without memory bloat
- **Network Resilience**: Exponential backoff with jitter for failed requests

### 🔧 Technical Improvements
- **Modern Python Package**: Proper `__main__.py` entry point with `python -m thinkific_downloader`
- **Session Management**: Improved HTTP session handling with connection pooling
- **File System Safety**: Cross-platform filename sanitization and atomic file operations  
- **Docker Optimization**: Multi-stage builds with Alpine Linux for minimal container size
- **Progress Persistence**: Download state survives application restarts

### 🛠️ Developer Experience
- **Code Organization**: Modular architecture with clear separation of concerns
- **Type Hints**: Comprehensive type annotations throughout the codebase  
- **Error Handling**: Robust exception handling with graceful degradation
- **Testing Support**: Improved validation and debugging capabilities

### 🔄 Migration Notes
- Existing `.env` configurations remain compatible
- Resume data from previous versions is automatically migrated
- Docker images updated to use Python 3.13 with FFmpeg support
- Legacy `thinkificdownloader.py` entry point still supported

---

## [1.0.0] - 2024-XX-XX

### Initial Release
- Basic Thinkific course downloading functionality
- Wistia video support
- Multi-threaded downloads
- Docker containerization
- Resume capability
- Rich terminal UI

---

## Contributing

When adding entries to this changelog:

1. **Keep entries organized** by type (Added, Changed, Deprecated, Removed, Fixed, Security)
2. **Use present tense** for descriptions ("Add feature" not "Added feature")  
3. **Include context** about why changes were made when helpful
4. **Link to issues/PRs** when available using `[#123](link)` format
5. **Group related changes** together under logical headings
6. **Use emojis sparingly** and consistently for visual organization

For more information, see our [Contributing Guidelines](DEVELOPMENT.md).