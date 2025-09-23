#!/usr/bin/env python3
"""
Quick installation script for Thinkific Downloader
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        sys.exit(1)

def install_optional_dependencies():
    """Install optional dependencies"""
    print("\n🔧 Installing optional dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "brotli"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Brotli compression support installed")
    except subprocess.CalledProcessError:
        print("⚠️  Brotli compression support not installed (optional)")

def check_ffmpeg():
    """Check if FFmpeg is available"""
    print("\n🎬 Checking for FFmpeg...")
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("✅ FFmpeg found - presentation merging will be available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  FFmpeg not found - presentation merging will be disabled")
        print("   Install FFmpeg from https://ffmpeg.org/ for full functionality")

def check_env_file():
    """Check if .env file exists and has required values"""
    print("\n⚙️  Checking configuration...")
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Please copy .env.example to .env and configure your settings")
        return False
    
    # Basic check for required values
    env_content = env_path.read_text()
    if 'CLIENT_DATE=""' in env_content or 'COOKIE_DATA=""' in env_content:
        print("⚠️  .env file exists but CLIENT_DATE and/or COOKIE_DATA are empty")
        print("   Please configure these values before running the downloader")
        return False
    
    print("✅ Configuration file found and appears configured")
    return True

def main():
    """Main installation function"""
    print("🚀 Thinkific Downloader Installation")
    print("=" * 40)
    
    check_python_version()
    install_requirements()
    install_optional_dependencies()
    check_ffmpeg()
    config_ok = check_env_file()
    
    print("\n" + "=" * 40)
    print("🎉 Installation complete!")
    print("\nUsage:")
    print("  python thinkidownloader3.py")
    print("  python -m thinkific_downloader")
    print("  python thinkidownloader3.py --json course.json")
    
    if not config_ok:
        print("\n⚠️  Remember to configure your .env file before running!")

if __name__ == "__main__":
    main()