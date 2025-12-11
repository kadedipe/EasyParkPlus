# File: src/infrastructure/repositories.py
"""
Repository Pattern Implementation for Parking Management System

This module implements the Repository Pattern for data persistence.
Repositories provide a collection-like interface for accessing domain aggregates
while abstracting the underlying data storage implementation.

Key Benefits:
- Decouples domain layer from data layer
- Provides a consistent interface for data access
- Enables easy swapping of storage implementations
- Centralizes data access logic
- Supports unit testing with mock repositories

Repository Types:
1. Aggregate Repositories - For domain aggregates (ParkingLot, ChargingStation)
2. Entity Repositories - For domain entities (Vehicle, ParkingSlot, Customer)
3. Value Object Repositories - For value objects (when needed)
4. View Repositories - For read-optimized queries

Storage Implementations:
- InMemoryRepository - For testing and development
- SQLAlchemyRepository - For relational databases
- MongoDBRepository - For document databases
- RedisRepository - For caching
"""

from abc import ABC, abstractmethod
from typing import (
    Type, TypeVar, Generic, Optional, List, Dict, Any,
    Union, Iterator, Iterable, Set, Tuple, Callable
)
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging
from uuid import UUID, uuid4
from contextlib import contextmanager
import asyncio

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Float,
    DateTime, ForeignKey, Text, DECIMAL, JSON, UniqueConstraint,
    func, select, update, delete, and_, or_, not_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import redis
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from ..domain.models import (
    Vehicle, ElectricVehicle, ParkingSlot, ParkingLot,
    ChargingStation, ChargingConnector, Customer, ParkingTicket,
    Invoice, Payment, Reservation,
    VehicleType, SlotType, ChargerType,
    Money, LicensePlate, Location, ContactInfo,
    TimeRange
)
from ..domain.aggregates import ParkingLotAggregate, ChargingStationAggregate
from ..application.dtos import (
    VehicleDTO, ParkingSlotDTO, ParkingLotDTO, ChargingStationDTO,
    CustomerDTO, InvoiceDTO, PaymentDTO, ReservationDTO,
    ParkingSlotQueryDTO, ParkingLotQueryDTO, InvoiceQueryDTO,
    PaginatedRequest, PaginatedResponse
)

# Type variables for generic repositories
T = TypeVar('T')  # Entity type
ID = TypeVar('ID')  # ID type (usually UUID)
AggregateT = TypeVar('AggregateT')  # Aggregate type


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class Repository(ABC, Generic[T, ID]):
    """Base repository interface"""
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """Add an entity to the repository"""
        pass
    
    @abstractmethod
    def get(self, id: ID) -> Optional[T]:
        """Get an entity by ID"""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination"""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an entity"""
        pass
    
    @abstractmethod
    def delete(self, id: ID) -> bool:
        """Delete an entity by ID"""
        pass
    
    @abstractmethod
    def exists(self, id: ID) -> bool:
        """Check if an entity exists"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Count all entities"""
        pass


class AggregateRepository(Repository[T, ID], ABC):
    """Repository for domain aggregates with additional methods"""
    
    @abstractmethod
    def get_with_children(self, id: ID) -> Optional[T]:
        """Get aggregate with all child entities loaded"""
        pass
    
    @abstractmethod
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find aggregates by criteria"""
        pass


class ReadRepository(ABC, Generic[T, ID]):
    """Read-only repository interface (CQRS pattern)"""
    
    @abstractmethod
    def get(self, id: ID) -> Optional[T]:
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        pass
    
    @abstractmethod
    def find(self, **kwargs) -> List[T]:
        pass
    
    @abstractmethod
    def count(self, **kwargs) -> int:
        pass


# ============================================================================
# UNIT OF WORK PATTERN
# ============================================================================

class UnitOfWork(ABC):
    """Unit of Work pattern for transaction management"""
    
    @abstractmethod
    def __enter__(self):
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    @abstractmethod
    def commit(self):
        """Commit the transaction"""
        pass
    
    @abstractmethod
    def rollback(self):
        """Rollback the transaction"""
        pass
    
    @property
    @abstractmethod
    def vehicles(self) -> 'VehicleRepository':
        pass
    
    @property
    @abstractmethod
    def parking_slots(self) -> 'ParkingSlotRepository':
        pass
    
    @property
    @abstractmethod
    def parking_lots(self) -> 'ParkingLotRepository':
        pass
    
    @property
    @abstractmethod
    def charging_stations(self) -> 'ChargingStationRepository':
        pass
    
    @property
    @abstractmethod
    def customers(self) -> 'CustomerRepository':
        pass
    
    @property
    @abstractmethod
    def invoices(self) -> 'InvoiceRepository':
        pass
    
    @property
    @abstractmethod
    def payments(self) -> 'PaymentRepository':
        pass
    
    @property
    @abstractmethod
    def reservations(self) -> 'ReservationRepository':
        pass


# ============================================================================
# SQLALCHEMY ORM MODELS
# ============================================================================

Base = declarative_base()


class VehicleModel(Base):
    """SQLAlchemy model for Vehicle"""
    __tablename__ = 'vehicles'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    license_plate = Column(String(20), nullable=False, index=True, unique=True)
    vehicle_type = Column(String(20), nullable=False)
    make = Column(String(50))
    model = Column(String(50))
    year = Column(Integer)
    color = Column(String(30))
    disabled_permit = Column(Boolean, default=False)
    
    # Electric vehicle fields
    battery_capacity_kwh = Column(Float)
    max_charging_rate_kw = Column(Float)
    compatible_chargers = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    customer_id = Column(String(36), ForeignKey('customers.id'))
    customer = relationship('CustomerModel', back_populates='vehicles')
    
    __table_args__ = (
        UniqueConstraint('license_plate', name='uq_vehicle_license_plate'),
    )


class ParkingSlotModel(Base):
    """SQLAlchemy model for ParkingSlot"""
    __tablename__ = 'parking_slots'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    parking_lot_id = Column(String(36), ForeignKey('parking_lots.id'), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    floor_level = Column(Integer, default=0)
    slot_type = Column(String(20), nullable=False)
    vehicle_types = Column(JSON, default=list)
    features = Column(JSON, default=list)
    
    # Occupancy
    is_occupied = Column(Boolean, default=False)
    occupied_by = Column(String(20))  # License plate
    occupied_since = Column(DateTime)
    
    # Pricing
    hourly_rate_amount = Column(DECIMAL(10, 2), nullable=False)
    hourly_rate_currency = Column(String(3), default='USD')
    
    # Status
    is_reserved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parking_lot = relationship('ParkingLotModel', back_populates='slots')
    
    __table_args__ = (
        UniqueConstraint('parking_lot_id', 'number', name='uq_slot_parking_lot_number'),
    )


class ParkingLotModel(Base):
    """SQLAlchemy model for ParkingLot"""
    __tablename__ = 'parking_lots'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True, index=True)
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(200))
    city = Column(String(50))
    state = Column(String(50))
    country = Column(String(50))
    postal_code = Column(String(20))
    
    # Capacity
    total_capacity = Column(Integer, nullable=False)
    total_slots = Column(Integer, nullable=False)
    
    # Contact
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    contact_mobile = Column(String(20))
    
    # Operating hours (JSON)
    operating_hours = Column(JSON)
    
    # Policies (JSON)
    policies = Column(JSON, default={
        "ev_can_use_regular": True,
        "motorcycles_per_slot": 2,
        "max_parking_hours": 24,
        "grace_period_minutes": 15,
        "overstay_penalty_rate": 1.5,
        "reservation_hold_minutes": 30
    })
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    slots = relationship('ParkingSlotModel', back_populates='parking_lot', cascade='all, delete-orphan')
    charging_stations = relationship('ChargingStationModel', back_populates='parking_lot', cascade='all, delete-orphan')
    
    __table_args__ = (
        UniqueConstraint('code', name='uq_parking_lot_code'),
    )


class ChargingStationModel(Base):
    """SQLAlchemy model for ChargingStation"""
    __tablename__ = 'charging_stations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True, index=True)
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(200))
    
    # Capacity
    total_power_capacity_kw = Column(Float, nullable=False)
    
    # Contact
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    
    # Operating hours (JSON)
    operating_hours = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Association
    parking_lot_id = Column(String(36), ForeignKey('parking_lots.id'))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parking_lot = relationship('ParkingLotModel', back_populates='charging_stations')
    connectors = relationship('ChargingConnectorModel', back_populates='station', cascade='all, delete-orphan')
    
    __table_args__ = (
        UniqueConstraint('code', name='uq_charging_station_code'),
    )


class ChargingConnectorModel(Base):
    """SQLAlchemy model for ChargingConnector"""
    __tablename__ = 'charging_connectors'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    station_id = Column(String(36), ForeignKey('charging_stations.id'), nullable=False, index=True)
    connector_id = Column(String(20), nullable=False)  # Physical connector ID
    connector_type = Column(String(20), nullable=False)
    max_power_kw = Column(Float, nullable=False)
    
    # Pricing
    hourly_rate_amount = Column(DECIMAL(10, 2))
    hourly_rate_currency = Column(String(3), default='USD')
    energy_rate_per_kwh_amount = Column(DECIMAL(10, 2), nullable=False)
    energy_rate_per_kwh_currency = Column(String(3), default='USD')
    
    # Status
    is_available = Column(Boolean, default=True)
    occupied_by = Column(String(20))  # License plate
    occupied_since = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    station = relationship('ChargingStationModel', back_populates='connectors')
    
    __table_args__ = (
        UniqueConstraint('station_id', 'connector_id', name='uq_connector_station_id'),
    )


class CustomerModel(Base):
    """SQLAlchemy model for Customer"""
    __tablename__ = 'customers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_number = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20))
    company = Column(String(100))
    
    # Subscription
    has_subscription = Column(Boolean, default=False)
    subscription_tier = Column(String(20))
    
    # Financials
    total_spent_amount = Column(DECIMAL(12, 2), default=0)
    total_spent_currency = Column(String(3), default='USD')
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vehicles = relationship('VehicleModel', back_populates='customer')
    invoices = relationship('InvoiceModel', back_populates='customer')
    reservations = relationship('ReservationModel', back_populates='customer')
    
    __table_args__ = (
        UniqueConstraint('email', name='uq_customer_email'),
        UniqueConstraint('customer_number', name='uq_customer_number'),
    )


class InvoiceModel(Base):
    """SQLAlchemy model for Invoice"""
    __tablename__ = 'invoices'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_number = Column(String(20), nullable=False, unique=True, index=True)
    
    # References
    customer_id = Column(String(36), ForeignKey('customers.id'))
    license_plate = Column(String(20), nullable=False, index=True)
    
    # Items (JSON array)
    items = Column(JSON, nullable=False)
    
    # Amounts
    subtotal_amount = Column(DECIMAL(12, 2), nullable=False)
    subtotal_currency = Column(String(3), default='USD')
    tax_amount = Column(DECIMAL(12, 2), default=0)
    tax_currency = Column(String(3), default='USD')
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    total_currency = Column(String(3), default='USD')
    
    # Status
    status = Column(String(20), default='issued')  # draft, issued, paid, overdue, cancelled, refunded
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    paid_date = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship('CustomerModel', back_populates='invoices')
    payments = relationship('PaymentModel', back_populates='invoice')
    
    __table_args__ = (
        UniqueConstraint('invoice_number', name='uq_invoice_number'),
    )


class PaymentModel(Base):
    """SQLAlchemy model for Payment"""
    __tablename__ = 'payments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id = Column(String(36), ForeignKey('invoices.id'), nullable=False, index=True)
    payment_number = Column(String(20), nullable=False, unique=True, index=True)
    
    # Amount and method
    amount_amount = Column(DECIMAL(12, 2), nullable=False)
    amount_currency = Column(String(3), default='USD')
    payment_method = Column(String(20), nullable=False)  # credit_card, debit_card, cash, etc.
    payment_details = Column(JSON)
    
    # Status
    status = Column(String(20), default='pending')  # pending, processing, completed, failed, refunded, cancelled
    transaction_id = Column(String(100))  # From payment gateway
    
    # References
    customer_id = Column(String(36), ForeignKey('customers.id'))
    
    # Timestamps
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship('InvoiceModel', back_populates='payments')
    customer = relationship('CustomerModel')
    
    __table_args__ = (
        UniqueConstraint('payment_number', name='uq_payment_number'),
    )


class ReservationModel(Base):
    """SQLAlchemy model for Reservation"""
    __tablename__ = 'reservations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reservation_number = Column(String(20), nullable=False, unique=True, index=True)
    confirmation_code = Column(String(20), nullable=False, index=True)
    
    # References
    customer_id = Column(String(36), ForeignKey('customers.id'))
    parking_lot_id = Column(String(36), ForeignKey('parking_lots.id'), nullable=False)
    license_plate = Column(String(20), nullable=False, index=True)
    vehicle_type = Column(String(20), nullable=False)
    
    # Slot info (may be assigned later)
    slot_number = Column(Integer)
    slot_type = Column(String(20))
    
    # Times
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    
    # Status
    status = Column(String(20), default='confirmed')  # pending, confirmed, active, completed, cancelled, no_show
    
    # Pricing
    estimated_amount = Column(DECIMAL(10, 2))
    estimated_currency = Column(String(3), default='USD')
    
    # Metadata
    preferences = Column(JSON)
    
    # Timestamps
    checked_in_at = Column(DateTime)
    checked_out_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship('CustomerModel', back_populates='reservations')
    parking_lot = relationship('ParkingLotModel')
    
    __table_args__ = (
        UniqueConstraint('reservation_number', name='uq_reservation_number'),
        UniqueConstraint('confirmation_code', name='uq_reservation_confirmation_code'),
    )


# ============================================================================
# DOMAIN <-> ORM MAPPERS
# ============================================================================

class Mapper:
    """Maps between domain models and ORM models"""
    
    @staticmethod
    def vehicle_to_orm(vehicle: Vehicle) -> VehicleModel:
        """Map Vehicle domain model to ORM model"""
        model = VehicleModel(
            id=str(vehicle.id) if hasattr(vehicle, 'id') else str(uuid4()),
            license_plate=vehicle.license_plate.value,
            vehicle_type=vehicle.vehicle_type.value,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year if hasattr(vehicle, 'year') else None,
            color=vehicle.color if hasattr(vehicle, 'color') else None,
            disabled_permit=vehicle.disabled_permit if hasattr(vehicle, 'disabled_permit') else False
        )
        
        if isinstance(vehicle, ElectricVehicle):
            model.battery_capacity_kwh = vehicle.battery_capacity_kwh
            model.max_charging_rate_kw = vehicle.max_charging_rate_kw
            model.compatible_chargers = [c.value for c in vehicle.compatible_chargers]
        
        return model
    
    @staticmethod
    def vehicle_to_domain(model: VehicleModel) -> Vehicle:
        """Map ORM model to Vehicle domain model"""
        vehicle_type = VehicleType(model.vehicle_type)
        
        if vehicle_type.is_electric:
            return ElectricVehicle(
                id=UUID(model.id),
                license_plate=LicensePlate(model.license_plate),
                vehicle_type=vehicle_type,
                make=model.make,
                model=model.model,
                year=model.year,
                color=model.color,
                disabled_permit=model.disabled_permit,
                battery_capacity_kwh=model.battery_capacity_kwh,
                max_charging_rate_kw=model.max_charging_rate_kw,
                compatible_chargers=[ChargerType(c) for c in (model.compatible_chargers or [])]
            )
        else:
            return Vehicle(
                id=UUID(model.id),
                license_plate=LicensePlate(model.license_plate),
                vehicle_type=vehicle_type,
                make=model.make,
                model=model.model,
                year=model.year,
                color=model.color,
                disabled_permit=model.disabled_permit
            )
    
    @staticmethod
    def parking_slot_to_orm(slot: ParkingSlot) -> ParkingSlotModel:
        """Map ParkingSlot domain model to ORM model"""
        return ParkingSlotModel(
            id=str(slot.id) if hasattr(slot, 'id') else str(uuid4()),
            parking_lot_id=str(slot.parking_lot_id),
            number=slot.number,
            floor_level=slot.floor_level,
            slot_type=slot.slot_type.value,
            vehicle_types=[vt.value for vt in slot.vehicle_types],
            features=slot.features,
            is_occupied=slot.is_occupied,
            occupied_by=slot.occupied_by,
            occupied_since=slot.occupied_since,
            hourly_rate_amount=slot.hourly_rate.amount,
            hourly_rate_currency=slot.hourly_rate.currency,
            is_reserved=slot.is_reserved,
            is_active=slot.is_active
        )
    
    @staticmethod
    def parking_slot_to_domain(model: ParkingSlotModel) -> ParkingSlot:
        """Map ORM model to ParkingSlot domain model"""
        return ParkingSlot(
            id=UUID(model.id),
            parking_lot_id=UUID(model.parking_lot_id),
            number=model.number,
            floor_level=model.floor_level,
            slot_type=SlotType(model.slot_type),
            vehicle_types=[VehicleType(vt) for vt in model.vehicle_types],
            features=model.features or [],
            is_occupied=model.is_occupied,
            occupied_by=model.occupied_by,
            occupied_since=model.occupied_since,
            hourly_rate=Money(
                amount=Decimal(str(model.hourly_rate_amount)),
                currency=model.hourly_rate_currency
            ),
            is_reserved=model.is_reserved,
            is_active=model.is_active
        )
    
    @staticmethod
    def parking_lot_to_orm(lot: ParkingLot) -> ParkingLotModel:
        """Map ParkingLot domain model to ORM model"""
        return ParkingLotModel(
            id=str(lot.id) if hasattr(lot, 'id') else str(uuid4()),
            name=lot.name,
            code=lot.code,
            latitude=lot.location.latitude,
            longitude=lot.location.longitude,
            address=lot.location.address,
            city=lot.location.city,
            state=lot.location.state,
            country=lot.location.country,
            postal_code=lot.location.postal_code,
            total_capacity=lot.total_capacity,
            total_slots=lot.total_slots,
            contact_email=lot.contact_info.email if lot.contact_info else None,
            contact_phone=lot.contact_info.phone if lot.contact_info else None,
            contact_mobile=lot.contact_info.mobile if lot.contact_info else None,
            operating_hours=lot.operating_hours,
            policies={
                "ev_can_use_regular": lot.policies.ev_can_use_regular,
                "motorcycles_per_slot": lot.policies.motorcycles_per_slot,
                "max_parking_hours": lot.policies.max_parking_hours,
                "grace_period_minutes": lot.policies.grace_period_minutes,
                "overstay_penalty_rate": float(lot.policies.overstay_penalty_rate),
                "reservation_hold_minutes": lot.policies.reservation_hold_minutes
            },
            is_active=lot.is_active
        )
    
    @staticmethod
    def parking_lot_to_domain(model: ParkingLotModel) -> ParkingLot:
        """Map ORM model to ParkingLot domain model"""
        from ..domain.aggregates import ParkingLotPolicies
        
        location = Location(
            latitude=model.latitude,
            longitude=model.longitude,
            address=model.address,
            city=model.city,
            state=model.state,
            country=model.country,
            postal_code=model.postal_code
        )
        
        contact_info = None
        if model.contact_email or model.contact_phone:
            contact_info = ContactInfo(
                email=model.contact_email,
                phone=model.contact_phone,
                mobile=model.contact_mobile
            )
        
        policies = ParkingLotPolicies(
            ev_can_use_regular=model.policies.get('ev_can_use_regular', True),
            motorcycles_per_slot=model.policies.get('motorcycles_per_slot', 2),
            max_parking_hours=model.policies.get('max_parking_hours'),
            grace_period_minutes=model.policies.get('grace_period_minutes', 15),
            overstay_penalty_rate=Decimal(str(model.policies.get('overstay_penalty_rate', 1.5))),
            reservation_hold_minutes=model.policies.get('reservation_hold_minutes', 30)
        )
        
        return ParkingLot(
            id=UUID(model.id),
            name=model.name,
            code=model.code,
            location=location,
            total_capacity=model.total_capacity,
            total_slots=model.total_slots,
            contact_info=contact_info,
            operating_hours=model.operating_hours,
            policies=policies,
            is_active=model.is_active
        )
    
    @staticmethod
    def parking_lot_aggregate_to_domain(model: ParkingLotModel) -> ParkingLotAggregate:
        """Map ORM model to ParkingLotAggregate"""
        lot = Mapper.parking_lot_to_domain(model)
        slots = [Mapper.parking_slot_to_domain(slot) for slot in model.slots]
        
        return ParkingLotAggregate(lot, slots)
    
    # Additional mappers for other entities...
    @staticmethod
    def customer_to_orm(customer: Customer) -> CustomerModel:
        """Map Customer domain model to ORM model"""
        return CustomerModel(
            id=str(customer.id) if hasattr(customer, 'id') else str(uuid4()),
            customer_number=customer.customer_number,
            email=customer.contact_info.email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.contact_info.phone,
            company=customer.company,
            has_subscription=customer.has_subscription,
            subscription_tier=customer.subscription_tier,
            total_spent_amount=customer.total_spent.amount,
            total_spent_currency=customer.total_spent.currency,
            is_active=customer.is_active
        )
    
    @staticmethod
    def customer_to_domain(model: CustomerModel) -> Customer:
        """Map ORM model to Customer domain model"""
        contact_info = ContactInfo(
            email=model.email,
            phone=model.phone,
            mobile=None  # Mobile not stored separately
        )
        
        total_spent = Money(
            amount=Decimal(str(model.total_spent_amount)),
            currency=model.total_spent_currency
        )
        
        return Customer(
            id=UUID(model.id),
            customer_number=model.customer_number,
            contact_info=contact_info,
            first_name=model.first_name,
            last_name=model.last_name,
            company=model.company,
            has_subscription=model.has_subscription,
            subscription_tier=model.subscription_tier,
            total_spent=total_spent,
            is_active=model.is_active
        )


# ============================================================================
# IN-MEMORY REPOSITORIES (For Testing)
# ============================================================================

class InMemoryRepository(Repository[T, UUID]):
    """In-memory repository for testing"""
    
    def __init__(self):
        self._storage: Dict[UUID, T] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add(self, entity: T) -> T:
        entity_id = getattr(entity, 'id', None)
        if not entity_id:
            entity_id = uuid4()
            setattr(entity, 'id', entity_id)
        
        self._storage[entity_id] = entity
        self._logger.debug(f"Added entity {entity_id}")
        return entity
    
    def get(self, id: UUID) -> Optional[T]:
        return self._storage.get(id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        items = list(self._storage.values())
        return items[skip:skip + limit]
    
    def update(self, entity: T) -> T:
        entity_id = getattr(entity, 'id')
        if entity_id not in self._storage:
            raise KeyError(f"Entity {entity_id} not found")
        
        self._storage[entity_id] = entity
        self._logger.debug(f"Updated entity {entity_id}")
        return entity
    
    def delete(self, id: UUID) -> bool:
        if id in self._storage:
            del self._storage[id]
            self._logger.debug(f"Deleted entity {id}")
            return True
        return False
    
    def exists(self, id: UUID) -> bool:
        return id in self._storage
    
    def count(self) -> int:
        return len(self._storage)
    
    def clear(self):
        """Clear all data (for testing)"""
        self._storage.clear()


class InMemoryVehicleRepository(InMemoryRepository[Vehicle]):
    """In-memory repository for vehicles"""
    
    def find_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        """Find vehicle by license plate"""
        for vehicle in self._storage.values():
            if vehicle.license_plate.value == license_plate:
                return vehicle
        return None
    
    def find_by_customer(self, customer_id: UUID) -> List[Vehicle]:
        """Find vehicles by customer ID"""
        # Note: This assumes Vehicle has customer_id attribute
        return [v for v in self._storage.values() if getattr(v, 'customer_id', None) == customer_id]


# ============================================================================
# SQLALCHEMY REPOSITORIES
# ============================================================================

class SQLAlchemyRepository(Repository[T, UUID], ABC):
    """Base SQLAlchemy repository"""
    
    def __init__(self, session: Session):
        self.session = session
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def model_class(self) -> Type[Base]:
        """Return SQLAlchemy model class"""
        pass
    
    @abstractmethod
    def to_domain(self, model: Base) -> T:
        """Convert ORM model to domain model"""
        pass
    
    @abstractmethod
    def to_orm(self, entity: T) -> Base:
        """Convert domain model to ORM model"""
        pass
    
    def add(self, entity: T) -> T:
        try:
            model = self.to_orm(entity)
            self.session.add(model)
            self.session.flush()
            
            # Update entity with generated ID if needed
            if hasattr(entity, 'id') and not getattr(entity, 'id'):
                setattr(entity, 'id', UUID(model.id))
            
            self._logger.debug(f"Added entity: {model.id}")
            return entity
        except IntegrityError as e:
            self.session.rollback()
            self._logger.error(f"Integrity error adding entity: {e}")
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error adding entity: {e}")
            raise
    
    def get(self, id: UUID) -> Optional[T]:
        try:
            model = self.session.get(self.model_class, str(id))
            if model:
                return self.to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting entity {id}: {e}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        try:
            query = self.session.query(self.model_class)
            models = query.offset(skip).limit(limit).all()
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting all entities: {e}")
            raise
    
    def update(self, entity: T) -> T:
        try:
            entity_id = getattr(entity, 'id')
            model = self.session.get(self.model_class, str(entity_id))
            if not model:
                raise ValueError(f"Entity {entity_id} not found")
            
            # Update model from entity
            updated_model = self.to_orm(entity)
            
            # Copy updated fields to existing model
            for column in self.model_class.__table__.columns:
                if column.name != 'id':  # Don't update ID
                    new_value = getattr(updated_model, column.name, None)
                    if new_value is not None:
                        setattr(model, column.name, new_value)
            
            self.session.flush()
            self._logger.debug(f"Updated entity: {entity_id}")
            return entity
        except IntegrityError as e:
            self.session.rollback()
            self._logger.error(f"Integrity error updating entity: {e}")
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error updating entity: {e}")
            raise
    
    def delete(self, id: UUID) -> bool:
        try:
            model = self.session.get(self.model_class, str(id))
            if model:
                self.session.delete(model)
                self.session.flush()
                self._logger.debug(f"Deleted entity: {id}")
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error deleting entity {id}: {e}")
            raise
    
    def exists(self, id: UUID) -> bool:
        try:
            count = self.session.query(self.model_class).filter(
                self.model_class.id == str(id)
            ).count()
            return count > 0
        except SQLAlchemyError as e:
            self._logger.error(f"Database error checking existence of {id}: {e}")
            raise
    
    def count(self) -> int:
        try:
            return self.session.query(self.model_class).count()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error counting entities: {e}")
            raise
    
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find entities by criteria"""
        try:
            query = self.session.query(self.model_class)
            
            for key, value in criteria.items():
                if hasattr(self.model_class, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model_class, key).in_(value))
                    else:
                        query = query.filter(getattr(self.model_class, key) == value)
            
            models = query.all()
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding by criteria: {e}")
            raise


class VehicleRepository(SQLAlchemyRepository[Vehicle]):
    """Repository for vehicles"""
    
    @property
    def model_class(self) -> Type[Base]:
        return VehicleModel
    
    def to_domain(self, model: VehicleModel) -> Vehicle:
        return Mapper.vehicle_to_domain(model)
    
    def to_orm(self, entity: Vehicle) -> VehicleModel:
        return Mapper.vehicle_to_orm(entity)
    
    def find_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        """Find vehicle by license plate"""
        try:
            model = self.session.query(VehicleModel).filter(
                VehicleModel.license_plate == license_plate,
                VehicleModel.is_active == True
            ).first()
            
            if model:
                return self.to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding vehicle by license plate: {e}")
            raise
    
    def find_by_customer(self, customer_id: UUID) -> List[Vehicle]:
        """Find vehicles by customer ID"""
        try:
            models = self.session.query(VehicleModel).filter(
                VehicleModel.customer_id == str(customer_id),
                VehicleModel.is_active == True
            ).all()
            
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding vehicles by customer: {e}")
            raise
    
    def find_electric_vehicles(self) -> List[ElectricVehicle]:
        """Find all electric vehicles"""
        try:
            models = self.session.query(VehicleModel).filter(
                VehicleModel.vehicle_type.in_(['ev_car', 'ev_motorcycle', 'ev_truck']),
                VehicleModel.is_active == True
            ).all()
            
            vehicles = []
            for model in models:
                vehicle = self.to_domain(model)
                if isinstance(vehicle, ElectricVehicle):
                    vehicles.append(vehicle)
            
            return vehicles
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding electric vehicles: {e}")
            raise


class ParkingSlotRepository(SQLAlchemyRepository[ParkingSlot]):
    """Repository for parking slots"""
    
    @property
    def model_class(self) -> Type[Base]:
        return ParkingSlotModel
    
    def to_domain(self, model: ParkingSlotModel) -> ParkingSlot:
        return Mapper.parking_slot_to_domain(model)
    
    def to_orm(self, entity: ParkingSlot) -> ParkingSlotModel:
        return Mapper.parking_slot_to_orm(entity)
    
    def find_by_parking_lot(self, parking_lot_id: UUID) -> List[ParkingSlot]:
        """Find all slots in a parking lot"""
        try:
            models = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.parking_lot_id == str(parking_lot_id),
                ParkingSlotModel.is_active == True
            ).all()
            
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding slots by parking lot: {e}")
            raise
    
    def find_available_slots(
        self,
        parking_lot_id: UUID,
        vehicle_type: Optional[VehicleType] = None,
        slot_type: Optional[SlotType] = None
    ) -> List[ParkingSlot]:
        """Find available slots matching criteria"""
        try:
            query = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.parking_lot_id == str(parking_lot_id),
                ParkingSlotModel.is_occupied == False,
                ParkingSlotModel.is_reserved == False,
                ParkingSlotModel.is_active == True
            )
            
            if vehicle_type:
                # Check if vehicle type is in the slot's compatible types
                query = query.filter(
                    ParkingSlotModel.vehicle_types.contains([vehicle_type.value])
                )
            
            if slot_type:
                query = query.filter(ParkingSlotModel.slot_type == slot_type.value)
            
            models = query.all()
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding available slots: {e}")
            raise
    
    def find_occupied_slots(self, parking_lot_id: UUID) -> List[ParkingSlot]:
        """Find all occupied slots in a parking lot"""
        try:
            models = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.parking_lot_id == str(parking_lot_id),
                ParkingSlotModel.is_occupied == True,
                ParkingSlotModel.is_active == True
            ).all()
            
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding occupied slots: {e}")
            raise
    
    def find_by_vehicle_type(self, vehicle_type: VehicleType) -> List[ParkingSlot]:
        """Find slots compatible with a vehicle type"""
        try:
            models = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.vehicle_types.contains([vehicle_type.value]),
                ParkingSlotModel.is_active == True
            ).all()
            
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding slots by vehicle type: {e}")
            raise
    
    def occupy_slot(self, slot_id: UUID, license_plate: str) -> bool:
        """Mark slot as occupied"""
        try:
            result = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.id == str(slot_id),
                ParkingSlotModel.is_occupied == False
            ).update({
                'is_occupied': True,
                'occupied_by': license_plate,
                'occupied_since': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            self.session.flush()
            return result > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error occupying slot: {e}")
            raise
    
    def release_slot(self, slot_id: UUID) -> bool:
        """Mark slot as available"""
        try:
            result = self.session.query(ParkingSlotModel).filter(
                ParkingSlotModel.id == str(slot_id),
                ParkingSlotModel.is_occupied == True
            ).update({
                'is_occupied': False,
                'occupied_by': None,
                'occupied_since': None,
                'updated_at': datetime.utcnow()
            })
            
            self.session.flush()
            return result > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error releasing slot: {e}")
            raise
    
    def get_occupancy_stats(self, parking_lot_id: UUID) -> Dict[str, Any]:
        """Get occupancy statistics for a parking lot"""
        try:
            total = self.session.query(func.count(ParkingSlotModel.id)).filter(
                ParkingSlotModel.parking_lot_id == str(parking_lot_id),
                ParkingSlotModel.is_active == True
            ).scalar()
            
            occupied = self.session.query(func.count(ParkingSlotModel.id)).filter(
                ParkingSlotModel.parking_lot_id == str(parking_lot_id),
                ParkingSlotModel.is_occupied == True,
                ParkingSlotModel.is_active == True
            ).scalar()
            
            if total == 0:
                occupancy_rate = 0.0
            else:
                occupancy_rate = occupied / total
            
            return {
                'total_slots': total or 0,
                'occupied_slots': occupied or 0,
                'available_slots': (total or 0) - (occupied or 0),
                'occupancy_rate': occupancy_rate
            }
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting occupancy stats: {e}")
            raise


class ParkingLotRepository(SQLAlchemyRepository[ParkingLot]):
    """Repository for parking lots"""
    
    @property
    def model_class(self) -> Type[Base]:
        return ParkingLotModel
    
    def to_domain(self, model: ParkingLotModel) -> ParkingLot:
        return Mapper.parking_lot_to_domain(model)
    
    def to_orm(self, entity: ParkingLot) -> ParkingLotModel:
        return Mapper.parking_lot_to_orm(entity)
    
    def get_with_slots(self, id: UUID) -> Optional[ParkingLotAggregate]:
        """Get parking lot with all slots loaded"""
        try:
            model = self.session.query(ParkingLotModel).options(
                joinedload(ParkingLotModel.slots)
            ).filter(
                ParkingLotModel.id == str(id),
                ParkingLotModel.is_active == True
            ).first()
            
            if model:
                return Mapper.parking_lot_aggregate_to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting parking lot with slots: {e}")
            raise
    
    def find_by_code(self, code: str) -> Optional[ParkingLot]:
        """Find parking lot by code"""
        try:
            model = self.session.query(ParkingLotModel).filter(
                ParkingLotModel.code == code,
                ParkingLotModel.is_active == True
            ).first()
            
            if model:
                return self.to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding parking lot by code: {e}")
            raise
    
    def find_by_location(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None
    ) -> List[ParkingLot]:
        """Find parking lots by location"""
        try:
            query = self.session.query(ParkingLotModel).filter(
                ParkingLotModel.is_active == True
            )
            
            if city:
                query = query.filter(ParkingLotModel.city.ilike(f'%{city}%'))
            if state:
                query = query.filter(ParkingLotModel.state == state)
            if country:
                query = query.filter(ParkingLotModel.country == country)
            
            models = query.all()
            return [self.to_domain(model) for model in models]
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding parking lots by location: {e}")
            raise
    
    def get_occupancy_summary(self) -> List[Dict[str, Any]]:
        """Get occupancy summary for all parking lots"""
        try:
            from sqlalchemy import func
            
            # This is a complex query that joins with slots
            # For simplicity, using multiple queries
            results = []
            
            parking_lots = self.session.query(ParkingLotModel).filter(
                ParkingLotModel.is_active == True
            ).all()
            
            for lot in parking_lots:
                slots = self.session.query(ParkingSlotModel).filter(
                    ParkingSlotModel.parking_lot_id == lot.id,
                    ParkingSlotModel.is_active == True
                ).all()
                
                total_slots = len(slots)
                occupied_slots = len([s for s in slots if s.is_occupied])
                
                if total_slots > 0:
                    occupancy_rate = occupied_slots / total_slots
                else:
                    occupancy_rate = 0.0
                
                results.append({
                    'parking_lot_id': UUID(lot.id),
                    'name': lot.name,
                    'code': lot.code,
                    'total_slots': total_slots,
                    'occupied_slots': occupied_slots,
                    'available_slots': total_slots - occupied_slots,
                    'occupancy_rate': occupancy_rate,
                    'city': lot.city,
                    'state': lot.state
                })
            
            return results
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting occupancy summary: {e}")
            raise
    
    def search(self, query_dto: ParkingLotQueryDTO) -> PaginatedResponse:
        """Search parking lots with pagination"""
        try:
            db_query = self.session.query(ParkingLotModel).filter(
                ParkingLotModel.is_active == True
            )
            
            # Apply filters
            if query_dto.name:
                db_query = db_query.filter(ParkingLotModel.name.ilike(f'%{query_dto.name}%'))
            
            if query_dto.code:
                db_query = db_query.filter(ParkingLotModel.code.ilike(f'%{query_dto.code}%'))
            
            if query_dto.city:
                db_query = db_query.filter(ParkingLotModel.city.ilike(f'%{query_dto.city}%'))
            
            if query_dto.state:
                db_query = db_query.filter(ParkingLotModel.state == query_dto.state)
            
            if query_dto.country:
                db_query = db_query.filter(ParkingLotModel.country == query_dto.country)
            
            if query_dto.min_capacity:
                db_query = db_query.filter(ParkingLotModel.total_capacity >= query_dto.min_capacity)
            
            if query_dto.max_capacity:
                db_query = db_query.filter(ParkingLotModel.total_capacity <= query_dto.max_capacity)
            
            if query_dto.has_ev_charging is not None:
                # Check if parking lot has charging stations
                subquery = self.session.query(ParkingLotModel.id).join(
                    ChargingStationModel,
                    ParkingLotModel.id == ChargingStationModel.parking_lot_id
                ).subquery()
                
                if query_dto.has_ev_charging:
                    db_query = db_query.filter(ParkingLotModel.id.in_(select(subquery)))
                else:
                    db_query = db_query.filter(ParkingLotModel.id.notin_(select(subquery)))
            
            # Count total
            total = db_query.count()
            
            # Apply sorting
            if query_dto.sort_by:
                sort_column = getattr(ParkingLotModel, query_dto.sort_by, None)
                if sort_column:
                    if query_dto.sort_order == 'desc':
                        db_query = db_query.order_by(sort_column.desc())
                    else:
                        db_query = db_query.order_by(sort_column.asc())
            
            # Apply pagination
            models = db_query.offset((query_dto.page - 1) * query_dto.page_size).limit(query_dto.page_size).all()
            
            # Convert to domain models
            items = [self.to_domain(model) for model in models]
            
            # Calculate pagination info
            total_pages = (total + query_dto.page_size - 1) // query_dto.page_size
            has_next = query_dto.page < total_pages
            has_prev = query_dto.page > 1
            
            return PaginatedResponse(
                items=items,
                total=total,
                page=query_dto.page,
                page_size=query_dto.page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev
            )
        except SQLAlchemyError as e:
            self._logger.error(f"Database error searching parking lots: {e}")
            raise


# ============================================================================
# CUSTOMER REPOSITORY
# ============================================================================

class CustomerRepository(SQLAlchemyRepository[Customer]):
    """Repository for customers"""
    
    @property
    def model_class(self) -> Type[Base]:
        return CustomerModel
    
    def to_domain(self, model: CustomerModel) -> Customer:
        return Mapper.customer_to_domain(model)
    
    def to_orm(self, entity: Customer) -> CustomerModel:
        return Mapper.customer_to_orm(entity)
    
    def find_by_email(self, email: str) -> Optional[Customer]:
        """Find customer by email"""
        try:
            model = self.session.query(CustomerModel).filter(
                CustomerModel.email == email,
                CustomerModel.is_active == True
            ).first()
            
            if model:
                return self.to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding customer by email: {e}")
            raise
    
    def find_by_customer_number(self, customer_number: str) -> Optional[Customer]:
        """Find customer by customer number"""
        try:
            model = self.session.query(CustomerModel).filter(
                CustomerModel.customer_number == customer_number,
                CustomerModel.is_active == True
            ).first()
            
            if model:
                return self.to_domain(model)
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error finding customer by number: {e}")
            raise
    
    def get_with_vehicles(self, id: UUID) -> Optional[Customer]:
        """Get customer with vehicles loaded"""
        try:
            model = self.session.query(CustomerModel).options(
                joinedload(CustomerModel.vehicles)
            ).filter(
                CustomerModel.id == str(id),
                CustomerModel.is_active == True
            ).first()
            
            if model:
                customer = self.to_domain(model)
                # Note: Vehicles would need to be loaded separately or via mapper
                return customer
            return None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting customer with vehicles: {e}")
            raise
    
    def update_total_spent(self, customer_id: UUID, amount: Money) -> bool:
        """Update customer's total spent"""
        try:
            customer = self.session.get(CustomerModel, str(customer_id))
            if not customer:
                return False
            
            # Convert to same currency
            if customer.total_spent_currency != amount.currency:
                # In real system, would do currency conversion
                # For now, assume same currency
                pass
            
            new_total = Decimal(str(customer.total_spent_amount)) + amount.amount
            
            customer.total_spent_amount = new_total
            customer.updated_at = datetime.utcnow()
            
            self.session.flush()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            self._logger.error(f"Database error updating customer total spent: {e}")
            raise


# ============================================================================
# CHARGING STATION REPOSITORY
# ============================================================================

class ChargingStationRepository(SQLAlchemyRepository[ChargingStation]):
    """Repository for charging stations"""
    
    @property
    def model_class(self) -> Type[Base]:
        return ChargingStationModel
    
    def to_domain(self, model: ChargingStationModel) -> ChargingStation:
        # Implementation would map ORM to domain
        pass
    
    def to_orm(self, entity: ChargingStation) -> ChargingStationModel:
        # Implementation would map domain to ORM
        pass


# ============================================================================
# INVOICE REPOSITORY
# ============================================================================

class InvoiceRepository(SQLAlchemyRepository[Invoice]):
    """Repository for invoices"""
    
    @property
    def model_class(self) -> Type[Base]:
        return InvoiceModel
    
    def to_domain(self, model: InvoiceModel) -> Invoice:
        # Implementation would map ORM to domain
        pass
    
    def to_orm(self, entity: Invoice) -> InvoiceModel:
        # Implementation would map domain to ORM
        pass
    
    def find_by_customer(self, customer_id: UUID) -> List[Invoice]:
        """Find invoices by customer"""
        pass
    
    def find_unpaid(self) -> List[Invoice]:
        """Find unpaid invoices"""
        pass
    
    def search(self, query_dto: InvoiceQueryDTO) -> PaginatedResponse:
        """Search invoices with pagination"""
        pass


# ============================================================================
# SQLALCHEMY UNIT OF WORK
# ============================================================================

class SQLAlchemyUnitOfWork(UnitOfWork):
    """Unit of Work implementation with SQLAlchemy"""
    
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def __enter__(self):
        self.session = self.session_factory()
        
        # Initialize repositories
        self._vehicles = VehicleRepository(self.session)
        self._parking_slots = ParkingSlotRepository(self.session)
        self._parking_lots = ParkingLotRepository(self.session)
        self._charging_stations = ChargingStationRepository(self.session)
        self._customers = CustomerRepository(self.session)
        self._invoices = InvoiceRepository(self.session)
        self._payments = PaymentRepository(self.session)
        self._reservations = ReservationRepository(self.session)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(f"Exception in unit of work: {exc_val}")
            self.rollback()
        else:
            self.commit()
        
        self.session.close()
    
    def commit(self):
        """Commit the transaction"""
        try:
            self.session.commit()
            self._logger.debug("Transaction committed")
        except SQLAlchemyError as e:
            self._logger.error(f"Error committing transaction: {e}")
            self.session.rollback()
            raise
    
    def rollback(self):
        """Rollback the transaction"""
        self.session.rollback()
        self._logger.debug("Transaction rolled back")
    
    @property
    def vehicles(self) -> VehicleRepository:
        return self._vehicles
    
    @property
    def parking_slots(self) -> ParkingSlotRepository:
        return self._parking_slots
    
    @property
    def parking_lots(self) -> ParkingLotRepository:
        return self._parking_lots
    
    @property
    def charging_stations(self) -> ChargingStationRepository:
        return self._charging_stations
    
    @property
    def customers(self) -> CustomerRepository:
        return self._customers
    
    @property
    def invoices(self) -> InvoiceRepository:
        return self._invoices
    
    @property
    def payments(self) -> PaymentRepository:
        return self._payments
    
    @property
    def reservations(self) -> ReservationRepository:
        return self._reservations


# ============================================================================
# REPOSITORY FACTORY
# ============================================================================

class RepositoryFactory:
    """Factory for creating repositories"""
    
    @staticmethod
    def create_sqlalchemy_repository(
        entity_type: Type[T],
        session: Session
    ) -> Repository[T, UUID]:
        """Create SQLAlchemy repository for entity type"""
        # Map entity types to repository classes
        repository_map = {
            Vehicle: VehicleRepository,
            ParkingSlot: ParkingSlotRepository,
            ParkingLot: ParkingLotRepository,
            Customer: CustomerRepository,
            # Add more mappings as needed
        }
        
        repository_class = repository_map.get(entity_type)
        if not repository_class:
            raise ValueError(f"No repository found for entity type: {entity_type}")
        
        return repository_class(session)
    
    @staticmethod
    def create_in_memory_repository(entity_type: Type[T]) -> InMemoryRepository[T]:
        """Create in-memory repository for testing"""
        return InMemoryRepository()
    
    @staticmethod
    def create_sqlalchemy_uow(database_url: str) -> SQLAlchemyUnitOfWork:
        """Create SQLAlchemy Unit of Work"""
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        return SQLAlchemyUnitOfWork(SessionLocal)


# ============================================================================
# CACHING REPOSITORY (Decorator Pattern)
# ============================================================================

class CachingRepository(Repository[T, UUID]):
    """Repository decorator that adds caching"""
    
    def __init__(self, repository: Repository[T, UUID], cache_client: Any):
        self.repository = repository
        self.cache = cache_client
        self._logger = logging.getLogger(self.__class__.__name__)
        self.cache_prefix = f"{repository.__class__.__name__}:"
    
    def _cache_key(self, id: UUID) -> str:
        return f"{self.cache_prefix}{id}"
    
    def add(self, entity: T) -> T:
        result = self.repository.add(entity)
        # Invalidate cache for this entity
        entity_id = getattr(entity, 'id')
        if entity_id:
            self.cache.delete(self._cache_key(entity_id))
        return result
    
    def get(self, id: UUID) -> Optional[T]:
        cache_key = self._cache_key(id)
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached:
            self._logger.debug(f"Cache hit for {id}")
            return cached
        
        # Get from repository
        entity = self.repository.get(id)
        if entity:
            # Cache for future requests
            self.cache.set(cache_key, entity, ex=300)  # 5 minutes
            self._logger.debug(f"Cached entity {id}")
        
        return entity
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        # Don't cache getAll as it's likely to change frequently
        return self.repository.get_all(skip, limit)
    
    def update(self, entity: T) -> T:
        result = self.repository.update(entity)
        # Invalidate cache
        entity_id = getattr(entity, 'id')
        if entity_id:
            self.cache.delete(self._cache_key(entity_id))
        return result
    
    def delete(self, id: UUID) -> bool:
        result = self.repository.delete(id)
        if result:
            self.cache.delete(self._cache_key(id))
        return result
    
    def exists(self, id: UUID) -> bool:
        # Don't cache exists check
        return self.repository.exists(id)
    
    def count(self) -> int:
        # Don't cache count
        return self.repository.count()


# ============================================================================
# EVENT PUBLISHING REPOSITORY (Decorator Pattern)
# ============================================================================

class EventPublishingRepository(Repository[T, UUID]):
    """Repository decorator that publishes domain events"""
    
    def __init__(self, repository: Repository[T, UUID], event_publisher: Any):
        self.repository = repository
        self.event_publisher = event_publisher
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add(self, entity: T) -> T:
        result = self.repository.add(entity)
        
        # Publish domain events if entity has them
        if hasattr(entity, 'events') and entity.events:
            for event in entity.events:
                self.event_publisher.publish(event)
            # Clear events after publishing
            entity.clear_events()
        
        return result
    
    def update(self, entity: T) -> T:
        result = self.repository.update(entity)
        
        # Publish domain events if entity has them
        if hasattr(entity, 'events') and entity.events:
            for event in entity.events:
                self.event_publisher.publish(event)
            # Clear events after publishing
            entity.clear_events()
        
        return result
    
    # Delegate other methods to wrapped repository
    def get(self, id: UUID) -> Optional[T]:
        return self.repository.get(id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        return self.repository.get_all(skip, limit)
    
    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)
    
    def exists(self, id: UUID) -> bool:
        return self.repository.exists(id)
    
    def count(self) -> int:
        return self.repository.count()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of repositories"""
    import os
    
    # Create database URL
    database_url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    # Create Unit of Work
    uow_factory = RepositoryFactory()
    uow = uow_factory.create_sqlalchemy_uow(database_url)
    
    # Use Unit of Work
    with uow as uow_instance:
        # Create a parking lot
        from ..domain.models import Location, ContactInfo, ParkingLotPolicies
        from ..domain.aggregates import ParkingLotAggregate
        
        location = Location(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St",
            city="New York",
            state="NY",
            country="USA",
            postal_code="10001"
        )
        
        contact_info = ContactInfo(
            email="info@parkinglot.com",
            phone="+1-234-567-8900",
            mobile="+1-234-567-8901"
        )
        
        policies = ParkingLotPolicies(
            ev_can_use_regular=True,
            motorcycles_per_slot=2,
            max_parking_hours=24,
            grace_period_minutes=15,
            overstay_penalty_rate=Decimal('1.5'),
            reservation_hold_minutes=30
        )
        
        parking_lot = ParkingLot(
            name="Downtown Parking",
            code="DT001",
            location=location,
            total_capacity=100,
            total_slots=0,  # Will be calculated from slots
            contact_info=contact_info,
            operating_hours={"weekday": "6AM-10PM", "weekend": "8AM-8PM"},
            policies=policies,
            is_active=True
        )
        
        # Add parking lot
        uow_instance.parking_lots.add(parking_lot)
        
        # Create some parking slots
        from ..domain.models import Money
        
        for i in range(1, 11):
            slot = ParkingSlot(
                parking_lot_id=parking_lot.id,
                number=i,
                floor_level=0,
                slot_type=SlotType.REGULAR,
                vehicle_types=[VehicleType.CAR, VehicleType.EV_CAR],
                features=["covered", "camera"],
                hourly_rate=Money(amount=Decimal('5.00'), currency="USD"),
                is_active=True
            )
            uow_instance.parking_slots.add(slot)
        
        # Commit transaction
        uow_instance.commit()
        
        print(f"Created parking lot: {parking_lot.name}")
        
        # Query parking lots
        query_dto = ParkingLotQueryDTO(
            page=1,
            page_size=10,
            city="New York"
        )
        
        result = uow_instance.parking_lots.search(query_dto)
        print(f"Found {result.total} parking lots in New York")
        
        # Get parking lot with slots
        lot_with_slots = uow_instance.parking_lots.get_with_slots(parking_lot.id)
        if lot_with_slots:
            print(f"Parking lot has {len(lot_with_slots.slots)} slots")
        
        # Find available slots
        available_slots = uow_instance.parking_slots.find_available_slots(
            parking_lot_id=parking_lot.id,
            vehicle_type=VehicleType.CAR
        )
        print(f"Found {len(available_slots)} available slots")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    example_usage()