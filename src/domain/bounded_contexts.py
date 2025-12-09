# File: src/domain/bounded_contexts.py
"""
Bounded Contexts for Parking Management System

This module defines the bounded contexts that encapsulate specific domain logic
within the parking management system. Each bounded context has:
1. Clear boundaries and responsibilities
2. Its own ubiquitous language
3. Specific domain models and aggregates
4. Context-specific business rules

Key Bounded Contexts:
1. Parking Management Context - Core parking operations and allocation
2. Billing & Pricing Context - Fee calculation and payment processing
3. EV Charging Context - Electric vehicle charging management
4. Security & Validation Context - Access control and validation
5. Monitoring & Analytics Context - Real-time monitoring and reporting

Context Maps:
- Define relationships between contexts
- Translation between contexts when needed
- Anti-corruption layers for external integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional, Any, Protocol, runtime_checkable
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import (
    ParkingSlot, Vehicle, ElectricVehicle,
    VehicleType, SlotType, ChargerType,
    Money, TimeRange, LicensePlate,
    ParkingTicket, Invoice, Payment
)
from .aggregates import ParkingLot, ChargingStation
from .strategies import (
    ParkingStrategy, PricingStrategy, ChargingStrategy, ValidationStrategy,
    StandardCarStrategy, ElectricCarStrategy, MotorcycleStrategy,
    LargeVehicleStrategy, NearestEntryStrategy,
    StandardPricingStrategy, DynamicPricingStrategy, SubscriptionPricingStrategy,
    FastChargingStrategy, CostOptimizedChargingStrategy, BalancedChargingStrategy
)


# ============================================================================
# CONTEXT INTERFACES
# ============================================================================

class BoundedContext(ABC):
    """Abstract base class for bounded contexts"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{self.__class__.__name__}:{name}")
        self.logger.info(f"Initialized {name} bounded context")
    
    @abstractmethod
    def execute_command(self, command: Any) -> Any:
        """Execute a command within this bounded context"""
        pass
    
    @abstractmethod
    def execute_query(self, query: Any) -> Any:
        """Execute a query within this bounded context"""
        pass
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get information about this bounded context"""
        return {
            "name": self.name,
            "description": self.__doc__ or "",
            "timestamp": datetime.now().isoformat()
        }


@runtime_checkable
class ContextIntegration(Protocol):
    """Protocol for context integration points"""
    
    def translate_to_context(self, data: Dict[str, Any], target_context: str) -> Dict[str, Any]:
        """Translate data from this context to another context"""
        ...
    
    def receive_from_context(self, data: Dict[str, Any], source_context: str) -> Dict[str, Any]:
        """Receive and adapt data from another context"""
        ...


# ============================================================================
# PARKING MANAGEMENT CONTEXT
# ============================================================================

class ParkingManagementContext(BoundedContext):
    """
    Bounded Context: Parking Management
    
    Core Responsibility:
    - Manage parking slot allocation and deallocation
    - Handle vehicle entry and exit
    - Enforce parking policies and rules
    - Coordinate with other contexts for pricing and validation
    
    Ubiquitous Language:
    - Slot Allocation, Vehicle Accommodation, Occupancy Management
    - Entry/Exit Flow, Slot Reservation, Overstay Handling
    """
    
    def __init__(self):
        super().__init__("ParkingManagement")
        
        # Initialize strategies based on configuration
        self.parking_strategies: Dict[VehicleType, ParkingStrategy] = {
            VehicleType.CAR: StandardCarStrategy(),
            VehicleType.EV_CAR: ElectricCarStrategy(),
            VehicleType.MOTORCYCLE: MotorcycleStrategy(),
            VehicleType.EV_MOTORCYCLE: MotorcycleStrategy(),
            VehicleType.TRUCK: LargeVehicleStrategy(),
            VehicleType.EV_TRUCK: LargeVehicleStrategy(),
            VehicleType.BUS: LargeVehicleStrategy(),
        }
        
        # Context state
        self.parking_lots: Dict[str, ParkingLot] = {}
        self.active_tickets: Dict[str, ParkingTicket] = {}
        self.parking_history: List[Dict[str, Any]] = []
        
        # Integration points
        self.integrations: Dict[str, ContextIntegration] = {}
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parking management commands"""
        command_type = command.get("type")
        
        if command_type == "allocate_parking":
            return self._allocate_parking(command)
        elif command_type == "release_parking":
            return self._release_parking(command)
        elif command_type == "register_vehicle_entry":
            return self._register_vehicle_entry(command)
        elif command_type == "register_vehicle_exit":
            return self._register_vehicle_exit(command)
        elif command_type == "reserve_slot":
            return self._reserve_slot(command)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parking management queries"""
        query_type = query.get("type")
        
        if query_type == "get_available_slots":
            return self._get_available_slots(query)
        elif query_type == "get_parking_status":
            return self._get_parking_status(query)
        elif query_type == "get_occupancy":
            return self._get_occupancy(query)
        elif query_type == "get_vehicle_history":
            return self._get_vehicle_history(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _allocate_parking(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate parking slot for vehicle"""
        try:
            # Extract command data
            vehicle_data = command["vehicle"]
            lot_id = command["parking_lot_id"]
            preferences = command.get("preferences", {})
            
            # Get parking lot
            parking_lot = self.parking_lots.get(lot_id)
            if not parking_lot:
                return {"success": False, "error": f"Parking lot {lot_id} not found"}
            
            # Create vehicle (in real system, this would come from Vehicle context)
            vehicle = self._create_vehicle_from_data(vehicle_data)
            
            # Get appropriate strategy
            strategy = self.parking_strategies.get(vehicle.vehicle_type)
            if not strategy:
                strategy = StandardCarStrategy()  # Default
            
            # Allocate slot
            slot = strategy.allocate_slot(parking_lot, vehicle, preferences)
            
            if not slot:
                return {"success": False, "error": "No available slots"}
            
            # Mark slot as occupied
            parking_lot.occupy_slot(slot.number, vehicle.license_plate)
            
            # Create parking ticket
            ticket = ParkingTicket(
                ticket_id=f"TICKET-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                license_plate=vehicle.license_plate,
                slot_number=slot.number,
                entry_time=datetime.now(),
                vehicle_type=vehicle.vehicle_type
            )
            
            # Store ticket
            self.active_tickets[ticket.ticket_id] = ticket
            
            # Record history
            self.parking_history.append({
                "timestamp": datetime.now(),
                "action": "allocate_parking",
                "ticket_id": ticket.ticket_id,
                "license_plate": vehicle.license_plate,
                "slot_number": slot.number
            })
            
            return {
                "success": True,
                "ticket_id": ticket.ticket_id,
                "slot_number": slot.number,
                "slot_type": slot.slot_type.value,
                "strategy_used": strategy.get_strategy_name()
            }
            
        except Exception as e:
            self.logger.error(f"Error allocating parking: {e}")
            return {"success": False, "error": str(e)}
    
    def _release_parking(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Release parking slot"""
        try:
            ticket_id = command["ticket_id"]
            lot_id = command["parking_lot_id"]
            
            # Get ticket and parking lot
            ticket = self.active_tickets.get(ticket_id)
            if not ticket:
                return {"success": False, "error": f"Ticket {ticket_id} not found"}
            
            parking_lot = self.parking_lots.get(lot_id)
            if not parking_lot:
                return {"success": False, "error": f"Parking lot {lot_id} not found"}
            
            # Release slot
            parking_lot.release_slot(ticket.slot_number)
            
            # Remove active ticket
            del self.active_tickets[ticket_id]
            
            # Record history
            self.parking_history.append({
                "timestamp": datetime.now(),
                "action": "release_parking",
                "ticket_id": ticket_id,
                "slot_number": ticket.slot_number
            })
            
            # Send to billing context for fee calculation
            if "billing" in self.integrations:
                billing_data = {
                    "ticket_id": ticket_id,
                    "license_plate": ticket.license_plate,
                    "entry_time": ticket.entry_time,
                    "exit_time": datetime.now(),
                    "vehicle_type": ticket.vehicle_type.value,
                    "slot_number": ticket.slot_number
                }
                self.integrations["billing"].receive_from_context(billing_data, "parking_management")
            
            return {"success": True, "slot_released": ticket.slot_number}
            
        except Exception as e:
            self.logger.error(f"Error releasing parking: {e}")
            return {"success": False, "error": str(e)}
    
    def _register_vehicle_entry(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Register vehicle entry (without immediate allocation)"""
        # This would handle entry gate logic, license plate recognition, etc.
        # For now, delegate to allocate_parking
        return self._allocate_parking(command)
    
    def _register_vehicle_exit(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Register vehicle exit"""
        # This would handle exit gate logic, payment verification, etc.
        # For now, delegate to release_parking
        return self._release_parking(command)
    
    def _reserve_slot(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve parking slot in advance"""
        # Implementation for reservation system
        # Would handle time-based reservations, prepayments, etc.
        pass
    
    def _get_available_slots(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get available slots by criteria"""
        lot_id = query["parking_lot_id"]
        vehicle_type_str = query.get("vehicle_type")
        
        parking_lot = self.parking_lots.get(lot_id)
        if not parking_lot:
            return {"success": False, "error": f"Parking lot {lot_id} not found"}
        
        if vehicle_type_str:
            vehicle_type = VehicleType(vehicle_type_str)
            available_slots = parking_lot.get_available_slots_by_vehicle_type(vehicle_type)
        else:
            available_slots = parking_lot.get_all_available_slots()
        
        return {
            "success": True,
            "available_slots": len(available_slots),
            "slots": [slot.number for slot in available_slots]
        }
    
    def _get_parking_status(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get current parking status"""
        lot_id = query["parking_lot_id"]
        
        parking_lot = self.parking_lots.get(lot_id)
        if not parking_lot:
            return {"success": False, "error": f"Parking lot {lot_id} not found"}
        
        return {
            "success": True,
            "total_slots": parking_lot.total_slots,
            "occupied_slots": parking_lot.occupied_slots,
            "available_slots": parking_lot.available_slots,
            "occupancy_rate": parking_lot.get_occupancy_rate()
        }
    
    def _get_occupancy(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed occupancy information"""
        lot_id = query["parking_lot_id"]
        
        parking_lot = self.parking_lots.get(lot_id)
        if not parking_lot:
            return {"success": False, "error": f"Parking lot {lot_id} not found"}
        
        occupancy_by_type = {}
        for slot_type in SlotType:
            count = parking_lot.get_occupied_slots_by_type(slot_type)
            total = parking_lot.get_total_slots_by_type(slot_type)
            occupancy_by_type[slot_type.value] = {
                "occupied": count,
                "total": total,
                "rate": count / total if total > 0 else 0
            }
        
        return {
            "success": True,
            "overall_occupancy": parking_lot.get_occupancy_rate(),
            "by_slot_type": occupancy_by_type
        }
    
    def _get_vehicle_history(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get parking history for a vehicle"""
        license_plate = query["license_plate"]
        
        history = [
            record for record in self.parking_history
            if record.get("license_plate") == license_plate
        ]
        
        return {
            "success": True,
            "license_plate": license_plate,
            "total_visits": len(history),
            "history": history
        }
    
    def _create_vehicle_from_data(self, vehicle_data: Dict[str, Any]) -> Vehicle:
        """Create vehicle object from data dictionary"""
        # Simplified implementation
        # In real system, this would come from Vehicle Management context
        license_plate = LicensePlate(vehicle_data["license_plate"])
        vehicle_type = VehicleType(vehicle_data["vehicle_type"])
        
        if vehicle_type.is_electric:
            return ElectricVehicle(
                license_plate=license_plate,
                vehicle_type=vehicle_type,
                make=vehicle_data.get("make", "Unknown"),
                model=vehicle_data.get("model", "Unknown"),
                battery_capacity_kwh=vehicle_data.get("battery_capacity_kwh", 60.0),
                charge_percentage=vehicle_data.get("charge_percentage", 50.0)
            )
        else:
            return Vehicle(
                license_plate=license_plate,
                vehicle_type=vehicle_type,
                make=vehicle_data.get("make", "Unknown"),
                model=vehicle_data.get("model", "Unknown")
            )
    
    def register_integration(self, context_name: str, integration: ContextIntegration):
        """Register integration with another bounded context"""
        self.integrations[context_name] = integration
        self.logger.info(f"Registered integration with {context_name} context")


# ============================================================================
# BILLING & PRICING CONTEXT
# ============================================================================

class BillingPricingContext(BoundedContext):
    """
    Bounded Context: Billing & Pricing
    
    Core Responsibility:
    - Calculate parking and charging fees
    - Generate invoices and process payments
    - Handle discounts, promotions, and subscriptions
    - Manage billing disputes and refunds
    
    Ubiquitous Language:
    - Fee Calculation, Invoice Generation, Payment Processing
    - Discount Application, Billing Cycle, Payment Gateway
    """
    
    def __init__(self):
        super().__init__("BillingPricing")
        
        # Initialize pricing strategies
        self.pricing_strategies: Dict[str, PricingStrategy] = {
            "standard": StandardPricingStrategy(),
            "dynamic": DynamicPricingStrategy(),
            "subscription": SubscriptionPricingStrategy()
        }
        
        # Store invoices and payments
        self.invoices: Dict[str, Invoice] = {}
        self.payments: Dict[str, Payment] = {}
        self.revenue_records: List[Dict[str, Any]] = []
        
        # Business rules
        self.active_promotions: Dict[str, Dict[str, Any]] = {}
        self.tax_rate = Decimal('0.10')  # 10% tax
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute billing and pricing commands"""
        command_type = command.get("type")
        
        if command_type == "calculate_fee":
            return self._calculate_fee(command)
        elif command_type == "generate_invoice":
            return self._generate_invoice(command)
        elif command_type == "process_payment":
            return self._process_payment(command)
        elif command_type == "apply_discount":
            return self._apply_discount(command)
        elif command_type == "issue_refund":
            return self._issue_refund(command)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute billing and pricing queries"""
        query_type = query.get("type")
        
        if query_type == "get_invoice":
            return self._get_invoice(query)
        elif query_type == "get_payment_history":
            return self._get_payment_history(query)
        elif query_type == "get_revenue_report":
            return self._get_revenue_report(query)
        elif query_type == "check_promotion":
            return self._check_promotion(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _calculate_fee(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate parking or charging fee"""
        try:
            fee_type = command["fee_type"]
            pricing_strategy_name = command.get("pricing_strategy", "standard")
            
            strategy = self.pricing_strategies.get(pricing_strategy_name)
            if not strategy:
                strategy = self.pricing_strategies["standard"]
            
            if fee_type == "parking":
                # Extract parking fee calculation data
                # In real system, this would use actual domain objects
                slot_data = command["slot"]
                time_range = TimeRange(
                    start_time=datetime.fromisoformat(command["entry_time"]),
                    end_time=datetime.fromisoformat(command["exit_time"])
                )
                
                # Calculate base fee
                # Simplified: In real system, create proper domain objects
                base_amount = Decimal('10.00') * Decimal(time_range.duration_hours)
                fee = Money(base_amount)
                
                # Apply dynamic pricing if needed
                if pricing_strategy_name == "dynamic":
                    occupancy_rate = command.get("occupancy_rate", 0.0)
                    fee = strategy.calculate_parking_fee(
                        slot=None,  # Would be actual slot object
                        time_range=time_range,
                        vehicle=None,
                        occupancy_rate=occupancy_rate
                    )
                
                return {
                    "success": True,
                    "fee_amount": float(fee.amount),
                    "currency": fee.currency,
                    "duration_hours": time_range.duration_hours,
                    "pricing_strategy": pricing_strategy_name
                }
                
            elif fee_type == "charging":
                # Calculate charging fee
                energy_kwh = command["energy_kwh"]
                charger_type = ChargerType(command["charger_type"])
                time_of_day = datetime.fromisoformat(command["time_of_day"])
                
                fee = strategy.calculate_charging_fee(energy_kwh, charger_type, time_of_day)
                
                return {
                    "success": True,
                    "fee_amount": float(fee.amount),
                    "currency": fee.currency,
                    "energy_kwh": energy_kwh,
                    "charger_type": charger_type.value
                }
            else:
                return {"success": False, "error": f"Unknown fee type: {fee_type}"}
                
        except Exception as e:
            self.logger.error(f"Error calculating fee: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_invoice(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Generate invoice for parking/charging services"""
        try:
            # Extract invoice data
            customer_id = command.get("customer_id")
            license_plate = command["license_plate"]
            services = command["services"]  # List of services (parking, charging, etc.)
            
            # Calculate total
            subtotal = Decimal('0.00')
            service_details = []
            
            for service in services:
                fee_calculation = self._calculate_fee({
                    "type": "calculate_fee",
                    "fee_type": service["type"],
                    **service["details"]
                })
                
                if fee_calculation["success"]:
                    amount = Decimal(str(fee_calculation["fee_amount"]))
                    subtotal += amount
                    service_details.append({
                        "service_type": service["type"],
                        "amount": float(amount),
                        "details": service["details"]
                    })
            
            # Calculate tax
            tax = subtotal * self.tax_rate
            total = subtotal + tax
            
            # Generate invoice
            invoice_id = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            invoice = Invoice(
                invoice_id=invoice_id,
                customer_id=customer_id,
                license_plate=license_plate,
                issue_date=datetime.now(),
                due_date=datetime.now() + timedelta(days=14),
                subtotal=Money(subtotal),
                tax=Money(tax),
                total=Money(total),
                services=service_details,
                status="pending"
            )
            
            # Store invoice
            self.invoices[invoice_id] = invoice
            
            return {
                "success": True,
                "invoice_id": invoice_id,
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total),
                "due_date": invoice.due_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating invoice: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_payment(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for an invoice"""
        try:
            invoice_id = command["invoice_id"]
            payment_method = command["payment_method"]
            amount = Decimal(str(command["amount"]))
            
            invoice = self.invoices.get(invoice_id)
            if not invoice:
                return {"success": False, "error": f"Invoice {invoice_id} not found"}
            
            # Check if payment matches invoice total
            if amount != invoice.total.amount:
                return {"success": False, "error": "Payment amount does not match invoice total"}
            
            # Process payment (simulated)
            payment_id = f"PAY-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            payment = Payment(
                payment_id=payment_id,
                invoice_id=invoice_id,
                amount=invoice.total,
                method=payment_method,
                timestamp=datetime.now(),
                status="completed"
            )
            
            # Store payment
            self.payments[payment_id] = payment
            
            # Update invoice status
            invoice.status = "paid"
            invoice.payment_date = datetime.now()
            
            # Record revenue
            self.revenue_records.append({
                "timestamp": datetime.now(),
                "invoice_id": invoice_id,
                "payment_id": payment_id,
                "amount": float(invoice.total.amount),
                "service_type": "parking",  # Would be determined from invoice
                "license_plate": invoice.license_plate
            })
            
            return {
                "success": True,
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "amount_paid": float(amount),
                "payment_status": "completed"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing payment: {e}")
            return {"success": False, "error": str(e)}
    
    # Additional methods for other commands and queries...
    def _apply_discount(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Apply discount to a fee calculation"""
        pass
    
    def _issue_refund(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Issue refund for a payment"""
        pass
    
    def _get_invoice(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get invoice details"""
        invoice_id = query["invoice_id"]
        invoice = self.invoices.get(invoice_id)
        
        if not invoice:
            return {"success": False, "error": f"Invoice {invoice_id} not found"}
        
        return {
            "success": True,
            "invoice": {
                "invoice_id": invoice.invoice_id,
                "customer_id": invoice.customer_id,
                "license_plate": invoice.license_plate,
                "issue_date": invoice.issue_date.isoformat(),
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "subtotal": float(invoice.subtotal.amount),
                "tax": float(invoice.tax.amount),
                "total": float(invoice.total.amount),
                "status": invoice.status,
                "services": invoice.services
            }
        }
    
    def _get_payment_history(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get payment history for a license plate or customer"""
        pass
    
    def _get_revenue_report(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Generate revenue report for a date range"""
        pass
    
    def _check_promotion(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a promotion applies to a transaction"""
        pass


# ============================================================================
# EV CHARGING CONTEXT
# ============================================================================

class EVChargingContext(BoundedContext):
    """
    Bounded Context: EV Charging Management
    
    Core Responsibility:
    - Manage EV charging stations and connectors
    - Optimize charging schedules and power distribution
    - Handle charging sessions and billing
    - Monitor battery health and charging efficiency
    
    Ubiquitous Language:
    - Charging Session, Connector Allocation, Power Management
    - Battery Optimization, Charging Profile, Session Management
    """
    
    def __init__(self):
        super().__init__("EVCharging")
        
        # Initialize charging strategies
        self.charging_strategies: Dict[str, ChargingStrategy] = {
            "fast": FastChargingStrategy(),
            "cost_optimized": CostOptimizedChargingStrategy(),
            "balanced": BalancedChargingStrategy()
        }
        
        # Charging stations
        self.charging_stations: Dict[str, ChargingStation] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Power management
        self.total_power_capacity_kw = 1000.0
        self.available_power_kw = 1000.0
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute EV charging commands"""
        command_type = command.get("type")
        
        if command_type == "start_charging_session":
            return self._start_charging_session(command)
        elif command_type == "stop_charging_session":
            return self._stop_charging_session(command)
        elif command_type == "optimize_charging":
            return self._optimize_charging(command)
        elif command_type == "allocate_connector":
            return self._allocate_connector(command)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute EV charging queries"""
        query_type = query.get("type")
        
        if query_type == "get_charging_status":
            return self._get_charging_status(query)
        elif query_type == "get_available_connectors":
            return self._get_available_connectors(query)
        elif query_type == "get_session_history":
            return self._get_session_history(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _start_charging_session(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new EV charging session"""
        try:
            vehicle_data = command["vehicle"]
            station_id = command["station_id"]
            strategy_name = command.get("strategy", "balanced")
            
            # Get charging station
            station = self.charging_stations.get(station_id)
            if not station:
                return {"success": False, "error": f"Charging station {station_id} not found"}
            
            # Get charging strategy
            strategy = self.charging_strategies.get(strategy_name)
            if not strategy:
                strategy = self.charging_strategies["balanced"]
            
            # Create EV object (simplified)
            ev = ElectricVehicle(
                license_plate=LicensePlate(vehicle_data["license_plate"]),
                vehicle_type=VehicleType(vehicle_data["vehicle_type"]),
                battery_capacity_kwh=vehicle_data["battery_capacity_kwh"],
                charge_percentage=vehicle_data["charge_percentage"]
            )
            
            # Get available connectors
            available_connectors = station.get_available_connectors()
            
            if not available_connectors:
                return {"success": False, "error": "No available connectors"}
            
            # Optimize charging
            target_charge = command.get("target_charge_percentage", 80.0)
            max_time = command.get("max_time_hours", 2.0)
            
            best_charger, estimated_time, estimated_cost = strategy.optimize_charging(
                ev, available_connectors, target_charge, max_time
            )
            
            # Allocate connector
            connector = station.allocate_connector(best_charger, ev.license_plate)
            if not connector:
                return {"success": False, "error": "Failed to allocate connector"}
            
            # Start session
            session_id = f"CHG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            session = {
                "session_id": session_id,
                "license_plate": ev.license_plate.value,
                "connector_type": best_charger.value,
                "connector_id": connector,
                "start_time": datetime.now(),
                "initial_charge": ev.charge_percentage,
                "target_charge": target_charge,
                "estimated_time_hours": estimated_time,
                "estimated_cost": estimated_cost,
                "strategy_used": strategy_name,
                "status": "active"
            }
            
            self.active_sessions[session_id] = session
            
            # Update power allocation
            power_needed = best_charger.typical_power_kw
            if self.available_power_kw >= power_needed:
                self.available_power_kw -= power_needed
            else:
                # Implement power sharing logic
                pass
            
            return {
                "success": True,
                "session_id": session_id,
                "connector_id": connector,
                "connector_type": best_charger.value,
                "estimated_time_hours": estimated_time,
                "estimated_cost": estimated_cost,
                "strategy_used": strategy_name
            }
            
        except Exception as e:
            self.logger.error(f"Error starting charging session: {e}")
            return {"success": False, "error": str(e)}
    
    def _stop_charging_session(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Stop an active charging session"""
        try:
            session_id = command["session_id"]
            station_id = command["station_id"]
            
            session = self.active_sessions.get(session_id)
            if not session:
                return {"success": False, "error": f"Session {session_id} not found"}
            
            station = self.charging_stations.get(station_id)
            if not station:
                return {"success": False, "error": f"Station {station_id} not found"}
            
            # Stop charging
            connector_id = session["connector_id"]
            station.release_connector(connector_id)
            
            # Calculate actual charging details
            end_time = datetime.now()
            duration = (end_time - session["start_time"]).total_seconds() / 3600
            
            # Simulate energy delivered
            energy_delivered_kwh = 50.0 * duration  # Simplified
            
            # Update session
            session["end_time"] = end_time
            session["duration_hours"] = duration
            session["energy_delivered_kwh"] = energy_delivered_kwh
            session["status"] = "completed"
            
            # Update power availability
            connector_type = ChargerType(session["connector_type"])
            self.available_power_kw += connector_type.typical_power_kw
            
            # Send to billing context
            # In real system, would integrate with billing context
            
            return {
                "success": True,
                "session_id": session_id,
                "duration_hours": duration,
                "energy_delivered_kwh": energy_delivered_kwh,
                "end_time": end_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping charging session: {e}")
            return {"success": False, "error": str(e)}
    
    # Additional methods for EV charging context...
    def _optimize_charging(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize charging parameters for a session"""
        pass
    
    def _allocate_connector(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate charging connector for immediate use"""
        pass
    
    def _get_charging_status(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get current charging status"""
        pass
    
    def _get_available_connectors(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get available charging connectors"""
        pass
    
    def _get_session_history(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get charging session history"""
        pass


# ============================================================================
# SECURITY & VALIDATION CONTEXT
# ============================================================================

class SecurityValidationContext(BoundedContext):
    """
    Bounded Context: Security & Validation
    
    Core Responsibility:
    - Validate license plates and vehicle information
    - Enforce access control and security policies
    - Detect and prevent fraud
    - Manage user authentication and authorization
    
    Ubiquitous Language:
    - License Plate Validation, Access Control, Fraud Detection
    - Security Policy, Authentication, Authorization
    """
    
    def __init__(self):
        super().__init__("SecurityValidation")
        
        # Validation rules and patterns
        self.license_plate_patterns = {
            "default": r"^[A-Z0-9]{1,10}$",  # Basic alphanumeric
            "US": r"^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,2}$",
            "EU": r"^[A-Z]{1,3}-[A-Z]{1,2}-[0-9]{1,4}$",
        }
        
        # Blacklists and watchlists
        self.blacklisted_plates: Set[str] = set()
        self.suspicious_activities: List[Dict[str, Any]] = []
        
        # Security policies
        self.security_policies = {
            "max_parking_hours": 24,
            "consecutive_visits_limit": 3,
            "suspicious_time_window_hours": 2
        }
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security and validation commands"""
        command_type = command.get("type")
        
        if command_type == "validate_license_plate":
            return self._validate_license_plate(command)
        elif command_type == "check_access":
            return self._check_access(command)
        elif command_type == "log_security_event":
            return self._log_security_event(command)
        elif command_type == "add_to_blacklist":
            return self._add_to_blacklist(command)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security and validation queries"""
        query_type = query.get("type")
        
        if query_type == "get_security_status":
            return self._get_security_status(query)
        elif query_type == "check_blacklist":
            return self._check_blacklist(query)
        elif query_type == "get_security_logs":
            return self._get_security_logs(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _validate_license_plate(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Validate license plate format and status"""
        try:
            license_plate_str = command["license_plate"]
            country = command.get("country", "default")
            
            # Check format
            import re
            pattern = self.license_plate_patterns.get(country, self.license_plate_patterns["default"])
            
            if not re.match(pattern, license_plate_str):
                return {
                    "success": False,
                    "error": f"License plate {license_plate_str} does not match {country} format"
                }
            
            # Check blacklist
            if license_plate_str in self.blacklisted_plates:
                return {
                    "success": False,
                    "error": f"License plate {license_plate_str} is blacklisted",
                    "blacklisted": True
                }
            
            # Check for suspicious patterns
            is_suspicious = self._check_suspicious_pattern(license_plate_str)
            
            return {
                "success": True,
                "license_plate": license_plate_str,
                "format_valid": True,
                "blacklisted": False,
                "suspicious": is_suspicious
            }
            
        except Exception as e:
            self.logger.error(f"Error validating license plate: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_access(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Check if vehicle has access to parking facility"""
        try:
            license_plate = command["license_plate"]
            facility_type = command["facility_type"]  # "parking", "charging", "premium", etc.
            
            # Basic access control logic
            # In real system, would check subscriptions, permits, time restrictions, etc.
            
            # Check blacklist first
            if license_plate in self.blacklisted_plates:
                return {
                    "success": False,
                    "access_granted": False,
                    "reason": "blacklisted"
                }
            
            # Check time-based restrictions (simplified)
            current_hour = datetime.now().hour
            if facility_type == "premium" and current_hour >= 22:
                return {
                    "success": True,
                    "access_granted": False,
                    "reason": "premium_access_restricted_after_10pm"
                }
            
            # Default: Grant access
            return {
                "success": True,
                "access_granted": True,
                "facility_type": facility_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error checking access: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_suspicious_pattern(self, license_plate: str) -> bool:
        """Check for suspicious license plate patterns"""
        # Simple heuristics for demonstration
        suspicious_patterns = [
            r"^[0]{3,}",  # Multiple zeros at start
            r"[A-Z]{6,}",  # Too many consecutive letters
            r"[0-9]{6,}",  # Too many consecutive numbers
            r"(.)\1{4,}",  # Repeated character 4+ times
        ]
        
        import re
        for pattern in suspicious_patterns:
            if re.search(pattern, license_plate):
                return True
        
        return False
    
    # Additional methods for security context...
    def _log_security_event(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Log security event for auditing"""
        pass
    
    def _add_to_blacklist(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Add license plate to blacklist"""
        pass
    
    def _get_security_status(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get overall security status"""
        pass
    
    def _check_blacklist(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Check if license plate is blacklisted"""
        pass
    
    def _get_security_logs(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get security event logs"""
        pass


# ============================================================================
# MONITORING & ANALYTICS CONTEXT
# ============================================================================

class MonitoringAnalyticsContext(BoundedContext):
    """
    Bounded Context: Monitoring & Analytics
    
    Core Responsibility:
    - Real-time monitoring of parking and charging operations
    - Generate analytics and business intelligence reports
    - Predict demand and optimize resource allocation
    - Provide operational insights and alerts
    
    Ubiquitous Language:
    - Real-time Monitoring, Analytics Dashboard, Demand Prediction
    - Performance Metrics, Operational Insights, Alert Generation
    """
    
    def __init__(self):
        super().__init__("MonitoringAnalytics")
        
        # Data stores for analytics
        self.operational_metrics: List[Dict[str, Any]] = []
        self.performance_data: Dict[str, List[float]] = {}
        self.demand_patterns: Dict[str, Any] = {}
        
        # Alert thresholds
        self.alert_thresholds = {
            "occupancy_critical": 0.95,  # 95% occupancy
            "occupancy_warning": 0.85,   # 85% occupancy
            "charging_demand_high": 0.8,  # 80% charging utilization
            "revenue_drop": -0.2,  # 20% revenue drop
        }
        
        # Active alerts
        self.active_alerts: List[Dict[str, Any]] = []
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute monitoring and analytics commands"""
        command_type = command.get("type")
        
        if command_type == "record_metric":
            return self._record_metric(command)
        elif command_type == "generate_report":
            return self._generate_report(command)
        elif command_type == "predict_demand":
            return self._predict_demand(command)
        elif command_type == "check_alerts":
            return self._check_alerts(command)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute monitoring and analytics queries"""
        query_type = query.get("type")
        
        if query_type == "get_metrics":
            return self._get_metrics(query)
        elif query_type == "get_analytics":
            return self._get_analytics(query)
        elif query_type == "get_dashboard":
            return self._get_dashboard(query)
        elif query_type == "get_alerts":
            return self._get_alerts(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _record_metric(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Record operational metric"""
        try:
            metric_type = command["metric_type"]
            value = command["value"]
            timestamp = command.get("timestamp", datetime.now())
            source = command.get("source", "unknown")
            
            metric = {
                "timestamp": timestamp,
                "metric_type": metric_type,
                "value": value,
                "source": source
            }
            
            self.operational_metrics.append(metric)
            
            # Update performance data
            if metric_type not in self.performance_data:
                self.performance_data[metric_type] = []
            self.performance_data[metric_type].append(float(value))
            
            # Check for alerts
            self._evaluate_alerts(metric_type, value, timestamp)
            
            return {
                "success": True,
                "metric_recorded": metric_type,
                "value": value,
                "timestamp": timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error recording metric: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_report(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics report"""
        try:
            report_type = command["report_type"]
            start_date = datetime.fromisoformat(command["start_date"])
            end_date = datetime.fromisoformat(command["end_date"])
            
            # Filter metrics for date range
            filtered_metrics = [
                m for m in self.operational_metrics
                if start_date <= m["timestamp"] <= end_date
            ]
            
            if report_type == "occupancy":
                return self._generate_occupancy_report(filtered_metrics, start_date, end_date)
            elif report_type == "revenue":
                return self._generate_revenue_report(filtered_metrics, start_date, end_date)
            elif report_type == "charging":
                return self._generate_charging_report(filtered_metrics, start_date, end_date)
            else:
                return {"success": False, "error": f"Unknown report type: {report_type}"}
                
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_occupancy_report(self, metrics: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate occupancy analytics report"""
        # Filter occupancy metrics
        occupancy_metrics = [m for m in metrics if m["metric_type"] == "occupancy_rate"]
        
        if not occupancy_metrics:
            return {"success": False, "error": "No occupancy data available"}
        
        # Calculate statistics
        values = [m["value"] for m in occupancy_metrics]
        avg_occupancy = sum(values) / len(values)
        max_occupancy = max(values)
        min_occupancy = min(values)
        
        # Calculate peak hours
        peak_hours = {}
        for metric in occupancy_metrics:
            hour = metric["timestamp"].hour
            if metric["value"] > 0.7:  # Above 70% occupancy
                peak_hours[hour] = peak_hours.get(hour, 0) + 1
        
        sorted_peak_hours = sorted(peak_hours.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "success": True,
            "report_type": "occupancy",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "statistics": {
                "average_occupancy": avg_occupancy,
                "maximum_occupancy": max_occupancy,
                "minimum_occupancy": min_occupancy,
                "data_points": len(values)
            },
            "peak_hours": [
                {"hour": hour, "occurrences": count}
                for hour, count in sorted_peak_hours[:5]  # Top 5 peak hours
            ]
        }
    
    # Additional methods for other report types...
    def _generate_revenue_report(self, metrics: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate revenue analytics report"""
        pass
    
    def _generate_charging_report(self, metrics: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate charging analytics report"""
        pass
    
    def _predict_demand(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Predict future demand based on historical data"""
        pass
    
    def _check_alerts(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Check for alert conditions"""
        pass
    
    def _evaluate_alerts(self, metric_type: str, value: float, timestamp: datetime):
        """Evaluate metrics against alert thresholds"""
        # Simplified alert evaluation
        if metric_type == "occupancy_rate" and value > self.alert_thresholds["occupancy_critical"]:
            alert = {
                "type": "critical_occupancy",
                "message": f"Critical occupancy: {value:.1%}",
                "value": value,
                "threshold": self.alert_thresholds["occupancy_critical"],
                "timestamp": timestamp,
                "severity": "critical"
            }
            self.active_alerts.append(alert)
            self.logger.warning(f"Critical occupancy alert: {value:.1%}")
    
    def _get_metrics(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get metrics data"""
        pass
    
    def _get_analytics(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get analytics data"""
        pass
    
    def _get_dashboard(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get dashboard data"""
        pass
    
    def _get_alerts(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get active alerts"""
        return {
            "success": True,
            "active_alerts": self.active_alerts,
            "total_alerts": len(self.active_alerts)
        }


# ============================================================================
# CONTEXT MAPPER
# ============================================================================

class ContextMapper:
    """
    Maps and coordinates between bounded contexts
    
    Responsibilities:
    - Manage relationships between contexts
    - Route commands and queries to appropriate contexts
    - Handle context translations
    - Manage anti-corruption layers
    """
    
    def __init__(self):
        self.contexts: Dict[str, BoundedContext] = {}
        self.context_relationships: Dict[str, List[str]] = {}
        
        # Initialize all contexts
        self._initialize_contexts()
        
        # Set up integrations
        self._setup_integrations()
    
    def _initialize_contexts(self):
        """Initialize all bounded contexts"""
        # Create context instances
        self.contexts["parking_management"] = ParkingManagementContext()
        self.contexts["billing_pricing"] = BillingPricingContext()
        self.contexts["ev_charging"] = EVChargingContext()
        self.contexts["security_validation"] = SecurityValidationContext()
        self.contexts["monitoring_analytics"] = MonitoringAnalyticsContext()
        
        # Define relationships
        self.context_relationships = {
            "parking_management": ["billing_pricing", "security_validation", "monitoring_analytics"],
            "billing_pricing": ["parking_management", "ev_charging", "monitoring_analytics"],
            "ev_charging": ["billing_pricing", "parking_management", "monitoring_analytics"],
            "security_validation": ["parking_management", "monitoring_analytics"],
            "monitoring_analytics": ["parking_management", "billing_pricing", "ev_charging", "security_validation"]
        }
    
    def _setup_integrations(self):
        """Set up integrations between contexts"""
        # In real implementation, would set up proper integration adapters
        # For now, use simple integration pattern
        
        # Example: Parking Management needs to talk to Billing
        parking_context = self.contexts["parking_management"]
        billing_context = self.contexts["billing_pricing"]
        
        # Create simple integration adapter
        class BillingIntegration:
            def receive_from_context(self, data: Dict[str, Any], source_context: str) -> Dict[str, Any]:
                # Translate parking data to billing format
                if source_context == "parking_management":
                    # Example translation
                    billing_data = {
                        "type": "calculate_fee",
                        "fee_type": "parking",
                        "entry_time": data.get("entry_time"),
                        "exit_time": data.get("exit_time"),
                        "license_plate": data.get("license_plate"),
                        "vehicle_type": data.get("vehicle_type"),
                        "slot_number": data.get("slot_number")
                    }
                    return billing_context.execute_command(billing_data)
                return {}
        
        parking_context.register_integration("billing", BillingIntegration())
    
    def execute_in_context(self, context_name: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation in specific bounded context"""
        context = self.contexts.get(context_name)
        if not context:
            return {"success": False, "error": f"Context {context_name} not found"}
        
        operation_type = operation.get("operation_type", "command")
        
        if operation_type == "command":
            return context.execute_command(operation)
        elif operation_type == "query":
            return context.execute_query(operation)
        else:
            return {"success": False, "error": f"Unknown operation type: {operation_type}"}
    
    def get_context_relationships(self) -> Dict[str, List[str]]:
        """Get relationships between contexts"""
        return self.context_relationships
    
    def get_all_contexts_info(self) -> List[Dict[str, Any]]:
        """Get information about all bounded contexts"""
        return [
            {
                "name": name,
                "info": context.get_context_info(),
                "relationships": self.context_relationships.get(name, [])
            }
            for name, context in self.contexts.items()
        ]


# ============================================================================
# FACTORY FOR BOUNDED CONTEXTS
# ============================================================================

class BoundedContextFactory:
    """Factory for creating and configuring bounded contexts"""
    
    @staticmethod
    def create_standard_configuration() -> ContextMapper:
        """Create standard configuration with all contexts"""
        return ContextMapper()
    
    @staticmethod
    def create_minimal_configuration() -> ContextMapper:
        """Create minimal configuration with essential contexts"""
        mapper = ContextMapper()
        
        # Keep only essential contexts
        essential = ["parking_management", "billing_pricing"]
        for name in list(mapper.contexts.keys()):
            if name not in essential:
                del mapper.contexts[name]
        
        return mapper
    
    @staticmethod
    def create_with_custom_strategies(strategy_config: Dict[str, Any]) -> ContextMapper:
        """Create configuration with custom strategies"""
        mapper = ContextMapper()
        
        # Apply custom strategy configurations
        # This would configure each context with specific strategies
        # based on the provided configuration
        
        return mapper