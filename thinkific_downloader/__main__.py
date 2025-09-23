#!/usr/bin/env python3
"""
Command line entry point for Thinkific Downloader
"""

import sys
from thinkific_downloader.downloader import main

if __name__ == "__main__":
    main(sys.argv)