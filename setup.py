#!/usr/bin/env python3
"""
Setup script for Chinese-English Speech Translation Service
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="speech-translation-service",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A real-time Chinese-English speech translation service using Gemini API",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/speech-translation-service",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-mock>=3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "speech-translate=main:main",
            "speech-translate-api=api_server:main",
            "speech-translate-test=test_service:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.yml", "*.yaml"],
    },
    keywords=[
        "speech",
        "translation",
        "chinese",
        "english",
        "gemini",
        "ai",
        "audio",
        "tts",
        "stt",
        "real-time",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/speech-translation-service/issues",
        "Source": "https://github.com/yourusername/speech-translation-service",
        "Documentation": "https://github.com/yourusername/speech-translation-service#readme",
    },
)
