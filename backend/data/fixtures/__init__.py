"""
Fixtures package initialization.
Provides utilities for loading and managing test data fixtures.
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, date, time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Base directory for fixtures
FIXTURES_DIR = Path(__file__).parent

# Available fixtures
FIXTURE_FILES = {
    'users': 'users.json',
    'vehicles': 'vehicles.json',
    'parking_spots': 'parking_spots.json',
    'reservations': 'reservations.json',
    'payments': 'payments.json',
    'notifications': 'notifications.json',
    'reviews': 'reviews.json',
    'waitlist': 'waitlist.json',
    'maintenance': 'maintenance.json',
    'price_rules': 'price_rules.json',
    'discounts': 'discounts.json',
    'loyalty_programs': 'loyalty_programs.json',
    'audit_logs': 'audit_logs.json',
}

# Fixture dependencies (order matters for loading)
FIXTURE_DEPENDENCIES = {
    'users': [],
    'vehicles': ['users'],
    'parking_spots': [],
    'reservations': ['users', 'vehicles', 'parking_spots'],
    'payments': ['users', 'reservations'],
    'notifications': ['users'],
    'reviews': ['users', 'reservations'],
    'waitlist': ['users', 'parking_spots'],
    'maintenance': ['parking_spots', 'users'],
    'price_rules': [],
    'discounts': [],
    'loyalty_programs': ['users'],
    'audit_logs': ['users'],
}


def load_fixture(fixture_name: str) -> List[Dict[str, Any]]:
    """
    Load a specific fixture file.
    
    Args:
        fixture_name: Name of the fixture (key from FIXTURE_FILES)
        
    Returns:
        List of fixture records
        
    Raises:
        FileNotFoundError: If fixture file doesn't exist
        json.JSONDecodeError: If fixture file is invalid JSON
    """
    if fixture_name not in FIXTURE_FILES:
        raise ValueError(f"Unknown fixture: {fixture_name}")
    
    fixture_path = FIXTURES_DIR / FIXTURE_FILES[fixture_name]
    
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")
    
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.debug(f"Loaded {len(data)} records from {fixture_name}")
    return data


def load_all_fixtures() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all fixture files.
    
    Returns:
        Dictionary mapping fixture names to their data
    """
    fixtures = {}
    for name in FIXTURE_FILES:
        try:
            fixtures[name] = load_fixture(name)
        except Exception as e:
            logger.error(f"Failed to load fixture {name}: {e}")
            fixtures[name] = []
    
    return fixtures


def get_fixture_path(fixture_name: str) -> Path:
    """
    Get the full path to a fixture file.
    
    Args:
        fixture_name: Name of the fixture
        
    Returns:
        Path object for the fixture file
    """
    return FIXTURES_DIR / FIXTURE_FILES[fixture_name]


def validate_fixture(fixture_name: str, data: List[Dict[str, Any]]) -> bool:
    """
    Validate fixture data structure.
    
    Args:
        fixture_name: Name of the fixture
        data: Fixture data to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Basic validation - check if it's a list
    if not isinstance(data, list):
        logger.error(f"Fixture {fixture_name} must be a list")
        return False
    
    # Check if list is not empty
    if not data:
        logger.warning(f"Fixture {fixture_name} is empty")
    
    return True


def save_fixture(fixture_name: str, data: List[Dict[str, Any]], indent: int = 2) -> bool:
    """
    Save data to a fixture file.
    
    Args:
        fixture_name: Name of the fixture
        data: Data to save
        indent: JSON indent level
        
    Returns:
        True if successful, False otherwise
    """
    if not validate_fixture(fixture_name, data):
        return False
    
    fixture_path = get_fixture_path(fixture_name)
    
    try:
        with open(fixture_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.info(f"Saved {len(data)} records to {fixture_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save fixture {fixture_name}: {e}")
        return False


def clear_fixture(fixture_name: str) -> bool:
    """
    Clear a fixture file (write empty list).
    
    Args:
        fixture_name: Name of the fixture
        
    Returns:
        True if successful, False otherwise
    """
    return save_fixture(fixture_name, [])


def get_fixture_dependencies(fixture_name: str) -> List[str]:
    """
    Get dependencies for a fixture.
    
    Args:
        fixture_name: Name of the fixture
        
    Returns:
        List of dependent fixture names
    """
    return FIXTURE_DEPENDENCIES.get(fixture_name, [])


def get_loading_order() -> List[str]:
    """
    Get fixtures in correct loading order based on dependencies.
    
    Returns:
        List of fixture names in dependency order
    """
    from collections import deque
    
    # Build dependency graph
    graph = {name: set(get_fixture_dependencies(name)) for name in FIXTURE_FILES}
    
    # Topological sort
    result = []
    visited = set()
    temp_visited = set()
    
    def dfs(node):
        if node in temp_visited:
            raise ValueError(f"Circular dependency detected involving {node}")
        if node in visited:
            return
        
        temp_visited.add(node)
        
        for dep in graph[node]:
            dfs(dep)
        
        temp_visited.remove(node)
        visited.add(node)
        result.append(node)
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return result


def export_fixtures_to_sql(output_file: Optional[Path] = None) -> str:
    """
    Export fixtures as SQL INSERT statements.
    
    Args:
        output_file: Optional file to write SQL to
        
    Returns:
        SQL string if output_file is None
    """
    fixtures = load_all_fixtures()
    sql_lines = []
    
    for fixture_name, records in fixtures.items():
        if not records:
            continue
        
        # Determine table name (singularize and convert to snake_case)
        table_name = fixture_name.rstrip('s')
        
        for record in records:
            columns = []
            values = []
            
            for key, value in record.items():
                columns.append(f'"{key}"')
                
                if value is None:
                    values.append('NULL')
                elif isinstance(value, bool):
                    values.append('TRUE' if value else 'FALSE')
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, (datetime, date)):
                    values.append(f"'{value.isoformat()}'")
                else:
                    # Escape single quotes
                    escaped = str(value).replace("'", "''")
                    values.append(f"'{escaped}'")
            
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
            sql_lines.append(sql)
    
    sql = '\n'.join(sql_lines)
    
    if output_file:
        output_file.write_text(sql, encoding='utf-8')
        logger.info(f"Exported SQL to {output_file}")
    else:
        return sql


def import_from_csv(fixture_name: str, csv_path: Path) -> bool:
    """
    Import fixture data from CSV file.
    
    Args:
        fixture_name: Name of the fixture
        csv_path: Path to CSV file
        
    Returns:
        True if successful, False otherwise
    """
    import csv
    
    try:
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string values to appropriate types
                processed_row = {}
                for key, value in row.items():
                    if value.lower() == 'null':
                        processed_row[key] = None
                    elif value.lower() == 'true':
                        processed_row[key] = True
                    elif value.lower() == 'false':
                        processed_row[key] = False
                    elif value.isdigit():
                        processed_row[key] = int(value)
                    else:
                        try:
                            processed_row[key] = float(value)
                        except ValueError:
                            processed_row[key] = value
                data.append(processed_row)
        
        return save_fixture(fixture_name, data)
    except Exception as e:
        logger.error(f"Failed to import CSV for {fixture_name}: {e}")
        return False


def export_to_csv(fixture_name: str, csv_path: Path) -> bool:
    """
    Export fixture data to CSV file.
    
    Args:
        fixture_name: Name of the fixture
        csv_path: Path to output CSV file
        
    Returns:
        True if successful, False otherwise
    """
    import csv
    
    data = load_fixture(fixture_name)
    if not data:
        logger.warning(f"No data to export for {fixture_name}")
        return False
    
    try:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        
        logger.info(f"Exported {len(data)} records to {csv_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export CSV for {fixture_name}: {e}")
        return False


__all__ = [
    'FIXTURE_FILES',
    'FIXTURE_DEPENDENCIES',
    'load_fixture',
    'load_all_fixtures',
    'get_fixture_path',
    'validate_fixture',
    'save_fixture',
    'clear_fixture',
    'get_fixture_dependencies',
    'get_loading_order',
    'export_fixtures_to_sql',
    'import_from_csv',
    'export_to_csv',
]