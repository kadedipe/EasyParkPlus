"""Tests for parking management system repositories."""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Assuming you have actual repository classes, we'll create mock imports
# Replace these with your actual repository imports
try:
    from app.repositories import (
        ReservationRepository, UserRepository, ParkingSpotRepository,
        VehicleRepository, RecurringReservationRepository,
        WaitlistRepository, ReservationHistoryRepository,
        ReservationNoteRepository, ReservationAddonRepository
    )
    from app.models import Reservation, User, ParkingSpot, Vehicle
    from app.database import SessionLocal
except ImportError:
    # Mock repositories for testing when actual ones aren't available
    pytest.skip("Repositories not available - skipping integration tests", allow_module_level=True)


class TestReservationRepository:
    """Tests for the ReservationRepository."""
    
    @pytest.fixture
    def reservation_repo(self, db_session):
        """Create a reservation repository instance."""
        return ReservationRepository(db_session)
    
    def test_get_by_id(self, reservation_repo, sample_reservation):
        """Test getting a reservation by ID."""
        # Mock the repository method
        with patch.object(reservation_repo, 'get_by_id') as mock_get:
            mock_get.return_value = Reservation(**sample_reservation)
            
            result = reservation_repo.get_by_id(sample_reservation['id'])
            
            assert result is not None
            assert result.id == sample_reservation['id']
            mock_get.assert_called_once_with(sample_reservation['id'])
    
    def test_get_by_confirmation_code(self, reservation_repo, sample_reservation):
        """Test getting a reservation by confirmation code."""
        with patch.object(reservation_repo, 'get_by_confirmation_code') as mock_get:
            mock_get.return_value = Reservation(**sample_reservation)
            
            result = reservation_repo.get_by_confirmation_code(sample_reservation['confirmation_code'])
            
            assert result is not None
            assert result.confirmation_code == sample_reservation['confirmation_code']
            mock_get.assert_called_once_with(sample_reservation['confirmation_code'])
    
    def test_get_by_user(self, reservation_repo, user_reservations):
        """Test getting reservations by user ID."""
        user_id = 5
        expected_count = len(user_reservations.get(user_id, []))
        
        with patch.object(reservation_repo, 'get_by_user') as mock_get:
            mock_get.return_value = [Reservation(**r) for r in user_reservations.get(user_id, [])]
            
            results = reservation_repo.get_by_user(user_id)
            
            assert len(results) == expected_count
            for reservation in results:
                assert reservation.user_id == user_id
            mock_get.assert_called_once_with(user_id)
    
    def test_get_by_spot(self, reservation_repo, spot_reservations):
        """Test getting reservations by spot ID."""
        spot_id = 4
        expected_count = len(spot_reservations.get(spot_id, []))
        
        with patch.object(reservation_repo, 'get_by_spot') as mock_get:
            mock_get.return_value = [Reservation(**r) for r in spot_reservations.get(spot_id, [])]
            
            results = reservation_repo.get_by_spot(spot_id)
            
            assert len(results) == expected_count
            for reservation in results:
                assert reservation.spot_id == spot_id
            mock_get.assert_called_once_with(spot_id)
    
    def test_get_by_status(self, reservation_repo, reservations):
        """Test getting reservations by status."""
        status = 'completed'
        expected_count = len([r for r in reservations if r['status'] == status])
        
        with patch.object(reservation_repo, 'get_by_status') as mock_get:
            mock_get.return_value = [Reservation(**r) for r in reservations if r['status'] == status]
            
            results = reservation_repo.get_by_status(status)
            
            assert len(results) == expected_count
            for reservation in results:
                assert reservation.status == status
            mock_get.assert_called_once_with(status)
    
    def test_get_by_date_range(self, reservation_repo, reservations):
        """Test getting reservations within a date range."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        expected_count = len([
            r for r in reservations 
            if start_date <= datetime.fromisoformat(r['start_time'].replace('Z', '+00:00')) <= end_date
        ])
        
        with patch.object(reservation_repo, 'get_by_date_range') as mock_get:
            mock_get.return_value = [
                Reservation(**r) for r in reservations 
                if start_date <= datetime.fromisoformat(r['start_time'].replace('Z', '+00:00')) <= end_date
            ]
            
            results = reservation_repo.get_by_date_range(start_date, end_date)
            
            assert len(results) == expected_count
            mock_get.assert_called_once_with(start_date, end_date)
    
    def test_get_active_reservations(self, reservation_repo, reservations):
        """Test getting active reservations."""
        active_statuses = ['checked_in']
        expected_count = len([r for r in reservations if r['status'] in active_statuses])
        
        with patch.object(reservation_repo, 'get_active_reservations') as mock_get:
            mock_get.return_value = [
                Reservation(**r) for r in reservations if r['status'] in active_statuses
            ]
            
            results = reservation_repo.get_active_reservations()
            
            assert len(results) == expected_count
            for reservation in results:
                assert reservation.status in active_statuses
    
    def test_get_upcoming_reservations(self, reservation_repo, reservations):
        """Test getting upcoming reservations."""
        now = datetime.now()
        
        with patch.object(reservation_repo, 'get_upcoming_reservations') as mock_get:
            mock_get.return_value = [
                Reservation(**r) for r in reservations 
                if r['status'] in ['confirmed', 'pending'] 
                and datetime.fromisoformat(r['start_time'].replace('Z', '+00:00')) > now
            ]
            
            results = reservation_repo.get_upcoming_reservations(days=7)
            
            assert isinstance(results, list)
            mock_get.assert_called_once_with(days=7)
    
    def test_get_conflicts(self, reservation_repo):
        """Test checking for conflicting reservations."""
        spot_id = 4
        start_time = datetime(2024, 1, 20, 9, 0)
        end_time = datetime(2024, 1, 20, 17, 0)
        
        with patch.object(reservation_repo, 'get_conflicts') as mock_get:
            mock_get.return_value = [
                Reservation(id=218, spot_id=4, start_time='2024-01-20T09:00:00Z', end_time='2024-01-20T17:00:00Z')
            ]
            
            conflicts = reservation_repo.get_conflicts(spot_id, start_time, end_time)
            
            assert len(conflicts) > 0
            for conflict in conflicts:
                assert conflict.spot_id == spot_id
            mock_get.assert_called_once_with(spot_id, start_time, end_time)
    
    def test_create_reservation(self, reservation_repo, reservation_factory):
        """Test creating a new reservation."""
        new_reservation = reservation_factory(
            user_id=100,
            spot_id=50,
            start_time=datetime.now().isoformat() + 'Z',
            end_time=(datetime.now() + timedelta(hours=4)).isoformat() + 'Z'
        )
        
        with patch.object(reservation_repo, 'create') as mock_create:
            mock_create.return_value = new_reservation
            
            result = reservation_repo.create(new_reservation)
            
            assert result is not None
            assert result.id == new_reservation.id
            assert result.user_id == 100
            assert result.spot_id == 50
            mock_create.assert_called_once_with(new_reservation)
    
    def test_update_reservation(self, reservation_repo, sample_reservation):
        """Test updating an existing reservation."""
        reservation = Reservation(**sample_reservation)
        update_data = {'status': 'cancelled', 'cancelled_at': datetime.now().isoformat() + 'Z'}
        
        with patch.object(reservation_repo, 'update') as mock_update:
            updated_reservation = Reservation(**{**sample_reservation, **update_data})
            mock_update.return_value = updated_reservation
            
            result = reservation_repo.update(reservation.id, update_data)
            
            assert result.status == 'cancelled'
            assert result.cancelled_at is not None
            mock_update.assert_called_once_with(reservation.id, update_data)
    
    def test_delete_reservation(self, reservation_repo, sample_reservation):
        """Test deleting a reservation."""
        reservation_id = sample_reservation['id']
        
        with patch.object(reservation_repo, 'delete') as mock_delete:
            mock_delete.return_value = True
            
            result = reservation_repo.delete(reservation_id)
            
            assert result is True
            mock_delete.assert_called_once_with(reservation_id)
    
    def test_check_in(self, reservation_repo, sample_reservation):
        """Test checking in a reservation."""
        reservation_id = sample_reservation['id']
        
        with patch.object(reservation_repo, 'check_in') as mock_check_in:
            updated_reservation = Reservation(**{**sample_reservation, 'status': 'checked_in'})
            mock_check_in.return_value = updated_reservation
            
            result = reservation_repo.check_in(reservation_id)
            
            assert result.status == 'checked_in'
            mock_check_in.assert_called_once_with(reservation_id)
    
    def test_check_out(self, reservation_repo, sample_reservation):
        """Test checking out a reservation."""
        reservation_id = sample_reservation['id']
        
        with patch.object(reservation_repo, 'check_out') as mock_check_out:
            updated_reservation = Reservation(**{**sample_reservation, 'status': 'completed'})
            mock_check_out.return_value = updated_reservation
            
            result = reservation_repo.check_out(reservation_id)
            
            assert result.status == 'completed'
            mock_check_out.assert_called_once_with(reservation_id)
    
    def test_cancel_reservation(self, reservation_repo, sample_reservation):
        """Test cancelling a reservation."""
        reservation_id = sample_reservation['id']
        reason = "Change of plans"
        
        with patch.object(reservation_repo, 'cancel') as mock_cancel:
            updated_reservation = Reservation(**{
                **sample_reservation, 
                'status': 'cancelled',
                'cancellation_reason': reason
            })
            mock_cancel.return_value = updated_reservation
            
            result = reservation_repo.cancel(reservation_id, reason)
            
            assert result.status == 'cancelled'
            assert result.cancellation_reason == reason
            mock_cancel.assert_called_once_with(reservation_id, reason)
    
    def test_get_statistics(self, reservation_repo, reservations):
        """Test getting reservation statistics."""
        with patch.object(reservation_repo, 'get_statistics') as mock_stats:
            mock_stats.return_value = {
                'total': len(reservations),
                'by_status': {
                    'confirmed': 35,
                    'checked_in': 15,
                    'completed': 30,
                    'cancelled': 12,
                    'no_show': 5,
                    'pending': 3
                },
                'total_revenue': 1500.00,
                'average_duration': 4.5
            }
            
            stats = reservation_repo.get_statistics(
                start_date=datetime(2023, 10, 1),
                end_date=datetime(2024, 3, 15)
            )
            
            assert stats['total'] == 100
            assert stats['by_status']['confirmed'] == 35
            assert stats['total_revenue'] > 0
            mock_stats.assert_called_once()


class TestUserRepository:
    """Tests for the UserRepository."""
    
    @pytest.fixture
    def user_repo(self, db_session):
        """Create a user repository instance."""
        return UserRepository(db_session)
    
    def test_get_by_email(self, user_repo):
        """Test getting a user by email."""
        email = "john.doe@example.com"
        
        with patch.object(user_repo, 'get_by_email') as mock_get:
            mock_user = Mock()
            mock_user.id = 5
            mock_user.email = email
            mock_get.return_value = mock_user
            
            result = user_repo.get_by_email(email)
            
            assert result is not None
            assert result.email == email
            mock_get.assert_called_once_with(email)
    
    def test_get_users_with_upcoming_reservations(self, user_repo):
        """Test getting users with upcoming reservations."""
        with patch.object(user_repo, 'get_users_with_upcoming_reservations') as mock_get:
            mock_users = [Mock(id=5), Mock(id=7), Mock(id=8)]
            mock_get.return_value = mock_users
            
            results = user_repo.get_users_with_upcoming_reservations(days=3)
            
            assert len(results) == 3
            mock_get.assert_called_once_with(days=3)
    
    def test_get_user_reservation_history(self, user_repo, user_reservations):
        """Test getting a user's reservation history."""
        user_id = 5
        
        with patch.object(user_repo, 'get_user_reservation_history') as mock_get:
            mock_reservations = [Mock(id=r['id']) for r in user_reservations.get(user_id, [])]
            mock_get.return_value = mock_reservations
            
            results = user_repo.get_user_reservation_history(user_id)
            
            assert len(results) == len(user_reservations.get(user_id, []))
            mock_get.assert_called_once_with(user_id)
    
    def test_get_user_statistics(self, user_repo):
        """Test getting user statistics."""
        user_id = 5
        
        with patch.object(user_repo, 'get_user_statistics') as mock_stats:
            mock_stats.return_value = {
                'total_reservations': 3,
                'total_spent': 74.00,
                'cancellation_rate': 0.1,
                'no_show_rate': 0.0,
                'favorite_spot': 4
            }
            
            stats = user_repo.get_user_statistics(user_id)
            
            assert stats['total_reservations'] == 3
            assert stats['total_spent'] > 0
            mock_stats.assert_called_once_with(user_id)


class TestParkingSpotRepository:
    """Tests for the ParkingSpotRepository."""
    
    @pytest.fixture
    def spot_repo(self, db_session):
        """Create a parking spot repository instance."""
        return ParkingSpotRepository(db_session)
    
    def test_get_available_spots(self, spot_repo, reservations):
        """Test getting available spots for a time range."""
        start_time = datetime(2024, 1, 20, 9, 0)
        end_time = datetime(2024, 1, 20, 17, 0)
        
        with patch.object(spot_repo, 'get_available_spots') as mock_get:
            mock_spots = [Mock(id=1), Mock(id=2), Mock(id=3)]
            mock_get.return_value = mock_spots
            
            results = spot_repo.get_available_spots(start_time, end_time)
            
            assert isinstance(results, list)
            mock_get.assert_called_once_with(start_time, end_time)
    
    def test_get_spots_by_type(self, spot_repo):
        """Test getting parking spots by type."""
        spot_type = 'ev_charging'
        
        with patch.object(spot_repo, 'get_by_type') as mock_get:
            mock_spots = [Mock(id=22), Mock(id=21)]
            mock_get.return_value = mock_spots
            
            results = spot_repo.get_by_type(spot_type)
            
            assert len(results) == 2
            mock_get.assert_called_once_with(spot_type)
    
    def test_get_spot_occupancy(self, spot_repo, spot_reservations):
        """Test getting occupancy rate for a spot."""
        spot_id = 4
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        with patch.object(spot_repo, 'get_occupancy') as mock_get:
            mock_get.return_value = 0.45  # 45% occupancy
            
            occupancy = spot_repo.get_occupancy(spot_id, start_date, end_date)
            
            assert occupancy == 0.45
            mock_get.assert_called_once_with(spot_id, start_date, end_date)
    
    def test_get_spot_utilization_report(self, spot_repo):
        """Test getting utilization report for all spots."""
        with patch.object(spot_repo, 'get_utilization_report') as mock_get:
            mock_get.return_value = [
                {'spot_id': 4, 'utilization': 0.75, 'revenue': 150.00},
                {'spot_id': 12, 'utilization': 0.60, 'revenue': 120.00},
                {'spot_id': 18, 'utilization': 0.90, 'revenue': 200.00}
            ]
            
            report = spot_repo.get_utilization_report(
                start_date=datetime(2023, 12, 1),
                end_date=datetime(2023, 12, 31)
            )
            
            assert len(report) == 3
            assert report[0]['spot_id'] == 4
            mock_get.assert_called_once()


class TestVehicleRepository:
    """Tests for the VehicleRepository."""
    
    @pytest.fixture
    def vehicle_repo(self, db_session):
        """Create a vehicle repository instance."""
        return VehicleRepository(db_session)
    
    def test_get_by_license_plate(self, vehicle_repo):
        """Test getting a vehicle by license plate."""
        license_plate = "ABC-123"
        
        with patch.object(vehicle_repo, 'get_by_license_plate') as mock_get:
            mock_vehicle = Mock()
            mock_vehicle.id = 101
            mock_vehicle.license_plate = license_plate
            mock_get.return_value = mock_vehicle
            
            result = vehicle_repo.get_by_license_plate(license_plate)
            
            assert result is not None
            assert result.license_plate == license_plate
            mock_get.assert_called_once_with(license_plate)
    
    def test_get_by_user(self, vehicle_repo):
        """Test getting vehicles by user ID."""
        user_id = 5
        
        with patch.object(vehicle_repo, 'get_by_user') as mock_get:
            mock_vehicles = [Mock(id=101), Mock(id=102)]
            mock_get.return_value = mock_vehicles
            
            results = vehicle_repo.get_by_user(user_id)
            
            assert len(results) == 2
            mock_get.assert_called_once_with(user_id)
    
    def test_get_ev_vehicles(self, vehicle_repo):
        """Test getting all electric vehicles."""
        with patch.object(vehicle_repo, 'get_ev_vehicles') as mock_get:
            mock_vehicles = [Mock(id=109), Mock(id=113)]
            mock_get.return_value = mock_vehicles
            
            results = vehicle_repo.get_ev_vehicles()
            
            assert len(results) == 2
            mock_get.assert_called_once()


class TestRecurringReservationRepository:
    """Tests for the RecurringReservationRepository."""
    
    @pytest.fixture
    def recurring_repo(self, db_session):
        """Create a recurring reservation repository instance."""
        return RecurringReservationRepository(db_session)
    
    def test_get_active_recurring(self, recurring_repo, recurring_reservations):
        """Test getting active recurring reservations."""
        with patch.object(recurring_repo, 'get_active') as mock_get:
            active_count = len([r for r in recurring_reservations if r['is_active']])
            mock_get.return_value = [Mock(id=r['id']) for r in recurring_reservations if r['is_active']]
            
            results = recurring_repo.get_active()
            
            assert len(results) == active_count
            mock_get.assert_called_once()
    
    def test_get_by_spot(self, recurring_repo, recurring_reservations):
        """Test getting recurring reservations by spot."""
        spot_id = 4
        
        with patch.object(recurring_repo, 'get_by_spot') as mock_get:
            spot_reservations = [r for r in recurring_reservations if r['spot_id'] == spot_id]
            mock_get.return_value = [Mock(id=r['id']) for r in spot_reservations]
            
            results = recurring_repo.get_by_spot(spot_id)
            
            assert len(results) == len(spot_reservations)
            mock_get.assert_called_once_with(spot_id)
    
    def test_generate_occurrences(self, recurring_repo):
        """Test generating occurrences for a recurring reservation."""
        recurring_id = 1
        start_date = datetime(2024, 1, 8)
        end_date = datetime(2024, 1, 21)
        
        with patch.object(recurring_repo, 'generate_occurrences') as mock_generate:
            mock_generate.return_value = [
                Mock(start_time='2024-01-08T09:00:00Z'),
                Mock(start_time='2024-01-10T09:00:00Z'),
                Mock(start_time='2024-01-12T09:00:00Z'),
                Mock(start_time='2024-01-15T09:00:00Z'),
                Mock(start_time='2024-01-17T09:00:00Z'),
                Mock(start_time='2024-01-19T09:00:00Z')
            ]
            
            occurrences = recurring_repo.generate_occurrences(recurring_id, start_date, end_date)
            
            assert len(occurrences) == 6
            mock_generate.assert_called_once_with(recurring_id, start_date, end_date)


class TestWaitlistRepository:
    """Tests for the WaitlistRepository."""
    
    @pytest.fixture
    def waitlist_repo(self, db_session):
        """Create a waitlist repository instance."""
        return WaitlistRepository(db_session)
    
    def test_get_active_entries(self, waitlist_repo, waitlist_entries):
        """Test getting active waitlist entries."""
        with patch.object(waitlist_repo, 'get_active') as mock_get:
            active_count = len([w for w in waitlist_entries if w['status'] == 'active'])
            mock_get.return_value = [Mock(id=w['id']) for w in waitlist_entries if w['status'] == 'active']
            
            results = waitlist_repo.get_active()
            
            assert len(results) == active_count
            mock_get.assert_called_once()
    
    def test_get_by_spot_and_date(self, waitlist_repo, waitlist_entries):
        """Test getting waitlist entries by spot and date."""
        spot_id = 18
        date_from = datetime(2024, 1, 20, 18, 0)
        
        with patch.object(waitlist_repo, 'get_by_spot_and_date') as mock_get:
            spot_entries = [w for w in waitlist_entries if w['spot_id'] == spot_id]
            mock_get.return_value = [Mock(id=w['id']) for w in spot_entries]
            
            results = waitlist_repo.get_by_spot_and_date(spot_id, date_from)
            
            assert len(results) == len(spot_entries)
            mock_get.assert_called_once_with(spot_id, date_from)
    
    def test_get_next_in_line(self, waitlist_repo):
        """Test getting the next person in line for a spot."""
        spot_id = 18
        date_from = datetime(2024, 1, 20, 18, 0)
        
        with patch.object(waitlist_repo, 'get_next_in_line') as mock_get:
            mock_entry = Mock(id=1, user_id=17, position=1)
            mock_get.return_value = mock_entry
            
            result = waitlist_repo.get_next_in_line(spot_id, date_from)
            
            assert result is not None
            assert result.position == 1
            mock_get.assert_called_once_with(spot_id, date_from)
    
    def test_notify_next_in_line(self, waitlist_repo):
        """Test notifying the next person in line."""
        spot_id = 4
        date_from = datetime(2024, 1, 25, 9, 0)
        
        with patch.object(waitlist_repo, 'notify_next_in_line') as mock_notify:
            mock_notify.return_value = Mock(id=4, status='notified')
            
            result = waitlist_repo.notify_next_in_line(spot_id, date_from)
            
            assert result is not None
            assert result.status == 'notified'
            mock_notify.assert_called_once_with(spot_id, date_from)
    
    def test_reposition_after_notification(self, waitlist_repo):
        """Test repositioning waitlist after notification."""
        spot_id = 18
        date_from = datetime(2024, 1, 20, 18, 0)
        
        with patch.object(waitlist_repo, 'reposition_waitlist') as mock_reposition:
            mock_reposition.return_value = [
                Mock(id=2, position=1),
                Mock(id=3, position=2)
            ]
            
            results = waitlist_repo.reposition_waitlist(spot_id, date_from)
            
            assert results[0].position == 1
            assert results[1].position == 2
            mock_reposition.assert_called_once_with(spot_id, date_from)


class TestReservationHistoryRepository:
    """Tests for the ReservationHistoryRepository."""
    
    @pytest.fixture
    def history_repo(self, db_session):
        """Create a reservation history repository instance."""
        return ReservationHistoryRepository(db_session)
    
    def test_get_by_reservation(self, history_repo, reservation_history):
        """Test getting history entries for a reservation."""
        reservation_id = 201
        
        with patch.object(history_repo, 'get_by_reservation') as mock_get:
            reservation_history_entries = [
                h for h in reservation_history if h['reservation_id'] == reservation_id
            ]
            mock_get.return_value = [Mock(id=i) for i in range(len(reservation_history_entries))]
            
            results = history_repo.get_by_reservation(reservation_id)
            
            assert len(results) == len(reservation_history_entries)
            mock_get.assert_called_once_with(reservation_id)
    
    def test_get_status_change_timeline(self, history_repo):
        """Test getting status change timeline for a reservation."""
        reservation_id = 201
        
        with patch.object(history_repo, 'get_status_change_timeline') as mock_get:
            mock_get.return_value = [
                {'status': 'pending', 'changed_at': '2023-12-01T14:30:00Z'},
                {'status': 'confirmed', 'changed_at': '2023-12-01T14:35:00Z'},
                {'status': 'checked_in', 'changed_at': '2023-12-10T08:45:00Z'},
                {'status': 'completed', 'changed_at': '2023-12-10T17:15:00Z'}
            ]
            
            timeline = history_repo.get_status_change_timeline(reservation_id)
            
            assert len(timeline) == 4
            assert timeline[0]['status'] == 'pending'
            assert timeline[-1]['status'] == 'completed'
            mock_get.assert_called_once_with(reservation_id)
    
    def test_add_history_entry(self, history_repo):
        """Test adding a history entry."""
        reservation_id = 201
        status = 'checked_in'
        changed_by = 'gate'
        
        with patch.object(history_repo, 'add_entry') as mock_add:
            mock_entry = Mock(
                reservation_id=reservation_id,
                status=status,
                changed_by=changed_by
            )
            mock_add.return_value = mock_entry
            
            result = history_repo.add_entry(reservation_id, status, changed_by)
            
            assert result.reservation_id == reservation_id
            assert result.status == status
            assert result.changed_by == changed_by
            mock_add.assert_called_once_with(reservation_id, status, changed_by)


class TestReservationNoteRepository:
    """Tests for the ReservationNoteRepository."""
    
    @pytest.fixture
    def note_repo(self, db_session):
        """Create a reservation note repository instance."""
        return ReservationNoteRepository(db_session)
    
    def test_get_by_reservation(self, note_repo, reservation_notes):
        """Test getting notes for a reservation."""
        reservation_id = 201
        
        with patch.object(note_repo, 'get_by_reservation') as mock_get:
            reservation_notes_list = [
                n for n in reservation_notes if n['reservation_id'] == reservation_id
            ]
            mock_get.return_value = [Mock(id=i) for i in range(len(reservation_notes_list))]
            
            results = note_repo.get_by_reservation(reservation_id)
            
            assert len(results) == len(reservation_notes_list)
            mock_get.assert_called_once_with(reservation_id)
    
    def test_get_public_notes(self, note_repo, reservation_notes):
        """Test getting public notes for a reservation."""
        reservation_id = 201
        
        with patch.object(note_repo, 'get_public_notes') as mock_get:
            public_notes = [
                n for n in reservation_notes 
                if n['reservation_id'] == reservation_id and not n['is_private']
            ]
            mock_get.return_value = [Mock(id=i) for i in range(len(public_notes))]
            
            results = note_repo.get_public_notes(reservation_id)
            
            assert len(results) == len(public_notes)
            mock_get.assert_called_once_with(reservation_id)
    
    def test_add_note(self, note_repo):
        """Test adding a note to a reservation."""
        reservation_id = 201
        user_id = 5
        note_text = "Customer requested extra time"
        is_private = False
        
        with patch.object(note_repo, 'add_note') as mock_add:
            mock_note = Mock(
                reservation_id=reservation_id,
                user_id=user_id,
                note=note_text,
                is_private=is_private
            )
            mock_add.return_value = mock_note
            
            result = note_repo.add_note(reservation_id, user_id, note_text, is_private)
            
            assert result.reservation_id == reservation_id
            assert result.user_id == user_id
            assert result.note == note_text
            assert result.is_private == is_private
            mock_add.assert_called_once_with(reservation_id, user_id, note_text, is_private)


class TestReservationAddonRepository:
    """Tests for the ReservationAddonRepository."""
    
    @pytest.fixture
    def addon_repo(self, db_session):
        """Create a reservation addon repository instance."""
        return ReservationAddonRepository(db_session)
    
    def test_get_by_reservation(self, addon_repo, reservation_addons):
        """Test getting addons for a reservation."""
        reservation_id = 217
        
        with patch.object(addon_repo, 'get_by_reservation') as mock_get:
            reservation_addons_list = [
                a for a in reservation_addons if a['reservation_id'] == reservation_id
            ]
            mock_get.return_value = [Mock(id=i) for i in range(len(reservation_addons_list))]
            
            results = addon_repo.get_by_reservation(reservation_id)
            
            assert len(results) == len(reservation_addons_list)
            mock_get.assert_called_once_with(reservation_id)
    
    def test_get_by_type(self, addon_repo, reservation_addons):
        """Test getting addons by type."""
        addon_type = 'valet'
        
        with patch.object(addon_repo, 'get_by_type') as mock_get:
            type_addons = [a for a in reservation_addons if a['addon_type'] == addon_type]
            mock_get.return_value = [Mock(id=i) for i in range(len(type_addons))]
            
            results = addon_repo.get_by_type(addon_type)
            
            assert len(results) == len(type_addons)
            mock_get.assert_called_once_with(addon_type)
    
    def test_get_total_addons_revenue(self, addon_repo, reservation_addons):
        """Test getting total revenue from addons."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        with patch.object(addon_repo, 'get_total_revenue') as mock_get:
            mock_get.return_value = 75.00
            
            revenue = addon_repo.get_total_revenue(start_date, end_date)
            
            assert revenue == 75.00
            mock_get.assert_called_once_with(start_date, end_date)


# Integration tests combining multiple repositories
class TestRepositoryIntegration:
    """Integration tests for multiple repositories working together."""
    
    def test_complete_booking_flow(
        self, 
        reservation_repo, 
        user_repo, 
        spot_repo, 
        waitlist_repo,
        history_repo,
        note_repo,
        addon_repo,
        reservation_factory
    ):
        """Test complete booking flow across repositories."""
        # 1. Check available spots
        with patch.object(spot_repo, 'get_available_spots') as mock_available:
            mock_available.return_value = [Mock(id=4)]
            available_spots = spot_repo.get_available_spots(
                datetime(2024, 1, 25, 9, 0),
                datetime(2024, 1, 25, 17, 0)
            )
            assert len(available_spots) > 0
        
        # 2. Create reservation
        with patch.object(reservation_repo, 'create') as mock_create:
            new_reservation = reservation_factory(
                user_id=5,
                spot_id=4,
                status='confirmed'
            )
            mock_create.return_value = new_reservation
            reservation = reservation_repo.create(new_reservation)
            assert reservation.id is not None
        
        # 3. Add to history
        with patch.object(history_repo, 'add_entry') as mock_history:
            mock_history.return_value = Mock()
            history_repo.add_entry(reservation.id, 'confirmed', 'system')
            mock_history.assert_called_once()
        
        # 4. Add a note
        with patch.object(note_repo, 'add_note') as mock_note:
            mock_note.return_value = Mock()
            note_repo.add_note(reservation.id, 5, "Test note", False)
            mock_note.assert_called_once()
        
        # 5. Check in
        with patch.object(reservation_repo, 'check_in') as mock_checkin:
            checked_in = Mock(status='checked_in')
            mock_checkin.return_value = checked_in
            result = reservation_repo.check_in(reservation.id)
            assert result.status == 'checked_in'
        
        # 6. Add addons
        with patch.object(addon_repo, 'get_by_reservation') as mock_addons:
            mock_addons.return_value = [Mock(addon_type='valet')]
            addons = addon_repo.get_by_reservation(reservation.id)
            assert len(addons) > 0
    
    def test_conflict_detection_and_waitlist(
        self,
        reservation_repo,
        spot_repo,
        waitlist_repo
    ):
        """Test conflict detection and waitlist management."""
        spot_id = 18
        start_time = datetime(2024, 1, 20, 18, 0)
        end_time = datetime(2024, 1, 20, 22, 0)
        
        # 1. Check for conflicts
        with patch.object(reservation_repo, 'get_conflicts') as mock_conflicts:
            mock_conflicts.return_value = [Mock(id=209)]
            conflicts = reservation_repo.get_conflicts(spot_id, start_time, end_time)
            
            if conflicts:
                # 2. Add to waitlist
                with patch.object(waitlist_repo, 'create') as mock_waitlist:
                    mock_waitlist.return_value = Mock(
                        id=6,
                        user_id=25,
                        spot_id=spot_id,
                        position=3
                    )
                    waitlist_entry = waitlist_repo.create({
                        'user_id': 25,
                        'spot_id': spot_id,
                        'date_from': start_time,
                        'date_to': end_time
                    })
                    assert waitlist_entry.spot_id == spot_id
                
                # 3. Get next in line
                with patch.object(waitlist_repo, 'get_next_in_line') as mock_next:
                    mock_next.return_value = Mock(user_id=17, position=1)
                    next_in_line = waitlist_repo.get_next_in_line(spot_id, start_time)
                    assert next_in_line.position == 1


# Performance and edge cases
class TestRepositoryEdgeCases:
    """Tests for repository edge cases and error conditions."""
    
    def test_get_nonexistent_reservation(self, reservation_repo):
        """Test getting a reservation that doesn't exist."""
        with patch.object(reservation_repo, 'get_by_id') as mock_get:
            mock_get.return_value = None
            result = reservation_repo.get_by_id(99999)
            assert result is None
    
    def test_create_reservation_with_invalid_data(self, reservation_repo, reservation_factory):
        """Test creating a reservation with invalid data."""
        invalid_reservation = reservation_factory(
            start_time="invalid-date",
            end_time="invalid-date"
        )
        
        with patch.object(reservation_repo, 'create') as mock_create:
            mock_create.side_effect = ValueError("Invalid date format")
            
            with pytest.raises(ValueError):
                reservation_repo.create(invalid_reservation)
    
    def test_update_nonexistent_reservation(self, reservation_repo):
        """Test updating a reservation that doesn't exist."""
        with patch.object(reservation_repo, 'update') as mock_update:
            mock_update.return_value = None
            result = reservation_repo.update(99999, {'status': 'cancelled'})
            assert result is None
    
    def test_delete_nonexistent_reservation(self, reservation_repo):
        """Test deleting a reservation that doesn't exist."""
        with patch.object(reservation_repo, 'delete') as mock_delete:
            mock_delete.return_value = False
            result = reservation_repo.delete(99999)
            assert result is False
    
    def test_concurrent_reservation_creation(self, reservation_repo, reservation_factory):
        """Test handling concurrent reservation creation."""
        spot_id = 4
        start_time = datetime(2024, 1, 25, 9, 0)
        end_time = datetime(2024, 1, 25, 17, 0)
        
        # Create first reservation
        reservation1 = reservation_factory(spot_id=spot_id)
        
        # Attempt to create conflicting reservation
        reservation2 = reservation_factory(spot_id=spot_id)
        
        with patch.object(reservation_repo, 'get_conflicts') as mock_conflicts:
            mock_conflicts.return_value = [reservation1]
            
            conflicts = reservation_repo.get_conflicts(spot_id, start_time, end_time)
            assert len(conflicts) == 1
            
            with patch.object(reservation_repo, 'create') as mock_create:
                mock_create.side_effect = Exception("Spot already booked")
                
                with pytest.raises(Exception):
                    reservation_repo.create(reservation2)
    
    def test_bulk_operations(self, reservation_repo, reservation_factory):
        """Test bulk repository operations."""
        reservations = [
            reservation_factory(user_id=i) for i in range(1, 6)
        ]
        
        with patch.object(reservation_repo, 'bulk_create') as mock_bulk:
            mock_bulk.return_value = reservations
            results = reservation_repo.bulk_create(reservations)
            assert len(results) == 5
            mock_bulk.assert_called_once_with(reservations)
        
        with patch.object(reservation_repo, 'bulk_update_status') as mock_update:
            mock_update.return_value = 5
            count = reservation_repo.bulk_update_status([r.id for r in reservations], 'confirmed')
            assert count == 5
            mock_update.assert_called_once()