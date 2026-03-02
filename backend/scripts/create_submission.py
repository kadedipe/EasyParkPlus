#!/usr/bin/env python3
"""
Parking Management System - Submission Creator

This script creates a submission package for the Parking Management System.
It collects all necessary files, organizes them, creates documentation,
and generates a final submission zip file.

Features:
1. File collection and validation
2. Code documentation generation
3. Test execution and reporting
4. Dependency analysis
5. Package creation with proper structure
6. README and installation guide generation
"""

import os
import sys
import shutil
import zipfile
import tarfile
import json
import yaml
import subprocess
import hashlib
import datetime
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import tempfile
import stat
import re

# Add the project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Try to import the project modules to verify they exist
try:
    from src.presentation.parking_gui import ParkingManagementApp
    from src.application.parking_service import ParkingService
    HAS_PROJECT_MODULES = True
except ImportError:
    HAS_PROJECT_MODULES = False
    print("Warning: Could not import project modules. Some validations may be skipped.")


# ============================================================================
# CONFIGURATION
# ============================================================================

class SubmissionConfig:
    """Configuration for submission creation"""
    
    # Project metadata
    PROJECT_NAME = "Parking Management System"
    PROJECT_VERSION = "1.0.0"
    AUTHORS = ["Your Name/Team Name"]
    COMPANY = "Parking Solutions Inc."
    LICENSE = "MIT"
    
    # Required files and directories
    REQUIRED_DIRS = [
        "src",
        "tests",
        "docs",
        "scripts",
        "data",
        "config"
    ]
    
    REQUIRED_FILES = [
        "README.md",
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        ".gitignore",
        "LICENSE"
    ]
    
    # Files to include in submission
    INCLUDE_PATTERNS = [
        "**/*.py",
        "**/*.md",
        "**/*.txt",
        "**/*.yml",
        "**/*.yaml",
        "**/*.json",
        "**/*.toml",
        "**/*.ini",
        "**/*.cfg",
        "**/*.sql",
        "**/*.csv",
        "**/*.xml",
        "**/*.html",
        "**/*.css",
        "**/*.js",
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.gif",
        "**/*.ico",
        "**/*.svg",
        "**/*.pdf"
    ]
    
    # Files to exclude from submission
    EXCLUDE_PATTERNS = [
        "__pycache__/**",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "*.so",
        "*.dll",
        "*.exe",
        "*.log",
        "*.tmp",
        "*.temp",
        "*.bak",
        "*.swp",
        ".git/**",
        ".svn/**",
        ".hg/**",
        ".vscode/**",
        ".idea/**",
        "*.egg-info/**",
        "dist/**",
        "build/**",
        "venv/**",
        "env/**",
        ".env",
        ".venv",
        "node_modules/**",
        "*.db",
        "*.sqlite",
        "*.sqlite3"
    ]
    
    # Submission structure
    SUBMISSION_STRUCTURE = {
        "documentation": [
            "README.md",
            "INSTALL.md",
            "USER_GUIDE.md",
            "API_DOCS.md",
            "ARCHITECTURE.md",
            "CHANGELOG.md"
        ],
        "source_code": [
            "src/",
            "tests/",
            "scripts/",
            "requirements.txt",
            "setup.py",
            "pyproject.toml"
        ],
        "configuration": [
            "config/",
            ".env.example",
            "config.yml.example"
        ],
        "data": [
            "data/",
            "database/"
        ],
        "assets": [
            "assets/",
            "images/",
            "icons/"
        ]
    }
    
    # Test configurations
    TEST_COMMANDS = [
        ["python", "-m", "pytest", "tests/", "-v"],
        ["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=html"],
        ["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=xml"]
    ]
    
    # Code quality tools
    CODE_QUALITY_COMMANDS = [
        ["flake8", "src/", "--max-line-length=120"],
        ["black", "--check", "src/"],
        ["mypy", "src/"],
        ["pylint", "src/"]
    ]


# ============================================================================
# FILE VALIDATOR
# ============================================================================

class FileValidator:
    """Validate project files and structure"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors = []
        self.warnings = []
        self.valid_files = []
        self.missing_files = []
    
    def validate_structure(self) -> bool:
        """Validate project structure"""
        print("Validating project structure...")
        
        # Check required directories
        for dir_name in SubmissionConfig.REQUIRED_DIRS:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"  ✓ Directory exists: {dir_name}")
                self.valid_files.append(str(dir_path.relative_to(self.project_root)))
            else:
                print(f"  ✗ Missing directory: {dir_name}")
                self.warnings.append(f"Directory '{dir_name}' does not exist")
        
        # Check required files
        for file_name in SubmissionConfig.REQUIRED_FILES:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"  ✓ File exists: {file_name}")
                self.valid_files.append(str(file_path.relative_to(self.project_root)))
            else:
                print(f"  ✗ Missing file: {file_name}")
                self.missing_files.append(file_name)
        
        # Check for source files
        src_files = list(self.project_root.rglob("src/**/*.py"))
        if src_files:
            print(f"  ✓ Found {len(src_files)} Python source files")
        else:
            print(f"  ✗ No Python source files found in src/")
            self.errors.append("No Python source files found")
        
        # Check for test files
        test_files = list(self.project_root.rglob("tests/**/*.py"))
        if test_files:
            print(f"  ✓ Found {len(test_files)} test files")
        else:
            print(f"  ⚠ No test files found in tests/")
            self.warnings.append("No test files found")
        
        return len(self.errors) == 0
    
    def check_python_syntax(self) -> bool:
        """Check Python syntax of all .py files"""
        print("\nChecking Python syntax...")
        
        py_files = list(self.project_root.rglob("**/*.py"))
        syntax_errors = []
        
        for py_file in py_files:
            # Skip __pycache__ and virtual environments
            if any(exclude in str(py_file) for exclude in ["__pycache__", ".pyc", "venv", ".venv", "env"]):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to compile to check syntax
                compile(content, str(py_file), 'exec')
                print(f"  ✓ Syntax OK: {py_file.relative_to(self.project_root)}")
                
            except SyntaxError as e:
                print(f"  ✗ Syntax error in {py_file.relative_to(self.project_root)}: {e}")
                syntax_errors.append(str(py_file.relative_to(self.project_root)))
        
        if syntax_errors:
            self.errors.extend([f"Syntax error in: {file}" for file in syntax_errors])
            return False
        
        return True
    
    def validate_imports(self) -> bool:
        """Validate Python imports"""
        print("\nValidating Python imports...")
        
        import_errors = []
        
        # Try to import key modules
        modules_to_test = [
            ("src.presentation.parking_gui", "ParkingManagementApp"),
            ("src.application.parking_service", "ParkingService"),
            ("src.infrastructure.factories", "FactoryRegistry")
        ]
        
        for module_path, class_name in modules_to_test:
            try:
                # Dynamic import
                module = __import__(module_path, fromlist=[class_name])
                getattr(module, class_name)
                print(f"  ✓ Import OK: {module_path}.{class_name}")
            except ImportError as e:
                print(f"  ✗ Import failed: {module_path}.{class_name} - {e}")
                import_errors.append(f"{module_path}.{class_name}")
            except AttributeError as e:
                print(f"  ✗ Class not found: {module_path}.{class_name} - {e}")
                import_errors.append(f"{module_path}.{class_name}")
        
        if import_errors:
            self.warnings.extend([f"Import issue: {imp}" for imp in import_errors])
            return False
        
        return True
    
    def get_summary(self) -> Dict:
        """Get validation summary"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_files": self.missing_files,
            "valid_files_count": len(self.valid_files)
        }


# ============================================================================
# DOCUMENTATION GENERATOR
# ============================================================================

class DocumentationGenerator:
    """Generate submission documentation"""
    
    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = project_root
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_readme(self) -> Path:
        """Generate comprehensive README.md"""
        readme_path = self.output_dir / "README.md"
        
        # Get project information
        try:
            with open(self.project_root / "requirements.txt", 'r') as f:
                requirements = f.read().splitlines()
        except:
            requirements = ["Not available"]
        
        # Count files
        src_files = list(self.project_root.rglob("src/**/*.py"))
        test_files = list(self.project_root.rglob("tests/**/*.py"))
        
        readme_content = f"""# {SubmissionConfig.PROJECT_NAME}

## Project Overview

A comprehensive Parking Management System built with Python and Tkinter. This system provides a modern, feature-rich desktop application for managing parking operations with real-time monitoring, billing, and reporting capabilities.

### Key Features
- 🚗 Real-time parking lot visualization
- ⚡ EV charging station monitoring
- 💰 Automated billing and invoicing
- 📅 Reservation management system
- 📊 Advanced reporting and analytics
- 🔔 Real-time notifications and alerts
- 👤 User management and authentication
- 🎨 Modern, customizable GUI

## Project Information

- **Version:** {SubmissionConfig.PROJECT_VERSION}
- **Authors:** {', '.join(SubmissionConfig.AUTHORS)}
- **Company:** {SubmissionConfig.COMPANY}
- **License:** {SubmissionConfig.LICENSE}
- **Source Files:** {len(src_files)} Python files
- **Test Files:** {len(test_files)} test files

## System Architecture

The system follows a clean architecture with clear separation of concerns:
