#!/usr/bin/env python3
"""
Integration Test Setup Script

This script sets up the environment for running integration tests.
It checks dependencies, creates necessary directories, and prepares
test data.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check for required dependencies"""
    print("Checking dependencies...")
    
    dependencies = [
        ("Python", "python3", "--version"),
        ("pip", "pip3", "--version"),
        ("Tkinter", "python3", "-c \"import tkinter; print('Tkinter available')\""),
    ]
    
    missing = []
    
    for name, command, check in dependencies:
        try:
            result = subprocess.run(
                [command] + check.split()[1:],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name}")
                missing.append(name)
        except (subprocess.SubprocessError, FileNotFoundError):
            print(f"  ✗ {name}")
            missing.append(name)
    
    return missing

def create_test_directories():
    """Create directories for test reports and data"""
    print("\nCreating test directories...")
    
    directories = [
        "test_reports/integration",
        "test_data",
        "test_logs"
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")

def install_test_dependencies():
    """Install test-specific dependencies"""
    print("\nInstalling test dependencies...")
    
    requirements_files = [
        "requirements.txt",
        "requirements-test.txt"
    ]
    
    for req_file in requirements_files:
        if Path(req_file).exists():
            try:
                subprocess.run(
                    ["pip3", "install", "-r", req_file],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"  ✓ Installed from {req_file}")
            except subprocess.CalledProcessError as e:
                print(f"  ✗ Failed to install from {req_file}: {e}")
        else:
            print(f"  ⚠ {req_file} not found")

def generate_test_data():
    """Generate sample test data"""
    print("\nGenerating test data...")
    
    test_data_dir = Path("test_data")
    
    # Sample parking lots data
    parking_lots = [
        {
            "id": "lot-001",
            "name": "Downtown Center",
            "code": "DTC001",
            "address": "123 Main St",
            "total_slots": 100,
            "available_slots": 45,
            "hourly_rate": 5.0
        },
        {
            "id": "lot-002",
            "name": "Airport Parking",
            "code": "AIR002",
            "address": "456 Airport Rd",
            "total_slots": 200,
            "available_slots": 120,
            "hourly_rate": 8.0
        }
    ]
    
    import json
    with open(test_data_dir / "parking_lots.json", "w") as f:
        json.dump(parking_lots, f, indent=2)
    print("  ✓ parking_lots.json")
    
    # Sample test configuration
    test_config = {
        "database": {
            "test_path": "test_data/test_parking.db",
            "backup_path": "test_data/backup.db"
        },
        "performance": {
            "timeout_seconds": 30,
            "retry_attempts": 3
        },
        "reporting": {
            "generate_html": True,
            "generate_json": True
        }
    }
    
    with open(test_data_dir / "test_config.json", "w") as f:
        json.dump(test_config, f, indent=2)
    print("  ✓ test_config.json")

def setup_test_environment():
    """Set up complete test environment"""
    print("=" * 60)
    print("Integration Test Environment Setup")
    print("=" * 60)
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Please install missing dependencies before running tests.")
        return False
    
    # Create directories
    create_test_directories()
    
    # Install dependencies
    install_test_dependencies()
    
    # Generate test data
    generate_test_data()
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run critical tests: python -m tests.integration.test_runner --critical-only")
    print("2. Run all tests: python -m tests.integration.test_runner")
    print("3. View reports in: test_reports/integration/")
    print("\nFor help: python -m tests.integration.test_runner --help")
    
    return True

if __name__ == "__main__":
    success = setup_test_environment()
    sys.exit(0 if success else 1)