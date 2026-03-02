#!/usr/bin/env python3
"""
Setup script for parking management data layer.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="parking-management-data",
    version="1.0.0",
    author="Parking Management Team",
    author_email="dev@parking-management.com",
    description="Data layer for Parking Management System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/parking-management",
    packages=find_packages(exclude=["tests*", "docs*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
        "postgres": [
            "psycopg2-binary>=2.9.9",
            "asyncpg>=0.29.0",
        ],
        "mysql": [
            "mysqlclient>=2.2.0",
            "aiomysql>=0.2.0",
        ],
        "redis": [
            "redis>=5.0.1",
        ],
        "elasticsearch": [
            "elasticsearch>=8.11.0",
            "elasticsearch-dsl>=8.11.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "opentelemetry-api>=1.22.0",
            "opentelemetry-sdk>=1.22.0",
        ],
        "cloud": [
            "boto3>=1.34.0",
            "google-cloud-storage>=2.13.0",
            "azure-storage-blob>=12.19.0",
        ],
        "all": [
            "psycopg2-binary>=2.9.9",
            "asyncpg>=0.29.0",
            "redis>=5.0.1",
            "elasticsearch>=8.11.0",
            "elasticsearch-dsl>=8.11.0",
            "prometheus-client>=0.19.0",
            "opentelemetry-api>=1.22.0",
            "opentelemetry-sdk>=1.22.0",
            "boto3>=1.34.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "parking-data-init=scripts.init_db:main",
            "parking-data-seed=scripts.seed_data:main",
            "parking-data-backup=scripts.backup_db:main",
            "parking-data-restore=scripts.restore_db:main",
            "parking-data-migrate=scripts.migrate_data:main",
            "parking-data-cleanup=scripts.cleanup_old_data:main",
            "parking-data-analyze=scripts.analyze_performance:main",
        ],
    },
    include_package_data=True,
    package_data={
        "parking-management-data": [
            "schemas/**/*.sql",
            "schemas/**/*.json",
            "schemas/**/*.lua",
            "seed/**/*.json",
            "config/**/*.yaml",
            "migrations/**/*.py",
            "migrations/**/*.ini",
            "migrations/**/*.mako",
        ],
    },
    zip_safe=False,
)