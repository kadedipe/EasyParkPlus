"""Test data package for parking management system.

This package contains test data and fixtures for unit and integration tests.
The data includes reservations, recurring reservations, waitlist entries,
reservation history, notes, and addons as defined in the seed data file.

Test data version: 1.0.0
Generated: 2024-01-15
Total reservations: 100
Date range: 2023-10-01 to 2024-03-15
"""

"""Test data package for parking management system.

This package contains test data and fixtures for unit and integration tests.
"""

import json
import os
from pathlib import Path

# Get the path to the test data file
TEST_DATA_PATH = Path(__file__).parent / "seed_data.json"

def load_test_data():
    """Load the test data from the JSON file."""
    if TEST_DATA_PATH.exists():
        with open(TEST_DATA_PATH, 'r') as f:
            return json.load(f)
    return None

def get_reservations():
    """Get all test reservations."""
    data = load_test_data()
    return data.get('reservations', []) if data else []

def get_recurring_reservations():
    """Get all test recurring reservations."""
    data = load_test_data()
    return data.get('recurring_reservations', []) if data else []

# You can add similar helper functions for other data types like waitlist entries, reservation history, notes, and addons as needed.