"""
Setup configuration for Enterprise Real-Time Patterns

This package provides production-tested patterns and implementations for 
high-performance real-time data processing systems.
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read README for long description
README_PATH = Path(__file__).parent / "README.md"
if README_PATH.exists():
    with open(README_PATH, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "Enterprise-grade patterns for high-performance real-time data processing systems."

# Read requirements from requirements.txt
REQUIREMENTS_PATH = Path(__file__).parent / "requirements.txt"
requirements = []
if REQUIREMENTS_PATH.exists():
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as fh:
        requirements = [
            line.strip() 
            for line in fh.readlines() 
            if line.strip() and not line.startswith("#") and not line.startswith("-")
        ]

# Development requirements
DEV_REQUIREMENTS_PATH = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if DEV_REQUIREMENTS_PATH.exists():
    with open(DEV_REQUIREMENTS_PATH, "r", encoding="utf-8") as fh:
        dev_requirements = [
            line.strip() 
            for line in fh.readlines() 
            if line.strip() and not line.startswith("#") and not line.startswith("-r")
        ]

setup(
    name="enterprise-realtime-patterns",
    version="1.0.0",
    author="Real-Time Systems Engineering",
    author_email="your.email@domain.com",
    description="Production-tested patterns for high-performance real-time data processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/enterprise-realtime-patterns",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/enterprise-realtime-patterns/issues",
        "Source": "https://github.com/yourusername/enterprise-realtime-patterns",
        "Documentation": "https://enterprise-realtime-patterns.readthedocs.io/",
    },
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Python version requirement
    python_requires=">=3.9",
    
    # Dependencies
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        "dev": dev_requirements,
        "docs": [
            "sphinx>=5.3.0",
            "sphinx-rtd-theme>=1.1.0",
            "sphinx-autodoc-typehints>=1.19.0",
        ],
        "testing": [
            "pytest>=7.2.0",
            "pytest-asyncio>=0.21.0", 
            "pytest-cov>=4.0.0",
            "hypothesis>=6.60.0",
        ],
        "monitoring": [
            "prometheus-client>=0.15.0",
            "grafana-api>=1.0.3",
            "jaeger-client>=4.8.0",
        ],
        "performance": [
            "uvloop>=0.17.0",
            "orjson>=3.8.0",
            "msgpack>=1.0.4",
        ]
    },
    
    # Package metadata
    classifiers=[
        # Development Status
        "Development Status :: 5 - Production/Stable",
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: System Administrators",
        
        # Topic Classification
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Monitoring",
        "Topic :: Office/Business :: Financial",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Programming Language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        
        # Operating System
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        
        # Framework
        "Framework :: AsyncIO",
        "Framework :: Pytest",
        
        # Environment
        "Environment :: Console",
        "Environment :: Web Environment",
        
        # Natural Language
        "Natural Language :: English",
    ],
    
    # Keywords for package discovery
    keywords=[
        "fintech", "trading", "real-time", "kafka", "clickhouse", "kubernetes",
        "circuit-breaker", "microservices", "performance", "asyncio", "pydantic",
        "prometheus", "grafana", "devops", "enterprise", "production-ready",
        "high-frequency", "streaming", "financial-data", "market-data"
    ],
    
    # Entry points for console scripts
    entry_points={
        "console_scripts": [
            "enterprise-patterns=enterprise_patterns.cli:main",
        ],
    },
    
    # Include additional files
    include_package_data=True,
    package_data={
        "enterprise_patterns": [
            "config/*.yaml",
            "templates/*.json",
            "schemas/*.json",
        ],
    },
    
    # Zip safety
    zip_safe=False,
    
    # Project maturity and stability
    platforms=["any"],
) 