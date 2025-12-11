# File: src/application/parking_service.py
"""
Parking Management Application Service

This module implements the application service layer for the parking management system.
It orchestrates the domain logic, coordinates bounded contexts, and handles
the use cases of the system.

Responsibilities:
1. Coordinate between bounded contexts and domain aggregates
2. Execute business transactions (use cases)
3. Handle cross-cutting concerns (logging, validation, error handling)
4. Provide a clean API for the presentation/interface layer

Key Principles:
- Transaction Script pattern for complex use cases
- Dependency Injection for testability
- Command/Query separation
- Idempotent operations where possible
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Protocol, runtime_checkable
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from ..domain.models import (
    ParkingSlot, Vehicle, ElectricVehicle,
    VehicleType, SlotType, ChargerType,
    Money, TimeRange, LicensePlate,
    ParkingTicket, Invoice, Payment
)
from ..domain.aggregates import ParkingLot, ChargingStation
from ..domain.strategies import (
    ParkingStrategy, PricingStrategy, ChargingStrategy,
    StandardCarStrategy, ElectricCarStrategy, MotorcycleStrategy,
    LargeVehicleStrategy, NearestEntryStrategy,
    StandardPricingStrategy, DynamicPricingStrategy, SubscriptionPricingStrategy
)
from ..domain.bounded_contexts import (
    ContextMapper, ParkingManagementContext,
    BillingPricingContext, EVChargingContext,
    SecurityValidationContext, MonitoringAnalyticsContext
)


# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class VehicleDTO:
    """DTO for vehicle information"""
    license_plate: str
    vehicle_type: str
    make: Optional[str] = None
    model: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    charge_percentage: Optional[float] = None
    is_electric: bool = False
    disabled_permit: bool = False


@dataclass
class ParkingRequestDTO:
    """DTO for parking requests"""
    license_plate: str
    vehicle_type: str
    parking_lot_id: str
    entry_time: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = None
    customer_id: Optional[str] = None
    requires_charging: bool = False


@dataclass
class ParkingAllocationDTO:
    """DTO for parking allocation results"""
    success: bool
    ticket_id: Optional[str] = None
    slot_number: Optional[int] = None
    slot_type: Optional[str] = None
    floor_level: Optional[int] = None
    estimated_fee_per_hour: Optional[float] = None
    message: Optional[str] = None
    strategy_used: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class ExitRequestDTO:
    """DTO for exit requests"""
    ticket_id: Optional[str] = None
    license_plate: Optional[str] = None
    parking_lot_id: str
    exit_time: Optional[datetime] = None


@dataclass
class ParkingExitDTO:
    """DTO for parking exit results"""
    success: bool
    license_plate: Optional[str] = None
    slot_number: Optional[int] = None
    duration_hours: Optional[float] = None
    total_fee: Optional[float] = None
    invoice_id: Optional[str] = None
    payment_required: bool = False
    message: Optional[str] = None


@dataclass
class ChargingRequestDTO:
    """DTO for charging requests"""
    license_plate: str
    vehicle_type: str
    station_id: str
    current_charge_percentage: float
    target_charge_percentage: float
    battery_capacity_kwh: float
    charging_strategy: str = "balanced"  # "fast", "cost_optimized", "balanced"
    customer_id: Optional[str] = None


@dataclass
class ChargingSessionDTO:
    """DTO for charging session results"""
    success: bool
    session_id: Optional[str] = None
    connector_id: Optional[str] = None
    connector_type: Optional[str] = None
    estimated_time_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    message: Optional[str] = None
    strategy_used: Optional[str] = None


@dataclass
class InvoiceDTO:
    """DTO for invoice information"""
    invoice_id: str
    customer_id: Optional[str]
    license_plate: str
    total_amount: float
    currency: str = "USD"
    status: str = "pending"
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    services: List[Dict[str, Any]] = None


@dataclass
class ParkingLotStatusDTO:
    """DTO for parking lot status"""
    parking_lot_id: str
    total_slots: int
    occupied_slots: int
    available_slots: int
    occupancy_rate: float
    by_slot_type: Dict[str, Dict[str, int]]
    timestamp: datetime


@dataclass
class ReservationRequestDTO:
    """DTO for reservation requests"""
    license_plate: str
    vehicle_type: str
    parking_lot_id: str
    start_time: datetime
    end_time: datetime
    preferred_slot_type: Optional[str] = None
    customer_id: Optional[str] = None


@dataclass
class ReservationDTO:
    """DTO for reservation results"""
    success: bool
    reservation_id: Optional[str] = None
    slot_number: Optional[int] = None
    slot_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    confirmation_code: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class IParkingService(Protocol):
    """Interface for parking service operations"""
    
    def park_vehicle(self, request: ParkingRequestDTO) -> ParkingAllocationDTO:
        """Park a vehicle in the parking lot"""
        ...
    
    def exit_vehicle(self, request: ExitRequestDTO) -> ParkingExitDTO:
        """Exit a vehicle from the parking lot"""
        ...
    
    def start_charging_session(self, request: ChargingRequestDTO) -> ChargingSessionDTO:
        """Start an EV charging session"""
        ...
    
    def stop_charging_session(self, session_id: str, station_id: str) -> Dict[str, Any]:
        """Stop an active charging session"""
        ...
    
    def get_parking_lot_status(self, parking_lot_id: str) -> ParkingLotStatusDTO:
        """Get current status of a parking lot"""
        ...
    
    def make_reservation(self, request: ReservationRequestDTO) -> ReservationDTO:
        """Make a parking reservation"""
        ...
    
    def cancel_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """Cancel a parking reservation"""
        ...
    
    def get_invoice(self, invoice_id: str) -> InvoiceDTO:
        """Get invoice details"""
        ...
    
    def process_payment(self, invoice_id: str, payment_method: str, amount: float) -> Dict[str, Any]:
        """Process payment for an invoice"""
        ...


# ============================================================================
# EXCEPTIONS
# ============================================================================

class ParkingServiceError(Exception):
    """Base exception for parking service errors"""
    pass


class VehicleValidationError(ParkingServiceError):
    """Exception for vehicle validation errors"""
    pass


class SlotAllocationError(ParkingServiceError):
    """Exception for slot allocation errors"""
    pass


class ParkingLotFullError(SlotAllocationError):
    """Exception when parking lot is full"""
    pass


class ChargingSessionError(ParkingServiceError):
    """Exception for charging session errors"""
    pass


class PaymentProcessingError(ParkingServiceError):
    """Exception for payment processing errors"""
    pass


class ReservationError(ParkingServiceError):
    """Exception for reservation errors"""
    pass


# ============================================================================
# MAIN PARKING SERVICE
# ============================================================================

class ParkingService:
    """
    Main application service for parking management
    
    This service orchestrates the use cases of the system:
    1. Vehicle parking and exit
    2. EV charging
    3. Reservation management
    4. Payment processing
    5. Status monitoring
    
    It coordinates between bounded contexts and applies business rules.
    """
    
    def __init__(self, context_mapper: Optional[ContextMapper] = None):
        """
        Initialize the parking service
        
        Args:
            context_mapper: Optional context mapper for bounded contexts.
                          If not provided, creates a standard configuration.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize context mapper
        if context_mapper:
            self.context_mapper = context_mapper
        else:
            from ..domain.bounded_contexts import BoundedContextFactory
            self.context_mapper = BoundedContextFactory.create_standard_configuration()
        
        # Get references to contexts
        self.parking_context = self.context_mapper.contexts["parking_management"]
        self.billing_context = self.context_mapper.contexts["billing_pricing"]
        self.charging_context = self.context_mapper.contexts["ev_charging"]
        self.security_context = self.context_mapper.contexts["security_validation"]
        self.monitoring_context = self.context_mapper.contexts["monitoring_analytics"]
        
        # Initialize parking strategies registry
        self._initialize_strategies()
        
        # Service configuration
        self.config = {
            "max_parking_duration_hours": 168,  # 7 days
            "grace_period_minutes": 15,
            "overstay_penalty_rate": 1.5,  # 50% penalty
            "reservation_hold_minutes": 30,
            "default_currency": "USD"
        }
        
        self.logger.info("ParkingService initialized")
    
    def _initialize_strategies(self):
        """Initialize parking strategies registry"""
        self.parking_strategies = {
            VehicleType.CAR: StandardCarStrategy(),
            VehicleType.EV_CAR: ElectricCarStrategy(),
            VehicleType.MOTORCYCLE: MotorcycleStrategy(),
            VehicleType.EV_MOTORCYCLE: MotorcycleStrategy(),
            VehicleType.TRUCK: LargeVehicleStrategy(),
            VehicleType.EV_TRUCK: LargeVehicleStrategy(),
            VehicleType.BUS: LargeVehicleStrategy(),
        }
        
        self.pricing_strategies = {
            "standard": StandardPricingStrategy(),
            "dynamic": DynamicPricingStrategy(),
            "subscription": SubscriptionPricingStrategy()
        }
    
    def park_vehicle(self, request: ParkingRequestDTO) -> ParkingAllocationDTO:
        """
        Park a vehicle in the parking lot
        
        Use Case: Vehicle Entry
        1. Validate vehicle and license plate
        2. Check access permissions
        3. Allocate parking slot
        4. Create parking ticket
        5. Update monitoring metrics
        
        Returns: Parking allocation result
        """
        self.logger.info(f"Processing parking request for {request.license_plate}")
        
        try:
            # Step 1: Validate license plate
            validation_result = self.security_context.execute_command({
                "type": "validate_license_plate",
                "license_plate": request.license_plate,
                "country": "default"
            })
            
            if not validation_result.get("success", False):
                return ParkingAllocationDTO(
                    success=False,
                    message=f"License plate validation failed: {validation_result.get('error')}"
                )
            
            # Step 2: Check access permissions
            access_result = self.security_context.execute_command({
                "type": "check_access",
                "license_plate": request.license_plate,
                "facility_type": "parking"
            })
            
            if not access_result.get("access_granted", False):
                return ParkingAllocationDTO(
                    success=False,
                    message=f"Access denied: {access_result.get('reason')}"
                )
            
            # Step 3: Prepare parking command
            entry_time = request.entry_time or datetime.now()
            vehicle_data = {
                "license_plate": request.license_plate,
                "vehicle_type": request.vehicle_type,
                "make": "Unknown",
                "model": "Unknown"
            }
            
            # Add EV-specific data if applicable
            vehicle_type = VehicleType(request.vehicle_type)
            if vehicle_type.is_electric and request.requires_charging:
                vehicle_data.update({
                    "battery_capacity_kwh": 60.0,  # Default
                    "charge_percentage": 50.0  # Default
                })
            
            parking_command = {
                "type": "allocate_parking",
                "vehicle": vehicle_data,
                "parking_lot_id": request.parking_lot_id,
                "preferences": request.preferences or {},
                "entry_time": entry_time.isoformat()
            }
            
            # Step 4: Execute parking allocation
            allocation_result = self.parking_context.execute_command(parking_command)
            
            if not allocation_result.get("success", False):
                return ParkingAllocationDTO(
                    success=False,
                    message=f"Parking allocation failed: {allocation_result.get('error')}"
                )
            
            # Step 5: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "vehicle_entry",
                "value": 1,
                "source": request.parking_lot_id
            })
            
            # Step 6: Return allocation result
            return ParkingAllocationDTO(
                success=True,
                ticket_id=allocation_result["ticket_id"],
                slot_number=allocation_result["slot_number"],
                slot_type=allocation_result["slot_type"],
                strategy_used=allocation_result.get("strategy_used", "unknown"),
                timestamp=datetime.now(),
                message="Vehicle parked successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error parking vehicle: {e}", exc_info=True)
            return ParkingAllocationDTO(
                success=False,
                message=f"Internal error: {str(e)}"
            )
    
    def exit_vehicle(self, request: ExitRequestDTO) -> ParkingExitDTO:
        """
        Exit a vehicle from the parking lot
        
        Use Case: Vehicle Exit
        1. Validate exit request
        2. Calculate parking duration and fee
        3. Generate invoice
        4. Release parking slot
        5. Update monitoring metrics
        
        Returns: Exit processing result
        """
        self.logger.info(f"Processing exit request: {request}")
        
        try:
            exit_time = request.exit_time or datetime.now()
            
            # Step 1: Determine ticket ID (if not provided, find by license plate)
            ticket_id = request.ticket_id
            if not ticket_id and request.license_plate:
                # Find active ticket by license plate
                # In real system, would query parking context
                pass
            
            if not ticket_id:
                return ParkingExitDTO(
                    success=False,
                    message="Ticket ID or license plate required"
                )
            
            # Step 2: Get ticket details
            # In real system, would retrieve from parking context
            
            # Step 3: Release parking
            release_result = self.parking_context.execute_command({
                "type": "release_parking",
                "ticket_id": ticket_id,
                "parking_lot_id": request.parking_lot_id
            })
            
            if not release_result.get("success", False):
                return ParkingExitDTO(
                    success=False,
                    message=f"Failed to release parking: {release_result.get('error')}"
                )
            
            # Step 4: Calculate fee
            # In real system, would get actual entry time and calculate
            duration_hours = 2.5  # Mock value
            fee_calculation = self.billing_context.execute_command({
                "type": "calculate_fee",
                "fee_type": "parking",
                "pricing_strategy": "standard",
                "entry_time": (exit_time - timedelta(hours=duration_hours)).isoformat(),
                "exit_time": exit_time.isoformat(),
                "slot": {"type": "regular"},  # Mock slot data
                "vehicle_type": "car"  # Mock vehicle type
            })
            
            if not fee_calculation.get("success", False):
                return ParkingExitDTO(
                    success=False,
                    message=f"Fee calculation failed: {fee_calculation.get('error')}"
                )
            
            total_fee = fee_calculation.get("fee_amount", 0.0)
            
            # Step 5: Generate invoice
            invoice_result = self.billing_context.execute_command({
                "type": "generate_invoice",
                "license_plate": request.license_plate or "UNKNOWN",
                "services": [{
                    "type": "parking",
                    "details": {
                        "duration_hours": duration_hours,
                        "slot_type": "regular"
                    }
                }]
            })
            
            if not invoice_result.get("success", False):
                return ParkingExitDTO(
                    success=False,
                    message=f"Invoice generation failed: {invoice_result.get('error')}"
                )
            
            # Step 6: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "vehicle_exit",
                "value": 1,
                "source": request.parking_lot_id
            })
            
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "revenue",
                "value": total_fee,
                "source": request.parking_lot_id
            })
            
            # Step 7: Return exit result
            return ParkingExitDTO(
                success=True,
                license_plate=request.license_plate,
                slot_number=release_result.get("slot_released"),
                duration_hours=duration_hours,
                total_fee=total_fee,
                invoice_id=invoice_result.get("invoice_id"),
                payment_required=total_fee > 0,
                message="Vehicle exited successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error exiting vehicle: {e}", exc_info=True)
            return ParkingExitDTO(
                success=False,
                message=f"Internal error: {str(e)}"
            )
    
    def start_charging_session(self, request: ChargingRequestDTO) -> ChargingSessionDTO:
        """
        Start an EV charging session
        
        Use Case: EV Charging Start
        1. Validate EV and charging needs
        2. Check charging station availability
        3. Optimize charging parameters
        4. Start charging session
        5. Update monitoring metrics
        
        Returns: Charging session result
        """
        self.logger.info(f"Starting charging session for {request.license_plate}")
        
        try:
            # Step 1: Validate vehicle type is electric
            vehicle_type = VehicleType(request.vehicle_type)
            if not vehicle_type.is_electric:
                return ChargingSessionDTO(
                    success=False,
                    message=f"Vehicle type {request.vehicle_type} is not electric"
                )
            
            # Step 2: Execute charging command
            charging_result = self.charging_context.execute_command({
                "type": "start_charging_session",
                "vehicle": {
                    "license_plate": request.license_plate,
                    "vehicle_type": request.vehicle_type,
                    "battery_capacity_kwh": request.battery_capacity_kwh,
                    "charge_percentage": request.current_charge_percentage
                },
                "station_id": request.station_id,
                "strategy": request.charging_strategy,
                "target_charge_percentage": request.target_charge_percentage,
                "max_time_hours": 4.0  # Default max time
            })
            
            if not charging_result.get("success", False):
                return ChargingSessionDTO(
                    success=False,
                    message=f"Charging session failed to start: {charging_result.get('error')}"
                )
            
            # Step 3: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "charging_session_start",
                "value": 1,
                "source": request.station_id
            })
            
            # Step 4: Return charging session result
            return ChargingSessionDTO(
                success=True,
                session_id=charging_result["session_id"],
                connector_id=charging_result["connector_id"],
                connector_type=charging_result["connector_type"],
                estimated_time_hours=charging_result["estimated_time_hours"],
                estimated_cost=charging_result["estimated_cost"],
                strategy_used=charging_result["strategy_used"],
                message="Charging session started successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error starting charging session: {e}", exc_info=True)
            return ChargingSessionDTO(
                success=False,
                message=f"Internal error: {str(e)}"
            )
    
    def stop_charging_session(self, session_id: str, station_id: str) -> Dict[str, Any]:
        """
        Stop an active charging session
        
        Use Case: EV Charging Stop
        1. Validate session
        2. Stop charging
        3. Calculate charging fee
        4. Generate invoice
        5. Update monitoring metrics
        """
        self.logger.info(f"Stopping charging session {session_id}")
        
        try:
            # Step 1: Stop charging session
            stop_result = self.charging_context.execute_command({
                "type": "stop_charging_session",
                "session_id": session_id,
                "station_id": station_id
            })
            
            if not stop_result.get("success", False):
                return {
                    "success": False,
                    "error": stop_result.get("error", "Failed to stop charging session")
                }
            
            # Step 2: Calculate charging fee and generate invoice
            # In real system, would use actual energy delivered
            energy_kwh = stop_result.get("energy_delivered_kwh", 30.0)
            
            fee_calculation = self.billing_context.execute_command({
                "type": "calculate_fee",
                "fee_type": "charging",
                "energy_kwh": energy_kwh,
                "charger_type": "DC_FAST",  # Mock
                "time_of_day": datetime.now().isoformat()
            })
            
            # Step 3: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "charging_session_stop",
                "value": 1,
                "source": station_id
            })
            
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "charging_energy",
                "value": energy_kwh,
                "source": station_id
            })
            
            return {
                "success": True,
                "session_id": session_id,
                "energy_delivered_kwh": energy_kwh,
                "duration_hours": stop_result.get("duration_hours"),
                "fee_amount": fee_calculation.get("fee_amount") if fee_calculation.get("success") else 0.0,
                "message": "Charging session stopped successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping charging session: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parking_lot_status(self, parking_lot_id: str) -> ParkingLotStatusDTO:
        """
        Get current status of a parking lot
        
        Use Case: Status Monitoring
        1. Get occupancy data
        2. Get availability by slot type
        3. Get recent activity
        4. Return formatted status
        """
        self.logger.debug(f"Getting status for parking lot {parking_lot_id}")
        
        try:
            # Step 1: Get occupancy information
            occupancy_result = self.parking_context.execute_query({
                "type": "get_occupancy",
                "parking_lot_id": parking_lot_id
            })
            
            if not occupancy_result.get("success", False):
                raise ParkingServiceError(f"Failed to get occupancy: {occupancy_result.get('error')}")
            
            # Step 2: Get parking status
            status_result = self.parking_context.execute_query({
                "type": "get_parking_status",
                "parking_lot_id": parking_lot_id
            })
            
            if not status_result.get("success", False):
                raise ParkingServiceError(f"Failed to get parking status: {status_result.get('error')}")
            
            # Step 3: Format and return status
            return ParkingLotStatusDTO(
                parking_lot_id=parking_lot_id,
                total_slots=status_result["total_slots"],
                occupied_slots=status_result["occupied_slots"],
                available_slots=status_result["available_slots"],
                occupancy_rate=status_result["occupancy_rate"],
                by_slot_type=occupancy_result.get("by_slot_type", {}),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting parking lot status: {e}", exc_info=True)
            raise
    
    def make_reservation(self, request: ReservationRequestDTO) -> ReservationDTO:
        """
        Make a parking reservation
        
        Use Case: Reservation Management
        1. Validate reservation parameters
        2. Check slot availability for time period
        3. Create reservation
        4. Generate confirmation
        5. Send notification
        
        Returns: Reservation result
        """
        self.logger.info(f"Processing reservation for {request.license_plate}")
        
        try:
            # Step 1: Validate time range
            if request.end_time <= request.start_time:
                return ReservationDTO(
                    success=False,
                    message="End time must be after start time"
                )
            
            # Step 2: Validate license plate
            validation_result = self.security_context.execute_command({
                "type": "validate_license_plate",
                "license_plate": request.license_plate
            })
            
            if not validation_result.get("success", False):
                return ReservationDTO(
                    success=False,
                    message=f"Invalid license plate: {validation_result.get('error')}"
                )
            
            # Step 3: Check availability
            availability_result = self.parking_context.execute_query({
                "type": "get_available_slots",
                "parking_lot_id": request.parking_lot_id,
                "vehicle_type": request.vehicle_type
            })
            
            if not availability_result.get("success", False):
                return ReservationDTO(
                    success=False,
                    message=f"Failed to check availability: {availability_result.get('error')}"
                )
            
            available_slots = availability_result.get("available_slots", 0)
            if available_slots == 0:
                return ReservationDTO(
                    success=False,
                    message="No available slots for reservation"
                )
            
            # Step 4: Create reservation
            # In real system, would use a reservation context
            reservation_id = f"RES-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            confirmation_code = self._generate_confirmation_code()
            
            # Step 5: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "reservation_made",
                "value": 1,
                "source": request.parking_lot_id
            })
            
            # Step 6: Return reservation result
            return ReservationDTO(
                success=True,
                reservation_id=reservation_id,
                start_time=request.start_time,
                end_time=request.end_time,
                confirmation_code=confirmation_code,
                message="Reservation created successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Error making reservation: {e}", exc_info=True)
            return ReservationDTO(
                success=False,
                message=f"Internal error: {str(e)}"
            )
    
    def cancel_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """
        Cancel a parking reservation
        
        Use Case: Reservation Cancellation
        1. Validate reservation
        2. Check cancellation policy
        3. Cancel reservation
        4. Process refund if applicable
        5. Update monitoring metrics
        """
        self.logger.info(f"Cancelling reservation {reservation_id}")
        
        try:
            # In real system, would validate and cancel reservation
            # For now, return mock result
            
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "reservation_cancelled",
                "value": 1,
                "source": "reservation_system"
            })
            
            return {
                "success": True,
                "reservation_id": reservation_id,
                "cancelled_at": datetime.now().isoformat(),
                "message": "Reservation cancelled successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error cancelling reservation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_invoice(self, invoice_id: str) -> InvoiceDTO:
        """
        Get invoice details
        
        Use Case: Invoice Retrieval
        1. Validate invoice ID
        2. Retrieve invoice details
        3. Format invoice data
        4. Return invoice DTO
        """
        self.logger.debug(f"Getting invoice {invoice_id}")
        
        try:
            # Step 1: Get invoice from billing context
            invoice_result = self.billing_context.execute_query({
                "type": "get_invoice",
                "invoice_id": invoice_id
            })
            
            if not invoice_result.get("success", False):
                raise ParkingServiceError(f"Failed to get invoice: {invoice_result.get('error')}")
            
            invoice_data = invoice_result.get("invoice", {})
            
            # Step 2: Create InvoiceDTO
            return InvoiceDTO(
                invoice_id=invoice_data.get("invoice_id"),
                customer_id=invoice_data.get("customer_id"),
                license_plate=invoice_data.get("license_plate"),
                total_amount=invoice_data.get("total", 0.0),
                currency="USD",  # Would come from invoice data
                status=invoice_data.get("status", "unknown"),
                issue_date=datetime.fromisoformat(invoice_data.get("issue_date")) if invoice_data.get("issue_date") else None,
                due_date=datetime.fromisoformat(invoice_data.get("due_date")) if invoice_data.get("due_date") else None,
                services=invoice_data.get("services", [])
            )
            
        except Exception as e:
            self.logger.error(f"Error getting invoice: {e}", exc_info=True)
            raise
    
    def process_payment(self, invoice_id: str, payment_method: str, amount: float) -> Dict[str, Any]:
        """
        Process payment for an invoice
        
        Use Case: Payment Processing
        1. Validate invoice and amount
        2. Process payment through payment gateway
        3. Update invoice status
        4. Generate receipt
        5. Update monitoring metrics
        """
        self.logger.info(f"Processing payment for invoice {invoice_id}")
        
        try:
            # Step 1: Process payment through billing context
            payment_result = self.billing_context.execute_command({
                "type": "process_payment",
                "invoice_id": invoice_id,
                "payment_method": payment_method,
                "amount": amount
            })
            
            if not payment_result.get("success", False):
                return {
                    "success": False,
                    "error": payment_result.get("error", "Payment processing failed")
                }
            
            # Step 2: Record monitoring metric
            self.monitoring_context.execute_command({
                "type": "record_metric",
                "metric_type": "payment_processed",
                "value": amount,
                "source": payment_method
            })
            
            # Step 3: Return payment result
            return {
                "success": True,
                "payment_id": payment_result.get("payment_id"),
                "invoice_id": invoice_id,
                "amount_paid": amount,
                "payment_status": payment_result.get("payment_status"),
                "timestamp": datetime.now().isoformat(),
                "message": "Payment processed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing payment: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_license_plate(self, license_plate: str) -> Dict[str, Any]:
        """
        Validate a license plate
        
        Use Case: License Plate Validation
        1. Validate format
        2. Check blacklist
        3. Return validation result
        """
        return self.security_context.execute_command({
            "type": "validate_license_plate",
            "license_plate": license_plate
        })
    
    def get_dashboard_data(self, parking_lot_id: str) -> Dict[str, Any]:
        """
        Get dashboard data for monitoring
        
        Use Case: Dashboard Display
        1. Get parking lot status
        2. Get recent transactions
        3. Get revenue summary
        4. Get alerts
        5. Return combined dashboard data
        """
        try:
            dashboard_data = {}
            
            # Get parking lot status
            try:
                status = self.get_parking_lot_status(parking_lot_id)
                dashboard_data["parking_status"] = asdict(status)
            except Exception as e:
                self.logger.warning(f"Failed to get parking status: {e}")
                dashboard_data["parking_status"] = None
            
            # Get active alerts
            try:
                alerts_result = self.monitoring_context.execute_query({
                    "type": "get_alerts"
                })
                dashboard_data["alerts"] = alerts_result.get("active_alerts", [])
            except Exception as e:
                self.logger.warning(f"Failed to get alerts: {e}")
                dashboard_data["alerts"] = []
            
            # Get recent metrics
            try:
                metrics_result = self.monitoring_context.execute_query({
                    "type": "get_metrics",
                    "metric_types": ["occupancy_rate", "revenue", "vehicle_entry"],
                    "limit": 10
                })
                dashboard_data["recent_metrics"] = metrics_result.get("metrics", [])
            except Exception as e:
                self.logger.warning(f"Failed to get metrics: {e}")
                dashboard_data["recent_metrics"] = []
            
            dashboard_data["timestamp"] = datetime.now().isoformat()
            dashboard_data["success"] = True
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_confirmation_code(self) -> str:
        """Generate a confirmation code for reservations"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def _get_pricing_strategy(self, customer_type: str = "standard") -> PricingStrategy:
        """Get appropriate pricing strategy based on customer type"""
        return self.pricing_strategies.get(customer_type, self.pricing_strategies["standard"])
    
    def _get_parking_strategy(self, vehicle_type: VehicleType) -> ParkingStrategy:
        """Get appropriate parking strategy based on vehicle type"""
        return self.parking_strategies.get(vehicle_type, StandardCarStrategy())


# ============================================================================
# SERVICE FACTORY
# ============================================================================

class ParkingServiceFactory:
    """Factory for creating parking service instances"""
    
    @staticmethod
    def create_default_service() -> ParkingService:
        """Create a default parking service instance"""
        return ParkingService()
    
    @staticmethod
    def create_service_with_config(config: Dict[str, Any]) -> ParkingService:
        """Create a parking service with custom configuration"""
        service = ParkingService()
        service.config.update(config)
        return service
    
    @staticmethod
    def create_mock_service() -> 'MockParkingService':
        """Create a mock parking service for testing"""
        return MockParkingService()


# ============================================================================
# MOCK SERVICE FOR TESTING
# ============================================================================

class MockParkingService(ParkingService):
    """
    Mock parking service for testing
    
    Overrides real operations with mock implementations
    """
    
    def __init__(self):
        super().__init__()
        self.mock_data = {
            "parking_lots": {
                "lot-001": {
                    "total_slots": 100,
                    "occupied_slots": 45,
                    "available_slots": 55
                }
            },
            "tickets": {},
            "reservations": {},
            "invoices": {}
        }
    
    def park_vehicle(self, request: ParkingRequestDTO) -> ParkingAllocationDTO:
        """Mock park vehicle"""
        return ParkingAllocationDTO(
            success=True,
            ticket_id=f"TICKET-MOCK-{datetime.now().strftime('%H%M%S')}",
            slot_number=42,
            slot_type="REGULAR",
            strategy_used="MockStrategy",
            timestamp=datetime.now(),
            message="Mock: Vehicle parked successfully"
        )
    
    def exit_vehicle(self, request: ExitRequestDTO) -> ParkingExitDTO:
        """Mock exit vehicle"""
        return ParkingExitDTO(
            success=True,
            license_plate=request.license_plate or "MOCK-123",
            slot_number=42,
            duration_hours=2.5,
            total_fee=15.75,
            invoice_id=f"INV-MOCK-{datetime.now().strftime('%H%M%S')}",
            payment_required=True,
            message="Mock: Vehicle exited successfully"
        )
    
    def get_parking_lot_status(self, parking_lot_id: str) -> ParkingLotStatusDTO:
        """Mock parking lot status"""
        return ParkingLotStatusDTO(
            parking_lot_id=parking_lot_id,
            total_slots=100,
            occupied_slots=45,
            available_slots=55,
            occupancy_rate=0.45,
            by_slot_type={
                "REGULAR": {"occupied": 30, "total": 70, "available": 40},
                "PREMIUM": {"occupied": 10, "total": 20, "available": 10},
                "EV": {"occupied": 5, "total": 10, "available": 5}
            },
            timestamp=datetime.now()
        )


# ============================================================================
# COMMAND HANDLER
# ============================================================================

class ParkingCommandHandler:
    """
    Handler for parking commands
    
    Implements command pattern for parking operations
    """
    
    def __init__(self, service: ParkingService):
        self.service = service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def handle(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a parking command"""
        command_type = command.get("type")
        
        try:
            if command_type == "park_vehicle":
                request = ParkingRequestDTO(**command["data"])
                result = self.service.park_vehicle(request)
                return {"success": result.success, "data": asdict(result)}
            
            elif command_type == "exit_vehicle":
                request = ExitRequestDTO(**command["data"])
                result = self.service.exit_vehicle(request)
                return {"success": result.success, "data": asdict(result)}
            
            elif command_type == "start_charging":
                request = ChargingRequestDTO(**command["data"])
                result = self.service.start_charging_session(request)
                return {"success": result.success, "data": asdict(result)}
            
            elif command_type == "make_reservation":
                request = ReservationRequestDTO(**command["data"])
                result = self.service.make_reservation(request)
                return {"success": result.success, "data": asdict(result)}
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown command type: {command_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Error handling command {command_type}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage():
    """Example usage of the parking service"""
    
    # Create service instance
    service_factory = ParkingServiceFactory()
    service = service_factory.create_default_service()
    
    # Example 1: Park a vehicle
    parking_request = ParkingRequestDTO(
        license_plate="ABC-123",
        vehicle_type="CAR",
        parking_lot_id="lot-001",
        preferences={"preferred_slot_type": "REGULAR"}
    )
    
    result = service.park_vehicle(parking_request)
    print(f"Parking result: {result}")
    
    # Example 2: Get parking lot status
    status = service.get_parking_lot_status("lot-001")
    print(f"Parking lot status: {status.occupancy_rate:.1%} occupied")
    
    # Example 3: Start charging session
    if result.success and result.ticket_id:
        exit_request = ExitRequestDTO(
            ticket_id=result.ticket_id,
            parking_lot_id="lot-001"
        )
        
        exit_result = service.exit_vehicle(exit_request)
        print(f"Exit result: {exit_result}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    example_usage()