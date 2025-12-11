# File: src/application/commands.py
"""
Command Pattern Implementation for Parking Management System

This module implements the Command Pattern to encapsulate parking operations
as first-class objects. Each command represents a business operation that
can be executed, validated, undone, and logged.

Key Benefits:
- Decouple operation invocation from execution
- Support undo/redo operations
- Enable command queuing and scheduling
- Provide audit trail for all operations
- Enable transaction-like behavior

Command Types:
1. Parking Commands - Vehicle entry, exit, allocation
2. Charging Commands - EV charging operations
3. Billing Commands - Payment and invoice operations
4. Reservation Commands - Booking and cancellation
5. Admin Commands - System management operations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, Protocol, runtime_checkable
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import uuid

from ..domain.models import (
    VehicleType, SlotType, ChargerType,
    Money, LicensePlate, ParkingTicket, Invoice, Payment
)
from ..application.parking_service import (
    ParkingService, ParkingRequestDTO, ExitRequestDTO,
    ChargingRequestDTO, ReservationRequestDTO,
    ParkingAllocationDTO, ParkingExitDTO, ChargingSessionDTO, ReservationDTO
)
from ..domain.bounded_contexts import ContextMapper


# ============================================================================
# COMMAND INTERFACES AND BASE CLASSES
# ============================================================================

class Command(ABC):
    """
    Abstract base class for all commands
    
    A command represents an intent to change the system state.
    Commands are named in the imperative (e.g., ParkVehicleCommand).
    """
    
    def __init__(self, command_id: Optional[str] = None):
        self.command_id = command_id or str(uuid.uuid4())
        self.executed_at: Optional[datetime] = None
        self.executed_by: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Command metadata
        self.metadata = {
            "command_id": self.command_id,
            "command_type": self.__class__.__name__,
            "created_at": datetime.now().isoformat()
        }
    
    @abstractmethod
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """
        Execute the command using the provided service
        
        Returns: Execution result dictionary
        """
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate command parameters before execution
        
        Returns: (is_valid, error_messages)
        """
        pass
    
    def can_undo(self) -> bool:
        """
        Check if this command can be undone
        
        Returns: True if command supports undo, False otherwise
        """
        return False
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """
        Undo the effects of this command
        
        Returns: Undo result dictionary
        """
        if not self.can_undo():
            return {
                "success": False,
                "error": f"{self.__class__.__name__} does not support undo"
            }
        return {"success": False, "error": "Undo not implemented"}
    
    def get_description(self) -> str:
        """Get human-readable command description"""
        return self.__class__.__name__.replace("Command", "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary for serialization"""
        return {
            "command_id": self.command_id,
            "command_type": self.__class__.__name__,
            "metadata": self.metadata,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "executed_by": self.executed_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """Create command instance from dictionary"""
        # This would be implemented by subclasses for deserialization
        raise NotImplementedError("Subclasses must implement from_dict")


class CompositeCommand(Command):
    """
    Command that executes multiple commands as a single unit
    
    Useful for transactions or complex operations that need atomicity.
    """
    
    def __init__(self, commands: Optional[List[Command]] = None):
        super().__init__()
        self.commands = commands or []
    
    def add_command(self, command: Command):
        """Add a command to the composite"""
        self.commands.append(command)
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute all commands in sequence"""
        self.logger.info(f"Executing composite command with {len(self.commands)} subcommands")
        
        results = []
        executed_commands = []
        
        try:
            for command in self.commands:
                self.logger.debug(f"Executing subcommand: {command.get_description()}")
                
                # Validate command
                is_valid, errors = command.validate()
                if not is_valid:
                    raise ValueError(f"Command validation failed: {errors}")
                
                # Execute command
                result = command.execute(service)
                results.append(result)
                executed_commands.append(command)
                
                # Stop if any command fails
                if not result.get("success", False):
                    # Rollback executed commands
                    self._rollback(executed_commands, service)
                    
                    return {
                        "success": False,
                        "error": f"Composite command failed at: {command.get_description()}",
                        "failed_command_result": result,
                        "partial_results": results
                    }
            
            return {
                "success": True,
                "message": f"Composite command executed successfully",
                "results": results,
                "total_commands": len(self.commands)
            }
            
        except Exception as e:
            # Rollback on any exception
            self._rollback(executed_commands, service)
            
            self.logger.error(f"Error executing composite command: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "partial_results": results
            }
    
    def _rollback(self, executed_commands: List[Command], service: ParkingService):
        """Rollback all executed commands in reverse order"""
        self.logger.info(f"Rolling back {len(executed_commands)} commands")
        
        for command in reversed(executed_commands):
            if command.can_undo():
                try:
                    undo_result = command.undo(service)
                    if not undo_result.get("success", False):
                        self.logger.error(f"Failed to undo command {command.get_description()}: {undo_result.get('error')}")
                except Exception as e:
                    self.logger.error(f"Error undoing command {command.get_description()}: {e}")
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all commands"""
        errors = []
        
        for command in self.commands:
            is_valid, command_errors = command.validate()
            if not is_valid:
                errors.extend([f"{command.get_description()}: {err}" for err in command_errors])
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        """Check if all commands can be undone"""
        return all(command.can_undo() for command in self.commands)
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo all commands in reverse order"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Not all subcommands support undo"
            }
        
        undo_results = []
        
        for command in reversed(self.commands):
            try:
                result = command.undo(service)
                undo_results.append({
                    "command": command.get_description(),
                    "result": result
                })
                
                if not result.get("success", False):
                    return {
                        "success": False,
                        "error": f"Failed to undo command: {command.get_description()}",
                        "partial_undo_results": undo_results
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error undoing command {command.get_description()}: {str(e)}",
                    "partial_undo_results": undo_results
                }
        
        return {
            "success": True,
            "message": "All commands undone successfully",
            "undo_results": undo_results
        }
    
    def get_description(self) -> str:
        """Get description of composite command"""
        descriptions = [cmd.get_description() for cmd in self.commands]
        return f"CompositeCommand[{', '.join(descriptions)}]"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert composite command to dictionary"""
        data = super().to_dict()
        data["commands"] = [cmd.to_dict() for cmd in self.commands]
        return data


# ============================================================================
# COMMAND RESULT CLASSES
# ============================================================================

@dataclass
class CommandResult:
    """Base class for command execution results"""
    success: bool
    command_id: str
    command_type: str
    executed_at: datetime
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "command_id": self.command_id,
            "command_type": self.command_type,
            "executed_at": self.executed_at.isoformat(),
            "data": self.data,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class ParkingCommandResult(CommandResult):
    """Result for parking-related commands"""
    ticket_id: Optional[str] = None
    slot_number: Optional[int] = None
    license_plate: Optional[str] = None


@dataclass
class ChargingCommandResult(CommandResult):
    """Result for charging-related commands"""
    session_id: Optional[str] = None
    connector_id: Optional[str] = None
    estimated_cost: Optional[float] = None


@dataclass
class BillingCommandResult(CommandResult):
    """Result for billing-related commands"""
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount: Optional[float] = None


# ============================================================================
# PARKING COMMANDS
# ============================================================================

class ParkVehicleCommand(Command):
    """
    Command: Park a vehicle
    
    Business Operation: Vehicle Entry and Slot Allocation
    Can be undone by: ExitVehicleCommand (simulated)
    """
    
    def __init__(self, request: ParkingRequestDTO, executed_by: Optional[str] = None):
        super().__init__()
        self.request = request
        self.executed_by = executed_by or "system"
        
        # Store original state for undo
        self.original_state: Optional[Dict[str, Any]] = None
        self.result: Optional[ParkingAllocationDTO] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute vehicle parking"""
        self.logger.info(f"Executing ParkVehicleCommand for {self.request.license_plate}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute parking operation
            self.result = service.park_vehicle(self.request)
            self.executed_at = datetime.now()
            
            if self.result.success:
                # Store original state for undo
                self.original_state = {
                    "ticket_id": self.result.ticket_id,
                    "license_plate": self.request.license_plate,
                    "slot_number": self.result.slot_number,
                    "parking_lot_id": self.request.parking_lot_id
                }
                
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": asdict(self.result),
                    "message": "Vehicle parked successfully",
                    "ticket_id": self.result.ticket_id,
                    "slot_number": self.result.slot_number
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.message,
                    "data": asdict(self.result)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing ParkVehicleCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate parking request"""
        errors = []
        
        # Check required fields
        if not self.request.license_plate:
            errors.append("License plate is required")
        
        if not self.request.vehicle_type:
            errors.append("Vehicle type is required")
        
        if not self.request.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        # Validate vehicle type
        try:
            VehicleType(self.request.vehicle_type)
        except ValueError:
            errors.append(f"Invalid vehicle type: {self.request.vehicle_type}")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        """This command can be undone by exiting the vehicle"""
        return self.original_state is not None and self.result is not None and self.result.success
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo parking by exiting the vehicle"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: Command was not successfully executed"
            }
        
        try:
            # Create exit request
            exit_request = ExitRequestDTO(
                ticket_id=self.original_state["ticket_id"],
                parking_lot_id=self.request.parking_lot_id,
                license_plate=self.request.license_plate
            )
            
            # Execute exit
            exit_result = service.exit_vehicle(exit_request)
            
            if exit_result.success:
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "message": "Parking undone successfully",
                    "undo_action": "vehicle_exited",
                    "ticket_id": self.original_state["ticket_id"]
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": f"Failed to exit vehicle: {exit_result.message}"
                }
                
        except Exception as e:
            self.logger.error(f"Error undoing ParkVehicleCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Park Vehicle {self.request.license_plate} at {self.request.parking_lot_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["request"] = asdict(self.request)
        data["result"] = asdict(self.result) if self.result else None
        return data


class ExitVehicleCommand(Command):
    """
    Command: Exit a vehicle
    
    Business Operation: Vehicle Exit and Fee Calculation
    Can be undone by: Re-parking (complex, not implemented here)
    """
    
    def __init__(self, request: ExitRequestDTO, executed_by: Optional[str] = None):
        super().__init__()
        self.request = request
        self.executed_by = executed_by or "system"
        self.result: Optional[ParkingExitDTO] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute vehicle exit"""
        self.logger.info(f"Executing ExitVehicleCommand for {self.request.license_plate or self.request.ticket_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute exit operation
            self.result = service.exit_vehicle(self.request)
            self.executed_at = datetime.now()
            
            if self.result.success:
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": asdict(self.result),
                    "message": "Vehicle exited successfully",
                    "invoice_id": self.result.invoice_id,
                    "total_fee": self.result.total_fee
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.message,
                    "data": asdict(self.result)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing ExitVehicleCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate exit request"""
        errors = []
        
        # Need either ticket_id or license_plate
        if not self.request.ticket_id and not self.request.license_plate:
            errors.append("Either ticket ID or license plate is required")
        
        if not self.request.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        return len(errors) == 0, errors
    
    def get_description(self) -> str:
        identifier = self.request.ticket_id or self.request.license_plate
        return f"Exit Vehicle {identifier} from {self.request.parking_lot_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["request"] = asdict(self.request)
        data["result"] = asdict(self.result) if self.result else None
        return data


class AllocateSpecificSlotCommand(Command):
    """
    Command: Allocate a specific parking slot
    
    Business Operation: Manual slot allocation (e.g., for VIP, disabled)
    Can be undone by: ReleaseSpecificSlotCommand
    """
    
    def __init__(
        self,
        license_plate: str,
        vehicle_type: str,
        parking_lot_id: str,
        slot_number: int,
        executed_by: str
    ):
        super().__init__()
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type
        self.parking_lot_id = parking_lot_id
        self.slot_number = slot_number
        self.executed_by = executed_by
        
        self.original_state: Optional[Dict[str, Any]] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute specific slot allocation"""
        self.logger.info(f"Executing AllocateSpecificSlotCommand: {self.license_plate} to slot {self.slot_number}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Create parking request with specific slot preference
            request = ParkingRequestDTO(
                license_plate=self.license_plate,
                vehicle_type=self.vehicle_type,
                parking_lot_id=self.parking_lot_id,
                preferences={
                    "specific_slot": self.slot_number,
                    "force_allocation": True
                }
            )
            
            # Execute parking
            result = service.park_vehicle(request)
            self.executed_at = datetime.now()
            
            if result.success:
                # Store original state
                self.original_state = {
                    "license_plate": self.license_plate,
                    "slot_number": result.slot_number,
                    "parking_lot_id": self.parking_lot_id,
                    "ticket_id": result.ticket_id
                }
                
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": asdict(result),
                    "message": f"Slot {self.slot_number} allocated to {self.license_plate}",
                    "ticket_id": result.ticket_id,
                    "slot_number": result.slot_number
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": result.message,
                    "data": asdict(result)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing AllocateSpecificSlotCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate allocation parameters"""
        errors = []
        
        if not self.license_plate:
            errors.append("License plate is required")
        
        if not self.vehicle_type:
            errors.append("Vehicle type is required")
        
        if not self.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        if self.slot_number <= 0:
            errors.append("Slot number must be positive")
        
        if not self.executed_by:
            errors.append("Executor identity is required for manual allocation")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.original_state is not None
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo specific slot allocation"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: Command was not successfully executed"
            }
        
        try:
            # Create exit request
            exit_request = ExitRequestDTO(
                ticket_id=self.original_state["ticket_id"],
                parking_lot_id=self.parking_lot_id,
                license_plate=self.license_plate
            )
            
            # Execute exit
            result = service.exit_vehicle(exit_request)
            
            if result.success:
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "message": f"Slot {self.slot_number} released",
                    "undo_action": "slot_released",
                    "ticket_id": self.original_state["ticket_id"]
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": f"Failed to release slot: {result.message}"
                }
                
        except Exception as e:
            self.logger.error(f"Error undoing AllocateSpecificSlotCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Allocate Slot {self.slot_number} to {self.license_plate}"


# ============================================================================
# CHARGING COMMANDS
# ============================================================================

class StartChargingSessionCommand(Command):
    """
    Command: Start an EV charging session
    
    Business Operation: EV Charging Initiation
    Can be undone by: StopChargingSessionCommand
    """
    
    def __init__(self, request: ChargingRequestDTO, executed_by: Optional[str] = None):
        super().__init__()
        self.request = request
        self.executed_by = executed_by or "system"
        self.result: Optional[ChargingSessionDTO] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute charging session start"""
        self.logger.info(f"Executing StartChargingSessionCommand for {self.request.license_plate}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute charging start
            self.result = service.start_charging_session(self.request)
            self.executed_at = datetime.now()
            
            if self.result.success:
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": asdict(self.result),
                    "message": "Charging session started successfully",
                    "session_id": self.result.session_id,
                    "connector_id": self.result.connector_id
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.message,
                    "data": asdict(self.result)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing StartChargingSessionCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate charging request"""
        errors = []
        
        if not self.request.license_plate:
            errors.append("License plate is required")
        
        if not self.request.vehicle_type:
            errors.append("Vehicle type is required")
        
        if not self.request.station_id:
            errors.append("Station ID is required")
        
        # Validate EV vehicle type
        try:
            vehicle_type = VehicleType(self.request.vehicle_type)
            if not vehicle_type.is_electric:
                errors.append(f"Vehicle type {self.request.vehicle_type} is not electric")
        except ValueError:
            errors.append(f"Invalid vehicle type: {self.request.vehicle_type}")
        
        # Validate charge percentages
        if not 0 <= self.request.current_charge_percentage <= 100:
            errors.append("Current charge percentage must be between 0 and 100")
        
        if not 0 <= self.request.target_charge_percentage <= 100:
            errors.append("Target charge percentage must be between 0 and 100")
        
        if self.request.target_charge_percentage <= self.request.current_charge_percentage:
            errors.append("Target charge percentage must be greater than current charge")
        
        if self.request.battery_capacity_kwh <= 0:
            errors.append("Battery capacity must be positive")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.result is not None and self.result.success
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo by stopping the charging session"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: Command was not successfully executed"
            }
        
        try:
            # Stop charging session
            stop_result = service.stop_charging_session(
                session_id=self.result.session_id,
                station_id=self.request.station_id
            )
            
            if stop_result.get("success", False):
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "message": "Charging session stopped (undone)",
                    "undo_action": "charging_stopped",
                    "session_id": self.result.session_id
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": f"Failed to stop charging session: {stop_result.get('error')}"
                }
                
        except Exception as e:
            self.logger.error(f"Error undoing StartChargingSessionCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Start Charging Session for {self.request.license_plate} at {self.request.station_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["request"] = asdict(self.request)
        data["result"] = asdict(self.result) if self.result else None
        return data


class StopChargingSessionCommand(Command):
    """
    Command: Stop an EV charging session
    
    Business Operation: EV Charging Termination and Billing
    """
    
    def __init__(
        self,
        session_id: str,
        station_id: str,
        executed_by: Optional[str] = None
    ):
        super().__init__()
        self.session_id = session_id
        self.station_id = station_id
        self.executed_by = executed_by or "system"
        self.result: Optional[Dict[str, Any]] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute charging session stop"""
        self.logger.info(f"Executing StopChargingSessionCommand for session {self.session_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute charging stop
            self.result = service.stop_charging_session(self.session_id, self.station_id)
            self.executed_at = datetime.now()
            
            if self.result.get("success", False):
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": self.result,
                    "message": "Charging session stopped successfully",
                    "session_id": self.session_id,
                    "energy_delivered": self.result.get("energy_delivered_kwh")
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.get("error"),
                    "data": self.result
                }
                
        except Exception as e:
            self.logger.error(f"Error executing StopChargingSessionCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate stop request"""
        errors = []
        
        if not self.session_id:
            errors.append("Session ID is required")
        
        if not self.station_id:
            errors.append("Station ID is required")
        
        return len(errors) == 0, errors
    
    def get_description(self) -> str:
        return f"Stop Charging Session {self.session_id}"


# ============================================================================
# RESERVATION COMMANDS
# ============================================================================

class MakeReservationCommand(Command):
    """
    Command: Make a parking reservation
    
    Business Operation: Future Parking Slot Booking
    Can be undone by: CancelReservationCommand
    """
    
    def __init__(self, request: ReservationRequestDTO, executed_by: Optional[str] = None):
        super().__init__()
        self.request = request
        self.executed_by = executed_by or "system"
        self.result: Optional[ReservationDTO] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute reservation creation"""
        self.logger.info(f"Executing MakeReservationCommand for {self.request.license_plate}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute reservation
            self.result = service.make_reservation(self.request)
            self.executed_at = datetime.now()
            
            if self.result.success:
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": asdict(self.result),
                    "message": "Reservation created successfully",
                    "reservation_id": self.result.reservation_id,
                    "confirmation_code": self.result.confirmation_code
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.message,
                    "data": asdict(self.result)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing MakeReservationCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate reservation request"""
        errors = []
        
        if not self.request.license_plate:
            errors.append("License plate is required")
        
        if not self.request.vehicle_type:
            errors.append("Vehicle type is required")
        
        if not self.request.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        if not self.request.start_time:
            errors.append("Start time is required")
        
        if not self.request.end_time:
            errors.append("End time is required")
        
        # Validate times
        if self.request.start_time and self.request.end_time:
            if self.request.end_time <= self.request.start_time:
                errors.append("End time must be after start time")
            
            # Cannot reserve in the past
            if self.request.start_time < datetime.now():
                errors.append("Start time cannot be in the past")
            
            # Maximum reservation duration (e.g., 7 days)
            max_duration = timedelta(days=7)
            if self.request.end_time - self.request.start_time > max_duration:
                errors.append(f"Maximum reservation duration is {max_duration.days} days")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.result is not None and self.result.success
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo reservation by cancelling it"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: Command was not successfully executed"
            }
        
        try:
            # Cancel reservation
            cancel_result = service.cancel_reservation(self.result.reservation_id)
            
            if cancel_result.get("success", False):
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "message": "Reservation cancelled (undone)",
                    "undo_action": "reservation_cancelled",
                    "reservation_id": self.result.reservation_id
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": f"Failed to cancel reservation: {cancel_result.get('error')}"
                }
                
        except Exception as e:
            self.logger.error(f"Error undoing MakeReservationCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Make Reservation for {self.request.license_plate} from {self.request.start_time} to {self.request.end_time}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["request"] = asdict(self.request)
        data["result"] = asdict(self.result) if self.result else None
        return data


class CancelReservationCommand(Command):
    """
    Command: Cancel a parking reservation
    
    Business Operation: Reservation Cancellation
    """
    
    def __init__(self, reservation_id: str, executed_by: Optional[str] = None):
        super().__init__()
        self.reservation_id = reservation_id
        self.executed_by = executed_by or "system"
        self.result: Optional[Dict[str, Any]] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute reservation cancellation"""
        self.logger.info(f"Executing CancelReservationCommand for {self.reservation_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Execute cancellation
            self.result = service.cancel_reservation(self.reservation_id)
            self.executed_at = datetime.now()
            
            if self.result.get("success", False):
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": self.result,
                    "message": "Reservation cancelled successfully",
                    "reservation_id": self.reservation_id
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": self.result.get("error"),
                    "data": self.result
                }
                
        except Exception as e:
            self.logger.error(f"Error executing CancelReservationCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate cancellation request"""
        errors = []
        
        if not self.reservation_id:
            errors.append("Reservation ID is required")
        
        return len(errors) == 0, errors
    
    def get_description(self) -> str:
        return f"Cancel Reservation {self.reservation_id}"


# ============================================================================
# BILLING COMMANDS
# ============================================================================

class GenerateInvoiceCommand(Command):
    """
    Command: Generate an invoice
    
    Business Operation: Invoice Generation
    """
    
    def __init__(
        self,
        license_plate: str,
        services: List[Dict[str, Any]],
        customer_id: Optional[str] = None,
        executed_by: Optional[str] = None
    ):
        super().__init__()
        self.license_plate = license_plate
        self.services = services
        self.customer_id = customer_id
        self.executed_by = executed_by or "system"
        self.invoice_id: Optional[str] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute invoice generation"""
        self.logger.info(f"Executing GenerateInvoiceCommand for {self.license_plate}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Get invoice from service
            # Note: In real system, would call service.generate_invoice()
            # For now, simulate by getting the latest invoice
            self.executed_at = datetime.now()
            
            # Simulate invoice generation
            self.invoice_id = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": "Invoice generated successfully",
                "invoice_id": self.invoice_id,
                "license_plate": self.license_plate,
                "services": self.services
            }
            
        except Exception as e:
            self.logger.error(f"Error executing GenerateInvoiceCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate invoice generation parameters"""
        errors = []
        
        if not self.license_plate:
            errors.append("License plate is required")
        
        if not self.services:
            errors.append("At least one service is required")
        
        return len(errors) == 0, errors
    
    def get_description(self) -> str:
        return f"Generate Invoice for {self.license_plate}"


class ProcessPaymentCommand(Command):
    """
    Command: Process a payment
    
    Business Operation: Payment Processing
    Can be undone by: RefundPaymentCommand
    """
    
    def __init__(
        self,
        invoice_id: str,
        payment_method: str,
        amount: float,
        executed_by: Optional[str] = None
    ):
        super().__init__()
        self.invoice_id = invoice_id
        self.payment_method = payment_method
        self.amount = amount
        self.executed_by = executed_by or "system"
        self.payment_id: Optional[str] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute payment processing"""
        self.logger.info(f"Executing ProcessPaymentCommand for invoice {self.invoice_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # Process payment
            result = service.process_payment(
                invoice_id=self.invoice_id,
                payment_method=self.payment_method,
                amount=self.amount
            )
            
            self.executed_at = datetime.now()
            
            if result.get("success", False):
                self.payment_id = result.get("payment_id")
                return {
                    "success": True,
                    "command_id": self.command_id,
                    "data": result,
                    "message": "Payment processed successfully",
                    "payment_id": self.payment_id,
                    "invoice_id": self.invoice_id
                }
            else:
                return {
                    "success": False,
                    "command_id": self.command_id,
                    "error": result.get("error"),
                    "data": result
                }
                
        except Exception as e:
            self.logger.error(f"Error executing ProcessPaymentCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate payment parameters"""
        errors = []
        
        if not self.invoice_id:
            errors.append("Invoice ID is required")
        
        if not self.payment_method:
            errors.append("Payment method is required")
        
        if self.amount <= 0:
            errors.append("Payment amount must be positive")
        
        # Validate payment method
        valid_methods = ["credit_card", "debit_card", "cash", "mobile_wallet", "subscription"]
        if self.payment_method not in valid_methods:
            errors.append(f"Invalid payment method. Valid methods: {', '.join(valid_methods)}")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.payment_id is not None
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo payment by issuing refund"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: Payment was not successfully processed"
            }
        
        try:
            # In real system, would call service.issue_refund()
            # For now, simulate refund
            
            refund_id = f"REF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": "Payment refunded (undone)",
                "undo_action": "payment_refunded",
                "refund_id": refund_id,
                "payment_id": self.payment_id,
                "amount": self.amount
            }
            
        except Exception as e:
            self.logger.error(f"Error undoing ProcessPaymentCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Process Payment of ${self.amount:.2f} for invoice {self.invoice_id}"


# ============================================================================
# ADMIN COMMANDS
# ============================================================================

class UpdatePricingStrategyCommand(Command):
    """
    Command: Update pricing strategy
    
    Business Operation: Dynamic Pricing Configuration
    Can be undone by: Restore previous strategy
    """
    
    def __init__(
        self,
        parking_lot_id: str,
        strategy_type: str,
        parameters: Dict[str, Any],
        executed_by: str
    ):
        super().__init__()
        self.parking_lot_id = parking_lot_id
        self.strategy_type = strategy_type
        self.parameters = parameters
        self.executed_by = executed_by
        
        self.previous_strategy: Optional[Dict[str, Any]] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute pricing strategy update"""
        self.logger.info(f"Executing UpdatePricingStrategyCommand for {self.parking_lot_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # In real system, would update pricing strategy in database
            # For now, simulate update
            
            # Store previous strategy for undo
            self.previous_strategy = {
                "strategy_type": "standard",  # Would be actual previous strategy
                "parameters": {"base_rate": 10.0}  # Would be actual parameters
            }
            
            self.executed_at = datetime.now()
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": f"Pricing strategy updated to {self.strategy_type}",
                "parking_lot_id": self.parking_lot_id,
                "new_strategy": {
                    "type": self.strategy_type,
                    "parameters": self.parameters
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error executing UpdatePricingStrategyCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate pricing strategy update"""
        errors = []
        
        if not self.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        if not self.strategy_type:
            errors.append("Strategy type is required")
        
        valid_strategies = ["standard", "dynamic", "subscription", "peak", "offpeak"]
        if self.strategy_type not in valid_strategies:
            errors.append(f"Invalid strategy type. Valid types: {', '.join(valid_strategies)}")
        
        if not self.executed_by:
            errors.append("Executor identity is required for admin operations")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.previous_strategy is not None
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo by restoring previous strategy"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: No previous strategy stored"
            }
        
        try:
            # In real system, would restore previous strategy
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": "Pricing strategy restored to previous version",
                "undo_action": "strategy_restored",
                "restored_strategy": self.previous_strategy
            }
            
        except Exception as e:
            self.logger.error(f"Error undoing UpdatePricingStrategyCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Update Pricing Strategy for {self.parking_lot_id} to {self.strategy_type}"


class ConfigureParkingLotCommand(Command):
    """
    Command: Configure parking lot settings
    
    Business Operation: Parking Lot Management
    """
    
    def __init__(
        self,
        parking_lot_id: str,
        configuration: Dict[str, Any],
        executed_by: str
    ):
        super().__init__()
        self.parking_lot_id = parking_lot_id
        self.configuration = configuration
        self.executed_by = executed_by
        self.previous_configuration: Optional[Dict[str, Any]] = None
    
    def execute(self, service: ParkingService) -> Dict[str, Any]:
        """Execute parking lot configuration"""
        self.logger.info(f"Executing ConfigureParkingLotCommand for {self.parking_lot_id}")
        
        try:
            # Validate command
            is_valid, errors = self.validate()
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {errors}",
                    "command_id": self.command_id
                }
            
            # In real system, would update parking lot configuration
            # Store previous configuration for undo
            self.previous_configuration = {
                "total_slots": 100,
                "slot_distribution": {"REGULAR": 70, "PREMIUM": 20, "EV": 10},
                "policies": {"ev_can_use_regular": True}
            }
            
            self.executed_at = datetime.now()
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": "Parking lot configuration updated",
                "parking_lot_id": self.parking_lot_id,
                "new_configuration": self.configuration
            }
            
        except Exception as e:
            self.logger.error(f"Error executing ConfigureParkingLotCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration"""
        errors = []
        
        if not self.parking_lot_id:
            errors.append("Parking lot ID is required")
        
        if not self.configuration:
            errors.append("Configuration is required")
        
        if not self.executed_by:
            errors.append("Executor identity is required for admin operations")
        
        return len(errors) == 0, errors
    
    def can_undo(self) -> bool:
        return self.previous_configuration is not None
    
    def undo(self, service: ParkingService) -> Dict[str, Any]:
        """Undo by restoring previous configuration"""
        if not self.can_undo():
            return {
                "success": False,
                "error": "Cannot undo: No previous configuration stored"
            }
        
        try:
            # In real system, would restore previous configuration
            
            return {
                "success": True,
                "command_id": self.command_id,
                "message": "Parking lot configuration restored",
                "undo_action": "configuration_restored",
                "restored_configuration": self.previous_configuration
            }
            
        except Exception as e:
            self.logger.error(f"Error undoing ConfigureParkingLotCommand: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": self.command_id,
                "error": str(e)
            }
    
    def get_description(self) -> str:
        return f"Configure Parking Lot {self.parking_lot_id}"


# ============================================================================
# COMMAND FACTORY
# ============================================================================

class CommandFactory:
    """Factory for creating commands from dictionary data"""
    
    @staticmethod
    def create_command(command_type: str, data: Dict[str, Any]) -> Optional[Command]:
        """
        Create a command instance from type and data
        
        Args:
            command_type: Type of command to create
            data: Command parameters
            
        Returns: Command instance or None if type not recognized
        """
        command_classes = {
            # Parking commands
            "park_vehicle": ParkVehicleCommand,
            "exit_vehicle": ExitVehicleCommand,
            "allocate_specific_slot": AllocateSpecificSlotCommand,
            
            # Charging commands
            "start_charging_session": StartChargingSessionCommand,
            "stop_charging_session": StopChargingSessionCommand,
            
            # Reservation commands
            "make_reservation": MakeReservationCommand,
            "cancel_reservation": CancelReservationCommand,
            
            # Billing commands
            "generate_invoice": GenerateInvoiceCommand,
            "process_payment": ProcessPaymentCommand,
            
            # Admin commands
            "update_pricing_strategy": UpdatePricingStrategyCommand,
            "configure_parking_lot": ConfigureParkingLotCommand,
        }
        
        command_class = command_classes.get(command_type)
        if not command_class:
            return None
        
        try:
            # Create DTOs from data
            if command_type == "park_vehicle":
                request = ParkingRequestDTO(**data.get("request", {}))
                return command_class(request, data.get("executed_by"))
            
            elif command_type == "exit_vehicle":
                request = ExitRequestDTO(**data.get("request", {}))
                return command_class(request, data.get("executed_by"))
            
            elif command_type == "start_charging_session":
                request = ChargingRequestDTO(**data.get("request", {}))
                return command_class(request, data.get("executed_by"))
            
            elif command_type == "make_reservation":
                request = ReservationRequestDTO(**data.get("request", {}))
                return command_class(request, data.get("executed_by"))
            
            else:
                # For commands with simple parameters
                return command_class(**data)
                
        except Exception as e:
            logging.getLogger("CommandFactory").error(f"Error creating command {command_type}: {e}")
            return None
    
    @staticmethod
    def create_composite_command(commands_data: List[Dict[str, Any]]) -> CompositeCommand:
        """Create a composite command from list of command data"""
        commands = []
        
        for cmd_data in commands_data:
            cmd_type = cmd_data.get("type")
            cmd = CommandFactory.create_command(cmd_type, cmd_data.get("data", {}))
            if cmd:
                commands.append(cmd)
        
        return CompositeCommand(commands)


# ============================================================================
# COMMAND PROCESSOR
# ============================================================================

class CommandProcessor:
    """
    Processes commands with features like:
    - Command queuing
    - Transaction management
    - Undo/redo support
    - Command logging
    """
    
    def __init__(self, service: ParkingService):
        self.service = service
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Command history for undo/redo
        self.command_history: List[Command] = []
        self.undone_commands: List[Command] = []
        
        # Maximum history size
        self.max_history_size = 1000
    
    def process(self, command: Command) -> Dict[str, Any]:
        """
        Process a command
        
        Args:
            command: Command to execute
            
        Returns: Execution result
        """
        self.logger.info(f"Processing command: {command.get_description()}")
        
        try:
            # Execute command
            result = command.execute(self.service)
            
            # Add to history if successful
            if result.get("success", False):
                self._add_to_history(command)
                # Clear undone commands stack (new branch)
                self.undone_commands.clear()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing command: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": command.command_id,
                "error": str(e)
            }
    
    def process_batch(self, commands: List[Command]) -> List[Dict[str, Any]]:
        """Process multiple commands as a batch"""
        results = []
        
        for command in commands:
            result = self.process(command)
            results.append(result)
            
            # Stop processing if a command fails (optional)
            # if not result.get("success", False):
            #     break
        
        return results
    
    def undo_last(self) -> Dict[str, Any]:
        """Undo the last executed command"""
        if not self.command_history:
            return {
                "success": False,
                "error": "No commands to undo"
            }
        
        command = self.command_history.pop()
        
        try:
            if command.can_undo():
                result = command.undo(self.service)
                
                if result.get("success", False):
                    self.undone_commands.append(command)
                
                return result
            else:
                return {
                    "success": False,
                    "error": f"Command {command.get_description()} does not support undo"
                }
                
        except Exception as e:
            self.logger.error(f"Error undoing command: {e}", exc_info=True)
            
            # Put command back in history
            self.command_history.append(command)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def redo_last(self) -> Dict[str, Any]:
        """Redo the last undone command"""
        if not self.undone_commands:
            return {
                "success": False,
                "error": "No commands to redo"
            }
        
        command = self.undone_commands.pop()
        
        try:
            result = command.execute(self.service)
            
            if result.get("success", False):
                self._add_to_history(command)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error redoing command: {e}", exc_info=True)
            
            # Put command back in undone stack
            self.undone_commands.append(command)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get command history"""
        history = self.command_history.copy()
        if limit:
            history = history[-limit:]
        
        return [cmd.to_dict() for cmd in history]
    
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()
        self.undone_commands.clear()
    
    def _add_to_history(self, command: Command):
        """Add command to history, respecting max size"""
        self.command_history.append(command)
        
        # Trim history if too large
        if len(self.command_history) > self.max_history_size:
            self.command_history = self.command_history[-self.max_history_size:]
    
    def create_transaction(self, commands: List[Command]) -> CompositeCommand:
        """Create a transaction (composite command)"""
        return CompositeCommand(commands)


# ============================================================================
# COMMAND SERIALIZER
# ============================================================================

class CommandSerializer:
    """Handles serialization and deserialization of commands"""
    
    @staticmethod
    def serialize(command: Command) -> str:
        """Serialize command to JSON string"""
        data = command.to_dict()
        return json.dumps(data, default=str)
    
    @staticmethod
    def deserialize(json_str: str) -> Optional[Command]:
        """Deserialize command from JSON string"""
        try:
            data = json.loads(json_str)
            command_type = data.get("command_type")
            
            if command_type == "CompositeCommand":
                commands_data = data.get("commands", [])
                commands = []
                
                for cmd_data in commands_data:
                    cmd = CommandSerializer._deserialize_single(cmd_data)
                    if cmd:
                        commands.append(cmd)
                
                return CompositeCommand(commands)
            else:
                return CommandSerializer._deserialize_single(data)
                
        except Exception as e:
            logging.getLogger("CommandSerializer").error(f"Error deserializing command: {e}")
            return None
    
    @staticmethod
    def _deserialize_single(data: Dict[str, Any]) -> Optional[Command]:
        """Deserialize a single command"""
        command_type = data.get("command_type")
        
        # Remove metadata fields
        command_data = {k: v for k, v in data.items() if k not in ["command_id", "command_type", "metadata", "executed_at", "executed_by"]}
        
        # Add executed_by if present
        if "executed_by" in data:
            command_data["executed_by"] = data["executed_by"]
        
        return CommandFactory.create_command(
            CommandSerializer._command_type_to_key(command_type),
            command_data
        )
    
    @staticmethod
    def _command_type_to_key(command_type: str) -> str:
        """Convert command class name to factory key"""
        # Remove "Command" suffix and convert to snake_case
        base_name = command_type.replace("Command", "")
        
        # Convert PascalCase to snake_case
        import re
        key = re.sub(r'(?<!^)(?=[A-Z])', '_', base_name).lower()
        
        # Special cases
        special_cases = {
            "ParkVehicle": "park_vehicle",
            "ExitVehicle": "exit_vehicle",
            "AllocateSpecificSlot": "allocate_specific_slot",
            "StartChargingSession": "start_charging_session",
            "StopChargingSession": "stop_charging_session",
            "MakeReservation": "make_reservation",
            "CancelReservation": "cancel_reservation",
            "GenerateInvoice": "generate_invoice",
            "ProcessPayment": "process_payment",
            "UpdatePricingStrategy": "update_pricing_strategy",
            "ConfigureParkingLot": "configure_parking_lot",
        }
        
        return special_cases.get(base_name, key)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage():
    """Example usage of the command pattern"""
    from ..application.parking_service import ParkingServiceFactory
    
    # Create service
    service = ParkingServiceFactory.create_default_service()
    
    # Create command processor
    processor = CommandProcessor(service)
    
    # Example 1: Park a vehicle
    parking_request = ParkingRequestDTO(
        license_plate="ABC-123",
        vehicle_type="CAR",
        parking_lot_id="lot-001"
    )
    
    park_command = ParkVehicleCommand(parking_request, executed_by="user-001")
    result = processor.process(park_command)
    print(f"Park command result: {result}")
    
    # Example 2: Start charging session
    charging_request = ChargingRequestDTO(
        license_plate="EV-456",
        vehicle_type="EV_CAR",
        station_id="station-001",
        current_charge_percentage=20.0,
        target_charge_percentage=80.0,
        battery_capacity_kwh=60.0
    )
    
    charge_command = StartChargingSessionCommand(charging_request, executed_by="user-001")
    result = processor.process(charge_command)
    print(f"Charge command result: {result}")
    
    # Example 3: Undo last command
    undo_result = processor.undo_last()
    print(f"Undo result: {undo_result}")
    
    # Example 4: Get command history
    history = processor.get_history()
    print(f"Command history: {len(history)} commands")
    
    # Example 5: Create and execute composite command (transaction)
    transaction_commands = [
        ParkVehicleCommand(
            ParkingRequestDTO(license_plate="XYZ-789", vehicle_type="CAR", parking_lot_id="lot-001"),
            executed_by="user-001"
        ),
        StartChargingSessionCommand(
            ChargingRequestDTO(
                license_plate="EV-999",
                vehicle_type="EV_CAR",
                station_id="station-001",
                current_charge_percentage=30.0,
                target_charge_percentage=90.0,
                battery_capacity_kwh=75.0
            ),
            executed_by="user-001"
        )
    ]
    
    transaction = CompositeCommand(transaction_commands)
    transaction_result = processor.process(transaction)
    print(f"Transaction result: {transaction_result}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    example_usage()