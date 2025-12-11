# File: src/infrastructure/factories.py
"""
Factory Pattern Implementation for Parking Management System

This module implements various Factory Patterns for creating domain objects:
1. Domain Object Factories - For creating complex domain aggregates and entities
2. Strategy Factories - For creating strategy implementations
3. DTO Factories - For creating DTOs from various sources
4. Repository Factories - For creating repository instances
5. Service Factories - For creating application services

Key Benefits:
- Centralized object creation logic
- Decouples object creation from usage
- Simplifies complex object construction
- Enables dependency injection
- Facilitates testing with mock factories
"""

from abc import ABC, abstractmethod
from typing import (
    Type, TypeVar, Generic, Optional, Dict, List, Any,
    Union, Callable, Tuple, Set, cast
)
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging
from uuid import UUID, uuid4
import random
import string

from ..domain.models import (
    Vehicle, ElectricVehicle, ParkingSlot, ParkingLot,
    ChargingStation, ChargingConnector, Customer,
    ParkingTicket, Invoice, InvoiceItem, Payment, Reservation,
    VehicleType, SlotType, ChargerType, ParkingStrategyType,
    PricingStrategyType, ChargingStrategyType,
    Money, LicensePlate, Location, ContactInfo, TimeRange,
    ParkingLotPolicies
)
from ..domain.aggregates import ParkingLotAggregate, ChargingStationAggregate
from ..domain.strategies import (
    ParkingStrategy, PricingStrategy, ChargingStrategy,
    StandardCarStrategy, ElectricCarStrategy, MotorcycleStrategy,
    LargeVehicleStrategy, NearestEntryStrategy,
    StandardPricingStrategy, DynamicPricingStrategy, SubscriptionPricingStrategy,
    FastChargingStrategy, CostOptimizedChargingStrategy, BalancedChargingStrategy
)
from ..application.dtos import (
    VehicleDTO, ParkingSlotDTO, ParkingLotDTO, ChargingStationDTO,
    CustomerDTO, InvoiceDTO, PaymentDTO, ReservationDTO,
    VehicleCreateDTO, ParkingSlotCreateDTO, ParkingLotCreateDTO,
    ChargingStationCreateDTO, CustomerCreateDTO,
    VehicleTypeDTO, SlotTypeDTO, ChargerTypeDTO,
    MoneyDTO, LicensePlateDTO, LocationDTO, ContactInfoDTO,
    ParkingRequestDTO, ChargingRequestDTO, ReservationRequestDTO
)
from ..infrastructure.repositories import (
    Repository, VehicleRepository, ParkingSlotRepository,
    ParkingLotRepository, CustomerRepository, UnitOfWork
)


# ============================================================================
# FACTORY INTERFACES
# ============================================================================

class Factory(ABC, Generic[T]):
    """Base factory interface"""
    
    @abstractmethod
    def create(self, **kwargs) -> T:
        """Create an instance of T"""
        pass
    
    @abstractmethod
    def create_many(self, count: int, **kwargs) -> List[T]:
        """Create multiple instances"""
        pass


class AggregateFactory(Factory[T], ABC):
    """Factory for domain aggregates"""
    
    @abstractmethod
    def create_from_dto(self, dto: Any) -> T:
        """Create aggregate from DTO"""
        pass
    
    @abstractmethod
    def create_from_dict(self, data: Dict[str, Any]) -> T:
        """Create aggregate from dictionary"""
        pass


class StrategyFactory(Factory[T], ABC):
    """Factory for strategy objects"""
    
    @abstractmethod
    def create_by_type(self, strategy_type: str) -> T:
        """Create strategy by type name"""
        pass


# ============================================================================
# DOMAIN OBJECT FACTORIES
# ============================================================================

class VehicleFactory(Factory[Vehicle]):
    """Factory for creating Vehicle domain objects"""
    
    def create(
        self,
        license_plate: str,
        vehicle_type: Union[VehicleType, str],
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        color: Optional[str] = None,
        disabled_permit: bool = False,
        battery_capacity_kwh: Optional[float] = None,
        max_charging_rate_kw: Optional[float] = None,
        compatible_chargers: Optional[List[ChargerType]] = None
    ) -> Vehicle:
        """
        Create a Vehicle or ElectricVehicle
        
        Args:
            license_plate: Vehicle license plate
            vehicle_type: Type of vehicle (string or enum)
            make: Vehicle make/brand
            model: Vehicle model
            year: Manufacturing year
            color: Vehicle color
            disabled_permit: Whether vehicle has disability permit
            battery_capacity_kwh: Battery capacity for EVs
            max_charging_rate_kw: Max charging rate for EVs
            compatible_chargers: Compatible charger types for EVs
        """
        # Convert string to enum if needed
        if isinstance(vehicle_type, str):
            try:
                vehicle_type = VehicleType(vehicle_type)
            except ValueError:
                raise ValueError(f"Invalid vehicle type: {vehicle_type}")
        
        # Create license plate
        license_plate_obj = LicensePlate(license_plate)
        
        # Create electric vehicle if type is electric
        if vehicle_type.is_electric:
            if battery_capacity_kwh is None:
                # Default battery capacities by vehicle type
                defaults = {
                    VehicleType.EV_CAR: 60.0,
                    VehicleType.EV_MOTORCYCLE: 10.0,
                    VehicleType.EV_TRUCK: 150.0
                }
                battery_capacity_kwh = defaults.get(vehicle_type, 60.0)
            
            if compatible_chargers is None:
                # Default compatible chargers
                if vehicle_type == VehicleType.EV_CAR:
                    compatible_chargers = [ChargerType.LEVEL_2, ChargerType.DC_FAST]
                elif vehicle_type == VehicleType.EV_TRUCK:
                    compatible_chargers = [ChargerType.DC_FAST, ChargerType.CCS]
                else:
                    compatible_chargers = [ChargerType.LEVEL_1, ChargerType.LEVEL_2]
            
            return ElectricVehicle(
                id=uuid4(),
                license_plate=license_plate_obj,
                vehicle_type=vehicle_type,
                make=make or "Unknown",
                model=model or "Unknown",
                year=year,
                color=color,
                disabled_permit=disabled_permit,
                battery_capacity_kwh=battery_capacity_kwh,
                max_charging_rate_kw=max_charging_rate_kw or 11.0,  # Default 11 kW
                compatible_chargers=compatible_chargers
            )
        else:
            # Create regular vehicle
            return Vehicle(
                id=uuid4(),
                license_plate=license_plate_obj,
                vehicle_type=vehicle_type,
                make=make or "Unknown",
                model=model or "Unknown",
                year=year,
                color=color,
                disabled_permit=disabled_permit
            )
    
    def create_many(self, count: int, **kwargs) -> List[Vehicle]:
        """Create multiple vehicles"""
        vehicles = []
        for i in range(count):
            # Generate unique license plate
            plate = kwargs.get('license_plate', f"TEST{str(i+1).zfill(3)}")
            vehicle_kwargs = kwargs.copy()
            vehicle_kwargs['license_plate'] = plate
            
            vehicle = self.create(**vehicle_kwargs)
            vehicles.append(vehicle)
        
        return vehicles
    
    def create_from_dto(self, dto: VehicleCreateDTO) -> Vehicle:
        """Create vehicle from DTO"""
        return self.create(
            license_plate=dto.license_plate,
            vehicle_type=dto.vehicle_type,
            make=dto.make,
            model=dto.model,
            year=dto.year,
            color=dto.color,
            disabled_permit=dto.disabled_permit,
            battery_capacity_kwh=dto.battery_capacity_kwh,
            max_charging_rate_kw=dto.max_charging_rate_kw
        )
    
    def create_random(self) -> Vehicle:
        """Create a random vehicle for testing"""
        # Random vehicle type
        vehicle_types = list(VehicleType)
        vehicle_type = random.choice(vehicle_types)
        
        # Random license plate
        plate = ''.join(random.choices(string.ascii_uppercase, k=3)) + \
                ''.join(random.choices(string.digits, k=3))
        
        # Random make/model
        makes = ["Toyota", "Honda", "Ford", "BMW", "Mercedes", "Tesla", "Nissan"]
        models = {
            "Toyota": ["Camry", "Corolla", "Prius", "RAV4"],
            "Honda": ["Civic", "Accord", "CR-V", "Pilot"],
            "Ford": ["F-150", "Focus", "Mustang", "Explorer"],
            "BMW": ["3 Series", "5 Series", "X5", "i3"],
            "Mercedes": ["C-Class", "E-Class", "S-Class", "GLC"],
            "Tesla": ["Model 3", "Model S", "Model X", "Model Y"],
            "Nissan": ["Altima", "Sentra", "Rogue", "Leaf"]
        }
        
        make = random.choice(makes)
        model = random.choice(models.get(make, ["Unknown"]))
        
        # Random year (2010-2023)
        year = random.randint(2010, 2023)
        
        # Random color
        colors = ["Red", "Blue", "Black", "White", "Silver", "Gray"]
        color = random.choice(colors)
        
        # 10% chance of disability permit
        disabled_permit = random.random() < 0.1
        
        # Create vehicle
        return self.create(
            license_plate=plate,
            vehicle_type=vehicle_type,
            make=make,
            model=model,
            year=year,
            color=color,
            disabled_permit=disabled_permit
        )


class ParkingSlotFactory(Factory[ParkingSlot]):
    """Factory for creating ParkingSlot domain objects"""
    
    def create(
        self,
        parking_lot_id: UUID,
        number: int,
        slot_type: Union[SlotType, str],
        vehicle_types: Optional[List[Union[VehicleType, str]]] = None,
        features: Optional[List[str]] = None,
        floor_level: int = 0,
        hourly_rate: Optional[Money] = None,
        is_reserved: bool = False,
        is_active: bool = True
    ) -> ParkingSlot:
        """
        Create a ParkingSlot
        
        Args:
            parking_lot_id: ID of the parking lot
            number: Slot number
            slot_type: Type of parking slot
            vehicle_types: Compatible vehicle types
            features: Slot features
            floor_level: Floor level (0 for ground)
            hourly_rate: Hourly parking rate
            is_reserved: Whether slot is reserved
            is_active: Whether slot is active
        """
        # Convert string to enum if needed
        if isinstance(slot_type, str):
            slot_type = SlotType(slot_type)
        
        # Convert vehicle types
        if vehicle_types:
            converted_types = []
            for vt in vehicle_types:
                if isinstance(vt, str):
                    converted_types.append(VehicleType(vt))
                else:
                    converted_types.append(vt)
            vehicle_types = converted_types
        else:
            # Default vehicle types based on slot type
            defaults = {
                SlotType.REGULAR: [VehicleType.CAR, VehicleType.MOTORCYCLE],
                SlotType.PREMIUM: [VehicleType.CAR, VehicleType.EV_CAR],
                SlotType.EV: [VehicleType.EV_CAR, VehicleType.EV_MOTORCYCLE, VehicleType.EV_TRUCK],
                SlotType.DISABLED: [VehicleType.CAR],
                SlotType.VALET: [VehicleType.CAR],
                SlotType.RESERVED: [VehicleType.CAR, VehicleType.EV_CAR]
            }
            vehicle_types = defaults.get(slot_type, [VehicleType.CAR])
        
        # Default features
        if features is None:
            if slot_type == SlotType.PREMIUM:
                features = ["covered", "camera", "wide"]
            elif slot_type == SlotType.EV:
                features = ["ev_charger", "covered"]
            elif slot_type == SlotType.DISABLED:
                features = ["wide", "close_to_entry"]
            else:
                features = []
        
        # Default hourly rate based on slot type
        if hourly_rate is None:
            rates = {
                SlotType.REGULAR: Decimal('5.00'),
                SlotType.PREMIUM: Decimal('10.00'),
                SlotType.EV: Decimal('7.50'),
                SlotType.DISABLED: Decimal('3.00'),
                SlotType.VALET: Decimal('15.00'),
                SlotType.RESERVED: Decimal('12.00')
            }
            amount = rates.get(slot_type, Decimal('5.00'))
            hourly_rate = Money(amount=amount, currency="USD")
        
        return ParkingSlot(
            id=uuid4(),
            parking_lot_id=parking_lot_id,
            number=number,
            floor_level=floor_level,
            slot_type=slot_type,
            vehicle_types=vehicle_types,
            features=features,
            hourly_rate=hourly_rate,
            is_reserved=is_reserved,
            is_active=is_active
        )
    
    def create_many(self, count: int, **kwargs) -> List[ParkingSlot]:
        """Create multiple parking slots"""
        parking_lot_id = kwargs.get('parking_lot_id')
        if not parking_lot_id:
            raise ValueError("parking_lot_id is required")
        
        start_number = kwargs.get('start_number', 1)
        slot_type = kwargs.get('slot_type', SlotType.REGULAR)
        
        slots = []
        for i in range(count):
            slot_kwargs = kwargs.copy()
            slot_kwargs['number'] = start_number + i
            slot = self.create(**slot_kwargs)
            slots.append(slot)
        
        return slots
    
    def create_from_dto(self, dto: ParkingSlotCreateDTO) -> ParkingSlot:
        """Create parking slot from DTO"""
        # Convert DTO enums to domain enums
        slot_type = SlotType(dto.slot_type.value)
        vehicle_types = [VehicleType(vt.value) for vt in dto.vehicle_types]
        
        return self.create(
            parking_lot_id=dto.parking_lot_id,
            number=dto.number,
            slot_type=slot_type,
            vehicle_types=vehicle_types,
            features=dto.features,
            floor_level=dto.floor_level,
            hourly_rate=Money(
                amount=Decimal(str(dto.hourly_rate.amount)),
                currency=dto.hourly_rate.currency
            ) if hasattr(dto, 'hourly_rate') and dto.hourly_rate else None,
            is_reserved=dto.is_reserved,
            is_active=getattr(dto, 'is_active', True)
        )
    
    def create_for_parking_lot(
        self,
        parking_lot_id: UUID,
        slot_distribution: Dict[SlotType, int],
        start_number: int = 1
    ) -> List[ParkingSlot]:
        """Create slots for a parking lot based on distribution"""
        all_slots = []
        current_number = start_number
        
        for slot_type, count in slot_distribution.items():
            if count > 0:
                slots = self.create_many(
                    count=count,
                    parking_lot_id=parking_lot_id,
                    slot_type=slot_type,
                    start_number=current_number
                )
                all_slots.extend(slots)
                current_number += count
        
        return all_slots


class ParkingLotFactory(Factory[ParkingLot]):
    """Factory for creating ParkingLot domain objects"""
    
    def __init__(self, parking_slot_factory: Optional[ParkingSlotFactory] = None):
        self.parking_slot_factory = parking_slot_factory or ParkingSlotFactory()
    
    def create(
        self,
        name: str,
        code: str,
        location: Union[Location, Dict[str, Any]],
        total_capacity: int,
        contact_info: Optional[Union[ContactInfo, Dict[str, Any]]] = None,
        operating_hours: Optional[Dict[str, Any]] = None,
        policies: Optional[Union[ParkingLotPolicies, Dict[str, Any]]] = None,
        is_active: bool = True
    ) -> ParkingLot:
        """
        Create a ParkingLot
        
        Args:
            name: Parking lot name
            code: Unique parking lot code
            location: Location information
            total_capacity: Total parking capacity
            contact_info: Contact information
            operating_hours: Operating hours
            policies: Parking lot policies
            is_active: Whether parking lot is active
        """
        # Convert dict to Location if needed
        if isinstance(location, dict):
            location = Location(**location)
        
        # Convert dict to ContactInfo if needed
        if isinstance(contact_info, dict):
            contact_info = ContactInfo(**contact_info)
        
        # Convert dict to Policies if needed
        if isinstance(policies, dict):
            policies = ParkingLotPolicies(**policies)
        elif policies is None:
            # Default policies
            policies = ParkingLotPolicies()
        
        return ParkingLot(
            id=uuid4(),
            name=name,
            code=code,
            location=location,
            total_capacity=total_capacity,
            total_slots=0,  # Will be updated when slots are added
            contact_info=contact_info,
            operating_hours=operating_hours or {
                "weekday": "6:00-22:00",
                "weekend": "8:00-20:00"
            },
            policies=policies,
            is_active=is_active
        )
    
    def create_many(self, count: int, **kwargs) -> List[ParkingLot]:
        """Create multiple parking lots"""
        base_name = kwargs.get('name', 'Parking Lot')
        base_code = kwargs.get('code', 'LOT')
        
        lots = []
        for i in range(count):
            lot_kwargs = kwargs.copy()
            lot_kwargs['name'] = f"{base_name} {i+1}"
            lot_kwargs['code'] = f"{base_code}{str(i+1).zfill(3)}"
            
            lot = self.create(**lot_kwargs)
            lots.append(lot)
        
        return lots
    
    def create_from_dto(self, dto: ParkingLotCreateDTO) -> ParkingLot:
        """Create parking lot from DTO"""
        # Convert DTO to domain objects
        location = Location(
            latitude=dto.location.latitude,
            longitude=dto.location.longitude,
            address=dto.location.address,
            city=dto.location.city,
            state=dto.location.state,
            country=dto.location.country,
            postal_code=dto.location.postal_code
        )
        
        contact_info = None
        if dto.contact_info:
            contact_info = ContactInfo(
                email=dto.contact_info.email,
                phone=dto.contact_info.phone,
                mobile=dto.contact_info.mobile
            )
        
        # Create parking lot
        parking_lot = self.create(
            name=dto.name,
            code=dto.code,
            location=location,
            total_capacity=dto.total_capacity,
            contact_info=contact_info,
            operating_hours=dto.operating_hours,
            is_active=getattr(dto, 'is_active', True)
        )
        
        return parking_lot
    
    def create_with_slots(
        self,
        name: str,
        code: str,
        location: Location,
        slot_distribution: Dict[SlotType, int],
        contact_info: Optional[ContactInfo] = None,
        operating_hours: Optional[Dict[str, Any]] = None,
        policies: Optional[ParkingLotPolicies] = None
    ) -> ParkingLotAggregate:
        """Create parking lot with slots"""
        # Calculate total capacity
        total_capacity = sum(slot_distribution.values())
        
        # Create parking lot
        parking_lot = self.create(
            name=name,
            code=code,
            location=location,
            total_capacity=total_capacity,
            contact_info=contact_info,
            operating_hours=operating_hours,
            policies=policies
        )
        
        # Create slots
        slots = self.parking_slot_factory.create_for_parking_lot(
            parking_lot_id=parking_lot.id,
            slot_distribution=slot_distribution
        )
        
        # Update total slots
        parking_lot.total_slots = len(slots)
        
        return ParkingLotAggregate(parking_lot, slots)
    
    def create_standard_lot(self, name: str, code: str, city: str) -> ParkingLotAggregate:
        """Create a standard parking lot configuration"""
        # Standard slot distribution
        slot_distribution = {
            SlotType.REGULAR: 70,    # 70%
            SlotType.PREMIUM: 20,    # 20%
            SlotType.EV: 10,         # 10%
            SlotType.DISABLED: 5     # 5% (can overlap with others)
        }
        
        # Standard location
        locations = {
            "New York": Location(
                latitude=40.7128,
                longitude=-74.0060,
                address="123 Main St",
                city="New York",
                state="NY",
                country="USA",
                postal_code="10001"
            ),
            "London": Location(
                latitude=51.5074,
                longitude=-0.1278,
                address="456 Oxford St",
                city="London",
                state="",
                country="UK",
                postal_code="W1D 1AB"
            ),
            "Tokyo": Location(
                latitude=35.6762,
                longitude=139.6503,
                address="789 Ginza",
                city="Tokyo",
                state="",
                country="Japan",
                postal_code="104-0061"
            )
        }
        
        location = locations.get(city, Location(
            latitude=0.0,
            longitude=0.0,
            address="Unknown",
            city=city,
            state="",
            country="",
            postal_code=""
        ))
        
        # Contact info
        contact_info = ContactInfo(
            email=f"info@{code.lower()}.com",
            phone="+1-555-123-4567",
            mobile="+1-555-987-6543"
        )
        
        # Create parking lot with slots
        return self.create_with_slots(
            name=name,
            code=code,
            location=location,
            slot_distribution=slot_distribution,
            contact_info=contact_info
        )


class CustomerFactory(Factory[Customer]):
    """Factory for creating Customer domain objects"""
    
    def create(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        has_subscription: bool = False,
        subscription_tier: Optional[str] = None,
        is_active: bool = True
    ) -> Customer:
        """
        Create a Customer
        
        Args:
            email: Customer email
            first_name: First name
            last_name: Last name
            phone: Phone number
            company: Company name
            has_subscription: Whether customer has subscription
            subscription_tier: Subscription tier
            is_active: Whether customer is active
        """
        # Generate customer number
        customer_number = self._generate_customer_number()
        
        # Create contact info
        contact_info = ContactInfo(
            email=email,
            phone=phone,
            mobile=None
        )
        
        # Default total spent
        total_spent = Money(amount=Decimal('0.00'), currency="USD")
        
        return Customer(
            id=uuid4(),
            customer_number=customer_number,
            contact_info=contact_info,
            first_name=first_name,
            last_name=last_name,
            company=company,
            has_subscription=has_subscription,
            subscription_tier=subscription_tier,
            total_spent=total_spent,
            is_active=is_active
        )
    
    def _generate_customer_number(self) -> str:
        """Generate unique customer number"""
        import time
        timestamp = int(time.time() * 1000) % 1000000
        random_part = random.randint(1000, 9999)
        return f"CUST{timestamp:06d}{random_part}"
    
    def create_many(self, count: int, **kwargs) -> List[Customer]:
        """Create multiple customers"""
        customers = []
        for i in range(count):
            customer_kwargs = kwargs.copy()
            
            # Generate unique email
            if 'email' in customer_kwargs:
                base_email = customer_kwargs['email'].split('@')[0]
                customer_kwargs['email'] = f"{base_email}{i+1}@example.com"
            
            customer = self.create(**customer_kwargs)
            customers.append(customer)
        
        return customers
    
    def create_from_dto(self, dto: CustomerCreateDTO) -> Customer:
        """Create customer from DTO"""
        return self.create(
            email=dto.email,
            first_name=dto.first_name,
            last_name=dto.last_name,
            phone=dto.phone,
            company=dto.company,
            has_subscription=getattr(dto, 'has_subscription', False),
            subscription_tier=getattr(dto, 'subscription_tier', None),
            is_active=getattr(dto, 'is_active', True)
        )
    
    def create_premium_customer(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None
    ) -> Customer:
        """Create a premium customer with subscription"""
        return self.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            has_subscription=True,
            subscription_tier="premium"
        )
    
    def create_random(self) -> Customer:
        """Create a random customer for testing"""
        first_names = ["John", "Jane", "Robert", "Emily", "Michael", "Sarah", "David", "Lisa"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        companies = ["Tech Corp", "Global Inc", "Solutions Ltd", "Consulting Group", None, None, None]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        phone = f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        company = random.choice(companies)
        
        # 20% chance of being premium
        has_subscription = random.random() < 0.2
        subscription_tier = "premium" if has_subscription else None
        
        return self.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            company=company,
            has_subscription=has_subscription,
            subscription_tier=subscription_tier
        )


class InvoiceFactory(Factory[Invoice]):
    """Factory for creating Invoice domain objects"""
    
    def __init__(self, customer_factory: Optional[CustomerFactory] = None):
        self.customer_factory = customer_factory or CustomerFactory()
    
    def create(
        self,
        license_plate: str,
        items: List[InvoiceItem],
        customer: Optional[Customer] = None,
        issue_date: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Invoice:
        """
        Create an Invoice
        
        Args:
            license_plate: Vehicle license plate
            items: Invoice items
            customer: Customer (optional)
            issue_date: Issue date (defaults to now)
            due_date: Due date (defaults to 14 days from issue)
            notes: Invoice notes
        """
        # Generate invoice number
        invoice_number = self._generate_invoice_number()
        
        # Set dates
        issue_date = issue_date or datetime.now()
        due_date = due_date or (issue_date + timedelta(days=14))
        
        # Calculate amounts
        subtotal = sum(item.total.amount for item in items)
        
        # Apply tax (10%)
        tax_amount = subtotal * Decimal('0.10')
        total_amount = subtotal + tax_amount
        
        subtotal_money = Money(amount=subtotal, currency="USD")
        tax_money = Money(amount=tax_amount, currency="USD")
        total_money = Money(amount=total_amount, currency="USD")
        
        # Create invoice
        invoice = Invoice(
            id=uuid4(),
            invoice_number=invoice_number,
            customer_id=customer.id if customer else None,
            license_plate=license_plate,
            items=items,
            subtotal=subtotal_money,
            tax=tax_money,
            total=total_money,
            status="issued",
            issue_date=issue_date,
            due_date=due_date,
            notes=notes
        )
        
        return invoice
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        import time
        timestamp = int(time.time() * 1000) % 1000000
        random_part = random.randint(100, 999)
        return f"INV{timestamp:06d}{random_part}"
    
    def create_many(self, count: int, **kwargs) -> List[Invoice]:
        """Create multiple invoices"""
        invoices = []
        for i in range(count):
            invoice = self.create(**kwargs)
            invoices.append(invoice)
        
        return invoices
    
    def create_parking_invoice(
        self,
        license_plate: str,
        parking_duration_hours: float,
        hourly_rate: Money,
        customer: Optional[Customer] = None
    ) -> Invoice:
        """Create an invoice for parking"""
        # Calculate parking fee
        parking_fee = hourly_rate.amount * Decimal(str(parking_duration_hours))
        
        # Create invoice item
        parking_item = InvoiceItem(
            description=f"Parking for {parking_duration_hours:.1f} hours",
            quantity=Decimal(str(parking_duration_hours)),
            unit_price=hourly_rate,
            total=Money(amount=parking_fee, currency=hourly_rate.currency),
            service_type="parking",
            metadata={
                "license_plate": license_plate,
                "duration_hours": parking_duration_hours
            }
        )
        
        return self.create(
            license_plate=license_plate,
            items=[parking_item],
            customer=customer
        )
    
    def create_charging_invoice(
        self,
        license_plate: str,
        energy_kwh: float,
        rate_per_kwh: Money,
        customer: Optional[Customer] = None
    ) -> Invoice:
        """Create an invoice for EV charging"""
        # Calculate charging fee
        charging_fee = rate_per_kwh.amount * Decimal(str(energy_kwh))
        
        # Create invoice item
        charging_item = InvoiceItem(
            description=f"EV Charging {energy_kwh:.1f} kWh",
            quantity=Decimal(str(energy_kwh)),
            unit_price=rate_per_kwh,
            total=Money(amount=charging_fee, currency=rate_per_kwh.currency),
            service_type="charging",
            metadata={
                "license_plate": license_plate,
                "energy_kwh": energy_kwh
            }
        )
        
        return self.create(
            license_plate=license_plate,
            items=[charging_item],
            customer=customer
        )


# ============================================================================
# STRATEGY FACTORIES
# ============================================================================

class ParkingStrategyFactory(StrategyFactory[ParkingStrategy]):
    """Factory for creating ParkingStrategy instances"""
    
    def create(self, **kwargs) -> ParkingStrategy:
        """Create a parking strategy"""
        # Default to standard car strategy
        return StandardCarStrategy()
    
    def create_many(self, count: int, **kwargs) -> List[ParkingStrategy]:
        """Create multiple strategies (not typically used)"""
        return [self.create(**kwargs) for _ in range(count)]
    
    def create_by_type(self, strategy_type: Union[str, ParkingStrategyType]) -> ParkingStrategy:
        """Create strategy by type"""
        # Convert enum to string if needed
        if isinstance(strategy_type, ParkingStrategyType):
            strategy_type = strategy_type.value
        
        # Map strategy types to classes
        strategy_map = {
            "standard_car": StandardCarStrategy,
            "electric_car": ElectricCarStrategy,
            "motorcycle": MotorcycleStrategy,
            "large_vehicle": LargeVehicleStrategy,
            "nearest_entry": NearestEntryStrategy
        }
        
        strategy_class = strategy_map.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown parking strategy type: {strategy_type}")
        
        # Check for special parameters
        if strategy_type == "nearest_entry" and kwargs.get("entry_points"):
            return strategy_class(entry_points=kwargs["entry_points"])
        
        return strategy_class()
    
    def create_for_vehicle_type(self, vehicle_type: VehicleType) -> ParkingStrategy:
        """Create appropriate strategy for vehicle type"""
        strategy_map = {
            VehicleType.CAR: "standard_car",
            VehicleType.EV_CAR: "electric_car",
            VehicleType.MOTORCYCLE: "motorcycle",
            VehicleType.EV_MOTORCYCLE: "motorcycle",
            VehicleType.TRUCK: "large_vehicle",
            VehicleType.EV_TRUCK: "large_vehicle",
            VehicleType.BUS: "large_vehicle"
        }
        
        strategy_type = strategy_map.get(vehicle_type, "standard_car")
        return self.create_by_type(strategy_type)


class PricingStrategyFactory(StrategyFactory[PricingStrategy]):
    """Factory for creating PricingStrategy instances"""
    
    def create(self, **kwargs) -> PricingStrategy:
        """Create a pricing strategy"""
        # Default to standard pricing
        return StandardPricingStrategy()
    
    def create_many(self, count: int, **kwargs) -> List[PricingStrategy]:
        """Create multiple strategies (not typically used)"""
        return [self.create(**kwargs) for _ in range(count)]
    
    def create_by_type(self, strategy_type: Union[str, PricingStrategyType]) -> PricingStrategy:
        """Create strategy by type"""
        # Convert enum to string if needed
        if isinstance(strategy_type, PricingStrategyType):
            strategy_type = strategy_type.value
        
        # Map strategy types to classes
        strategy_map = {
            "standard": StandardPricingStrategy,
            "dynamic": DynamicPricingStrategy,
            "subscription": SubscriptionPricingStrategy
        }
        
        strategy_class = strategy_map.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown pricing strategy type: {strategy_type}")
        
        # Check for special parameters
        if strategy_type == "dynamic" and "base_multiplier" in kwargs:
            return strategy_class(base_multiplier=kwargs["base_multiplier"])
        elif strategy_type == "subscription" and "monthly_rate" in kwargs:
            return strategy_class(monthly_rate=kwargs["monthly_rate"])
        
        return strategy_class()
    
    def create_for_customer_type(self, customer_type: str = "standard") -> PricingStrategy:
        """Create appropriate strategy for customer type"""
        strategy_map = {
            "standard": "standard",
            "premium": "subscription",
            "corporate": "subscription",
            "dynamic": "dynamic"
        }
        
        strategy_type = strategy_map.get(customer_type, "standard")
        return self.create_by_type(strategy_type)


class ChargingStrategyFactory(StrategyFactory[ChargingStrategy]):
    """Factory for creating ChargingStrategy instances"""
    
    def create(self, **kwargs) -> ChargingStrategy:
        """Create a charging strategy"""
        # Default to balanced strategy
        return BalancedChargingStrategy()
    
    def create_many(self, count: int, **kwargs) -> List[ChargingStrategy]:
        """Create multiple strategies (not typically used)"""
        return [self.create(**kwargs) for _ in range(count)]
    
    def create_by_type(self, strategy_type: Union[str, ChargingStrategyType]) -> ChargingStrategy:
        """Create strategy by type"""
        # Convert enum to string if needed
        if isinstance(strategy_type, ChargingStrategyType):
            strategy_type = strategy_type.value
        
        # Map strategy types to classes
        strategy_map = {
            "fast": FastChargingStrategy,
            "cost_optimized": CostOptimizedChargingStrategy,
            "balanced": BalancedChargingStrategy
        }
        
        strategy_class = strategy_map.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown charging strategy type: {strategy_type}")
        
        return strategy_class()
    
    def create_for_charging_scenario(
        self,
        scenario: str = "general"
    ) -> ChargingStrategy:
        """Create appropriate strategy for charging scenario"""
        strategy_map = {
            "quick_stop": "fast",
            "overnight": "cost_optimized",
            "general": "balanced",
            "road_trip": "fast",
            "daily_commute": "balanced"
        }
        
        strategy_type = strategy_map.get(scenario, "balanced")
        return self.create_by_type(strategy_type)


# ============================================================================
# DTO FACTORIES
# ============================================================================

class DTOFactory:
    """Factory for creating DTOs"""
    
    @staticmethod
    def create_vehicle_dto(vehicle: Vehicle) -> VehicleDTO:
        """Create VehicleDTO from domain model"""
        return VehicleDTO(
            id=vehicle.id,
            license_plate=vehicle.license_plate.value,
            vehicle_type=VehicleTypeDTO(vehicle.vehicle_type.value),
            make=vehicle.make,
            model=vehicle.model,
            year=getattr(vehicle, 'year', None),
            color=getattr(vehicle, 'color', None),
            disabled_permit=getattr(vehicle, 'disabled_permit', False),
            is_active=getattr(vehicle, 'is_active', True),
            created_at=getattr(vehicle, 'created_at', None),
            updated_at=getattr(vehicle, 'updated_at', None)
        )
    
    @staticmethod
    def create_parking_slot_dto(slot: ParkingSlot) -> ParkingSlotDTO:
        """Create ParkingSlotDTO from domain model"""
        return ParkingSlotDTO(
            id=slot.id,
            parking_lot_id=slot.parking_lot_id,
            number=slot.number,
            floor_level=slot.floor_level,
            slot_type=SlotTypeDTO(slot.slot_type.value),
            vehicle_types=[VehicleTypeDTO(vt.value) for vt in slot.vehicle_types],
            features=slot.features,
            is_occupied=slot.is_occupied,
            occupied_by=slot.occupied_by,
            occupied_since=slot.occupied_since,
            hourly_rate=MoneyDTO(
                amount=slot.hourly_rate.amount,
                currency=slot.hourly_rate.currency
            ),
            is_reserved=slot.is_reserved,
            is_active=slot.is_active,
            created_at=getattr(slot, 'created_at', None),
            updated_at=getattr(slot, 'updated_at', None)
        )
    
    @staticmethod
    def create_parking_lot_dto(lot: ParkingLot) -> ParkingLotDTO:
        """Create ParkingLotDTO from domain model"""
        return ParkingLotDTO(
            id=lot.id,
            name=lot.name,
            code=lot.code,
            location=LocationDTO(
                latitude=lot.location.latitude,
                longitude=lot.location.longitude,
                address=lot.location.address,
                city=lot.location.city,
                state=lot.location.state,
                country=lot.location.country,
                postal_code=lot.location.postal_code
            ),
            total_capacity=lot.total_capacity,
            total_slots=lot.total_slots,
            occupied_slots=getattr(lot, 'occupied_slots', 0),
            available_slots=getattr(lot, 'available_slots', lot.total_slots),
            occupancy_rate=getattr(lot, 'occupancy_rate', 0.0),
            contact_info=ContactInfoDTO(
                email=lot.contact_info.email if lot.contact_info else None,
                phone=lot.contact_info.phone if lot.contact_info else None,
                mobile=lot.contact_info.mobile if lot.contact_info else None
            ) if lot.contact_info else None,
            operating_hours=lot.operating_hours,
            is_active=lot.is_active,
            created_at=getattr(lot, 'created_at', None),
            updated_at=getattr(lot, 'updated_at', None)
        )
    
    @staticmethod
    def create_customer_dto(customer: Customer) -> CustomerDTO:
        """Create CustomerDTO from domain model"""
        return CustomerDTO(
            id=customer.id,
            customer_number=customer.customer_number,
            email=customer.contact_info.email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.contact_info.phone,
            company=customer.company,
            has_subscription=customer.has_subscription,
            subscription_tier=customer.subscription_tier,
            total_spent=MoneyDTO(
                amount=customer.total_spent.amount,
                currency=customer.total_spent.currency
            ),
            is_active=customer.is_active,
            created_at=getattr(customer, 'created_at', None),
            updated_at=getattr(customer, 'updated_at', None)
        )
    
    @staticmethod
    def create_parking_request_dto(
        license_plate: str,
        vehicle_type: str,
        parking_lot_id: UUID,
        **kwargs
    ) -> ParkingRequestDTO:
        """Create ParkingRequestDTO"""
        return ParkingRequestDTO(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            parking_lot_id=parking_lot_id,
            entry_time=kwargs.get('entry_time'),
            preferences=kwargs.get('preferences', {}),
            customer_id=kwargs.get('customer_id'),
            requires_charging=kwargs.get('requires_charging', False)
        )
    
    @staticmethod
    def create_charging_request_dto(
        license_plate: str,
        vehicle_type: str,
        station_id: UUID,
        current_charge: float,
        target_charge: float,
        battery_capacity: float,
        **kwargs
    ) -> ChargingRequestDTO:
        """Create ChargingRequestDTO"""
        return ChargingRequestDTO(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            station_id=station_id,
            current_charge_percentage=current_charge,
            target_charge_percentage=target_charge,
            battery_capacity_kwh=battery_capacity,
            charging_strategy=kwargs.get('charging_strategy', 'balanced'),
            customer_id=kwargs.get('customer_id')
        )


# ============================================================================
# REPOSITORY FACTORIES (Wrapper for infrastructure factories)
# ============================================================================

class RepositoryFactory:
    """Factory for creating repositories"""
    
    @staticmethod
    def create_vehicle_repository(session: Any) -> VehicleRepository:
        """Create VehicleRepository"""
        from ..infrastructure.repositories import VehicleRepository
        return VehicleRepository(session)
    
    @staticmethod
    def create_parking_slot_repository(session: Any) -> ParkingSlotRepository:
        """Create ParkingSlotRepository"""
        from ..infrastructure.repositories import ParkingSlotRepository
        return ParkingSlotRepository(session)
    
    @staticmethod
    def create_parking_lot_repository(session: Any) -> ParkingLotRepository:
        """Create ParkingLotRepository"""
        from ..infrastructure.repositories import ParkingLotRepository
        return ParkingLotRepository(session)
    
    @staticmethod
    def create_customer_repository(session: Any) -> CustomerRepository:
        """Create CustomerRepository"""
        from ..infrastructure.repositories import CustomerRepository
        return CustomerRepository(session)
    
    @staticmethod
    def create_caching_repository(
        repository: Repository,
        cache_client: Any
    ) -> Repository:
        """Create caching wrapper for repository"""
        from ..infrastructure.repositories import CachingRepository
        return CachingRepository(repository, cache_client)


# ============================================================================
# SERVICE FACTORIES
# ============================================================================

class ServiceFactory:
    """Factory for creating application services"""
    
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        vehicle_factory: Optional[VehicleFactory] = None,
        parking_strategy_factory: Optional[ParkingStrategyFactory] = None,
        pricing_strategy_factory: Optional[PricingStrategyFactory] = None
    ):
        self.uow_factory = uow_factory
        self.vehicle_factory = vehicle_factory or VehicleFactory()
        self.parking_strategy_factory = parking_strategy_factory or ParkingStrategyFactory()
        self.pricing_strategy_factory = pricing_strategy_factory or PricingStrategyFactory()
    
    def create_parking_service(self) -> 'ParkingService':
        """Create ParkingService with dependencies"""
        from ..application.parking_service import ParkingService
        
        return ParkingService(
            context_mapper=None,  # Would be created with appropriate factories
            uow_factory=self.uow_factory,
            vehicle_factory=self.vehicle_factory,
            parking_strategy_factory=self.parking_strategy_factory,
            pricing_strategy_factory=self.pricing_strategy_factory
        )
    
    def create_command_processor(self) -> 'CommandProcessor':
        """Create CommandProcessor with dependencies"""
        from ..application.commands import CommandProcessor
        
        parking_service = self.create_parking_service()
        return CommandProcessor(parking_service)


# ============================================================================
# COMPOSITE FACTORY
# ============================================================================

class DomainFactory:
    """Composite factory for creating all domain objects"""
    
    def __init__(self):
        # Initialize all factories
        self.vehicle_factory = VehicleFactory()
        self.parking_slot_factory = ParkingSlotFactory()
        self.parking_lot_factory = ParkingLotFactory(self.parking_slot_factory)
        self.customer_factory = CustomerFactory()
        self.invoice_factory = InvoiceFactory(self.customer_factory)
        
        # Strategy factories
        self.parking_strategy_factory = ParkingStrategyFactory()
        self.pricing_strategy_factory = PricingStrategyFactory()
        self.charging_strategy_factory = ChargingStrategyFactory()
        
        # DTO factory
        self.dto_factory = DTOFactory()
    
    def create_sample_parking_lot(self) -> ParkingLotAggregate:
        """Create a sample parking lot for testing/demo"""
        return self.parking_lot_factory.create_standard_lot(
            name="Downtown Parking Center",
            code="DPC001",
            city="New York"
        )
    
    def create_sample_customer_with_vehicles(self) -> Tuple[Customer, List[Vehicle]]:
        """Create a sample customer with vehicles"""
        # Create customer
        customer = self.customer_factory.create_premium_customer(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1-555-123-4567"
        )
        
        # Create vehicles
        car = self.vehicle_factory.create(
            license_plate="ABC123",
            vehicle_type=VehicleType.CAR,
            make="Toyota",
            model="Camry",
            year=2020,
            color="Blue"
        )
        
        ev_car = self.vehicle_factory.create(
            license_plate="EV456",
            vehicle_type=VehicleType.EV_CAR,
            make="Tesla",
            model="Model 3",
            year=2022,
            color="Red",
            battery_capacity_kwh=60.0
        )
        
        # Set customer ID on vehicles
        car.customer_id = customer.id
        ev_car.customer_id = customer.id
        
        return customer, [car, ev_car]
    
    def create_sample_parking_scenario(self) -> Dict[str, Any]:
        """Create a complete parking scenario for testing"""
        scenario = {}
        
        # Create parking lot
        parking_lot = self.create_sample_parking_lot()
        scenario['parking_lot'] = parking_lot
        
        # Create customers
        customer1, vehicles1 = self.create_sample_customer_with_vehicles()
        customer2 = self.customer_factory.create_random()
        
        scenario['customers'] = [customer1, customer2]
        scenario['vehicles'] = vehicles1
        
        # Create some occupied slots
        if parking_lot.slots:
            # Occupy first 3 slots
            for i in range(min(3, len(parking_lot.slots))):
                slot = parking_lot.slots[i]
                slot.is_occupied = True
                slot.occupied_by = vehicles1[0].license_plate.value if i == 0 else f"TEST{i:03d}"
                slot.occupied_since = datetime.now() - timedelta(hours=i)
        
        # Create strategies
        scenario['strategies'] = {
            'standard_car': self.parking_strategy_factory.create_by_type('standard_car'),
            'electric_car': self.parking_strategy_factory.create_by_type('electric_car'),
            'standard_pricing': self.pricing_strategy_factory.create_by_type('standard'),
            'dynamic_pricing': self.pricing_strategy_factory.create_by_type('dynamic')
        }
        
        return scenario


# ============================================================================
# FACTORY REGISTRY (Singleton)
# ============================================================================

class FactoryRegistry:
    """Singleton registry for all factories"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all factories"""
        self.domain_factory = DomainFactory()
        
        # Access individual factories through composite
        self.vehicle_factory = self.domain_factory.vehicle_factory
        self.parking_slot_factory = self.domain_factory.parking_slot_factory
        self.parking_lot_factory = self.domain_factory.parking_lot_factory
        self.customer_factory = self.domain_factory.customer_factory
        self.invoice_factory = self.domain_factory.invoice_factory
        
        self.parking_strategy_factory = self.domain_factory.parking_strategy_factory
        self.pricing_strategy_factory = self.domain_factory.pricing_strategy_factory
        self.charging_strategy_factory = self.domain_factory.charging_strategy_factory
        
        self.dto_factory = self.domain_factory.dto_factory
        
        # Repository factory
        self.repository_factory = RepositoryFactory()
    
    def get_factory(self, factory_type: str) -> Any:
        """Get factory by type"""
        factory_map = {
            'vehicle': self.vehicle_factory,
            'parking_slot': self.parking_slot_factory,
            'parking_lot': self.parking_lot_factory,
            'customer': self.customer_factory,
            'invoice': self.invoice_factory,
            'parking_strategy': self.parking_strategy_factory,
            'pricing_strategy': self.pricing_strategy_factory,
            'charging_strategy': self.charging_strategy_factory,
            'dto': self.dto_factory,
            'repository': self.repository_factory
        }
        
        factory = factory_map.get(factory_type)
        if not factory:
            raise ValueError(f"Unknown factory type: {factory_type}")
        
        return factory
    
    def create_test_data(self) -> Dict[str, Any]:
        """Create comprehensive test data"""
        return self.domain_factory.create_sample_parking_scenario()


# ============================================================================
# BUILDER PATTERN (Alternative to Factory)
# ============================================================================

class ParkingLotBuilder:
    """Builder pattern for constructing complex ParkingLot configurations"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder state"""
        self.parking_lot = None
        self.slots = []
        self.slot_factory = ParkingSlotFactory()
    
    def set_basic_info(self, name: str, code: str, location: Location) -> 'ParkingLotBuilder':
        """Set basic parking lot information"""
        self.parking_lot = ParkingLot(
            id=uuid4(),
            name=name,
            code=code,
            location=location,
            total_capacity=0,
            total_slots=0,
            is_active=True
        )
        return self
    
    def add_regular_slots(self, count: int, start_number: int = 1) -> 'ParkingLotBuilder':
        """Add regular parking slots"""
        for i in range(count):
            slot = self.slot_factory.create(
                parking_lot_id=self.parking_lot.id,
                number=start_number + i,
                slot_type=SlotType.REGULAR
            )
            self.slots.append(slot)
        return self
    
    def add_premium_slots(self, count: int, start_number: int = 1) -> 'ParkingLotBuilder':
        """Add premium parking slots"""
        for i in range(count):
            slot = self.slot_factory.create(
                parking_lot_id=self.parking_lot.id,
                number=start_number + i,
                slot_type=SlotType.PREMIUM
            )
            self.slots.append(slot)
        return self
    
    def add_ev_slots(self, count: int, start_number: int = 1) -> 'ParkingLotBuilder':
        """Add EV charging slots"""
        for i in range(count):
            slot = self.slot_factory.create(
                parking_lot_id=self.parking_lot.id,
                number=start_number + i,
                slot_type=SlotType.EV
            )
            self.slots.append(slot)
        return self
    
    def add_disabled_slots(self, count: int, start_number: int = 1) -> 'ParkingLotBuilder':
        """Add disabled parking slots"""
        for i in range(count):
            slot = self.slot_factory.create(
                parking_lot_id=self.parking_lot.id,
                number=start_number + i,
                slot_type=SlotType.DISABLED
            )
            self.slots.append(slot)
        return self
    
    def build(self) -> ParkingLotAggregate:
        """Build and return the ParkingLotAggregate"""
        if not self.parking_lot:
            raise ValueError("Parking lot not initialized")
        
        # Update parking lot capacity
        self.parking_lot.total_capacity = len(self.slots)
        self.parking_lot.total_slots = len(self.slots)
        
        return ParkingLotAggregate(self.parking_lot, self.slots)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of factories"""
    
    # Get factory registry (singleton)
    registry = FactoryRegistry()
    
    # Create a vehicle
    vehicle_factory = registry.vehicle_factory
    car = vehicle_factory.create(
        license_plate="ABC123",
        vehicle_type=VehicleType.CAR,
        make="Toyota",
        model="Camry",
        year=2020
    )
    
    print(f"Created vehicle: {car.license_plate.value} ({car.vehicle_type.value})")
    
    # Create an electric vehicle
    ev = vehicle_factory.create(
        license_plate="EV456",
        vehicle_type=VehicleType.EV_CAR,
        make="Tesla",
        model="Model 3",
        battery_capacity_kwh=75.0
    )
    
    print(f"Created EV: {ev.license_plate.value}, Battery: {ev.battery_capacity_kwh}kWh")
    
    # Create a parking lot with slots
    parking_lot_factory = registry.parking_lot_factory
    parking_lot = parking_lot_factory.create_standard_lot(
        name="City Center Parking",
        code="CCP001",
        city="New York"
    )
    
    print(f"Created parking lot: {parking_lot.parking_lot.name}")
    print(f"  Total slots: {len(parking_lot.slots)}")
    
    # Create a customer
    customer_factory = registry.customer_factory
    customer = customer_factory.create_premium_customer(
        email="premium@example.com",
        first_name="Premium",
        last_name="Customer"
    )
    
    print(f"Created customer: {customer.customer_number} ({customer.contact_info.email})")
    
    # Create parking strategy
    strategy_factory = registry.parking_strategy_factory
    car_strategy = strategy_factory.create_for_vehicle_type(VehicleType.CAR)
    ev_strategy = strategy_factory.create_for_vehicle_type(VehicleType.EV_CAR)
    
    print(f"Car strategy: {car_strategy.__class__.__name__}")
    print(f"EV strategy: {ev_strategy.__class__.__name__}")
    
    # Create DTOs
    dto_factory = registry.dto_factory
    car_dto = dto_factory.create_vehicle_dto(car)
    parking_lot_dto = dto_factory.create_parking_lot_dto(parking_lot.parking_lot)
    
    print(f"Vehicle DTO: {car_dto.license_plate}")
    print(f"Parking Lot DTO: {parking_lot_dto.name}")
    
    # Use builder pattern
    builder = ParkingLotBuilder()
    
    location = Location(
        latitude=51.5074,
        longitude=-0.1278,
        address="1 Park Lane",
        city="London",
        country="UK"
    )
    
    parking_lot2 = builder \
        .set_basic_info("London Parking", "LON001", location) \
        .add_regular_slots(50) \
        .add_premium_slots(20) \
        .add_ev_slots(10) \
        .add_disabled_slots(5) \
        .build()
    
    print(f"\nBuilt parking lot with builder:")
    print(f"  Name: {parking_lot2.parking_lot.name}")
    print(f"  Total slots: {len(parking_lot2.slots)}")
    
    # Create test data
    test_data = registry.create_test_data()
    print(f"\nTest data created:")
    print(f"  Parking lot: {test_data['parking_lot'].parking_lot.name}")
    print(f"  Customers: {len(test_data['customers'])}")
    print(f"  Vehicles: {len(test_data['vehicles'])}")
    print(f"  Strategies: {len(test_data['strategies'])}")


if __name__ == "__main__":
    example_usage()