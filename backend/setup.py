"""Setup script for parking management system backend."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="parking-management-backend",
    version="1.0.0",
    author="Parking Management Team",
    author_email="dev@parking.example.com",
    description="Backend for Parking Management System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/parking-management",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Topic :: Office/Business :: Scheduling",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "factory-boy>=3.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "sentry-sdk>=1.38.0",
            "opentelemetry-api>=1.21.0",
            "opentelemetry-sdk>=1.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "parking-api=parking_api.cli:main",
            "parking-worker=parking_api.worker:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)