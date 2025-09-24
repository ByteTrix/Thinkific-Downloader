#!/usr/bin/env python3
"""
Setup script for Thinkific Downloader
"""

from setuptools import setup, find_packages
import pathlib

# Read the README file
here = pathlib.Path(__file__).parent.resolve()
try:
    long_description = (here / 'README.md').read_text(encoding='utf-8')
except FileNotFoundError:
    long_description = "A modern Python utility to download courses from Thinkific-based platforms"

# Read version from __init__.py
version = {}
with open(here / 'thinkific_downloader' / '__init__.py') as f:
    exec(f.read(), version)

setup(
    name="thinkific-downloader",
    version=version['__version__'],
    description=version['__description__'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=version['__author__'],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "rich>=13.0.0",
        "tqdm>=4.65.0",
        "urllib3>=2.0.0",
    ],
    extras_require={
        "enhanced": [
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
        ],
        "brotli": ["brotli>=1.0.9"],
    },
    entry_points={
        "console_scripts": [
            "thinkific-downloader=thinkific_downloader.downloader:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Video",
        "Topic :: Education",
    ],
    keywords="thinkific downloader education video course offline",
    project_urls={
        "Bug Reports": "https://github.com/ByteTrix/Thinkific-Downloader/issues",
        "Source": "https://github.com/ByteTrix/Thinkific-Downloader",
        "Documentation": "https://github.com/ByteTrix/Thinkific-Downloader#readme",
        "Docker Hub": "https://hub.docker.com/r/kvnxo/thinkific-downloader",
    },
)