"""Pytest configuration and fixtures for parking management system tests."""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Generator
import random

# Load the seed data
SEED_DATA_PATH = Path(__file__).parent / "seed_data.json"

@pytest.fixture(scope="session")
def seed_data() -> Dict[str, Any]:
    """Load and return the complete seed data."""
    with open(SEED_DATA_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture(scope="session")
def reservations(seed_data) -> List[Dict[str, Any]]:
    """Return all reservations from seed data."""
    return seed_data['reservations']

@pytest.fixture(scope="session")
def recurring_reservations(seed_data) -> List[Dict[str, Any]]:
    """Return all recurring reservations from seed data."""
    return seed_data['recurring_reservations']

@pytest.fixture(scope="session")
def waitlist_entries(seed_data) -> List[Dict[str, Any]]:
    """Return all waitlist entries from seed data."""
    return seed_data['waitlist']

@pytest.fixture(scope="session")
def reservation_history(seed_data) -> List[Dict[str, Any]]:
    """Return all reservation history entries from seed data."""
    return seed_data['reservation_history']

@pytest.fixture(scope="session")
def reservation_notes(seed_data) -> List[Dict[str, Any]]:
    """Return all reservation notes from seed data."""
    return seed_data['reservation_notes']

@pytest.fixture(scope="session")
def reservation_addons(seed_data) -> List[Dict[str, Any]]:
    """Return all reservation addons from seed data."""
    return seed_data['reservation_addons']

@pytest.fixture
def sample_reservation(reservations) -> Dict[str, Any]:
    """Return a single sample reservation."""
    return reservations[0]

@pytest.fixture
def sample_recurring_reservation(recurring_reservations) -> Dict[str, Any]:
    """Return a single sample recurring reservation."""
    return recurring_reservations[0]

@pytest.fixture
def sample_waitlist_entry(waitlist_entries) -> Dict[str, Any]:
    """Return a single sample waitlist entry."""
    return waitlist_entries[0]

# Filtered fixtures for specific statuses
@pytest.fixture
def completed_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all completed reservations."""
    return [r for r in reservations if r['status'] == 'completed']

@pytest.fixture
def confirmed_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all confirmed reservations."""
    return [r for r in reservations if r['status'] == 'confirmed']

@pytest.fixture
def checked_in_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all checked-in reservations."""
    return [r for r in reservations if r['status'] == 'checked_in']

@pytest.fixture
def cancelled_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all cancelled reservations."""
    return [r for r in reservations if r['status'] == 'cancelled']

@pytest.fixture
def no_show_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all no-show reservations."""
    return [r for r in reservations if r['status'] == 'no_show']

@pytest.fixture
def pending_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all pending reservations."""
    return [r for r in reservations if r['status'] == 'pending']

# Filtered fixtures for specific types
@pytest.fixture
def ev_charging_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all EV charging reservations."""
    return [r for r in reservations if r.get('reservation_type') == 'ev_charging']

@pytest.fixture
def vip_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all VIP reservations."""
    return [r for r in reservations if r.get('reservation_type') == 'vip']

@pytest.fixture
def oversize_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all oversize vehicle reservations."""
    return [r for r in reservations if r.get('reservation_type') == 'oversize']

@pytest.fixture
def standard_reservations(reservations) -> List[Dict[str, Any]]:
    """Return all standard reservations."""
    return [r for r in reservations if r.get('reservation_type') == 'standard']

# User-specific fixtures
@pytest.fixture
def user_reservations(reservations) -> Dict[int, List[Dict[str, Any]]]:
    """Return reservations grouped by user_id."""
    user_dict = {}
    for r in reservations:
        user_id = r['user_id']
        if user_id not in user_dict:
            user_dict[user_id] = []
        user_dict[user_id].append(r)
    return user_dict

@pytest.fixture
def spot_reservations(reservations) -> Dict[int, List[Dict[str, Any]]]:
    """Return reservations grouped by spot_id."""
    spot_dict = {}
    for r in reservations:
        spot_id = r['spot_id']
        if spot_id not in spot_dict:
            spot_dict[spot_id] = []
        spot_dict[spot_id].append(r)
    return spot_dict

# Date-based fixtures
@pytest.fixture
def reservations_by_date_range(reservations) -> Dict[str, List[Dict[str, Any]]]:
    """Return reservations grouped by date (YYYY-MM-DD)."""
    date_dict = {}
    for r in reservations:
        start_date = r['start_time'][:10]  # Extract YYYY-MM-DD
        if start_date not in date_dict:
            date_dict[start_date] = []
        date_dict[start_date].append(r)
    return date_dict

# Factory fixtures for creating test data
@pytest.fixture
def reservation_factory() -> Generator[Callable, None, None]:
    """Factory fixture for creating reservation objects for testing."""
    counter = 1000
    
    def _create_reservation(**kwargs):
        nonlocal counter
        counter += 1
        
        base_reservation = {
            'id': counter,
            'user_id': 1,
            'spot_id': 1,
            'vehicle_id': 101,
            'confirmation_code': f"CONF-TEST-{counter}",
            'reservation_type': 'standard',
            'status': 'confirmed',
            'start_time': datetime.now().isoformat() + 'Z',
            'end_time': (datetime.now() + timedelta(hours=4)).isoformat() + 'Z',
            'total_amount': 20.00,
            'payment_status': 'paid',
            'payment_id': None,
            'created_at': datetime.now().isoformat() + 'Z',
            'confirmed_at': datetime.now().isoformat() + 'Z',
            'metadata': {}
        }
        
        base_reservation.update(kwargs)
        return base_reservation
    
    return _create_reservation

@pytest.fixture
def waitlist_factory() -> Generator[Callable, None, None]:
    """Factory fixture for creating waitlist entries for testing."""
    counter = 100
    
    def _create_waitlist_entry(**kwargs):
        nonlocal counter
        counter += 1
        
        base_entry = {
            'id': counter,
            'user_id': 1,
            'spot_id': 18,
            'date_from': (datetime.now() + timedelta(days=1)).isoformat() + 'Z',
            'date_to': (datetime.now() + timedelta(days=1, hours=4)).isoformat() + 'Z',
            'status': 'active',
            'position': 1,
            'created_at': datetime.now().isoformat() + 'Z'
        }
        
        base_entry.update(kwargs)
        return base_entry
    
    return _create_waitlist_entry

# Database session fixture (mock)
@pytest.fixture
def db_session():
    """Provide a mock database session for testing."""
    class MockSession:
        def __init__(self):
            self.added = []
            self.committed = False
            self.rolled_back = False
        
        def add(self, obj):
            self.added.append(obj)
        
        def add_all(self, objs):
            self.added.extend(objs)
        
        def commit(self):
            self.committed = True
        
        def rollback(self):
            self.rolled_back = True
        
        def query(self, model):
            return MockQuery(self, model)
        
        def close(self):
            pass
    
    class MockQuery:
        def __init__(self, session, model):
            self.session = session
            self.model = model
            self.filters = []
        
        def filter(self, condition):
            return self
        
        def filter_by(self, **kwargs):
            return self
        
        def all(self):
            return []
        
        def first(self):
            return None
        
        def get(self, id):
            return None
        
        def count(self):
            return 0
    
    session = MockSession()
    yield session
    session.close()

# API client fixture (mock)
@pytest.fixture
def api_client():
    """Provide a mock API client for testing."""
    class MockAPIClient:
        def __init__(self):
            self.requests = []
            self.base_url = "http://test-server/api"
        
        def get(self, endpoint, params=None):
            self.requests.append(('GET', endpoint, params))
            return MockResponse(200, {"message": "Success"})
        
        def post(self, endpoint, data=None):
            self.requests.append(('POST', endpoint, data))
            return MockResponse(201, {"message": "Created"})
        
        def put(self, endpoint, data=None):
            self.requests.append(('PUT', endpoint, data))
            return MockResponse(200, {"message": "Updated"})
        
        def delete(self, endpoint):
            self.requests.append(('DELETE', endpoint, None))
            return MockResponse(204, None)
    
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
        
        def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP Error: {self.status_code}")
    
    return MockAPIClient()

# Metadata fixtures
@pytest.fixture
def seed_data_metadata(seed_data) -> Dict[str, Any]:
    """Return the metadata section of the seed data."""
    return seed_data['metadata']

@pytest.fixture
def status_distribution(seed_data) -> Dict[str, int]:
    """Return the status distribution from the seed data metadata."""
    return seed_data['metadata']['status_distribution']

# Parametrized fixtures for testing different scenarios
@pytest.fixture(params=['standard', 'vip', 'ev_charging', 'oversize'])
def reservation_type(request) -> str:
    """Parametrized fixture for testing different reservation types."""
    return request.param

@pytest.fixture(params=['confirmed', 'checked_in', 'completed', 'cancelled', 'no_show', 'pending'])
def reservation_status(request) -> str:
    """Parametrized fixture for testing different reservation statuses."""
    return request.param

# Helper function fixtures
@pytest.fixture
def calculate_reservation_cost() -> Callable:
    """Fixture providing a function to calculate reservation costs."""
    def _calculate(spot_type: str, hours: int, has_ev: bool = False, is_vip: bool = False) -> float:
        base_rates = {
            'standard': 3.00,
            'oversize': 5.00,
            'ev_charging': 3.00,
            'vip': 8.00
        }
        
        rate = base_rates.get(spot_type, 3.00)
        cost = rate * hours
        
        if has_ev and spot_type == 'ev_charging':
            cost += 0.25 * hours  # EV charging fee
        
        if is_vip:
            cost *= 1.5  # VIP premium
        
        return cost
    
    return _calculate

@pytest.fixture
def validate_reservation_timeline() -> Callable:
    """Fixture providing a function to validate reservation timeline logic."""
    def _validate(reservation: Dict[str, Any]) -> Dict[str, bool]:
        timeline = {
            'has_valid_dates': True,
            'has_valid_status_flow': True,
            'has_consistent_timestamps': True
        }
        
        # Check date logic
        if reservation['start_time'] >= reservation['end_time']:
            timeline['has_valid_dates'] = False
        
        # Check status flow based on timestamps
        status = reservation['status']
        timestamps = {
            'created': reservation.get('created_at'),
            'confirmed': reservation.get('confirmed_at'),
            'checked_in': reservation.get('checked_in_at'),
            'checked_out': reservation.get('checked_out_at'),
            'completed': reservation.get('completed_at'),
            'cancelled': reservation.get('cancelled_at')
        }
        
        # Add more validation logic here
        
        return timeline
    
    return _validate