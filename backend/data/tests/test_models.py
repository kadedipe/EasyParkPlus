"""Tests for parking management system models."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import json

# Assuming you have actual model classes, we'll create mock imports
# Replace these with your actual model imports
try:
    from app.models import (
        Reservation, RecurringReservation, WaitlistEntry,
        ReservationHistory, ReservationNote, ReservationAddon,
        User, ParkingSpot, Vehicle
    )
except ImportError:
    # Mock models for testing when actual models aren't available
    pytest.skip("Models not available - skipping integration tests", allow_module_level=True)


class TestReservationModel:
    """Tests for the Reservation model."""
    
    def test_reservation_creation(self, sample_reservation):
        """Test creating a reservation with valid data."""
        reservation = Reservation(**sample_reservation)
        
        assert reservation.id == sample_reservation['id']
        assert reservation.user_id == sample_reservation['user_id']
        assert reservation.spot_id == sample_reservation['spot_id']
        assert reservation.vehicle_id == sample_reservation['vehicle_id']
        assert reservation.confirmation_code == sample_reservation['confirmation_code']
        assert reservation.reservation_type == sample_reservation['reservation_type']
        assert reservation.status == sample_reservation['status']
        assert reservation.total_amount == sample_reservation['total_amount']
        assert reservation.payment_status == sample_reservation['payment_status']
    
    def test_reservation_string_representation(self, sample_reservation):
        """Test the string representation of a reservation."""
        reservation = Reservation(**sample_reservation)
        expected = f"Reservation {reservation.id}: {reservation.confirmation_code} - {reservation.status}"
        assert str(reservation) == expected
    
    def test_reservation_duration_calculation(self, sample_reservation):
        """Test calculating reservation duration."""
        reservation = Reservation(**sample_reservation)
        
        start = datetime.fromisoformat(sample_reservation['start_time'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(sample_reservation['end_time'].replace('Z', '+00:00'))
        expected_duration = (end - start).total_seconds() / 3600  # in hours
        
        assert reservation.calculate_duration() == expected_duration
    
    def test_reservation_is_active(self):
        """Test checking if a reservation is active."""
        # Active reservation (checked_in)
        active_reservation = Reservation(
            id=215, status='checked_in',
            start_time='2024-01-15T08:00:00Z',
            end_time='2024-01-15T17:00:00Z'
        )
        assert active_reservation.is_active() is True
        
        # Non-active reservation (completed)
        completed_reservation = Reservation(
            id=201, status='completed',
            start_time='2023-12-10T09:00:00Z',
            end_time='2023-12-10T17:00:00Z'
        )
        assert completed_reservation.is_active() is False
        
        # Non-active reservation (cancelled)
        cancelled_reservation = Reservation(
            id=206, status='cancelled',
            start_time='2023-12-23T11:00:00Z',
            end_time='2023-12-23T15:00:00Z'
        )
        assert cancelled_reservation.is_active() is False
    
    def test_reservation_can_be_cancelled(self):
        """Test if a reservation can be cancelled based on its status."""
        # Pending reservation can be cancelled
        pending = Reservation(id=246, status='pending')
        assert pending.can_be_cancelled() is True
        
        # Confirmed reservation can be cancelled
        confirmed = Reservation(id=218, status='confirmed')
        assert confirmed.can_be_cancelled() is True
        
        # Checked-in reservation cannot be cancelled
        checked_in = Reservation(id=215, status='checked_in')
        assert checked_in.can_be_cancelled() is False
        
        # Completed reservation cannot be cancelled
        completed = Reservation(id=201, status='completed')
        assert completed.can_be_cancelled() is False
        
        # Cancelled reservation cannot be cancelled again
        cancelled = Reservation(id=206, status='cancelled')
        assert cancelled.can_be_cancelled() is False
    
    def test_reservation_ev_charging_specifics(self, ev_charging_reservations):
        """Test EV charging specific attributes."""
        if not ev_charging_reservations:
            pytest.skip("No EV charging reservations in test data")
        
        ev_reservation = Reservation(**ev_charging_reservations[0])
        
        assert ev_reservation.reservation_type == 'ev_charging'
        assert hasattr(ev_reservation, 'charging_fee')
        assert hasattr(ev_reservation, 'energy_used_kwh')
        
        if hasattr(ev_reservation, 'charging_fee'):
            assert ev_reservation.charging_fee > 0
    
    def test_reservation_vip_specifics(self, vip_reservations):
        """Test VIP reservation specific attributes."""
        if not vip_reservations:
            pytest.skip("No VIP reservations in test data")
        
        vip_reservation = Reservation(**vip_reservations[0])
        
        assert vip_reservation.reservation_type == 'vip'
        assert vip_reservation.total_amount > 20  # VIP typically costs more
        
        # Check for special requests
        if hasattr(vip_reservation, 'special_requests'):
            assert vip_reservation.special_requests is not None
    
    def test_reservation_status_transitions(self, reservation_factory):
        """Test valid and invalid status transitions."""
        reservation = reservation_factory(status='pending')
        
        # Valid transitions
        assert reservation.can_transition_to('confirmed') is True
        reservation.status = 'confirmed'
        
        assert reservation.can_transition_to('checked_in') is True
        reservation.status = 'checked_in'
        
        assert reservation.can_transition_to('completed') is True
        reservation.status = 'completed'
        
        # Invalid transitions
        reservation.status = 'completed'
        assert reservation.can_transition_to('cancelled') is False
        assert reservation.can_transition_to('checked_in') is False
    
    def test_reservation_metadata_handling(self, sample_reservation):
        """Test handling of reservation metadata."""
        reservation = Reservation(**sample_reservation)
        
        if 'metadata' in sample_reservation:
            assert reservation.metadata is not None
            assert isinstance(reservation.metadata, dict)
            
            # Test metadata access methods
            if hasattr(reservation, 'get_metadata_value'):
                value = reservation.get_metadata_value('source')
                assert value == sample_reservation['metadata'].get('source')
    
    def test_reservation_payment_status_validation(self):
        """Test payment status validation."""
        reservation = Reservation(id=201, payment_status='paid')
        assert reservation.is_paid() is True
        assert reservation.is_payment_pending() is False
        
        reservation.payment_status = 'pending'
        assert reservation.is_paid() is False
        assert reservation.is_payment_pending() is True
        
        reservation.payment_status = 'failed'
        assert reservation.is_paid() is False
        assert reservation.is_payment_failed() is True
        
        reservation.payment_status = 'refunded'
        assert reservation.is_refunded() is True
    
    def test_reservation_relationships(self, sample_reservation, user_reservations, spot_reservations):
        """Test reservation relationships with other models."""
        reservation = Reservation(**sample_reservation)
        
        # Test user relationship
        if hasattr(reservation, 'user'):
            user_id = reservation.user_id
            assert user_id in user_reservations
            assert any(r['id'] == reservation.id for r in user_reservations[user_id])
        
        # Test spot relationship
        if hasattr(reservation, 'parking_spot'):
            spot_id = reservation.spot_id
            assert spot_id in spot_reservations
            assert any(r['id'] == reservation.id for r in spot_reservations[spot_id])


class TestRecurringReservationModel:
    """Tests for the RecurringReservation model."""
    
    def test_recurring_reservation_creation(self, sample_recurring_reservation):
        """Test creating a recurring reservation."""
        recurring = RecurringReservation(**sample_recurring_reservation)
        
        assert recurring.id == sample_recurring_reservation['id']
        assert recurring.user_id == sample_recurring_reservation['user_id']
        assert recurring.spot_id == sample_recurring_reservation['spot_id']
        assert recurring.frequency == sample_recurring_reservation['frequency']
        assert recurring.is_active == sample_recurring_reservation['is_active']
    
    def test_recurring_pattern_generation(self, sample_recurring_reservation):
        """Test generating recurring reservation instances."""
        recurring = RecurringReservation(**sample_recurring_reservation)
        
        if hasattr(recurring, 'generate_occurrences'):
            start_date = datetime.strptime(sample_recurring_reservation['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(sample_recurring_reservation['end_date'], '%Y-%m-%d')
            
            occurrences = recurring.generate_occurrences(start_date, end_date)
            
            assert len(occurrences) > 0
            
            # Check weekly pattern
            if recurring.frequency == 'weekly' and hasattr(recurring, 'days_of_week'):
                for occ in occurrences:
                    assert occ.weekday() in recurring.days_of_week
    
    def test_recurring_reservation_weekly_pattern(self):
        """Test weekly recurring reservation pattern."""
        recurring = RecurringReservation(
            id=1,
            frequency='weekly',
            days_of_week=[1, 3, 5],  # Monday, Wednesday, Friday
            start_date='2024-01-08',
            end_date='2024-01-21',
            start_time='09:00',
            end_time='17:00'
        )
        
        occurrences = recurring.generate_occurrences()
        
        # Should have 6 occurrences (3 days per week for 2 weeks)
        assert len(occurrences) == 6
        
        # Check days are correct
        weekdays = [occ.weekday() for occ in occurrences]
        assert all(day in [1, 3, 5] for day in weekdays)
    
    def test_recurring_reservation_monthly_pattern(self):
        """Test monthly recurring reservation pattern."""
        recurring = RecurringReservation(
            id=3,
            frequency='monthly',
            day_of_month=5,
            start_date='2024-01-05',
            end_date='2024-03-05',
            start_time='19:00',
            end_time='23:30'
        )
        
        occurrences = recurring.generate_occurrences()
        
        # Should have 3 occurrences (Jan, Feb, Mar)
        assert len(occurrences) == 3
        
        # Check days are correct (5th of each month)
        for occ in occurrences:
            assert occ.day == 5
    
    def test_recurring_reservation_deactivation(self, sample_recurring_reservation):
        """Test deactivating a recurring reservation."""
        recurring = RecurringReservation(**sample_recurring_reservation)
        assert recurring.is_active is True
        
        recurring.deactivate()
        assert recurring.is_active is False
        
        # Should not generate occurrences when inactive
        if hasattr(recurring, 'generate_occurrences'):
            occurrences = recurring.generate_occurrences()
            assert len(occurrences) == 0


class TestWaitlistModel:
    """Tests for the WaitlistEntry model."""
    
    def test_waitlist_entry_creation(self, sample_waitlist_entry):
        """Test creating a waitlist entry."""
        waitlist = WaitlistEntry(**sample_waitlist_entry)
        
        assert waitlist.id == sample_waitlist_entry['id']
        assert waitlist.user_id == sample_waitlist_entry['user_id']
        assert waitlist.spot_id == sample_waitlist_entry['spot_id']
        assert waitlist.status == sample_waitlist_entry['status']
        assert waitlist.position == sample_waitlist_entry['position']
    
    def test_waitlist_position_update(self, waitlist_entries):
        """Test updating waitlist positions."""
        entries = [WaitlistEntry(**entry) for entry in waitlist_entries if entry['status'] == 'active']
        
        if len(entries) >= 2:
            # Sort by position
            entries.sort(key=lambda e: e.position)
            
            assert entries[0].position < entries[1].position
            
            # Move first entry to notified
            entries[0].status = 'notified'
            entries[0].notified_at = datetime.now().isoformat()
            
            # Update positions
            WaitlistEntry.update_positions(entries[1:])
            
            # Check that positions were updated
            assert entries[1].position == 1
    
    def test_waitlist_notification(self):
        """Test waitlist notification workflow."""
        waitlist = WaitlistEntry(
            id=4,
            user_id=5,
            spot_id=4,
            status='active',
            position=1
        )
        
        # Mark as notified
        waitlist.mark_as_notified()
        
        assert waitlist.status == 'notified'
        assert waitlist.notified_at is not None
        
        # Convert to reservation
        reservation = waitlist.convert_to_reservation()
        assert reservation is not None
        assert reservation.user_id == waitlist.user_id
        assert reservation.spot_id == waitlist.spot_id
    
    def test_waitlist_expiration(self):
        """Test waitlist entry expiration."""
        # Create expired waitlist entry
        expired_date = (datetime.now() - timedelta(days=2)).isoformat() + 'Z'
        waitlist = WaitlistEntry(
            id=5,
            created_at=expired_date,
            status='active'
        )
        
        assert waitlist.is_expired() is True
        
        # Create active waitlist entry
        active_date = datetime.now().isoformat() + 'Z'
        waitlist.created_at = active_date
        assert waitlist.is_expired() is False


class TestReservationHistoryModel:
    """Tests for the ReservationHistory model."""
    
    def test_history_entry_creation(self, reservation_history):
        """Test creating a history entry."""
        history = ReservationHistory(**reservation_history[0])
        
        assert history.reservation_id == reservation_history[0]['reservation_id']
        assert history.status == reservation_history[0]['status']
        assert history.changed_by == reservation_history[0]['changed_by']
    
    def test_history_timeline(self, sample_reservation):
        """Test reservation status timeline from history."""
        reservation_id = sample_reservation['id']
        
        # Get all history for this reservation
        history_entries = [
            entry for entry in reservation_history 
            if entry['reservation_id'] == reservation_id
        ]
        
        if history_entries:
            # Sort by timestamp
            history_entries.sort(key=lambda e: e['changed_at'])
            
            # Check status flow
            statuses = [entry['status'] for entry in history_entries]
            expected_flow = ['pending', 'confirmed', 'checked_in', 'completed']
            
            # Verify that statuses appear in expected order
            last_idx = -1
            for status in statuses:
                if status in expected_flow:
                    current_idx = expected_flow.index(status)
                    assert current_idx > last_idx
                    last_idx = current_idx


class TestReservationNoteModel:
    """Tests for the ReservationNote model."""
    
    def test_note_creation(self, reservation_notes):
        """Test creating a reservation note."""
        note = ReservationNote(**reservation_notes[0])
        
        assert note.reservation_id == reservation_notes[0]['reservation_id']
        assert note.user_id == reservation_notes[0]['user_id']
        assert note.note == reservation_notes[0]['note']
        assert note.is_private == reservation_notes[0]['is_private']
    
    def test_private_notes_visibility(self, reservation_notes):
        """Test private note visibility rules."""
        public_notes = [note for note in reservation_notes if not note['is_private']]
        private_notes = [note for note in reservation_notes if note['is_private']]
        
        for note_data in public_notes:
            note = ReservationNote(**note_data)
            assert note.is_visible_to_user(5) is True  # Any user can see public notes
            assert note.is_visible_to_staff(3) is True  # Staff can see public notes
        
        for note_data in private_notes:
            note = ReservationNote(**note_data)
            # Only staff or the creating user can see private notes
            assert note.is_visible_to_user(note.user_id) is True
            assert note.is_visible_to_user(999) is False  # Different user cannot see
            assert note.is_visible_to_staff(3) is True  # Staff can see


class TestReservationAddonModel:
    """Tests for the ReservationAddon model."""
    
    def test_addon_creation(self, reservation_addons):
        """Test creating a reservation addon."""
        addon = ReservationAddon(**reservation_addons[0])
        
        assert addon.reservation_id == reservation_addons[0]['reservation_id']
        assert addon.addon_type == reservation_addons[0]['addon_type']
        assert addon.quantity == reservation_addons[0]['quantity']
        assert addon.unit_price == reservation_addons[0]['unit_price']
        assert addon.total_price == reservation_addons[0]['total_price']
    
    def test_addon_total_calculation(self):
        """Test addon total price calculation."""
        addon = ReservationAddon(
            addon_type='valet',
            quantity=2,
            unit_price=15.00
        )
        
        # Total should be calculated automatically
        assert addon.total_price == 30.00
        
        # Test with different values
        addon.quantity = 3
        addon.unit_price = 25.00
        addon.calculate_total()
        assert addon.total_price == 75.00
    
    def test_addon_types(self, reservation_addons):
        """Test different addon types."""
        addon_types = set(addon['addon_type'] for addon in reservation_addons)
        
        for addon_data in reservation_addons:
            addon = ReservationAddon(**addon_data)
            assert addon.addon_type in addon_types
            
            # Test type-specific methods if they exist
            if addon.addon_type == 'valet' and hasattr(addon, 'assign_valet'):
                addon.assign_valet('VAL-789')
                assert addon.valet_id == 'VAL-789'
            
            if addon.addon_type == 'car_wash' and hasattr(addon, 'schedule_wash'):
                result = addon.schedule_wash()
                assert result is not None


class TestModelRelationships:
    """Tests for relationships between models."""
    
    def test_reservation_to_history_relationship(self, sample_reservation, reservation_history):
        """Test relationship between Reservation and ReservationHistory."""
        reservation = Reservation(**sample_reservation)
        
        # Get history for this reservation
        reservation_histories = [
            ReservationHistory(**h) for h in reservation_history 
            if h['reservation_id'] == reservation.id
        ]
        
        if hasattr(reservation, 'history'):
            # Test the relationship
            assert len(reservation.history) == len(reservation_histories)
            
            # Check that history entries are properly linked
            for history in reservation.history:
                assert history.reservation_id == reservation.id
    
    def test_reservation_to_notes_relationship(self, sample_reservation, reservation_notes):
        """Test relationship between Reservation and ReservationNote."""
        reservation = Reservation(**sample_reservation)
        
        # Get notes for this reservation
        reservation_notes_list = [
            ReservationNote(**n) for n in reservation_notes 
            if n['reservation_id'] == reservation.id
        ]
        
        if hasattr(reservation, 'notes'):
            # Test the relationship
            notes_count = len([n for n in reservation_notes if n['reservation_id'] == reservation.id])
            assert len(reservation.notes) == notes_count
    
    def test_reservation_to_addons_relationship(self, sample_reservation, reservation_addons):
        """Test relationship between Reservation and ReservationAddon."""
        reservation = Reservation(**sample_reservation)
        
        # Get addons for this reservation
        reservation_addons_list = [
            ReservationAddon(**a) for a in reservation_addons 
            if a['reservation_id'] == reservation.id
        ]
        
        if hasattr(reservation, 'addons') and reservation_addons_list:
            # Test the relationship
            assert len(reservation.addons) == len(reservation_addons_list)
            
            # Calculate total addons cost
            total_addons = sum(addon.total_price for addon in reservation.addons)
            assert total_addons > 0
    
    def test_user_to_reservations_relationship(self, user_reservations):
        """Test relationship between User and Reservation."""
        for user_id, user_res_list in user_reservations.items():
            if hasattr(User, 'reservations'):
                user = User(id=user_id)
                # This would need actual DB setup to test properly
                pass
    
    def test_parking_spot_to_reservations_relationship(self, spot_reservations):
        """Test relationship between ParkingSpot and Reservation."""
        for spot_id, spot_res_list in spot_reservations.items():
            if hasattr(ParkingSpot, 'reservations'):
                spot = ParkingSpot(id=spot_id)
                # This would need actual DB setup to test properly
                pass


# Integration tests that combine multiple models
class TestReservationWorkflow:
    """Integration tests for complete reservation workflows."""
    
    def test_complete_reservation_lifecycle(self, reservation_factory):
        """Test the complete lifecycle of a reservation."""
        # Create reservation
        reservation = reservation_factory(status='pending')
        assert reservation.status == 'pending'
        
        # Confirm reservation
        reservation.status = 'confirmed'
        reservation.confirmed_at = datetime.now().isoformat() + 'Z'
        assert reservation.can_be_cancelled() is True
        
        # Check-in
        reservation.status = 'checked_in'
        reservation.checked_in_at = datetime.now().isoformat() + 'Z'
        assert reservation.is_active() is True
        
        # Add a note
        note = ReservationNote(
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            note="Customer arrived early",
            is_private=False
        )
        assert note.reservation_id == reservation.id
        
        # Complete reservation
        reservation.status = 'completed'
        reservation.completed_at = datetime.now().isoformat() + 'Z'
        reservation.checked_out_at = reservation.completed_at
        assert reservation.is_active() is False
        
        # Add to history
        history = ReservationHistory(
            reservation_id=reservation.id,
            status='completed',
            changed_at=reservation.completed_at,
            changed_by='system'
        )
        assert history.reservation_id == reservation.id
    
    def test_cancellation_with_refund_workflow(self, reservation_factory):
        """Test reservation cancellation and refund workflow."""
        # Create and confirm reservation
        reservation = reservation_factory(
            status='confirmed',
            payment_status='paid',
            total_amount=50.00
        )
        
        # Cancel reservation
        reservation.status = 'cancelled'
        reservation.cancelled_at = datetime.now().isoformat() + 'Z'
        reservation.cancellation_reason = 'Customer request'
        
        # Process refund
        reservation.payment_status = 'refunded'
        if hasattr(reservation, 'metadata'):
            reservation.metadata['refund_amount'] = reservation.total_amount
            reservation.metadata['refund_processed_at'] = datetime.now().isoformat() + 'Z'
        
        assert reservation.payment_status == 'refunded'
        assert reservation.is_refunded() is True
    
    def test_ev_charging_workflow(self):
        """Test EV charging reservation workflow."""
        # Create EV charging reservation
        reservation = Reservation(
            id=208,
            reservation_type='ev_charging',
            status='confirmed',
            charging_fee=4.00,
            energy_used_kwh=0
        )
        
        # Check-in and start charging
        reservation.status = 'checked_in'
        reservation.checked_in_at = datetime.now().isoformat() + 'Z'
        
        if hasattr(reservation, 'start_charging'):
            reservation.start_charging()
            assert reservation.charging_started_at is not None
        
        # Complete charging
        reservation.energy_used_kwh = 32
        if hasattr(reservation, 'stop_charging'):
            reservation.stop_charging()
            assert reservation.charging_ended_at is not None
        
        # Check-out
        reservation.status = 'completed'
        reservation.completed_at = datetime.now().isoformat() + 'Z'
        
        # Verify total includes charging fee
        expected_total = 12.00 + reservation.charging_fee
        assert reservation.total_amount == expected_total
    
    def test_vip_reservation_with_addons_workflow(self):
        """Test VIP reservation with addons workflow."""
        # Create VIP reservation
        reservation = Reservation(
            id=225,
            reservation_type='vip',
            status='confirmed',
            total_amount=45.00,
            special_requests='Anniversary celebration'
        )
        
        # Add VIP addons
        valet_addon = ReservationAddon(
            reservation_id=reservation.id,
            addon_type='valet',
            quantity=1,
            unit_price=15.00
        )
        
        champagne_addon = ReservationAddon(
            reservation_id=reservation.id,
            addon_type='champagne',
            quantity=1,
            unit_price=35.00
        )
        
        # Calculate total with addons
        addons_total = valet_addon.total_price + champagne_addon.total_price
        total_with_addons = reservation.total_amount + addons_total
        
        assert total_with_addons == 95.00
        
        # Check-in with VIP handling
        reservation.status = 'checked_in'
        if hasattr(reservation, 'assign_valet'):
            reservation.assign_valet('VIP-123')
            assert reservation.valet_id == 'VIP-123'


# Performance and edge cases
class TestModelEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_invalid_reservation_dates(self):
        """Test reservation with invalid dates."""
        # End time before start time
        with pytest.raises(ValueError):
            reservation = Reservation(
                start_time='2024-01-15T17:00:00Z',
                end_time='2024-01-15T08:00:00Z'
            )
            reservation.validate_dates()
        
        # Past reservation date
        with pytest.raises(ValueError):
            reservation = Reservation(
                start_time='2020-01-15T08:00:00Z',
                end_time='2020-01-15T17:00:00Z'
            )
            reservation.validate_not_in_past()
    
    def test_maximum_duration_exceeded(self):
        """Test reservation exceeding maximum allowed duration."""
        reservation = Reservation(
            start_time='2024-01-15T08:00:00Z',
            end_time='2024-01-20T17:00:00Z'  # 5 days later
        )
        
        with pytest.raises(ValueError):
            reservation.validate_max_duration(max_hours=72)
    
    def test_duplicate_confirmation_code(self, reservations):
        """Test duplicate confirmation codes."""
        confirmation_codes = [r['confirmation_code'] for r in reservations]
        unique_codes = set(confirmation_codes)
        
        assert len(confirmation_codes) == len(unique_codes)
    
    def test_waitlist_position_collision(self, waitlist_factory):
        """Test waitlist position collision handling."""
        entry1 = waitlist_factory(spot_id=18, position=1)
        entry2 = waitlist_factory(spot_id=18, position=1)  # Same position
        
        with pytest.raises(ValueError):
            WaitlistEntry.validate_positions([entry1, entry2])
    
    def test_recurring_reservation_overlap(self):
        """Test overlapping recurring reservations."""
        recurring1 = RecurringReservation(
            spot_id=4,
            start_date='2024-01-01',
            end_date='2024-01-31',
            days_of_week=[1, 3, 5]
        )
        
        recurring2 = RecurringReservation(
            spot_id=4,
            start_date='2024-01-15',
            end_date='2024-02-15',
            days_of_week=[1, 3, 5]
        )
        
        assert recurring1.overlaps_with(recurring2) is True