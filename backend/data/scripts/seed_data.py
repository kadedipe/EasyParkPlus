#!/usr/bin/env python3
"""
Database seed data script for the parking management system.

This script populates the database with realistic test data for development,
testing, and demonstration purposes. It creates users, vehicles, reservations,
payments, and other entities with meaningful relationships.

Usage:
    python seed_data.py [--count N] [--clear] [--env ENV] [--db-url URL]
                       [--config CONFIG] [--verbose]

Options:
    --count N       Number of records to create (default: 100)
    --clear         Clear existing data before seeding
    --env ENV       Environment (dev, test, staging) [default: dev]
    --db-url URL    Database connection URL
    --config CONFIG Configuration file path
    --verbose       Verbose output
    --help          Show this help message
"""

import os
import sys
import argparse
import logging
import random
import string
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from faker import Faker
from faker.providers import automotive, company, person, phone_number, lorem
import names
import pytz

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from data.migrations.models import (
    User, UserProfile, UserPreference, UserSession, UserDevice, UserAuditLog,
    Role, Permission, RoleAssignment,
    Vehicle, VehicleRegistration, VehicleInsurance, VehicleInspection,
    VehicleOwnership, VehicleDocument, VehicleImage, VehicleHistory,
    ParkingSpot, ParkingZone, SpotMaintenance, SpotSensor,
    Reservation, RecurringReservation, Waitlist,
    Payment, Invoice, Subscription, Discount,
    Notification, NotificationTemplate, NotificationPreference,
    AuditLog, ComplianceLog,
    SystemConfig, FeatureFlag
)
from data.migrations.models.enums import (
    UserStatus, UserRole, AuthMethod, MFAMethod,
    VehicleStatus, VehicleType, VehicleClass, FuelType,
    TransmissionType, DriveType,
    RegistrationStatus, InsuranceStatus, InspectionStatus, OwnershipType,
    SpotType, SpotStatus, ZoneType, ZoneStatus,
    AccessType, GateType,
    ReservationStatus, ReservationType, PaymentStatus,
    RecurringFrequency, WaitlistStatus,
    PaymentMethodType, PaymentProvider, TransactionType,
    DisputeStatus, SubscriptionStatus, InvoiceStatus,
    DiscountType, Currency,
    NotificationType, NotificationChannel, NotificationStatus,
    NotificationPriority, TemplateType, DeviceType,
    AuditAction, AuditStatus, AuditSeverity, AuditCategory, AuditResourceType,
    DayOfWeek, Language, CountryCode, Timezone
)
from data.repositories import (
    UserRepository, RoleRepository, PermissionRepository,
    VehicleRepository, ParkingSpotRepository, ReservationRepository,
    PaymentRepository, NotificationRepository, AuditLogRepository,
    SystemConfigRepository
)
from utils.security import hash_password
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()
fake.add_provider(automotive)
fake.add_provider(company)
fake.add_provider(person)
fake.add_provider(phone_number)
fake.add_provider(lorem)


# ============================================================================
# Seed Data Generator
# ============================================================================

class SeedDataGenerator:
    """
    Generates realistic seed data for the parking management system.
    
    Creates entities with meaningful relationships and realistic attributes
    for development, testing, and demonstration.
    """
    
    def __init__(
        self,
        session: Session,
        count: int = 100,
        env: str = 'dev',
        clear: bool = False
    ):
        """
        Initialize the seed data generator.
        
        Args:
            session: SQLAlchemy session
            count: Number of records to generate
            env: Environment (dev, test, staging)
            clear: Whether to clear existing data
        """
        self.session = session
        self.count = count
        self.env = env
        self.clear = clear
        
        # Repositories
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)
        self.vehicle_repo = VehicleRepository(session)
        self.spot_repo = ParkingSpotRepository(session)
        self.reservation_repo = ReservationRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.audit_repo = AuditLogRepository(session)
        self.config_repo = SystemConfigRepository(session)
        
        # Storage for created entities
        self.users: List[User] = []
        self.vehicles: List[Vehicle] = []
        self.spots: List[ParkingSpot] = []
        self.reservations: List[Reservation] = []
        self.payments: List[Payment] = []
        
        # Configuration
        self.start_date = datetime.utcnow() - timedelta(days=180)  # 6 months ago
        self.end_date = datetime.utcnow() + timedelta(days=90)     # 3 months ahead
        
        logger.info(f"SeedDataGenerator initialized for {env} environment")
    
    def seed_all(self) -> Dict[str, int]:
        """
        Seed all data.
        
        Returns:
            Dictionary with counts of created records
        """
        results = {}
        
        try:
            # Clear existing data if requested
            if self.clear:
                self._clear_data()
            
            # Seed in correct order (respect foreign keys)
            results['roles'] = self._seed_roles()
            results['permissions'] = self._seed_permissions()
            results['zones'] = self._seed_zones()
            results['spots'] = self._seed_spots()
            results['users'] = self._seed_users()
            results['vehicles'] = self._seed_vehicles()
            results['reservations'] = self._seed_reservations()
            results['payments'] = self._seed_payments()
            results['notifications'] = self._seed_notifications()
            results['audit_logs'] = self._seed_audit_logs()
            
            # Seed additional data
            results['subscriptions'] = self._seed_subscriptions()
            results['discounts'] = self._seed_discounts()
            results['waitlist'] = self._seed_waitlist()
            results['maintenance'] = self._seed_maintenance()
            
            self.session.commit()
            
            logger.info(f"Seed data completed: {results}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Seed data failed: {e}")
            raise
        
        return results
    
    def _clear_data(self) -> None:
        """Clear existing data."""
        logger.warning("Clearing existing data...")
        
        # Order matters (respect foreign keys)
        tables = [
            'notifications', 'payments', 'reservations', 'vehicles',
            'users', 'parking_spots', 'parking_zones',
            'role_assignments', 'permissions', 'roles'
        ]
        
        for table in tables:
            self.session.execute(text(f"DELETE FROM {table}"))
            logger.debug(f"Cleared table: {table}")
        
        self.session.commit()
        logger.info("Existing data cleared")
    
    def _seed_roles(self) -> int:
        """Seed roles."""
        logger.info("Seeding roles...")
        
        roles_data = [
            {'name': 'user', 'description': 'Regular user', 'priority': 0},
            {'name': 'operator', 'description': 'Parking operator', 'priority': 10},
            {'name': 'manager', 'description': 'Parking manager', 'priority': 20},
            {'name': 'admin', 'description': 'Administrator', 'priority': 100},
            {'name': 'super_admin', 'description': 'Super administrator', 'priority': 1000}
        ]
        
        count = 0
        for role_data in roles_data:
            existing = self.role_repo.get_by_name(role_data['name'])
            if not existing:
                role = Role(**role_data)
                self.session.add(role)
                count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} roles")
        return count
    
    def _seed_permissions(self) -> int:
        """Seed permissions."""
        logger.info("Seeding permissions...")
        
        permissions_data = [
            # User permissions
            {'name': 'user:view', 'resource_type': 'user', 'action': 'view', 'description': 'View users'},
            {'name': 'user:create', 'resource_type': 'user', 'action': 'create', 'description': 'Create users'},
            {'name': 'user:edit', 'resource_type': 'user', 'action': 'edit', 'description': 'Edit users'},
            {'name': 'user:delete', 'resource_type': 'user', 'action': 'delete', 'description': 'Delete users'},
            
            # Vehicle permissions
            {'name': 'vehicle:view', 'resource_type': 'vehicle', 'action': 'view', 'description': 'View vehicles'},
            {'name': 'vehicle:create', 'resource_type': 'vehicle', 'action': 'create', 'description': 'Create vehicles'},
            {'name': 'vehicle:edit', 'resource_type': 'vehicle', 'action': 'edit', 'description': 'Edit vehicles'},
            {'name': 'vehicle:delete', 'resource_type': 'vehicle', 'action': 'delete', 'description': 'Delete vehicles'},
            
            # Parking permissions
            {'name': 'parking:view', 'resource_type': 'parking', 'action': 'view', 'description': 'View parking'},
            {'name': 'parking:manage', 'resource_type': 'parking', 'action': 'manage', 'description': 'Manage parking'},
            {'name': 'parking:configure', 'resource_type': 'parking', 'action': 'configure', 'description': 'Configure parking'},
            
            # Reservation permissions
            {'name': 'reservation:view', 'resource_type': 'reservation', 'action': 'view', 'description': 'View reservations'},
            {'name': 'reservation:create', 'resource_type': 'reservation', 'action': 'create', 'description': 'Create reservations'},
            {'name': 'reservation:cancel', 'resource_type': 'reservation', 'action': 'cancel', 'description': 'Cancel reservations'},
            {'name': 'reservation:modify', 'resource_type': 'reservation', 'action': 'modify', 'description': 'Modify reservations'},
            
            # Payment permissions
            {'name': 'payment:view', 'resource_type': 'payment', 'action': 'view', 'description': 'View payments'},
            {'name': 'payment:process', 'resource_type': 'payment', 'action': 'process', 'description': 'Process payments'},
            {'name': 'payment:refund', 'resource_type': 'payment', 'action': 'refund', 'description': 'Refund payments'},
            
            # Report permissions
            {'name': 'report:view', 'resource_type': 'report', 'action': 'view', 'description': 'View reports'},
            {'name': 'report:generate', 'resource_type': 'report', 'action': 'generate', 'description': 'Generate reports'},
            
            # Admin permissions
            {'name': 'admin:access', 'resource_type': 'admin', 'action': 'access', 'description': 'Access admin'},
            {'name': 'admin:configure', 'resource_type': 'admin', 'action': 'configure', 'description': 'Configure system'},
            {'name': 'admin:audit', 'resource_type': 'admin', 'action': 'audit', 'description': 'View audit logs'}
        ]
        
        count = 0
        for perm_data in permissions_data:
            existing = self.permission_repo.get_by_name(perm_data['name'])
            if not existing:
                permission = Permission(**perm_data)
                self.session.add(permission)
                count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} permissions")
        return count
    
    def _seed_zones(self) -> int:
        """Seed parking zones."""
        logger.info("Seeding parking zones...")
        
        zones_data = [
            {
                'name': 'Main Lot A',
                'zone_type': ZoneType.SURFACE,
                'total_spots': 50,
                'description': 'Main parking lot - Section A',
                'location': 'North Entrance',
                'hourly_rate': 2.50,
                'daily_max': 20.00,
                'is_active': True
            },
            {
                'name': 'Main Lot B',
                'zone_type': ZoneType.SURFACE,
                'total_spots': 50,
                'description': 'Main parking lot - Section B',
                'location': 'South Entrance',
                'hourly_rate': 2.50,
                'daily_max': 20.00,
                'is_active': True
            },
            {
                'name': 'Garage Level 1',
                'zone_type': ZoneType.STRUCTURE,
                'total_spots': 75,
                'description': 'Parking garage - Level 1',
                'location': 'West Building',
                'hourly_rate': 3.00,
                'daily_max': 24.00,
                'is_active': True
            },
            {
                'name': 'Garage Level 2',
                'zone_type': ZoneType.STRUCTURE,
                'total_spots': 75,
                'description': 'Parking garage - Level 2',
                'location': 'West Building',
                'hourly_rate': 3.00,
                'daily_max': 24.00,
                'is_active': True
            },
            {
                'name': 'VIP Section',
                'zone_type': ZoneType.RESERVED,
                'total_spots': 20,
                'description': 'VIP reserved parking',
                'location': 'Near Entrance',
                'hourly_rate': 5.00,
                'daily_max': 35.00,
                'is_active': True
            },
            {
                'name': 'EV Charging Station',
                'zone_type': ZoneType.COVERED,
                'total_spots': 30,
                'description': 'Electric vehicle charging area',
                'location': 'East Side',
                'hourly_rate': 3.50,
                'daily_max': 28.00,
                'is_active': True,
                'features': {'ev_charging': True}
            },
            {
                'name': 'Motorcycle Parking',
                'zone_type': ZoneType.SURFACE,
                'total_spots': 25,
                'description': 'Dedicated motorcycle parking',
                'location': 'South Side',
                'hourly_rate': 1.50,
                'daily_max': 10.00,
                'is_active': True
            },
            {
                'name': 'Oversize Vehicle Lot',
                'zone_type': ZoneType.SURFACE,
                'total_spots': 15,
                'description': 'For trucks, RVs, and oversize vehicles',
                'location': 'Remote Lot',
                'hourly_rate': 5.00,
                'daily_max': 30.00,
                'is_active': True
            }
        ]
        
        count = 0
        for zone_data in zones_data:
            zone = ParkingZone(**zone_data)
            self.session.add(zone)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} parking zones")
        return count
    
    def _seed_spots(self) -> int:
        """Seed parking spots."""
        logger.info("Seeding parking spots...")
        
        zones = self.session.query(ParkingZone).all()
        count = 0
        
        for zone in zones:
            # Create spots based on zone capacity
            for i in range(1, zone.total_spots + 1):
                # Determine spot type
                if 'VIP' in zone.name:
                    spot_type = SpotType.VIP
                elif 'EV' in zone.name:
                    spot_type = SpotType.ELECTRIC
                elif 'Motorcycle' in zone.name:
                    spot_type = SpotType.MOTORCYCLE
                elif 'Oversize' in zone.name:
                    spot_type = SpotType.OVERSIZE
                elif i <= zone.total_spots * 0.05:  # 5% handicapped spots
                    spot_type = SpotType.HANDICAPPED
                else:
                    spot_type = SpotType.STANDARD
                
                # Generate spot number
                if zone.zone_type == ZoneType.STRUCTURE:
                    level = zone.name.split()[-1]
                    spot_number = f"{level}-{i:03d}"
                else:
                    spot_number = f"{zone.name[0]}{i:03d}"
                
                spot = ParkingSpot(
                    zone_id=zone.id,
                    spot_number=spot_number,
                    spot_type=spot_type,
                    status=SpotStatus.AVAILABLE,
                    is_covered=zone.zone_type in [ZoneType.STRUCTURE, ZoneType.COVERED],
                    has_ev_charging=spot_type == SpotType.ELECTRIC,
                    width=self._get_spot_width(spot_type),
                    length=self._get_spot_length(spot_type),
                    features=self._get_spot_features(spot_type)
                )
                self.session.add(spot)
                count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} parking spots")
        return count
    
    def _get_spot_width(self, spot_type: SpotType) -> float:
        """Get standard width for spot type."""
        widths = {
            SpotType.COMPACT: 2.2,
            SpotType.STANDARD: 2.5,
            SpotType.HANDICAPPED: 3.0,
            SpotType.ELECTRIC: 2.5,
            SpotType.MOTORCYCLE: 1.2,
            SpotType.OVERSIZE: 3.5,
            SpotType.TRUCK: 3.0,
            SpotType.VIP: 2.5
        }
        return widths.get(spot_type, 2.5)
    
    def _get_spot_length(self, spot_type: SpotType) -> float:
        """Get standard length for spot type."""
        lengths = {
            SpotType.COMPACT: 4.5,
            SpotType.STANDARD: 5.0,
            SpotType.HANDICAPPED: 5.0,
            SpotType.ELECTRIC: 5.0,
            SpotType.MOTORCYCLE: 2.5,
            SpotType.OVERSIZE: 7.0,
            SpotType.TRUCK: 6.5,
            SpotType.VIP: 5.0
        }
        return lengths.get(spot_type, 5.0)
    
    def _get_spot_features(self, spot_type: SpotType) -> Dict:
        """Get features for spot type."""
        features = {}
        if spot_type == SpotType.ELECTRIC:
            features['charger_type'] = random.choice(['Level 2', 'DC Fast'])
            features['charger_power'] = random.choice([7.2, 11, 22, 50])
        elif spot_type == SpotType.HANDICAPPED:
            features['wider_aisle'] = True
            features['near_elevator'] = random.choice([True, False])
        return features
    
    def _seed_users(self) -> int:
        """Seed users."""
        logger.info("Seeding users...")
        
        # Get roles
        user_role = self.role_repo.get_by_name('user')
        operator_role = self.role_repo.get_by_name('operator')
        manager_role = self.role_repo.get_by_name('manager')
        admin_role = self.role_repo.get_by_name('admin')
        
        # Determine user counts
        num_users = self.count
        num_operators = max(1, num_users // 10)
        num_managers = max(1, num_users // 20)
        num_admins = max(1, num_users // 50)
        
        created_count = 0
        
        # Create regular users
        for i in range(num_users):
            user_data = self._generate_user_data()
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=hash_password('Password123!'),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                status=user_data['status'],
                email_verified=user_data['email_verified'],
                phone_verified=user_data['phone_verified'],
                created_at=user_data['created_at']
            )
            self.session.add(user)
            self.session.flush()
            
            # Assign role
            role_assignment = RoleAssignment(
                user_id=user.id,
                role_id=user_role.id,
                assigned_at=user.created_at
            )
            self.session.add(role_assignment)
            
            # Create profile
            profile = UserProfile(
                user_id=user.id,
                date_of_birth=user_data.get('date_of_birth'),
                address=user_data.get('address'),
                city=user_data.get('city'),
                country=user_data.get('country'),
                preferred_language=user_data.get('language', Language.EN)
            )
            self.session.add(profile)
            
            # Create preferences
            prefs = UserPreference(
                user_id=user.id,
                notification_email=True,
                notification_sms=random.choice([True, False]),
                notification_push=True,
                marketing_emails=random.choice([True, False])
            )
            self.session.add(prefs)
            
            self.users.append(user)
            created_count += 1
        
        # Create operators
        for i in range(num_operators):
            user_data = self._generate_user_data(role='operator')
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=hash_password('Operator123!'),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                status=UserStatus.ACTIVE,
                email_verified=True,
                phone_verified=True,
                created_at=user_data['created_at']
            )
            self.session.add(user)
            self.session.flush()
            
            role_assignment = RoleAssignment(
                user_id=user.id,
                role_id=operator_role.id,
                assigned_at=user.created_at
            )
            self.session.add(role_assignment)
            
            self.users.append(user)
            created_count += 1
        
        # Create managers
        for i in range(num_managers):
            user_data = self._generate_user_data(role='manager')
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=hash_password('Manager123!'),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                status=UserStatus.ACTIVE,
                email_verified=True,
                phone_verified=True,
                created_at=user_data['created_at']
            )
            self.session.add(user)
            self.session.flush()
            
            role_assignment = RoleAssignment(
                user_id=user.id,
                role_id=manager_role.id,
                assigned_at=user.created_at
            )
            self.session.add(role_assignment)
            
            self.users.append(user)
            created_count += 1
        
        # Create admins
        for i in range(num_admins):
            user_data = self._generate_user_data(role='admin')
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=hash_password('Admin123!'),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                status=UserStatus.ACTIVE,
                email_verified=True,
                phone_verified=True,
                created_at=user_data['created_at']
            )
            self.session.add(user)
            self.session.flush()
            
            role_assignment = RoleAssignment(
                user_id=user.id,
                role_id=admin_role.id,
                assigned_at=user.created_at
            )
            self.session.add(role_assignment)
            
            self.users.append(user)
            created_count += 1
        
        self.session.flush()
        logger.info(f"Seeded {created_count} users")
        return created_count
    
    def _generate_user_data(self, role: str = 'user') -> Dict:
        """Generate realistic user data."""
        first_name = names.get_first_name()
        last_name = names.get_last_name()
        
        # Generate email
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'company.com']
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
        
        # Generate username
        username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
        
        # Determine status based on role
        if role in ['admin', 'manager', 'operator']:
            status = UserStatus.ACTIVE
            email_verified = True
            phone_verified = True
        else:
            status_choices = [UserStatus.ACTIVE, UserStatus.ACTIVE, UserStatus.ACTIVE,
                            UserStatus.INACTIVE, UserStatus.PENDING]
            status = random.choice(status_choices)
            email_verified = status == UserStatus.ACTIVE and random.random() > 0.2
            phone_verified = email_verified and random.random() > 0.3
        
        # Generate creation date (spread over last 6 months)
        days_ago = random.randint(0, 180)
        created_at = self.end_date - timedelta(days=days_ago)
        
        return {
            'email': email,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'phone': fake.phone_number(),
            'status': status,
            'email_verified': email_verified,
            'phone_verified': phone_verified,
            'created_at': created_at,
            'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=80),
            'address': fake.street_address(),
            'city': fake.city(),
            'country': random.choice([c.value for c in CountryCode]),
            'language': random.choice([l.value for l in Language])
        }
    
    def _seed_vehicles(self) -> int:
        """Seed vehicles."""
        logger.info("Seeding vehicles...")
        
        if not self.users:
            logger.warning("No users available for vehicle creation")
            return 0
        
        vehicle_types = list(VehicleType)
        fuel_types = list(FuelType)
        
        makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'BMW', 'Mercedes', 
                'Audi', 'Volkswagen', 'Nissan', 'Hyundai', 'Kia', 'Mazda',
                'Subaru', 'Lexus', 'Acura', 'Tesla', 'Porsche', 'Jeep']
        
        models_by_make = {
            'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Tacoma'],
            'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'Odyssey'],
            'Ford': ['F-150', 'Escape', 'Explorer', 'Mustang', 'Focus'],
            'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Tahoe', 'Camaro'],
            'BMW': ['3 Series', '5 Series', 'X3', 'X5', 'M4'],
            'Mercedes': ['C-Class', 'E-Class', 'GLC', 'GLE', 'S-Class'],
            'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck']
        }
        
        colors = ['Black', 'White', 'Silver', 'Gray', 'Blue', 'Red', 
                 'Green', 'Brown', 'Beige', 'Yellow', 'Orange']
        
        count = 0
        
        for user in self.users:
            # Each user has 1-3 vehicles
            num_vehicles = random.choices([1, 2, 3], weights=[0.5, 0.3, 0.2])[0]
            
            for i in range(num_vehicles):
                # Generate license plate
                letters = ''.join(random.choices(string.ascii_uppercase, k=3))
                numbers = ''.join(random.choices(string.digits, k=3))
                license_plate = f"{letters}{numbers}"
                
                # Select make and model
                make = random.choice(makes)
                model_options = models_by_make.get(make, ['Generic Model'])
                model = random.choice(model_options)
                
                # Determine vehicle type
                if make in ['Tesla']:
                    vehicle_type = VehicleType.EV
                elif model in ['F-150', 'Silverado', 'Tacoma']:
                    vehicle_type = VehicleType.TRUCK
                elif model in ['Mustang', 'Camaro', 'M4']:
                    vehicle_type = VehicleType.LUXURY
                else:
                    vehicle_type = random.choice(vehicle_types)
                
                # Determine fuel type
                if vehicle_type == VehicleType.EV:
                    fuel_type = FuelType.ELECTRIC
                elif vehicle_type == VehicleType.HYBRID:
                    fuel_type = FuelType.HYBRID
                else:
                    fuel_type = random.choice(fuel_types)
                
                # Create vehicle
                vehicle = Vehicle(
                    license_plate=license_plate,
                    vin=fake.vin(),
                    make=make,
                    model=model,
                    year=random.randint(2015, 2024),
                    color=random.choice(colors),
                    vehicle_type=vehicle_type,
                    fuel_type=fuel_type,
                    status=VehicleStatus.ACTIVE,
                    created_at=user.created_at + timedelta(days=random.randint(1, 30))
                )
                self.session.add(vehicle)
                self.session.flush()
                
                # Add ownership
                ownership = VehicleOwnership(
                    vehicle_id=vehicle.id,
                    user_id=user.id,
                    ownership_type=OwnershipType.OWNER,
                    is_primary=True,
                    start_date=vehicle.created_at.date()
                )
                self.session.add(ownership)
                
                # Add registration
                self._add_vehicle_registration(vehicle)
                
                # Add insurance
                self._add_vehicle_insurance(vehicle)
                
                # Add inspection
                self._add_vehicle_inspection(vehicle)
                
                self.vehicles.append(vehicle)
                count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} vehicles")
        return count
    
    def _add_vehicle_registration(self, vehicle: Vehicle) -> None:
        """Add registration for a vehicle."""
        issue_date = vehicle.created_at.date()
        expiry_date = issue_date + timedelta(days=365)
        
        registration = VehicleRegistration(
            vehicle_id=vehicle.id,
            registration_number=f"REG-{vehicle.license_plate}",
            issue_date=issue_date,
            expiry_date=expiry_date,
            issuing_authority=f"DMV {fake.state()}",
            status=RegistrationStatus.CURRENT,
            is_current=True
        )
        self.session.add(registration)
    
    def _add_vehicle_insurance(self, vehicle: Vehicle) -> None:
        """Add insurance for a vehicle."""
        issue_date = vehicle.created_at.date()
        expiry_date = issue_date + timedelta(days=365)
        
        providers = ['Geico', 'Progressive', 'State Farm', 'Allstate', 'Farmers']
        
        insurance = VehicleInsurance(
            vehicle_id=vehicle.id,
            policy_number=f"POL-{random.randint(100000, 999999)}",
            provider=random.choice(providers),
            coverage_type='Full Coverage',
            issue_date=issue_date,
            expiry_date=expiry_date,
            status=InsuranceStatus.ACTIVE,
            is_current=True
        )
        self.session.add(insurance)
    
    def _add_vehicle_inspection(self, vehicle: Vehicle) -> None:
        """Add inspection for a vehicle."""
        inspection_date = vehicle.created_at.date()
        
        inspection = VehicleInspection(
            vehicle_id=vehicle.id,
            inspection_date=inspection_date,
            result=InspectionStatus.PASSED,
            inspector=f"Inspector {random.randint(1, 10)}",
            next_inspection_date=inspection_date + timedelta(days=365),
            notes="Routine inspection passed"
        )
        self.session.add(inspection)
    
    def _seed_reservations(self) -> int:
        """Seed reservations."""
        logger.info("Seeding reservations...")
        
        if not self.users or not self.vehicles or not self.spots:
            logger.warning("Missing required data for reservations")
            return 0
        
        count = 0
        target_count = min(self.count * 3, 500)  # Up to 500 reservations
        
        for i in range(target_count):
            # Select random user, vehicle, spot
            user = random.choice(self.users)
            user_vehicles = [v for v in self.vehicles if v.owner_id == user.id]
            if not user_vehicles:
                continue
            
            vehicle = random.choice(user_vehicles)
            spot = random.choice(self.spots)
            
            # Generate reservation times
            start_time = self._generate_reservation_time()
            duration_hours = random.choices([1, 2, 3, 4, 6, 8, 12, 24], 
                                          weights=[0.2, 0.2, 0.15, 0.1, 0.1, 0.1, 0.05, 0.05])[0]
            end_time = start_time + timedelta(hours=duration_hours)
            
            # Determine status based on time
            now = datetime.utcnow()
            if end_time < now:
                status = ReservationStatus.COMPLETED
            elif start_time < now < end_time:
                status = ReservationStatus.CHECKED_IN
            elif start_time > now:
                status = ReservationStatus.CONFIRMED
            else:
                status = ReservationStatus.CONFIRMED
            
            # Occasionally create cancelled or no-show
            if random.random() < 0.1 and status == ReservationStatus.CONFIRMED:
                status = ReservationStatus.CANCELLED
            elif random.random() < 0.05 and status == ReservationStatus.CONFIRMED:
                status = ReservationStatus.NO_SHOW
            
            try:
                # Create reservation
                reservation = Reservation(
                    user_id=user.id,
                    spot_id=spot.id,
                    vehicle_id=vehicle.id,
                    confirmation_code=self._generate_confirmation_code(),
                    start_time=start_time,
                    end_time=end_time,
                    status=status,
                    reservation_type=ReservationType.STANDARD,
                    total_amount=self._calculate_amount(duration_hours, spot),
                    created_at=start_time - timedelta(days=random.randint(1, 14))
                )
                self.session.add(reservation)
                self.session.flush()
                
                # Handle check-in if needed
                if status == ReservationStatus.CHECKED_IN:
                    reservation.checked_in_at = now
                
                # Handle completion
                if status == ReservationStatus.COMPLETED:
                    reservation.checked_in_at = start_time
                    reservation.checked_out_at = end_time
                
                self.reservations.append(reservation)
                count += 1
                
            except Exception as e:
                logger.debug(f"Failed to create reservation: {e}")
                continue
        
        self.session.flush()
        logger.info(f"Seeded {count} reservations")
        return count
    
    def _generate_reservation_time(self) -> datetime:
        """Generate a realistic reservation time."""
        now = datetime.utcnow()
        
        # Distribution: 30% past, 20% current, 50% future
        r = random.random()
        if r < 0.3:
            # Past reservation
            days_ago = random.randint(1, 30)
            hour = random.randint(8, 20)
            return now - timedelta(days=days_ago, hours=random.randint(-12, 12))
        elif r < 0.5:
            # Current/near future
            hours_from_now = random.randint(-2, 4)
            return now + timedelta(hours=hours_from_now)
        else:
            # Future reservation
            days_ahead = random.randint(1, 60)
            hour = random.randint(8, 20)
            return now + timedelta(days=days_ahead, hours=hour - now.hour)
    
    def _generate_confirmation_code(self) -> str:
        """Generate unique confirmation code."""
        letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        numbers = ''.join(random.choices(string.digits, k=4))
        return f"{letters}{numbers}"
    
    def _calculate_amount(self, hours: int, spot: ParkingSpot) -> float:
        """Calculate reservation amount."""
        base_rate = 2.50  # Default hourly rate
        multiplier = 1.0
        
        if spot.spot_type == SpotType.VIP:
            multiplier = 2.0
        elif spot.spot_type == SpotType.HANDICAPPED:
            multiplier = 0.8
        elif spot.spot_type == SpotType.ELECTRIC:
            multiplier = 1.2
        
        amount = hours * base_rate * multiplier
        return round(amount, 2)
    
    def _seed_payments(self) -> int:
        """Seed payments."""
        logger.info("Seeding payments...")
        
        if not self.reservations:
            logger.warning("No reservations available for payment creation")
            return 0
        
        payment_methods = list(PaymentMethodType)
        payment_providers = list(PaymentProvider)
        currencies = list(Currency)
        
        count = 0
        
        for reservation in self.reservations:
            # Only create payments for completed or checked-in reservations
            if reservation.status not in [ReservationStatus.COMPLETED, ReservationStatus.CHECKED_IN]:
                continue
            
            # 90% of reservations have payments
            if random.random() > 0.9:
                continue
            
            amount = reservation.total_amount or random.uniform(5, 50)
            
            # Determine payment status
            if reservation.status == ReservationStatus.COMPLETED:
                status = PaymentStatus.PAID
            elif reservation.status == ReservationStatus.CHECKED_IN:
                status = random.choices(
                    [PaymentStatus.PAID, PaymentStatus.AUTHORIZED, PaymentStatus.PENDING],
                    weights=[0.7, 0.2, 0.1]
                )[0]
            else:
                continue
            
            payment = Payment(
                user_id=reservation.user_id,
                reservation_id=reservation.id,
                amount=amount,
                currency=random.choice(currencies),
                payment_method_type=random.choice(payment_methods),
                provider=random.choice(payment_providers),
                transaction_id=f"TXN{random.randint(100000, 999999)}",
                status=status,
                created_at=reservation.created_at + timedelta(minutes=random.randint(1, 60))
            )
            self.session.add(payment)
            
            # Add transaction
            from data.migrations.payment_models import PaymentTransaction
            
            transaction = PaymentTransaction(
                payment_id=payment.id,
                transaction_type=TransactionType.SALE,
                amount=amount,
                provider=payment.provider,
                provider_transaction_id=f"PROV{random.randint(1000000, 9999999)}",
                status=status
            )
            self.session.add(transaction)
            
            self.payments.append(payment)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} payments")
        return count
    
    def _seed_notifications(self) -> int:
        """Seed notifications."""
        logger.info("Seeding notifications...")
        
        if not self.users:
            logger.warning("No users for notification creation")
            return 0
        
        notification_types = list(NotificationType)
        channels = list(NotificationChannel)
        priorities = list(NotificationPriority)
        
        count = 0
        target_count = min(self.count * 5, 1000)
        
        for i in range(target_count):
            user = random.choice(self.users)
            
            notification_type = random.choice(notification_types)
            channel = random.choice(channels)
            
            # Create notification
            notification = Notification(
                user_id=user.id,
                notification_type=notification_type,
                channel=channel,
                subject=f"Notification {i} - {notification_type.value}",
                content=fake.text(max_nb_chars=200),
                priority=random.choice(priorities),
                status=random.choice(list(NotificationStatus)),
                created_at=self._random_date(self.start_date, self.end_date)
            )
            self.session.add(notification)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} notifications")
        return count
    
    def _seed_audit_logs(self) -> int:
        """Seed audit logs."""
        logger.info("Seeding audit logs...")
        
        actions = list(AuditAction)
        categories = list(AuditCategory)
        severities = list(AuditSeverity)
        resource_types = list(AuditResourceType)
        
        count = 0
        target_count = min(self.count * 10, 2000)
        
        for i in range(target_count):
            user = random.choice(self.users) if self.users and random.random() > 0.3 else None
            
            audit_log = AuditLog(
                actor_id=user.id if user else None,
                actor_email=user.email if user else 'system@parking.com',
                action=random.choice(actions),
                category=random.choice(categories),
                resource_type=random.choice(resource_types),
                resource_id=str(random.randint(1, 1000)) if random.random() > 0.3 else None,
                severity=random.choice(severities),
                status=random.choice(list(AuditStatus)),
                details={'message': fake.sentence()},
                ip_address=fake.ipv4() if random.random() > 0.5 else None,
                user_agent=fake.user_agent() if random.random() > 0.5 else None,
                created_at=self._random_date(self.start_date, self.end_date)
            )
            self.session.add(audit_log)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} audit logs")
        return count
    
    def _seed_subscriptions(self) -> int:
        """Seed subscriptions."""
        logger.info("Seeding subscriptions...")
        
        if not self.users:
            return 0
        
        # Create subscription plans if they don't exist
        plans = self._ensure_subscription_plans()
        
        count = 0
        for user in self.users[:self.count // 10]:  # 10% of users have subscriptions
            if random.random() > 0.3:  # 30% of selected users
                continue
            
            plan = random.choice(plans)
            
            from data.migrations.payment_models import Subscription
            
            start_date = self._random_date(self.start_date, self.end_date - timedelta(days=30))
            
            # Determine end date based on interval
            if plan.interval == 'month':
                end_date = start_date + timedelta(days=30)
            elif plan.interval == 'year':
                end_date = start_date + timedelta(days=365)
            else:
                end_date = start_date + timedelta(days=30)
            
            # Determine status
            now = datetime.utcnow()
            if end_date < now:
                status = SubscriptionStatus.CANCELED
            elif start_date > now:
                status = SubscriptionStatus.ACTIVE
            else:
                status = SubscriptionStatus.ACTIVE
            
            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status=status,
                current_period_start=start_date,
                current_period_end=end_date,
                cancel_at_period_end=random.random() > 0.8
            )
            self.session.add(subscription)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} subscriptions")
        return count
    
    def _ensure_subscription_plans(self) -> List:
        """Ensure subscription plans exist."""
        from data.migrations.payment_models import SubscriptionPlan
        
        plans_data = [
            {
                'name': 'Basic',
                'description': 'Basic parking plan',
                'price': 29.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 10, 'discount': 5}
            },
            {
                'name': 'Premium',
                'description': 'Premium parking plan',
                'price': 49.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 30, 'discount': 10, 'priority': True}
            },
            {
                'name': 'Business',
                'description': 'Business parking plan',
                'price': 99.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 100, 'discount': 15, 'priority': True, 'dedicated': True}
            }
        ]
        
        plans = []
        for plan_data in plans_data:
            existing = self.session.query(SubscriptionPlan).filter_by(name=plan_data['name']).first()
            if not existing:
                plan = SubscriptionPlan(**plan_data)
                self.session.add(plan)
                self.session.flush()
                plans.append(plan)
            else:
                plans.append(existing)
        
        return plans
    
    def _seed_discounts(self) -> int:
        """Seed discounts and coupons."""
        logger.info("Seeding discounts...")
        
        from data.migrations.payment_models import Discount, Coupon
        
        count = 0
        
        # Create discounts
        discount_types = list(DiscountType)
        
        for i in range(10):
            discount_type = random.choice(discount_types)
            
            if discount_type == DiscountType.PERCENTAGE:
                value = random.uniform(5, 30)
            else:
                value = random.uniform(5, 50)
            
            discount = Discount(
                code=fake.bothify(text='???-######').upper(),
                description=fake.sentence(),
                discount_type=discount_type,
                discount_value=round(value, 2),
                valid_from=self._random_date(self.start_date, self.end_date - timedelta(days=60)),
                valid_until=self._random_date(datetime.utcnow(), self.end_date),
                max_uses=random.randint(10, 1000),
                is_active=True
            )
            self.session.add(discount)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} discounts")
        return count
    
    def _seed_waitlist(self) -> int:
        """Seed waitlist entries."""
        logger.info("Seeding waitlist...")
        
        if not self.users or not self.spots:
            return 0
        
        count = 0
        
        for i in range(min(50, self.count // 2)):
            user = random.choice(self.users)
            spot = random.choice(self.spots)
            
            desired_date = self._random_date(datetime.utcnow(), datetime.utcnow() + timedelta(days=30))
            
            waitlist = Waitlist(
                user_id=user.id,
                spot_id=spot.id,
                date_from=desired_date,
                date_to=desired_date + timedelta(hours=random.randint(1, 4)),
                status=WaitlistStatus.ACTIVE,
                position=i + 1,
                created_at=desired_date - timedelta(days=random.randint(1, 7))
            )
            self.session.add(waitlist)
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} waitlist entries")
        return count
    
    def _seed_maintenance(self) -> int:
        """Seed maintenance records."""
        logger.info("Seeding maintenance...")
        
        if not self.spots:
            return 0
        
        from data.migrations.parking_models import SpotMaintenance
        
        maintenance_types = ['cleaning', 'repair', 'inspection', 'upgrade', 'painting']
        
        count = 0
        
        for i in range(min(30, self.count // 3)):
            spot = random.choice(self.spots)
            
            start_date = self._random_date(self.start_date, self.end_date - timedelta(days=7))
            end_date = start_date + timedelta(hours=random.randint(2, 48))
            
            maintenance = SpotMaintenance(
                spot_id=spot.id,
                maintenance_type=random.choice(maintenance_types),
                started_at=start_date,
                completed_at=end_date if random.random() > 0.3 else None,
                scheduled_start=start_date,
                scheduled_end=end_date,
                status=random.choice(['scheduled', 'in_progress', 'completed']),
                notes=fake.sentence()
            )
            self.session.add(maintenance)
            
            # Update spot status if maintenance is ongoing
            if maintenance.status == 'in_progress' and start_date <= datetime.utcnow() <= end_date:
                spot.status = SpotStatus.MAINTENANCE
            
            count += 1
        
        self.session.flush()
        logger.info(f"Seeded {count} maintenance records")
        return count
    
    def _random_date(self, start: datetime, end: datetime) -> datetime:
        """Generate random datetime between start and end."""
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)


# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Seed database with test data')
    parser.add_argument('--count', type=int, default=100, help='Number of records to create')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')
    parser.add_argument('--env', default='dev', choices=['dev', 'test', 'staging'], 
                       help='Environment (dev, test, staging)')
    parser.add_argument('--db-url', help='Database connection URL')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Load configuration
    config = None
    if args.config:
        from utils.config import Config
        config = Config(args.config)
    else:
        from utils.config import Config
        config = Config()
    
    # Get database URL
    db_url = args.db_url or config.get('database.url', 'sqlite:///parking.db')
    
    # Create engine and session
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create generator
        generator = SeedDataGenerator(
            session=session,
            count=args.count,
            env=args.env,
            clear=args.clear
        )
        
        # Seed data
        results = generator.seed_all()
        
        # Print summary
        print("\n" + "="*60)
        print("SEED DATA COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Environment: {args.env}")
        print(f"Records created:")
        for entity, count in results.items():
            if count > 0:
                print(f"  {entity}: {count}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Seed data failed: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()