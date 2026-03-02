"""Tests for parking management system services."""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Assuming you have actual service classes, we'll create mock imports
# Replace these with your actual service imports
try:
    from app.services import (
        ReservationService, UserService, ParkingSpotService,
        PaymentService, NotificationService, WaitlistService,
        RecurringReservationService, AnalyticsService,
        VehicleService, PricingService
    )
    from app.repositories import (
        ReservationRepository, UserRepository, ParkingSpotRepository,
        PaymentRepository, NotificationRepository
    )
    from app.models import Reservation, User, ParkingSpot, Payment
    from app.exceptions import (
        ReservationConflictError, InvalidReservationError,
        PaymentRequiredError, SpotNotAvailableError,
        UnauthorizedAccessError, BusinessRuleViolation
    )
except ImportError:
    # Mock services for testing when actual ones aren't available
    pytest.skip("Services not available - skipping integration tests", allow_module_level=True)


class TestReservationService:
    """Tests for the ReservationService."""
    
    @pytest.fixture
    def reservation_service(self, db_session):
        """Create a reservation service instance with mocked repositories."""
        service = ReservationService()
        service.reservation_repo = Mock(spec=ReservationRepository)
        service.spot_repo = Mock(spec=ParkingSpotRepository)
        service.user_repo = Mock(spec=UserRepository)
        service.payment_service = Mock(spec=PaymentService)
        service.notification_service = Mock(spec=NotificationService)
        return service
    
    def test_create_reservation_success(self, reservation_service, reservation_factory):
        """Test successfully creating a reservation."""
        # Arrange
        user_id = 5
        spot_id = 4
        start_time = datetime(2024, 1, 25, 9, 0)
        end_time = datetime(2024, 1, 25, 17, 0)
        vehicle_id = 101
        
        # Mock spot availability
        reservation_service.spot_repo.is_available.return_value = True
        reservation_service.spot_repo.get_by_id.return_value = Mock(
            id=spot_id,
            spot_type='standard',
            hourly_rate=3.00
        )
        
        # Mock user validation
        reservation_service.user_repo.get_by_id.return_value = Mock(
            id=user_id,
            is_active=True,
            has_valid_payment_method=True
        )
        
        # Mock reservation creation
        expected_reservation = reservation_factory(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            start_time=start_time.isoformat() + 'Z',
            end_time=end_time.isoformat() + 'Z',
            total_amount=24.00
        )
        reservation_service.reservation_repo.create.return_value = expected_reservation
        
        # Mock notification
        reservation_service.notification_service.send_confirmation.return_value = True
        
        # Act
        result = reservation_service.create_reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Assert
        assert result is not None
        assert result.user_id == user_id
        assert result.spot_id == spot_id
        assert result.total_amount == 24.00
        
        reservation_service.reservation_repo.create.assert_called_once()
        reservation_service.notification_service.send_confirmation.assert_called_once()
    
    def test_create_reservation_spot_not_available(self, reservation_service):
        """Test creating a reservation when spot is not available."""
        # Arrange
        user_id = 5
        spot_id = 4
        start_time = datetime(2024, 1, 25, 9, 0)
        end_time = datetime(2024, 1, 25, 17, 0)
        
        # Mock spot unavailability
        reservation_service.spot_repo.is_available.return_value = False
        reservation_service.spot_repo.get_conflicting_reservations.return_value = [
            Mock(id=218, start_time='2024-01-25T09:00:00Z', end_time='2024-01-25T17:00:00Z')
        ]
        
        # Act & Assert
        with pytest.raises(SpotNotAvailableError) as exc_info:
            reservation_service.create_reservation(
                user_id=user_id,
                spot_id=spot_id,
                vehicle_id=101,
                start_time=start_time,
                end_time=end_time
            )
        
        assert "Spot is not available" in str(exc_info.value)
    
    def test_create_reservation_invalid_dates(self, reservation_service):
        """Test creating a reservation with invalid dates."""
        # Arrange
        user_id = 5
        spot_id = 4
        start_time = datetime(2024, 1, 25, 17, 0)  # End before start
        end_time = datetime(2024, 1, 25, 9, 0)
        
        # Act & Assert
        with pytest.raises(InvalidReservationError) as exc_info:
            reservation_service.create_reservation(
                user_id=user_id,
                spot_id=spot_id,
                vehicle_id=101,
                start_time=start_time,
                end_time=end_time
            )
        
        assert "End time must be after start time" in str(exc_info.value)
    
    def test_create_reservation_past_date(self, reservation_service):
        """Test creating a reservation with past date."""
        # Arrange
        user_id = 5
        spot_id = 4
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now() - timedelta(hours=1)
        
        # Act & Assert
        with pytest.raises(InvalidReservationError) as exc_info:
            reservation_service.create_reservation(
                user_id=user_id,
                spot_id=spot_id,
                vehicle_id=101,
                start_time=start_time,
                end_time=end_time
            )
        
        assert "Cannot create reservations in the past" in str(exc_info.value)
    
    def test_create_reservation_exceeds_max_duration(self, reservation_service):
        """Test creating a reservation that exceeds maximum duration."""
        # Arrange
        user_id = 5
        spot_id = 4
        start_time = datetime(2024, 1, 25, 9, 0)
        end_time = datetime(2024, 1, 30, 17, 0)  # 5 days later
        
        # Act & Assert
        with pytest.raises(InvalidReservationError) as exc_info:
            reservation_service.create_reservation(
                user_id=user_id,
                spot_id=spot_id,
                vehicle_id=101,
                start_time=start_time,
                end_time=end_time,
                max_duration_hours=72
            )
        
        assert "exceeds maximum allowed duration" in str(exc_info.value)
    
    def test_create_ev_charging_reservation(self, reservation_service, reservation_factory):
        """Test creating an EV charging reservation."""
        # Arrange
        user_id = 8
        spot_id = 21
        start_time = datetime(2024, 1, 23, 13, 0)
        end_time = datetime(2024, 1, 23, 17, 0)
        vehicle_id = 104
        
        # Mock spot as EV charging spot
        mock_spot = Mock(
            id=spot_id,
            spot_type='ev_charging',
            hourly_rate=3.00,
            has_charger=True,
            charger_type='Level 2'
        )
        reservation_service.spot_repo.get_by_id.return_value = mock_spot
        reservation_service.spot_repo.is_available.return_value = True
        
        # Mock user
        reservation_service.user_repo.get_by_id.return_value = Mock(
            id=user_id,
            is_active=True,
            has_valid_payment_method=True
        )
        
        # Mock reservation creation with EV specific fields
        expected_reservation = reservation_factory(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            reservation_type='ev_charging',
            start_time=start_time.isoformat() + 'Z',
            end_time=end_time.isoformat() + 'Z',
            total_amount=16.00,
            charging_fee=4.00,
            metadata={'charger_type': 'Level 2'}
        )
        reservation_service.reservation_repo.create.return_value = expected_reservation
        
        # Act
        result = reservation_service.create_reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            start_time=start_time,
            end_time=end_time,
            reservation_type='ev_charging'
        )
        
        # Assert
        assert result.reservation_type == 'ev_charging'
        assert result.charging_fee == 4.00
        assert result.metadata.get('charger_type') == 'Level 2'
    
    def test_cancel_reservation_success(self, reservation_service, sample_reservation):
        """Test successfully cancelling a reservation."""
        # Arrange
        reservation_id = 206
        user_id = 10
        cancellation_reason = "Change of plans"
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='confirmed',
            total_amount=12.00,
            payment_status='paid',
            payment_id=306,
            can_be_cancelled=Mock(return_value=True)
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Mock cancellation
        cancelled_reservation = Mock(
            id=reservation_id,
            status='cancelled',
            cancellation_reason=cancellation_reason
        )
        reservation_service.reservation_repo.cancel.return_value = cancelled_reservation
        
        # Mock refund processing
        reservation_service.payment_service.process_refund.return_value = Mock(
            id=500,
            amount=12.00,
            status='completed'
        )
        
        # Mock notification
        reservation_service.notification_service.send_cancellation.return_value = True
        
        # Act
        result = reservation_service.cancel_reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            reason=cancellation_reason
        )
        
        # Assert
        assert result.status == 'cancelled'
        assert result.cancellation_reason == cancellation_reason
        reservation_service.payment_service.process_refund.assert_called_once_with(
            payment_id=306,
            amount=12.00,
            reason=cancellation_reason
        )
        reservation_service.notification_service.send_cancellation.assert_called_once()
    
    def test_cancel_reservation_not_authorized(self, reservation_service):
        """Test cancelling a reservation as a different user."""
        # Arrange
        reservation_id = 206
        user_id = 5  # Different user than the one who made reservation
        wrong_user_id = 99
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='confirmed'
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Act & Assert
        with pytest.raises(UnauthorizedAccessError) as exc_info:
            reservation_service.cancel_reservation(
                reservation_id=reservation_id,
                user_id=wrong_user_id,
                reason="Test"
            )
        
        assert "not authorized" in str(exc_info.value).lower()
    
    def test_cancel_reservation_cannot_cancel(self, reservation_service):
        """Test cancelling a reservation that cannot be cancelled."""
        # Arrange
        reservation_id = 215  # Checked-in reservation
        user_id = 20
        
        # Mock reservation that cannot be cancelled
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='checked_in',
            can_be_cancelled=Mock(return_value=False)
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Act & Assert
        with pytest.raises(BusinessRuleViolation) as exc_info:
            reservation_service.cancel_reservation(
                reservation_id=reservation_id,
                user_id=user_id,
                reason="Test"
            )
        
        assert "cannot be cancelled" in str(exc_info.value).lower()
    
    def test_check_in_reservation_success(self, reservation_service):
        """Test successfully checking in to a reservation."""
        # Arrange
        reservation_id = 215
        user_id = 20
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='confirmed',
            spot_id=5,
            start_time=datetime(2024, 1, 15, 8, 0),
            end_time=datetime(2024, 1, 15, 17, 0)
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Mock check-in
        checked_in_reservation = Mock(
            id=reservation_id,
            status='checked_in',
            checked_in_at=datetime.now()
        )
        reservation_service.reservation_repo.check_in.return_value = checked_in_reservation
        
        # Mock gate access
        reservation_service.spot_repo.open_gate.return_value = True
        
        # Act
        result = reservation_service.check_in(reservation_id, user_id)
        
        # Assert
        assert result.status == 'checked_in'
        reservation_service.spot_repo.open_gate.assert_called_once_with(spot_id=5)
    
    def test_check_in_early(self, reservation_service):
        """Test checking in too early."""
        # Arrange
        reservation_id = 218
        user_id = 5
        
        # Mock reservation with future start time
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='confirmed',
            start_time=datetime.now() + timedelta(hours=3)
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Act & Assert
        with pytest.raises(BusinessRuleViolation) as exc_info:
            reservation_service.check_in(reservation_id, user_id)
        
        assert "too early" in str(exc_info.value).lower()
    
    def test_check_out_reservation_success(self, reservation_service):
        """Test successfully checking out from a reservation."""
        # Arrange
        reservation_id = 215
        user_id = 20
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='checked_in',
            spot_id=5
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Mock check-out
        checked_out_reservation = Mock(
            id=reservation_id,
            status='completed',
            checked_out_at=datetime.now(),
            completed_at=datetime.now()
        )
        reservation_service.reservation_repo.check_out.return_value = checked_out_reservation
        
        # Mock payment processing if needed
        reservation_service.payment_service.capture_payment.return_value = Mock(status='captured')
        
        # Mock gate exit
        reservation_service.spot_repo.open_exit_gate.return_value = True
        
        # Act
        result = reservation_service.check_out(reservation_id, user_id)
        
        # Assert
        assert result.status == 'completed'
        reservation_service.spot_repo.open_exit_gate.assert_called_once_with(spot_id=5)
    
    def test_extend_reservation_success(self, reservation_service):
        """Test successfully extending a reservation."""
        # Arrange
        reservation_id = 215
        user_id = 20
        new_end_time = datetime(2024, 1, 15, 19, 0)  # 2 hours later
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='checked_in',
            spot_id=5,
            end_time=datetime(2024, 1, 15, 17, 0),
            total_amount=27.00
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Check spot availability for extended time
        reservation_service.spot_repo.is_available.return_value = True
        
        # Mock extension
        extended_reservation = Mock(
            id=reservation_id,
            end_time=new_end_time,
            total_amount=35.00  # Additional charge
        )
        reservation_service.reservation_repo.extend.return_value = extended_reservation
        
        # Mock additional payment
        reservation_service.payment_service.charge_additional.return_value = Mock(
            amount=8.00,
            status='completed'
        )
        
        # Act
        result = reservation_service.extend_reservation(
            reservation_id=reservation_id,
            user_id=user_id,
            new_end_time=new_end_time
        )
        
        # Assert
        assert result.end_time == new_end_time
        assert result.total_amount == 35.00
        reservation_service.payment_service.charge_additional.assert_called_once_with(
            reservation_id=reservation_id,
            amount=8.00
        )
    
    def test_extend_reservation_conflict(self, reservation_service):
        """Test extending a reservation that conflicts with another."""
        # Arrange
        reservation_id = 215
        user_id = 20
        new_end_time = datetime(2024, 1, 15, 19, 0)
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            user_id=user_id,
            status='checked_in',
            spot_id=5,
            end_time=datetime(2024, 1, 15, 17, 0)
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Spot not available for extended time
        reservation_service.spot_repo.is_available.return_value = False
        reservation_service.spot_repo.get_conflicting_reservations.return_value = [
            Mock(id=299, start_time='2024-01-15T18:00:00Z', end_time='2024-01-15T20:00:00Z')
        ]
        
        # Act & Assert
        with pytest.raises(ReservationConflictError) as exc_info:
            reservation_service.extend_reservation(
                reservation_id=reservation_id,
                user_id=user_id,
                new_end_time=new_end_time
            )
        
        assert "conflict" in str(exc_info.value).lower()
    
    def test_get_user_upcoming_reservations(self, reservation_service, user_reservations):
        """Test getting upcoming reservations for a user."""
        # Arrange
        user_id = 5
        
        # Mock repository
        mock_reservations = [
            Mock(id=218, status='confirmed', start_time=datetime(2024, 1, 20, 9, 0)),
            Mock(id=233, status='confirmed', start_time=datetime(2024, 2, 22, 9, 0))
        ]
        reservation_service.reservation_repo.get_upcoming_by_user.return_value = mock_reservations
        
        # Act
        results = reservation_service.get_user_upcoming_reservations(user_id)
        
        # Assert
        assert len(results) == 2
        assert all(r.status == 'confirmed' for r in results)
        reservation_service.reservation_repo.get_upcoming_by_user.assert_called_once_with(
            user_id, days=30
        )
    
    def test_get_reservation_history(self, reservation_service, user_reservations):
        """Test getting reservation history for a user."""
        # Arrange
        user_id = 5
        
        # Mock repository
        mock_reservations = [
            Mock(id=201, status='completed', start_time=datetime(2023, 12, 10, 9, 0)),
            Mock(id=210, status='completed', start_time=datetime(2023, 12, 30, 8, 0)),
            Mock(id=242, status='no_show', start_time=datetime(2023, 12, 5, 9, 0))
        ]
        reservation_service.reservation_repo.get_by_user.return_value = mock_reservations
        
        # Act
        results = reservation_service.get_reservation_history(
            user_id, 
            from_date=datetime(2023, 12, 1),
            to_date=datetime(2023, 12, 31)
        )
        
        # Assert
        assert len(results) == 3
        reservation_service.reservation_repo.get_by_user.assert_called_once()


class TestParkingSpotService:
    """Tests for the ParkingSpotService."""
    
    @pytest.fixture
    def spot_service(self):
        """Create a parking spot service instance."""
        service = ParkingSpotService()
        service.spot_repo = Mock(spec=ParkingSpotRepository)
        service.reservation_repo = Mock(spec=ReservationRepository)
        return service
    
    def test_find_available_spots(self, spot_service):
        """Test finding available spots for a time range."""
        # Arrange
        start_time = datetime(2024, 1, 20, 9, 0)
        end_time = datetime(2024, 1, 20, 17, 0)
        
        # Mock available spots
        mock_spots = [
            Mock(id=4, spot_type='standard', hourly_rate=3.00),
            Mock(id=12, spot_type='standard', hourly_rate=3.00),
            Mock(id=18, spot_type='vip', hourly_rate=8.00)
        ]
        spot_service.spot_repo.get_available_spots.return_value = mock_spots
        
        # Act
        results = spot_service.find_available_spots(start_time, end_time)
        
        # Assert
        assert len(results) == 3
        spot_service.spot_repo.get_available_spots.assert_called_once_with(
            start_time, end_time, spot_type=None
        )
    
    def test_find_available_spots_by_type(self, spot_service):
        """Test finding available spots by type."""
        # Arrange
        start_time = datetime(2024, 1, 20, 9, 0)
        end_time = datetime(2024, 1, 20, 17, 0)
        spot_type = 'ev_charging'
        
        # Mock available spots
        mock_spots = [
            Mock(id=21, spot_type='ev_charging', hourly_rate=3.00, has_charger=True),
            Mock(id=22, spot_type='ev_charging', hourly_rate=3.00, has_charger=True)
        ]
        spot_service.spot_repo.get_available_spots.return_value = mock_spots
        
        # Act
        results = spot_service.find_available_spots(
            start_time, end_time, spot_type=spot_type
        )
        
        # Assert
        assert len(results) == 2
        assert all(s.spot_type == spot_type for s in results)
        spot_service.spot_repo.get_available_spots.assert_called_once_with(
            start_time, end_time, spot_type=spot_type
        )
    
    def test_get_spot_occupancy_report(self, spot_service):
        """Test getting occupancy report for a spot."""
        # Arrange
        spot_id = 4
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock occupancy data
        spot_service.spot_repo.get_occupancy.return_value = 0.45
        spot_service.reservation_repo.get_by_spot_and_date_range.return_value = [
            Mock(id=201, date='2023-12-10'),
            Mock(id=210, date='2023-12-30'),
            Mock(id=218, date='2023-12-20')  # Note: this is for 2024, shouldn't be counted
        ]
        
        # Act
        report = spot_service.get_spot_occupancy_report(spot_id, start_date, end_date)
        
        # Assert
        assert report['spot_id'] == spot_id
        assert report['occupancy_rate'] == 0.45
        assert report['total_reservations'] == 2  # Only Dec 10 and Dec 30
        assert report['start_date'] == start_date
        assert report['end_date'] == end_date
    
    def test_get_spot_utilization_summary(self, spot_service):
        """Test getting utilization summary for all spots."""
        # Arrange
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock utilization data
        spot_service.spot_repo.get_all_spots.return_value = [
            Mock(id=4, spot_type='standard'),
            Mock(id=12, spot_type='standard'),
            Mock(id=18, spot_type='vip'),
            Mock(id=21, spot_type='ev_charging'),
            Mock(id=22, spot_type='ev_charging')
        ]
        
        # Mock occupancy for each spot
        def mock_get_occupancy(spot_id, start, end):
            occupancy_map = {4: 0.45, 12: 0.30, 18: 0.60, 21: 0.25, 22: 0.35}
            return occupancy_map.get(spot_id, 0)
        
        spot_service.spot_repo.get_occupancy.side_effect = mock_get_occupancy
        
        # Act
        summary = spot_service.get_spot_utilization_summary(start_date, end_date)
        
        # Assert
        assert len(summary) == 5
        assert summary[0]['spot_id'] == 18  # Highest occupancy
        assert summary[0]['occupancy_rate'] == 0.60
        assert summary[-1]['spot_id'] == 21  # Lowest occupancy
        
        # Verify grouping by type
        by_type = spot_service.get_spot_utilization_summary(start_date, end_date, group_by_type=True)
        assert 'standard' in by_type
        assert 'vip' in by_type
        assert 'ev_charging' in by_type
        assert by_type['vip']['avg_occupancy'] == 0.60


class TestPaymentService:
    """Tests for the PaymentService."""
    
    @pytest.fixture
    def payment_service(self):
        """Create a payment service instance."""
        service = PaymentService()
        service.payment_repo = Mock(spec=PaymentRepository)
        service.reservation_repo = Mock(spec=ReservationRepository)
        service.notification_service = Mock(spec=NotificationService)
        return service
    
    def test_process_payment_success(self, payment_service):
        """Test successfully processing a payment."""
        # Arrange
        reservation_id = 218
        amount = 24.00
        payment_method = {
            'type': 'credit_card',
            'token': 'tok_visa',
            'last4': '4242'
        }
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            total_amount=amount,
            payment_status='pending'
        )
        payment_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Mock payment gateway
        with patch('app.services.payment_gateway.charge') as mock_charge:
            mock_charge.return_value = {
                'id': 'ch_123456',
                'status': 'succeeded',
                'amount': amount * 100,  # in cents
                'payment_method_details': {'card': {'last4': '4242'}}
            }
            
            # Mock payment creation
            mock_payment = Mock(
                id=301,
                reservation_id=reservation_id,
                amount=amount,
                status='completed',
                transaction_id='ch_123456'
            )
            payment_service.payment_repo.create.return_value = mock_payment
            
            # Mock reservation update
            payment_service.reservation_repo.update_payment_status.return_value = True
            
            # Act
            result = payment_service.process_payment(
                reservation_id=reservation_id,
                amount=amount,
                payment_method=payment_method
            )
            
            # Assert
            assert result['status'] == 'success'
            assert result['payment_id'] == 301
            assert result['transaction_id'] == 'ch_123456'
            
            mock_charge.assert_called_once_with(
                amount=amount * 100,
                currency='usd',
                payment_method=payment_method['token'],
                metadata={'reservation_id': reservation_id}
            )
    
    def test_process_payment_failure(self, payment_service):
        """Test payment processing failure."""
        # Arrange
        reservation_id = 218
        amount = 24.00
        payment_method = {'type': 'credit_card', 'token': 'tok_chargeDeclined'}
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            total_amount=amount,
            payment_status='pending'
        )
        payment_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        # Mock payment gateway failure
        with patch('app.services.payment_gateway.charge') as mock_charge:
            mock_charge.side_effect = Exception("Card declined")
            
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                payment_service.process_payment(
                    reservation_id=reservation_id,
                    amount=amount,
                    payment_method=payment_method
                )
            
            assert "declined" in str(exc_info.value).lower()
            
            # Verify payment failure was logged
            payment_service.payment_repo.create_failure_log.assert_called_once()
    
    def test_process_refund_success(self, payment_service):
        """Test successfully processing a refund."""
        # Arrange
        payment_id = 306
        amount = 12.00
        reason = "Cancellation"
        
        # Mock payment
        mock_payment = Mock(
            id=payment_id,
            reservation_id=206,
            amount=12.00,
            status='completed',
            transaction_id='ch_123456'
        )
        payment_service.payment_repo.get_by_id.return_value = mock_payment
        
        # Mock refund gateway
        with patch('app.services.payment_gateway.refund') as mock_refund:
            mock_refund.return_value = {
                'id': 're_123456',
                'status': 'succeeded',
                'amount': amount * 100
            }
            
            # Mock refund creation
            mock_refund_record = Mock(
                id=500,
                payment_id=payment_id,
                amount=amount,
                status='completed',
                reason=reason
            )
            payment_service.payment_repo.create_refund.return_value = mock_refund_record
            
            # Act
            result = payment_service.process_refund(
                payment_id=payment_id,
                amount=amount,
                reason=reason
            )
            
            # Assert
            assert result['status'] == 'success'
            assert result['refund_id'] == 500
            mock_refund.assert_called_once_with(
                transaction_id='ch_123456',
                amount=amount * 100
            )
    
    def test_calculate_reservation_cost(self, payment_service):
        """Test calculating reservation cost."""
        # Arrange
        spot_type = 'standard'
        hourly_rate = 3.00
        start_time = datetime(2024, 1, 20, 9, 0)
        end_time = datetime(2024, 1, 20, 17, 0)  # 8 hours
        
        # Act
        cost = payment_service.calculate_cost(
            spot_type=spot_type,
            hourly_rate=hourly_rate,
            start_time=start_time,
            end_time=end_time
        )
        
        # Assert
        assert cost == 24.00  # 8 hours * $3
    
    def test_calculate_ev_charging_cost(self, payment_service):
        """Test calculating EV charging reservation cost."""
        # Arrange
        spot_type = 'ev_charging'
        hourly_rate = 3.00
        charging_fee_per_hour = 0.50
        start_time = datetime(2024, 1, 23, 13, 0)
        end_time = datetime(2024, 1, 23, 17, 0)  # 4 hours
        
        # Act
        cost = payment_service.calculate_cost(
            spot_type=spot_type,
            hourly_rate=hourly_rate,
            start_time=start_time,
            end_time=end_time,
            charging_fee_per_hour=charging_fee_per_hour
        )
        
        # Assert
        assert cost == 14.00  # (4 * $3) + (4 * $0.50)


class TestWaitlistService:
    """Tests for the WaitlistService."""
    
    @pytest.fixture
    def waitlist_service(self):
        """Create a waitlist service instance."""
        service = WaitlistService()
        service.waitlist_repo = Mock(spec=WaitlistRepository)
        service.reservation_service = Mock(spec=ReservationService)
        service.notification_service = Mock(spec=NotificationService)
        return service
    
    def test_join_waitlist_success(self, waitlist_service):
        """Test successfully joining a waitlist."""
        # Arrange
        user_id = 25
        spot_id = 18
        date_from = datetime(2024, 1, 20, 18, 0)
        date_to = datetime(2024, 1, 20, 22, 0)
        
        # Mock waitlist entry creation
        mock_entry = Mock(
            id=6,
            user_id=user_id,
            spot_id=spot_id,
            date_from=date_from,
            date_to=date_to,
            status='active',
            position=3
        )
        waitlist_service.waitlist_repo.create.return_value = mock_entry
        
        # Act
        result = waitlist_service.join_waitlist(
            user_id=user_id,
            spot_id=spot_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Assert
        assert result.user_id == user_id
        assert result.spot_id == spot_id
        assert result.status == 'active'
        assert result.position == 3
        
        waitlist_service.notification_service.send_waitlist_confirmation.assert_called_once()
    
    def test_leave_waitlist(self, waitlist_service):
        """Test leaving a waitlist."""
        # Arrange
        waitlist_id = 2
        user_id = 19
        
        # Mock waitlist entry
        mock_entry = Mock(
            id=waitlist_id,
            user_id=user_id,
            status='active',
            position=2
        )
        waitlist_service.waitlist_repo.get_by_id.return_value = mock_entry
        waitlist_service.waitlist_repo.remove.return_value = True
        
        # Act
        result = waitlist_service.leave_waitlist(waitlist_id, user_id)
        
        # Assert
        assert result is True
        waitlist_service.waitlist_repo.remove.assert_called_once_with(waitlist_id)
        
        # Verify repositioning was triggered
        waitlist_service.waitlist_repo.reposition_waitlist.assert_called_once()
    
    def test_notify_next_available(self, waitlist_service):
        """Test notifying next person when spot becomes available."""
        # Arrange
        spot_id = 18
        date_from = datetime(2024, 1, 20, 18, 0)
        
        # Mock next in line
        mock_next = Mock(
            id=1,
            user_id=17,
            spot_id=spot_id,
            date_from=date_from,
            status='active',
            position=1
        )
        waitlist_service.waitlist_repo.get_next_in_line.return_value = mock_next
        
        # Mock notification
        waitlist_service.notification_service.send_spot_available.return_value = True
        
        # Act
        result = waitlist_service.notify_next_available(spot_id, date_from)
        
        # Assert
        assert result['notified_user_id'] == 17
        assert result['waitlist_id'] == 1
        
        # Verify waitlist entry was updated to 'notified'
        waitlist_service.waitlist_repo.update_status.assert_called_once_with(1, 'notified')
    
    def test_check_waitlist_expiration(self, waitlist_service):
        """Test checking for expired waitlist entries."""
        # Arrange
        mock_expired_entries = [
            Mock(id=5, user_id=7, spot_id=4, created_at=datetime.now() - timedelta(days=3)),
            Mock(id=6, user_id=8, spot_id=12, created_at=datetime.now() - timedelta(days=2))
        ]
        waitlist_service.waitlist_repo.get_expired_entries.return_value = mock_expired_entries
        
        # Act
        expired_count = waitlist_service.check_waitlist_expiration()
        
        # Assert
        assert expired_count == 2
        waitlist_service.waitlist_repo.mark_as_expired.assert_called()
    
    def test_convert_waitlist_to_reservation(self, waitlist_service, reservation_factory):
        """Test converting a waitlist entry to a reservation."""
        # Arrange
        waitlist_id = 1
        user_id = 17
        
        # Mock waitlist entry
        mock_entry = Mock(
            id=waitlist_id,
            user_id=user_id,
            spot_id=18,
            date_from=datetime(2024, 1, 20, 18, 0),
            date_to=datetime(2024, 1, 20, 22, 0),
            status='notified'
        )
        waitlist_service.waitlist_repo.get_by_id.return_value = mock_entry
        
        # Mock reservation creation
        mock_reservation = reservation_factory(
            user_id=user_id,
            spot_id=18,
            start_time='2024-01-20T18:00:00Z',
            end_time='2024-01-20T22:00:00Z'
        )
        waitlist_service.reservation_service.create_reservation.return_value = mock_reservation
        
        # Act
        result = waitlist_service.convert_to_reservation(waitlist_id, user_id)
        
        # Assert
        assert result is not None
        assert result.user_id == user_id
        assert result.spot_id == 18
        
        # Verify waitlist entry was deactivated
        waitlist_service.waitlist_repo.deactivate.assert_called_once_with(waitlist_id)


class TestNotificationService:
    """Tests for the NotificationService."""
    
    @pytest.fixture
    def notification_service(self):
        """Create a notification service instance."""
        service = NotificationService()
        service.notification_repo = Mock()
        service.email_service = Mock()
        service.sms_service = Mock()
        service.push_service = Mock()
        return service
    
    def test_send_confirmation_email(self, notification_service):
        """Test sending confirmation email."""
        # Arrange
        user_email = "user@example.com"
        reservation_details = {
            'confirmation_code': 'CONF-218-ABCD',
            'spot_id': 4,
            'start_time': '2024-01-20T09:00:00Z',
            'end_time': '2024-01-20T17:00:00Z',
            'total_amount': 24.00
        }
        
        # Mock email service
        notification_service.email_service.send.return_value = {'id': 'email_123', 'status': 'sent'}
        
        # Act
        result = notification_service.send_confirmation(user_email, reservation_details)
        
        # Assert
        assert result['status'] == 'sent'
        notification_service.email_service.send.assert_called_once()
        notification_service.notification_repo.log.assert_called_once()
    
    def test_send_reminder_notifications(self, notification_service):
        """Test sending reminder notifications for upcoming reservations."""
        # Arrange
        upcoming_reservations = [
            Mock(
                id=218,
                user=Mock(email='user5@example.com', phone='+1234567890'),
                start_time=datetime.now() + timedelta(hours=2),
                spot_id=4
            ),
            Mock(
                id=219,
                user=Mock(email='user7@example.com', phone='+1234567891'),
                start_time=datetime.now() + timedelta(hours=3),
                spot_id=12
            )
        ]
        notification_service.reservation_repo = Mock()
        notification_service.reservation_repo.get_upcoming_reservations.return_value = upcoming_reservations
        
        # Mock notification services
        notification_service.email_service.send_batch.return_value = [{'id': f'email_{i}', 'status': 'sent'} for i in range(2)]
        notification_service.sms_service.send_batch.return_value = [{'id': f'sms_{i}', 'status': 'sent'} for i in range(2)]
        
        # Act
        results = notification_service.send_reminder_notifications(minutes_before=60)
        
        # Assert
        assert results['total_sent'] == 4  # 2 emails + 2 SMS
        assert results['emails_sent'] == 2
        assert results['sms_sent'] == 2
    
    def test_send_waitlist_notification(self, notification_service):
        """Test sending waitlist notification."""
        # Arrange
        user = Mock(email='user17@example.com', phone='+1234567892')
        spot_details = {
            'spot_id': 18,
            'date_from': '2024-01-20T18:00:00Z',
            'date_to': '2024-01-20T22:00:00Z'
        }
        
        # Mock notification services
        notification_service.email_service.send.return_value = {'id': 'email_456', 'status': 'sent'}
        notification_service.sms_service.send.return_value = {'id': 'sms_456', 'status': 'sent'}
        
        # Act
        result = notification_service.send_waitlist_notification(user, spot_details)
        
        # Assert
        assert result['email_sent'] is True
        assert result['sms_sent'] is True
    
    def test_send_cancellation_notification(self, notification_service):
        """Test sending cancellation notification."""
        # Arrange
        user_email = "user10@example.com"
        reservation_details = {
            'confirmation_code': 'CONF-206-UVWX',
            'spot_id': 4,
            'cancellation_reason': 'Change of plans'
        }
        
        # Mock email service
        notification_service.email_service.send.return_value = {'id': 'email_789', 'status': 'sent'}
        
        # Act
        result = notification_service.send_cancellation(user_email, reservation_details)
        
        # Assert
        assert result['status'] == 'sent'
        assert 'cancelled' in result['message'].lower()


class TestRecurringReservationService:
    """Tests for the RecurringReservationService."""
    
    @pytest.fixture
    def recurring_service(self):
        """Create a recurring reservation service instance."""
        service = RecurringReservationService()
        service.recurring_repo = Mock()
        service.reservation_service = Mock(spec=ReservationService)
        return service
    
    def test_create_recurring_pattern_weekly(self, recurring_service):
        """Test creating a weekly recurring reservation pattern."""
        # Arrange
        user_id = 5
        spot_id = 4
        vehicle_id = 101
        start_date = datetime(2024, 1, 8)
        end_date = datetime(2024, 3, 25)
        days_of_week = [1, 3, 5]  # Mon, Wed, Fri
        start_time = time(9, 0)
        end_time = time(17, 0)
        
        # Mock recurring reservation creation
        mock_recurring = Mock(
            id=1,
            user_id=user_id,
            spot_id=spot_id,
            frequency='weekly',
            days_of_week=days_of_week,
            start_date=start_date,
            end_date=end_date
        )
        recurring_service.recurring_repo.create.return_value = mock_recurring
        
        # Act
        result = recurring_service.create_recurring_reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            frequency='weekly',
            start_date=start_date,
            end_date=end_date,
            days_of_week=days_of_week,
            start_time=start_time,
            end_time=end_time
        )
        
        # Assert
        assert result.frequency == 'weekly'
        assert result.days_of_week == days_of_week
    
    def test_generate_occurrences_for_month(self, recurring_service):
        """Test generating occurrences for a month."""
        # Arrange
        recurring_id = 1
        month = 2  # February
        year = 2024
        
        # Mock recurring reservation
        mock_recurring = Mock(
            id=1,
            frequency='weekly',
            days_of_week=[1, 3, 5],
            start_time='09:00',
            end_time='17:00',
            spot_id=4,
            user_id=5,
            vehicle_id=101
        )
        recurring_service.recurring_repo.get_by_id.return_value = mock_recurring
        
        # Mock reservation creation for each occurrence
        recurring_service.reservation_service.create_reservation.return_value = Mock(id=300)
        
        # Act
        occurrences = recurring_service.generate_occurrences(recurring_id, month, year)
        
        # Assert
        # February 2024 has 29 days, should have ~12 occurrences (Mon/Wed/Fri)
        assert len(occurrences) > 10
        assert len(occurrences) < 15
    
    def test_check_spot_availability_for_recurring(self, recurring_service):
        """Test checking spot availability for recurring reservations."""
        # Arrange
        spot_id = 4
        pattern = {
            'frequency': 'weekly',
            'days_of_week': [1, 3, 5],
            'start_time': '09:00',
            'end_time': '17:00',
            'start_date': datetime(2024, 1, 8),
            'end_date': datetime(2024, 3, 25)
        }
        
        # Mock availability check
        recurring_service.reservation_service.check_spot_availability.return_value = {
            'is_available': False,
            'conflicts': [
                {'date': '2024-01-10', 'reservation_id': 218},
                {'date': '2024-01-12', 'reservation_id': 233}
            ]
        }
        
        # Act
        availability = recurring_service.check_spot_availability(spot_id, pattern)
        
        # Assert
        assert availability['is_available'] is False
        assert len(availability['conflicts']) == 2
    
    def test_pause_recurring_reservation(self, recurring_service):
        """Test pausing a recurring reservation."""
        # Arrange
        recurring_id = 1
        pause_start = datetime(2024, 2, 1)
        pause_end = datetime(2024, 2, 15)
        
        # Mock recurring reservation
        mock_recurring = Mock(
            id=recurring_id,
            is_active=True,
            paused_periods=[]
        )
        recurring_service.recurring_repo.get_by_id.return_value = mock_recurring
        recurring_service.recurring_repo.update.return_value = mock_recurring
        
        # Act
        result = recurring_service.pause_recurring(recurring_id, pause_start, pause_end)
        
        # Assert
        assert result is True
        assert len(mock_recurring.paused_periods) == 1
        recurring_service.recurring_repo.update.assert_called_once()


class TestAnalyticsService:
    """Tests for the AnalyticsService."""
    
    @pytest.fixture
    def analytics_service(self):
        """Create an analytics service instance."""
        service = AnalyticsService()
        service.reservation_repo = Mock()
        service.spot_repo = Mock()
        service.user_repo = Mock()
        return service
    
    def test_get_revenue_report(self, analytics_service):
        """Test generating revenue report."""
        # Arrange
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock reservation data
        mock_reservations = [
            Mock(total_amount=20.00, payment_status='paid'),
            Mock(total_amount=12.00, payment_status='paid'),
            Mock(total_amount=30.00, payment_status='paid'),
            Mock(total_amount=14.00, payment_status='paid'),
            Mock(total_amount=10.00, payment_status='paid')
        ]
        analytics_service.reservation_repo.get_completed_in_date_range.return_value = mock_reservations
        
        # Act
        report = analytics_service.get_revenue_report(start_date, end_date)
        
        # Assert
        assert report['total_revenue'] == 86.00
        assert report['total_reservations'] == 5
        assert report['average_revenue_per_reservation'] == 17.20
    
    def test_get_occupancy_forecast(self, analytics_service):
        """Test getting occupancy forecast."""
        # Arrange
        start_date = datetime(2024, 1, 20)
        days = 7
        
        # Mock current reservations
        current_reservations = [
            Mock(date='2024-01-20', count=15),
            Mock(date='2024-01-21', count=12),
            Mock(date='2024-01-22', count=18),
            Mock(date='2024-01-23', count=20),
            Mock(date='2024-01-24', count=22),
            Mock(date='2024-01-25', count=25),
            Mock(date='2024-01-26', count=19)
        ]
        analytics_service.reservation_repo.get_daily_counts.return_value = current_reservations
        
        # Mock historical data for trend analysis
        analytics_service.reservation_repo.get_historical_trends.return_value = {
            'avg_growth_rate': 0.05,
            'seasonality_factors': {'Monday': 0.8, 'Tuesday': 0.9, 'Wednesday': 1.0, 
                                   'Thursday': 1.1, 'Friday': 1.2, 'Saturday': 1.3, 'Sunday': 0.7}
        }
        
        # Act
        forecast = analytics_service.get_occupancy_forecast(start_date, days)
        
        # Assert
        assert len(forecast) == days
        assert 'date' in forecast[0]
        assert 'predicted_occupancy' in forecast[0]
        assert 'confidence_interval' in forecast[0]
    
    def test_get_user_behavior_analytics(self, analytics_service, user_reservations):
        """Test getting user behavior analytics."""
        # Arrange
        user_id = 5
        
        # Mock user reservations
        mock_reservations = [
            Mock(status='completed', total_amount=20.00, start_time=datetime(2023, 12, 10)),
            Mock(status='completed', total_amount=30.00, start_time=datetime(2023, 12, 30)),
            Mock(status='cancelled', total_amount=12.00, start_time=datetime(2023, 12, 23)),
            Mock(status='no_show', total_amount=24.00, start_time=datetime(2023, 12, 5))
        ]
        analytics_service.reservation_repo.get_by_user.return_value = mock_reservations
        
        # Act
        analytics = analytics_service.get_user_behavior_analytics(user_id)
        
        # Assert
        assert analytics['user_id'] == user_id
        assert analytics['total_reservations'] == 4
        assert analytics['completed_reservations'] == 2
        assert analytics['cancellation_rate'] == 0.25
        assert analytics['no_show_rate'] == 0.25
        assert analytics['total_spent'] == 50.00
    
    def test_get_peak_hours_analysis(self, analytics_service):
        """Test analyzing peak hours."""
        # Arrange
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock hourly distribution
        hourly_distribution = {
            8: 5, 9: 12, 10: 15, 11: 18, 12: 20,
            13: 22, 14: 19, 15: 17, 16: 14, 17: 10,
            18: 8, 19: 6, 20: 4
        }
        analytics_service.reservation_repo.get_hourly_distribution.return_value = hourly_distribution
        
        # Act
        peak_hours = analytics_service.get_peak_hours_analysis(start_date, end_date)
        
        # Assert
        assert peak_hours['peak_hour'] == 13  # 1 PM
        assert peak_hours['peak_count'] == 22
        assert len(peak_hours['top_5_hours']) == 5
        assert peak_hours['top_5_hours'][0]['hour'] == 13
    
    def test_get_spot_type_performance(self, analytics_service):
        """Test analyzing performance by spot type."""
        # Arrange
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock data
        analytics_service.spot_repo.get_all_types.return_value = ['standard', 'vip', 'ev_charging', 'oversize']
        
        def mock_get_revenue_by_type(spot_type, start, end):
            revenue_map = {
                'standard': 500.00,
                'vip': 300.00,
                'ev_charging': 150.00,
                'oversize': 200.00
            }
            return revenue_map.get(spot_type, 0)
        
        analytics_service.reservation_repo.get_revenue_by_type.side_effect = mock_get_revenue_by_type
        
        def mock_get_occupancy_by_type(spot_type, start, end):
            occupancy_map = {
                'standard': 0.45,
                'vip': 0.60,
                'ev_charging': 0.30,
                'oversize': 0.25
            }
            return occupancy_map.get(spot_type, 0)
        
        analytics_service.spot_repo.get_occupancy_by_type.side_effect = mock_get_occupancy_by_type
        
        # Act
        performance = analytics_service.get_spot_type_performance(start_date, end_date)
        
        # Assert
        assert len(performance) == 4
        assert performance['standard']['revenue'] == 500.00
        assert performance['standard']['occupancy'] == 0.45
        assert performance['vip']['revenue_per_spot'] > performance['standard']['revenue_per_spot']


# Integration tests combining multiple services
class TestServiceIntegration:
    """Integration tests for multiple services working together."""
    
    def test_complete_booking_and_payment_flow(
        self, 
        reservation_service,
        payment_service,
        notification_service,
        spot_service,
        reservation_factory
    ):
        """Test complete booking and payment flow across services."""
        # Step 1: Find available spot
        with patch.object(spot_service, 'find_available_spots') as mock_find:
            mock_find.return_value = [Mock(id=4, spot_type='standard', hourly_rate=3.00)]
            available_spots = spot_service.find_available_spots(
                datetime(2024, 1, 25, 9, 0),
                datetime(2024, 1, 25, 17, 0)
            )
            assert len(available_spots) > 0
        
        # Step 2: Create reservation
        with patch.object(reservation_service, 'create_reservation') as mock_create:
            mock_reservation = reservation_factory(
                id=350,
                user_id=5,
                spot_id=4,
                total_amount=24.00
            )
            mock_create.return_value = mock_reservation
            
            reservation = reservation_service.create_reservation(
                user_id=5,
                spot_id=4,
                vehicle_id=101,
                start_time=datetime(2024, 1, 25, 9, 0),
                end_time=datetime(2024, 1, 25, 17, 0)
            )
            assert reservation.id == 350
        
        # Step 3: Process payment
        with patch.object(payment_service, 'process_payment') as mock_payment:
            mock_payment.return_value = {
                'status': 'success',
                'payment_id': 400,
                'transaction_id': 'ch_test123'
            }
            
            payment_result = payment_service.process_payment(
                reservation_id=350,
                amount=24.00,
                payment_method={'type': 'credit_card', 'token': 'tok_visa'}
            )
            assert payment_result['status'] == 'success'
        
        # Step 4: Send confirmation
        with patch.object(notification_service, 'send_confirmation') as mock_notify:
            mock_notify.return_value = {'status': 'sent'}
            
            notify_result = notification_service.send_confirmation(
                user_email="user@example.com",
                reservation_details={'id': 350, 'confirmation_code': 'CONF-350-TEST'}
            )
            assert notify_result['status'] == 'sent'
    
    def test_cancellation_and_waitlist_flow(
        self,
        reservation_service,
        payment_service,
        waitlist_service,
        notification_service
    ):
        """Test cancellation and waitlist notification flow."""
        # Step 1: Cancel reservation
        with patch.object(reservation_service, 'cancel_reservation') as mock_cancel:
            mock_cancel.return_value = Mock(
                id=206,
                status='cancelled',
                spot_id=4,
                start_time=datetime(2024, 1, 25, 9, 0),
                end_time=datetime(2024, 1, 25, 17, 0)
            )
            
            cancelled = reservation_service.cancel_reservation(
                reservation_id=206,
                user_id=10,
                reason="Change of plans"
            )
            assert cancelled.status == 'cancelled'
        
        # Step 2: Process refund
        with patch.object(payment_service, 'process_refund') as mock_refund:
            mock_refund.return_value = {'status': 'success', 'refund_id': 500}
            
            refund_result = payment_service.process_refund(
                payment_id=306,
                amount=12.00,
                reason="Cancellation"
            )
            assert refund_result['status'] == 'success'
        
        # Step 3: Notify waitlist
        with patch.object(waitlist_service, 'notify_next_available') as mock_notify:
            mock_notify.return_value = {
                'notified_user_id': 17,
                'waitlist_id': 1
            }
            
            notification = waitlist_service.notify_next_available(
                spot_id=4,
                date_from=datetime(2024, 1, 25, 9, 0)
            )
            assert notification['notified_user_id'] == 17
        
        # Step 4: Send waitlist notification
        with patch.object(notification_service, 'send_waitlist_notification') as mock_send:
            mock_send.return_value = {'email_sent': True, 'sms_sent': True}
            
            result = notification_service.send_waitlist_notification(
                user=Mock(email='user17@example.com'),
                spot_details={'spot_id': 4, 'date_from': '2024-01-25T09:00:00Z'}
            )
            assert result['email_sent'] is True
    
    def test_recurring_reservation_flow(
        self,
        recurring_service,
        reservation_service,
        spot_service
    ):
        """Test recurring reservation generation flow."""
        # Step 1: Create recurring pattern
        with patch.object(recurring_service, 'create_recurring_reservation') as mock_create:
            mock_create.return_value = Mock(
                id=4,
                frequency='weekly',
                days_of_week=[1, 3, 5]
            )
            
            recurring = recurring_service.create_recurring_reservation(
                user_id=5,
                spot_id=4,
                vehicle_id=101,
                frequency='weekly',
                start_date=datetime(2024, 2, 1),
                end_date=datetime(2024, 2, 29),
                days_of_week=[1, 3, 5],
                start_time=time(9, 0),
                end_time=time(17, 0)
            )
            assert recurring.frequency == 'weekly'
        
        # Step 2: Check spot availability for recurring
        with patch.object(recurring_service, 'check_spot_availability') as mock_check:
            mock_check.return_value = {
                'is_available': True,
                'conflicts': []
            }
            
            availability = recurring_service.check_spot_availability(
                spot_id=4,
                pattern={'days_of_week': [1, 3, 5]}
            )
            assert availability['is_available'] is True
        
        # Step 3: Generate occurrences
        with patch.object(recurring_service, 'generate_occurrences') as mock_generate:
            mock_generate.return_value = [Mock(id=i) for i in range(12)]
            
            occurrences = recurring_service.generate_occurrences(
                recurring_id=4,
                month=2,
                year=2024
            )
            assert len(occurrences) == 12


# Performance and edge cases
class TestServiceEdgeCases:
    """Tests for service edge cases and error conditions."""
    
    def test_concurrent_reservation_attempts(self, reservation_service, reservation_factory):
        """Test handling concurrent reservation attempts for same spot."""
        # Simulate race condition
        spot_id = 4
        start_time = datetime(2024, 1, 25, 9, 0)
        end_time = datetime(2024, 1, 25, 17, 0)
        
        # Mock spot availability check
        reservation_service.spot_repo.is_available.side_effect = [True, True, False]
        
        # Mock user validation
        reservation_service.user_repo.get_by_id.return_value = Mock(
            is_active=True,
            has_valid_payment_method=True
        )
        
        # Mock repository create to simulate race condition
        def create_with_conflict(*args, **kwargs):
            # After first creation, subsequent attempts should fail
            if reservation_service.reservation_repo.create.call_count > 0:
                raise Exception("Duplicate entry")
            return reservation_factory(spot_id=spot_id)
        
        reservation_service.reservation_repo.create.side_effect = create_with_conflict
        
        # First attempt should succeed
        result1 = reservation_service.create_reservation(
            user_id=5,
            spot_id=spot_id,
            vehicle_id=101,
            start_time=start_time,
            end_time=end_time
        )
        assert result1 is not None
        
        # Second attempt should fail
        with pytest.raises(Exception) as exc_info:
            reservation_service.create_reservation(
                user_id=6,
                spot_id=spot_id,
                vehicle_id=102,
                start_time=start_time,
                end_time=end_time
            )
        
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_payment_timeout_handling(self, payment_service):
        """Test handling payment gateway timeout."""
        reservation_id = 218
        amount = 24.00
        
        # Mock reservation
        payment_service.reservation_repo.get_by_id.return_value = Mock(
            id=reservation_id,
            payment_status='pending'
        )
        
        # Mock payment gateway timeout
        with patch('app.services.payment_gateway.charge') as mock_charge:
            mock_charge.side_effect = TimeoutError("Gateway timeout")
            
            with pytest.raises(TimeoutError):
                payment_service.process_payment(
                    reservation_id=reservation_id,
                    amount=amount,
                    payment_method={'token': 'tok_visa'}
                )
            
            # Verify payment was marked as failed
            payment_service.reservation_repo.update_payment_status.assert_called_with(
                reservation_id, 'failed'
            )
    
    def test_notification_failure_fallback(self, notification_service):
        """Test notification failure and fallback mechanism."""
        user_email = "user@example.com"
        user_phone = "+1234567890"
        
        # Email fails, should fall back to SMS
        notification_service.email_service.send.side_effect = Exception("Email service down")
        notification_service.sms_service.send.return_value = {'id': 'sms_123', 'status': 'sent'}
        
        result = notification_service.send_confirmation(
            user_email,
            {'confirmation_code': 'TEST123'},
            phone=user_phone
        )
        
        assert result['method_used'] == 'sms'
        assert result['status'] == 'sent'
    
    def test_reservation_extension_beyond_allowed(self, reservation_service):
        """Test extending reservation beyond allowed maximum."""
        reservation_id = 215
        current_end = datetime(2024, 1, 15, 17, 0)
        new_end = datetime(2024, 1, 16, 17, 0)  # 24 hours later
        
        # Mock reservation
        mock_reservation = Mock(
            id=reservation_id,
            status='checked_in',
            end_time=current_end,
            max_extension_hours=4  # Only 4 hours allowed
        )
        reservation_service.reservation_repo.get_by_id.return_value = mock_reservation
        
        with pytest.raises(BusinessRuleViolation) as exc_info:
            reservation_service.extend_reservation(
                reservation_id=reservation_id,
                user_id=20,
                new_end_time=new_end
            )
        
        assert "exceeds maximum extension" in str(exc_info.value).lower()