# File: src/domain/strategies.py
"""
Strategy Pattern Implementation for Parking Management System

This module implements the Strategy Pattern to encapsulate different algorithms
for parking operations, pricing, and EV charging. Each strategy can be selected
at runtime based on vehicle type, slot type, or business rules.

Key Strategies:
1. Parking Allocation Strategies - Different algorithms for slot allocation
2. Pricing Strategies - Different pricing models for parking and charging
3. Charging Strategies - Different algorithms for EV charging optimization
4. Validation Strategies - Different validation rules

Benefits:
- Open/Closed Principle: New strategies can be added without modifying existing code
- Eliminates complex conditional logic
- Each strategy is independently testable
- Clear separation of concerns
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from enum import Enum

from .models import (
    ParkingSlot, Vehicle, ElectricVehicle,
    VehicleType, SlotType, ChargerType,
    Money, TimeRange, LicensePlate, Location
)
from .aggregates import ParkingLot, ChargingStation


# ============================================================================
# STRATEGY INTERFACES
# ============================================================================

class ParkingStrategy(ABC):
    """
    Abstract base class for parking strategies
    Defines the interface for slot allocation algorithms
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate a parking slot for the given vehicle
        Returns: ParkingSlot if available, None otherwise
        """
        pass
    
    @abstractmethod
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if vehicle can park in the given slot
        Returns: True if allowed, False otherwise
        """
        pass
    
    def get_strategy_name(self) -> str:
        """Get human-readable strategy name"""
        return self.__class__.__name__.replace("Strategy", "")
    
    def __str__(self) -> str:
        return f"{self.get_strategy_name()} Strategy"


class PricingStrategy(ABC):
    """
    Abstract base class for pricing strategies
    Defines the interface for fee calculation algorithms
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def calculate_parking_fee(
        self,
        slot: ParkingSlot,
        time_range: TimeRange,
        vehicle: Optional[Vehicle] = None
    ) -> Money:
        """
        Calculate parking fee based on slot, time, and vehicle
        Returns: Calculated fee
        """
        pass
    
    @abstractmethod
    def calculate_charging_fee(
        self,
        energy_kwh: float,
        charger_type: ChargerType,
        time_of_day: datetime
    ) -> Money:
        """
        Calculate EV charging fee
        Returns: Calculated fee
        """
        pass


class ChargingStrategy(ABC):
    """
    Abstract base class for EV charging strategies
    Defines the interface for charging optimization algorithms
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def optimize_charging(
        self,
        vehicle: ElectricVehicle,
        available_connectors: List[ChargerType],
        target_charge_percentage: float,
        max_time_hours: float
    ) -> Tuple[ChargerType, float, float]:
        """
        Optimize charging parameters
        Returns: (best_charger_type, estimated_time_hours, estimated_cost)
        """
        pass
    
    @abstractmethod
    def should_interrupt_charging(
        self,
        vehicle: ElectricVehicle,
        current_charger: ChargerType,
        new_charger: ChargerType,
        time_elapsed_hours: float
    ) -> bool:
        """
        Determine if charging should be interrupted for a better charger
        Returns: True if should interrupt, False otherwise
        """
        pass


class ValidationStrategy(ABC):
    """
    Abstract base class for validation strategies
    Defines the interface for validation algorithms
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def validate_vehicle(self, vehicle: Vehicle) -> Tuple[bool, str]:
        """
        Validate vehicle information
        Returns: (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def validate_license_plate(self, license_plate: LicensePlate) -> Tuple[bool, str]:
        """
        Validate license plate
        Returns: (is_valid, error_message)
        """
        pass


# ============================================================================
# PARKING ALLOCATION STRATEGIES
# ============================================================================

class StandardCarStrategy(ParkingStrategy):
    """
    Strategy: Standard car parking allocation
    - Looks for regular slots first
    - Falls back to premium slots
    - Does not consider EV slots
    """
    
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate slot for standard car
        Priority: Regular → Premium → Disabled (if allowed)
        """
        self.logger.debug(f"Allocating slot for {vehicle.vehicle_type.value} vehicle")
        
        # Check preferences
        preferred_type = None
        if preferences and "preferred_slot_type" in preferences:
            preferred_type = preferences["preferred_slot_type"]
        
        # Try preferred type first
        if preferred_type:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, preferred_type)
            if slot:
                return slot
        
        # Business logic for standard cars
        slot_types_to_try = [
            SlotType.REGULAR,
            SlotType.PREMIUM,
            SlotType.DISABLED  # Only if vehicle has disability permit (handled by can_park)
        ]
        
        for slot_type in slot_types_to_try:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, slot_type)
            if slot and self.can_park(parking_lot, vehicle, slot):
                return slot
        
        return None
    
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if standard car can park in given slot
        Business rules:
        - Cannot park in EV slots
        - Can park in disabled slots only with permit (simplified)
        """
        # Standard cars cannot use EV slots
        if slot.slot_type == SlotType.EV:
            return False
        
        # Check slot's own compatibility
        if not slot.can_accommodate_vehicle_type(vehicle.vehicle_type):
            return False
        
        # Additional business rule: Disabled slots require permit
        # (In real system, this would check vehicle.disabled_permit)
        if slot.slot_type == SlotType.DISABLED:
            # Simplified: Assume no disability permit
            return False
        
        return True


class ElectricCarStrategy(ParkingStrategy):
    """
    Strategy: Electric car parking allocation
    - Prefers EV charging slots
    - Can use regular slots if allowed by policies
    - Optimizes for charging availability
    """
    
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate slot for electric car
        Priority: EV → Regular (if allowed) → Premium
        """
        self.logger.debug(f"Allocating slot for electric vehicle: {vehicle.license_plate}")
        
        if not vehicle.vehicle_type.is_electric:
            raise ValueError("ElectricCarStrategy can only be used for electric vehicles")
        
        # Check if EV needs charging
        needs_charging = False
        if isinstance(vehicle, ElectricVehicle):
            needs_charging = vehicle.charge_percentage < 20.0  # Business rule
        
        # Check preferences
        preferred_type = None
        if preferences:
            if "preferred_slot_type" in preferences:
                preferred_type = preferences["preferred_slot_type"]
            if "needs_charging" in preferences:
                needs_charging = preferences["needs_charging"]
        
        # If needs charging, prioritize EV slots
        if needs_charging:
            ev_slot = parking_lot.find_available_slot(vehicle.vehicle_type, SlotType.EV)
            if ev_slot:
                return ev_slot
        
        # Try preferred type
        if preferred_type:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, preferred_type)
            if slot:
                return slot
        
        # Business logic for EVs
        if parking_lot.policies.ev_can_use_regular:
            slot_types_to_try = [
                SlotType.EV,          # Still try EV slots first
                SlotType.REGULAR,     # Then regular if allowed
                SlotType.PREMIUM,     # Then premium
            ]
        else:
            slot_types_to_try = [
                SlotType.EV,
                SlotType.PREMIUM,     # Premium might allow EVs
            ]
        
        for slot_type in slot_types_to_try:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, slot_type)
            if slot and self.can_park(parking_lot, vehicle, slot):
                return slot
        
        return None
    
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if electric car can park in given slot
        Business rules:
        - Can park in EV slots (preferred)
        - Can park in regular slots if policies allow
        - Cannot park in disabled slots without permit
        """
        if not vehicle.vehicle_type.is_electric:
            return False
        
        # Check slot's own compatibility
        if not slot.can_accommodate_vehicle_type(vehicle.vehicle_type):
            return False
        
        # EV slots are always allowed for EVs
        if slot.slot_type == SlotType.EV:
            return True
        
        # Regular slots allowed if policy permits
        if slot.slot_type == SlotType.REGULAR:
            return parking_lot.policies.ev_can_use_regular
        
        # Premium slots might allow EVs
        if slot.slot_type == SlotType.PREMIUM:
            return True
        
        # Disabled slots require permit (simplified)
        if slot.slot_type == SlotType.DISABLED:
            return False
        
        return False


class MotorcycleStrategy(ParkingStrategy):
    """
    Strategy: Motorcycle parking allocation
    - Motorcycles can share regular slots (business rule)
    - Prefers compact spaces
    - Lower parking rates
    """
    
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate slot for motorcycle
        Priority: Regular slots (can share), then others
        """
        self.logger.debug(f"Allocating slot for motorcycle: {vehicle.license_plate}")
        
        if vehicle.vehicle_type not in [VehicleType.MOTORCYCLE, VehicleType.EV_MOTORCYCLE]:
            raise ValueError("MotorcycleStrategy can only be used for motorcycles")
        
        # Check preferences
        preferred_type = None
        if preferences and "preferred_slot_type" in preferences:
            preferred_type = preferences["preferred_slot_type"]
        
        # Try preferred type first
        if preferred_type:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, preferred_type)
            if slot:
                return slot
        
        # Business logic for motorcycles
        # Motorcycles prefer regular slots (can share space)
        slot_types_to_try = [
            SlotType.REGULAR,     # Regular slots (can share)
            SlotType.PREMIUM,     # Premium if available
        ]
        
        # For electric motorcycles, also try EV slots
        if vehicle.vehicle_type == VehicleType.EV_MOTORCYCLE:
            slot_types_to_try.insert(0, SlotType.EV)
        
        for slot_type in slot_types_to_try:
            slot = parking_lot.find_available_slot(vehicle.vehicle_type, slot_type)
            if slot and self.can_park(parking_lot, vehicle, slot):
                return slot
        
        return None
    
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if motorcycle can park in given slot
        Business rules:
        - Can use regular slots (multiple bikes per slot possible)
        - EV motorcycles can use EV slots
        - Lower clearance requirements
        """
        # Check vehicle type
        if vehicle.vehicle_type not in [VehicleType.MOTORCYCLE, VehicleType.EV_MOTORCYCLE]:
            return False
        
        # Check slot compatibility
        if not slot.can_accommodate_vehicle_type(vehicle.vehicle_type):
            return False
        
        # EV motorcycles can use EV slots
        if vehicle.vehicle_type == VehicleType.EV_MOTORCYCLE and slot.slot_type == SlotType.EV:
            return True
        
        # Motorcycles can use regular and premium slots
        if slot.slot_type in [SlotType.REGULAR, SlotType.PREMIUM]:
            return True
        
        return False


class LargeVehicleStrategy(ParkingStrategy):
    """
    Strategy: Large vehicle parking allocation (trucks, buses)
    - Requires larger spaces
    - Higher parking rates
    - Limited availability
    """
    
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate slot for large vehicle
        Looks for slots with 'wide' feature or premium slots
        """
        self.logger.debug(f"Allocating slot for large vehicle: {vehicle.vehicle_type.value}")
        
        if vehicle.vehicle_type not in [VehicleType.TRUCK, VehicleType.BUS, VehicleType.EV_TRUCK]:
            raise ValueError("LargeVehicleStrategy can only be used for trucks and buses")
        
        # Large vehicles need wide slots
        # First, find all available slots that can accommodate the vehicle
        available_slots = []
        for slot in parking_lot._slots.values():
            if not slot.is_occupied and self.can_park(parking_lot, vehicle, slot):
                available_slots.append(slot)
        
        if not available_slots:
            return None
        
        # Prioritize slots with 'wide' feature
        wide_slots = [s for s in available_slots if s.has_feature("wide")]
        if wide_slots:
            # Return the first wide slot
            return wide_slots[0]
        
        # Otherwise return first available slot
        return available_slots[0]
    
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if large vehicle can park in given slot
        Business rules:
        - Needs wide space (or special handling)
        - Cannot use compact spaces
        - Higher rate applies
        """
        # Check vehicle type
        if vehicle.vehicle_type not in [VehicleType.TRUCK, VehicleType.BUS, VehicleType.EV_TRUCK]:
            return False
        
        # Check slot compatibility
        if not slot.can_accommodate_vehicle_type(vehicle.vehicle_type):
            return False
        
        # Large vehicles prefer wide slots or premium slots
        if slot.has_feature("wide"):
            return True
        
        # Premium slots might accommodate large vehicles
        if slot.slot_type == SlotType.PREMIUM:
            return True
        
        # Regular slots might work for smaller trucks
        if slot.slot_type == SlotType.REGULAR and vehicle.vehicle_type == VehicleType.TRUCK:
            # Check if slot is at the end of row (easier access)
            # Simplified: Assume 25% of regular slots can handle trucks
            return slot.number % 4 == 0  # Every 4th slot
        
        return False


class NearestEntryStrategy(ParkingStrategy):
    """
    Strategy: Allocate nearest slot to entry/exit
    - Optimizes for customer convenience
    - Higher rates for premium locations
    - Useful for disabled or elderly customers
    """
    
    def __init__(self, entry_points: Optional[List[Tuple[int, int]]] = None):
        """
        Initialize with entry point coordinates
        entry_points: List of (x, y) coordinates for entry points
        """
        super().__init__()
        self.entry_points = entry_points or [(0, 0)]  # Default entry at origin
    
    def allocate_slot(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ParkingSlot]:
        """
        Allocate nearest available slot to entry point
        """
        self.logger.debug(f"Finding nearest slot for {vehicle.license_plate}")
        
        # Get all available slots that can accommodate the vehicle
        available_slots = []
        for slot in parking_lot._slots.values():
            if not slot.is_occupied and slot.can_accommodate_vehicle_type(vehicle.vehicle_type):
                available_slots.append(slot)
        
        if not available_slots:
            return None
        
        # Calculate distance from each entry point
        slot_distances = []
        for slot in available_slots:
            min_distance = float('inf')
            for entry_x, entry_y in self.entry_points:
                # Simplified distance calculation based on slot number
                # In real system, would use actual coordinates
                distance = abs(slot.number - entry_x) + abs(slot.floor_level - entry_y)
                min_distance = min(min_distance, distance)
            slot_distances.append((slot, min_distance))
        
        # Sort by distance and return nearest
        slot_distances.sort(key=lambda x: x[1])
        return slot_distances[0][0]
    
    def can_park(
        self,
        parking_lot: ParkingLot,
        vehicle: Vehicle,
        slot: ParkingSlot
    ) -> bool:
        """
        Check if vehicle can park in slot (delegates to slot's own logic)
        """
        return slot.can_accommodate_vehicle_type(vehicle.vehicle_type)


# ============================================================================
# PRICING STRATEGIES
# ============================================================================

class StandardPricingStrategy(PricingStrategy):
    """
    Standard pricing strategy
    - Fixed hourly rates by slot type
    - Time-based discounts/penalties
    - Vehicle type multipliers
    """
    
    def calculate_parking_fee(
        self,
        slot: ParkingSlot,
        time_range: TimeRange,
        vehicle: Optional[Vehicle] = None
    ) -> Money:
        """
        Calculate parking fee using standard pricing model
        """
        self.logger.debug(f"Calculating standard parking fee for slot {slot.number}")
        
        # Base calculation from slot
        base_fee = slot.calculate_fee(time_range.duration)
        
        # Apply vehicle-specific multiplier
        if vehicle:
            multiplier = vehicle.get_parking_rate_multiplier()
            adjusted_amount = base_fee.amount * multiplier
            base_fee = Money(adjusted_amount, base_fee.currency)
        
        # Apply time-based rules
        base_fee = self._apply_time_based_rules(base_fee, time_range)
        
        # Apply slot feature premiums
        base_fee = self._apply_feature_premiums(base_fee, slot)
        
        return base_fee
    
    def calculate_charging_fee(
        self,
        energy_kwh: float,
        charger_type: ChargerType,
        time_of_day: datetime
    ) -> Money:
        """
        Calculate EV charging fee using standard pricing
        """
        self.logger.debug(f"Calculating charging fee for {energy_kwh}kWh on {charger_type.value}")
        
        # Base rate per kWh
        base_rate_per_kwh = Decimal('0.30')  # $0.30 per kWh
        
        # Charger type multiplier
        charger_multipliers = {
            ChargerType.LEVEL_1: Decimal('1.0'),
            ChargerType.LEVEL_2: Decimal('1.2'),
            ChargerType.DC_FAST: Decimal('1.5'),
            ChargerType.TESLA: Decimal('1.8'),
            ChargerType.CHADEMO: Decimal('1.5'),
            ChargerType.CCS: Decimal('1.5'),
        }
        
        multiplier = charger_multipliers.get(charger_type, Decimal('1.0'))
        
        # Time of day adjustment (peak vs off-peak)
        hour = time_of_day.hour
        if 8 <= hour < 20:  # Peak hours: 8 AM to 8 PM
            multiplier *= Decimal('1.25')  # 25% peak surcharge
        else:  # Off-peak hours
            multiplier *= Decimal('0.75')  # 25% off-peak discount
        
        # Calculate fee
        fee_amount = Decimal(str(energy_kwh)) * base_rate_per_kwh * multiplier
        return Money(fee_amount)
    
    def _apply_time_based_rules(self, fee: Money, time_range: TimeRange) -> Money:
        """Apply time-based business rules to fee"""
        # First hour discount
        if time_range.duration_hours <= 1:
            # 10% discount for first hour
            discount = fee.amount * Decimal('0.10')
            fee = Money(fee.amount - discount, fee.currency)
        
        # Evening premium (6 PM to 6 AM)
        start_hour = time_range.start_time.hour
        if 18 <= start_hour or start_hour < 6:
            # 20% premium for evening/overnight
            premium = fee.amount * Decimal('0.20')
            fee = Money(fee.amount + premium, fee.currency)
        
        # Weekend premium
        if time_range.start_time.weekday() >= 5:  # Saturday or Sunday
            # 15% weekend premium
            premium = fee.amount * Decimal('0.15')
            fee = Money(fee.amount + premium, fee.currency)
        
        return fee
    
    def _apply_feature_premiums(self, fee: Money, slot: ParkingSlot) -> Money:
        """Apply premiums for slot features"""
        premium_multiplier = Decimal('1.0')
        
        if slot.has_feature("covered"):
            premium_multiplier += Decimal('0.15')  # 15% premium for covered
        
        if slot.has_feature("camera"):
            premium_multiplier += Decimal('0.05')   # 5% premium for security camera
        
        if slot.has_feature("valet"):
            premium_multiplier += Decimal('0.25')   # 25% premium for valet service
        
        if slot.has_feature("wide"):
            premium_multiplier += Decimal('0.10')   # 10% premium for wide space
        
        adjusted_amount = fee.amount * premium_multiplier
        return Money(adjusted_amount, fee.currency)


class DynamicPricingStrategy(PricingStrategy):
    """
    Dynamic pricing strategy based on demand
    - Prices increase with occupancy
    - Real-time adjustments
    - Peak/off-peak variations
    """
    
    def __init__(self, base_multiplier: Decimal = Decimal('1.0')):
        super().__init__()
        self.base_multiplier = base_multiplier
    
    def calculate_parking_fee(
        self,
        slot: ParkingSlot,
        time_range: TimeRange,
        vehicle: Optional[Vehicle] = None,
        occupancy_rate: float = 0.0
    ) -> Money:
        """
        Calculate parking fee with dynamic pricing based on occupancy
        """
        self.logger.debug(f"Calculating dynamic parking fee (occupancy: {occupancy_rate:.1f}%)")
        
        # Start with standard calculation
        standard_strategy = StandardPricingStrategy()
        base_fee = standard_strategy.calculate_parking_fee(slot, time_range, vehicle)
        
        # Apply demand-based multiplier
        demand_multiplier = self._calculate_demand_multiplier(occupancy_rate)
        dynamic_amount = base_fee.amount * demand_multiplier * self.base_multiplier
        
        return Money(dynamic_amount, base_fee.currency)
    
    def calculate_charging_fee(
        self,
        energy_kwh: float,
        charger_type: ChargerType,
        time_of_day: datetime,
        station_utilization: float = 0.0
    ) -> Money:
        """
        Calculate dynamic charging fee based on station utilization
        """
        self.logger.debug(f"Calculating dynamic charging fee (utilization: {station_utilization:.1f}%)")
        
        # Start with standard calculation
        standard_strategy = StandardPricingStrategy()
        base_fee = standard_strategy.calculate_charging_fee(energy_kwh, charger_type, time_of_day)
        
        # Apply utilization-based multiplier
        utilization_multiplier = self._calculate_utilization_multiplier(station_utilization)
        dynamic_amount = base_fee.amount * utilization_multiplier * self.base_multiplier
        
        return Money(dynamic_amount, base_fee.currency)
    
    def _calculate_demand_multiplier(self, occupancy_rate: float) -> Decimal:
        """
        Calculate price multiplier based on parking lot occupancy
        Business rule: Higher occupancy → higher prices
        """
        if occupancy_rate < 50:
            return Decimal('0.9')   # 10% discount when under 50% occupancy
        elif occupancy_rate < 75:
            return Decimal('1.0')   # Standard price at 50-75%
        elif occupancy_rate < 90:
            return Decimal('1.2')   # 20% premium at 75-90%
        else:
            return Decimal('1.5')   # 50% premium above 90%
    
    def _calculate_utilization_multiplier(self, utilization_rate: float) -> Decimal:
        """
        Calculate price multiplier based on charging station utilization
        """
        if utilization_rate < 30:
            return Decimal('0.8')   # 20% discount when under 30% utilization
        elif utilization_rate < 60:
            return Decimal('1.0')   # Standard price at 30-60%
        elif utilization_rate < 85:
            return Decimal('1.3')   # 30% premium at 60-85%
        else:
            return Decimal('1.7')   # 70% premium above 85%


class SubscriptionPricingStrategy(PricingStrategy):
    """
    Pricing strategy for subscription/membership customers
    - Fixed monthly rates
    - Discounts for long-term parking
    - Priority parking benefits
    """
    
    def __init__(self, monthly_rate: Money = Money(Decimal('100.00'))):
        super().__init__()
        self.monthly_rate = monthly_rate
    
    def calculate_parking_fee(
        self,
        slot: ParkingSlot,
        time_range: TimeRange,
        vehicle: Optional[Vehicle] = None,
        has_subscription: bool = True
    ) -> Money:
        """
        Calculate parking fee for subscription customers
        """
        if not has_subscription:
            # Fall back to standard pricing for non-subscribers
            standard = StandardPricingStrategy()
            return standard.calculate_parking_fee(slot, time_range, vehicle)
        
        self.logger.debug("Calculating subscription parking fee")
        
        # Subscription benefits:
        # 1. First 2 hours free
        # 2. 50% discount after that
        # 3. Maximum daily cap
        
        duration_hours = time_range.duration_hours
        
        if duration_hours <= 2:
            # First 2 hours free for subscribers
            return Money(Decimal('0.00'))
        
        # Calculate standard fee for the full duration
        standard = StandardPricingStrategy()
        standard_fee = standard.calculate_parking_fee(slot, time_range, vehicle)
        
        # Apply 50% discount
        discounted_amount = standard_fee.amount * Decimal('0.5')
        
        # Apply daily cap ($20 max for subscribers)
        daily_cap = Decimal('20.00')
        final_amount = min(discounted_amount, daily_cap)
        
        return Money(final_amount, standard_fee.currency)
    
    def calculate_charging_fee(
        self,
        energy_kwh: float,
        charger_type: ChargerType,
        time_of_day: datetime,
        has_subscription: bool = True
    ) -> Money:
        """
        Calculate charging fee for subscription customers
        """
        if not has_subscription:
            # Fall back to standard pricing
            standard = StandardPricingStrategy()
            return standard.calculate_charging_fee(energy_kwh, charger_type, time_of_day)
        
        self.logger.debug("Calculating subscription charging fee")
        
        # Subscription benefits for charging:
        # 1. First 10 kWh free per day
        # 2. 30% discount on additional kWh
        
        free_kwh = Decimal('10.0')
        energy_decimal = Decimal(str(energy_kwh))
        
        if energy_decimal <= free_kwh:
            return Money(Decimal('0.00'))
        
        # Calculate standard fee
        standard = StandardPricingStrategy()
        standard_fee = standard.calculate_charging_fee(energy_kwh, charger_type, time_of_day)
        
        # Calculate fee for energy above free limit with 30% discount
        charged_kwh = energy_decimal - free_kwh
        charged_fee = standard_fee.amount * (charged_kwh / energy_decimal) * Decimal('0.7')
        
        return Money(charged_fee, standard_fee.currency)


# ============================================================================
# CHARGING STRATEGIES
# ============================================================================

class FastChargingStrategy(ChargingStrategy):
    """
    Strategy: Optimize for fastest charging time
    - Prefers high-power chargers
    - Willing to pay premium for speed
    - Good for short stops
    """
    
    def optimize_charging(
        self,
        vehicle: ElectricVehicle,
        available_connectors: List[ChargerType],
        target_charge_percentage: float,
        max_time_hours: float
    ) -> Tuple[ChargerType, float, float]:
        """
        Find the fastest charging option
        """
        self.logger.debug(f"Optimizing for fastest charging to {target_charge_percentage}%")
        
        best_charger = None
        best_time = float('inf')
        best_cost = float('inf')
        
        for charger_type in available_connectors:
            # Check compatibility
            if not charger_type.is_compatible(vehicle.vehicle_type):
                continue
            
            # Calculate charging time
            charge_time = vehicle.get_charge_time_hours(target_charge_percentage, charger_type.typical_power_kw)
            
            # Calculate estimated cost (simplified)
            energy_needed = (target_charge_percentage - vehicle.charge_percentage) / 100 * vehicle.battery_capacity_kwh
            cost = energy_needed * 0.3  # Simplified cost calculation
            
            # Find fastest option
            if charge_time < best_time and charge_time <= max_time_hours:
                best_charger = charger_type
                best_time = charge_time
                best_cost = cost
        
        if not best_charger:
            # Fall back to first compatible charger
            for charger_type in available_connectors:
                if charger_type.is_compatible(vehicle.vehicle_type):
                    best_charger = charger_type
                    best_time = vehicle.get_charge_time_hours(target_charge_percentage, charger_type.typical_power_kw)
                    energy_needed = (target_charge_percentage - vehicle.charge_percentage) / 100 * vehicle.battery_capacity_kwh
                    best_cost = energy_needed * 0.3
                    break
        
        return best_charger, best_time, best_cost
    
    def should_interrupt_charging(
        self,
        vehicle: ElectricVehicle,
        current_charger: ChargerType,
        new_charger: ChargerType,
        time_elapsed_hours: float
    ) -> bool:
        """
        Decide if we should interrupt for a faster charger
        """
        # Calculate remaining time with current charger
        remaining_with_current = vehicle.get_charge_time_hours(100.0, current_charger.typical_power_kw)
        
        # Calculate time with new charger
        time_with_new = vehicle.get_charge_time_hours(100.0, new_charger.typical_power_kw)
        
        # Calculate time lost due to switching
        switch_penalty = 0.1  # 6 minutes to switch
        
        # Only switch if new charger is significantly faster
        time_saved = (remaining_with_current - time_elapsed_hours) - (time_with_new + switch_penalty)
        
        return time_saved > 0.25  # Switch if saves more than 15 minutes


class CostOptimizedChargingStrategy(ChargingStrategy):
    """
    Strategy: Optimize for lowest charging cost
    - Prefers slower, cheaper chargers
    - Time-insensitive
    - Good for overnight charging
    """
    
    def optimize_charging(
        self,
        vehicle: ElectricVehicle,
        available_connectors: List[ChargerType],
        target_charge_percentage: float,
        max_time_hours: float
    ) -> Tuple[ChargerType, float, float]:
        """
        Find the cheapest charging option
        """
        self.logger.debug(f"Optimizing for cheapest charging to {target_charge_percentage}%")
        
        best_charger = None
        best_cost = float('inf')
        best_time = float('inf')
        
        # Cost multipliers by charger type
        cost_multipliers = {
            ChargerType.LEVEL_1: 0.8,   # 20% cheaper
            ChargerType.LEVEL_2: 1.0,   # Standard
            ChargerType.DC_FAST: 1.5,   # 50% premium
            ChargerType.TESLA: 1.8,     # 80% premium
            ChargerType.CHADEMO: 1.5,
            ChargerType.CCS: 1.5,
        }
        
        for charger_type in available_connectors:
            if not charger_type.is_compatible(vehicle.vehicle_type):
                continue
            
            # Calculate energy needed
            energy_needed = (target_charge_percentage - vehicle.charge_percentage) / 100 * vehicle.battery_capacity_kwh
            
            # Calculate cost with multiplier
            base_cost = energy_needed * 0.3  # $0.30 per kWh base
            cost = base_cost * cost_multipliers.get(charger_type, 1.0)
            
            # Calculate time
            charge_time = vehicle.get_charge_time_hours(target_charge_percentage, charger_type.typical_power_kw)
            
            # Check time constraint
            if charge_time > max_time_hours:
                continue
            
            # Find cheapest option
            if cost < best_cost:
                best_charger = charger_type
                best_cost = cost
                best_time = charge_time
        
        return best_charger, best_time, best_cost
    
    def should_interrupt_charging(
        self,
        vehicle: ElectricVehicle,
        current_charger: ChargerType,
        new_charger: ChargerType,
        time_elapsed_hours: float
    ) -> bool:
        """
        Rarely interrupt for cost optimization (waste of time already spent)
        """
        return False  # Cost optimization prefers to continue with current charger


class BalancedChargingStrategy(ChargingStrategy):
    """
    Strategy: Balance between speed and cost
    - Finds best value (cost per time saved)
    - Good for general use
    """
    
    def optimize_charging(
        self,
        vehicle: ElectricVehicle,
        available_connectors: List[ChargerType],
        target_charge_percentage: float,
        max_time_hours: float
    ) -> Tuple[ChargerType, float, float]:
        """
        Find the best value charging option (cost vs time)
        """
        self.logger.debug(f"Optimizing for balanced charging to {target_charge_percentage}%")
        
        best_charger = None
        best_value = float('-inf')  # Higher is better
        
        # Define value function: value = (time_saved / cost_premium)
        base_charger = ChargerType.LEVEL_2  # Use Level 2 as baseline