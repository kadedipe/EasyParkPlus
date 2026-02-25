#!/usr/bin/env python3
"""
Test data generation script for the parking management system.

This script generates realistic test data for development, testing, and
performance benchmarking. It creates users, vehicles, reservations, payments,
and other entities with configurable volumes and realistic distributions.

Usage:
    python generate_test_data.py [options]

Options:
    --scale SCALE       Scale factor for data volume (1-100) [default: 1]
    --users N           Number of users to generate [default: 100]
    --vehicles N        Number of vehicles per user [default: 1-3]
    --reservations N    Number of reservations per user [default: 5-20]
    --days N            Days of history to generate [default: 180]
    --future N          Days of future reservations [default: 90]
    --batch-size N      Batch size for inserts [default: 1000]
    --clean             Clean existing data before generating
    --format FORMAT     Output format (db, json, csv) [default: db]
    --output PATH       Output file/directory [default: ./test_data]
    --seed N            Random seed for reproducibility
    --profile           Generate performance profile data
    --anonymize         Anonymize personal data
    --verbose           Verbose output
    --help              Show this help message

Examples:
    # Generate small test dataset
    python generate_test_data.py --users 50 --days 30

    # Generate large dataset for performance testing
    python generate_test_data.py --scale 10 --users 1000 --reservations 50

    # Generate and save as JSON
    python generate_test_data.py --format json --output test_data.json

    # Generate with specific seed for reproducibility
    python generate_test_data.py --seed 42 --users 100

    # Generate anonymized test data
    python generate_test_data.py --users 500 --anonymize
"""

import os
import sys
import argparse
import logging
import random
import json
import csv
import hashlib
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import itertools
import uuid
from collections import defaultdict
import warnings

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Suppress SQLAlchemy warnings
warnings.filterwarnings('ignore', category=Warning)

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session

from data.migrations.models import (
    User, UserProfile, UserPreference, UserSession, UserDevice,
    Role, Permission, RoleAssignment,
    Vehicle, VehicleRegistration, VehicleInsurance, VehicleInspection,
    VehicleOwnership, VehicleDocument, VehicleImage,
    ParkingSpot, ParkingZone, SpotMaintenance, SpotSensor,
    Reservation, RecurringReservation, Waitlist,
    Payment, Invoice, Subscription, Discount,
    Notification, NotificationTemplate,
    AuditLog,
    SystemConfig
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
from utils.security import hash_password
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Faker for realistic data generation
try:
    from faker import Faker
    from faker.providers import automotive, company, person, phone_number, lorem, date_time
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    logger.warning("Faker not installed. Using basic random data generation.")
    
    # Simple Faker-like functions for when Faker is not available
    class SimpleFaker:
        def __init__(self):
            self.first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth']
            self.last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
            self.domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'company.com']
            self.streets = ['Main St', 'Oak Ave', 'Maple Dr', 'Washington Blvd', 'Park Rd']
            self.cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
            self.states = ['NY', 'CA', 'IL', 'TX', 'AZ', 'PA', 'TX', 'CA', 'TX', 'CA']
            self.words_list = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']
        
        def first_name(self): return random.choice(self.first_names)
        def last_name(self): return random.choice(self.last_names)
        def email(self): return f"{self.first_name().lower()}.{self.last_name().lower()}@{random.choice(self.domains)}"
        def phone_number(self): return f"+1{random.randint(200, 999)}{random.randint(200, 999)}{random.randint(1000, 9999)}"
        def street_address(self): return f"{random.randint(100, 9999)} {random.choice(self.streets)}"
        def city(self): return random.choice(self.cities)
        def state(self): return random.choice(self.states)
        def zipcode(self): return f"{random.randint(10000, 99999)}"
        def date_of_birth(self, minimum_age=18, maximum_age=80): 
            days = random.randint(minimum_age*365, maximum_age*365)
            return date.today() - timedelta(days=days)
        def company(self): return f"{random.choice(['ABC', 'XYZ', 'Global', 'International', 'United'])} {random.choice(['Corp', 'Inc', 'LLC', 'Group'])}"
        def sentence(self, nb_words=6): return ' '.join(random.sample(self.words_list, min(nb_words, len(self.words_list))))
        def text(self, max_nb_chars=200): return self.sentence(10) * (max_nb_chars // 50)
        def vin(self): return ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ0123456789', k=17))
        def license_plate(self): return f"{''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=3))}{random.randint(100, 999)}"
        def bothify(self, text='???-####'): 
            result = ''
            for c in text:
                if c == '?':
                    result += random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                elif c == '#':
                    result += random.choice('0123456789')
                else:
                    result += c
            return result
        def ipv4(self): return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"
        def user_agent(self): return f"Mozilla/5.0 (compatible; MSIE {random.randint(5, 11)}.0; Windows NT {random.randint(5, 10)}.0)"
        def word(self): return random.choice(self.words_list)
        def words(self, nb=3): return random.sample(self.words_list, min(nb, len(self.words_list)))
        def mac_address(self): return ':'.join([f"{random.randint(0, 255):02x}" for _ in range(6)])


# ============================================================================
# Test Data Generator
# ============================================================================

class TestDataGenerator:
    """
    Generates realistic test data for the parking management system.
    
    Creates realistic volumes of data with proper relationships and
    distributions for development, testing, and performance benchmarking.
    """
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        scale: int = 1,
        num_users: int = 100,
        vehicles_per_user: Tuple[int, int] = (1, 3),
        reservations_per_user: Tuple[int, int] = (5, 20),
        history_days: int = 180,
        future_days: int = 90,
        batch_size: int = 1000,
        clean: bool = False,
        output_format: str = 'db',
        output_path: Optional[str] = None,
        seed: Optional[int] = None,
        anonymize: bool = False
    ):
        """
        Initialize the test data generator.
        
        Args:
            db_url: Database URL (if output_format is 'db')
            scale: Scale factor for data volume
            num_users: Number of users to generate
            vehicles_per_user: Min/max vehicles per user
            reservations_per_user: Min/max reservations per user
            history_days: Days of history to generate
            future_days: Days of future reservations
            batch_size: Batch size for inserts
            clean: Clean existing data before generating
            output_format: Output format ('db', 'json', 'csv')
            output_path: Output file/directory
            seed: Random seed for reproducibility
            anonymize: Anonymize personal data
        """
        self.scale = scale
        self.num_users = int(num_users * scale)
        self.vehicles_per_user = vehicles_per_user
        self.reservations_per_user = reservations_per_user
        self.history_days = history_days
        self.future_days = future_days
        self.batch_size = batch_size
        self.clean = clean
        self.output_format = output_format
        self.output_path = output_path
        self.anonymize = anonymize
        
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)
            if FAKER_AVAILABLE:
                Faker.seed(seed)
        
        # Initialize Faker
        if FAKER_AVAILABLE:
            self.fake = Faker()
            self.fake.add_provider(automotive)
            self.fake.add_provider(company)
            self.fake.add_provider(person)
            self.fake.add_provider(phone_number)
            self.fake.add_provider(lorem)
            self.fake.add_provider(date_time)
        else:
            self.fake = SimpleFaker()
        
        # Database connection (if needed)
        self.db_url = db_url
        self.engine = None
        self.Session = None
        
        if output_format == 'db' and db_url:
            self.engine = create_engine(
                db_url,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
        
        # Data storage for JSON/CSV output
        self.data = defaultdict(list)
        
        # Statistics
        self.stats = {
            'users': 0,
            'vehicles': 0,
            'reservations': 0,
            'payments': 0,
            'notifications': 0,
            'audit_logs': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Configuration
        self.payment_methods = list(PaymentMethodType)
        self.currencies = list(Currency)
        self.vehicle_types = list(VehicleType)
        self.fuel_types = list(FuelType)
        self.spot_types = list(SpotType)
        
        # Vehicle makes and models
        self.vehicle_makes = {
            'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Tacoma', 'Tundra'],
            'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'Odyssey'],
            'Ford': ['F-150', 'Escape', 'Explorer', 'Mustang', 'Focus'],
            'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Tahoe', 'Camaro'],
            'BMW': ['3 Series', '5 Series', 'X3', 'X5', 'M4'],
            'Mercedes': ['C-Class', 'E-Class', 'GLC', 'GLE', 'S-Class'],
            'Audi': ['A4', 'A6', 'Q5', 'Q7', 'e-tron'],
            'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck'],
            'Nissan': ['Altima', 'Rogue', 'Sentra', 'Pathfinder', 'Leaf'],
            'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Kona'],
            'Kia': ['Optima', 'Sorento', 'Sportage', 'Telluride', 'Niro'],
            'Volkswagen': ['Jetta', 'Passat', 'Tiguan', 'Atlas', 'ID.4'],
            'Subaru': ['Outback', 'Forester', 'Crosstrek', 'Impreza', 'Legacy'],
            'Mazda': ['Mazda3', 'Mazda6', 'CX-5', 'CX-9', 'MX-5'],
            'Lexus': ['ES', 'RX', 'NX', 'GX', 'LX'],
            'Jeep': ['Wrangler', 'Grand Cherokee', 'Cherokee', 'Compass', 'Renegade']
        }
        
        # Colors
        self.colors = ['Black', 'White', 'Silver', 'Gray', 'Blue', 'Red', 
                      'Green', 'Brown', 'Beige', 'Yellow', 'Orange', 'Gold']
        
        logger.info(f"TestDataGenerator initialized: {self.num_users} users, {self.history_days} days history")
    
    # ========================================================================
    # Main Generation Methods
    # ========================================================================
    
    def generate_all(self) -> Dict[str, int]:
        """
        Generate all test data.
        
        Returns:
            Statistics dictionary
        """
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info("Starting test data generation...")
        
        # Clean existing data if requested
        if self.clean and self.output_format == 'db' and self.engine:
            self._clean_database()
        
        # Generate data in order (respecting foreign keys)
        self._generate_roles_and_permissions()
        self._generate_parking_zones()
        self._generate_parking_spots()
        self._generate_users()
        self._generate_vehicles()
        self._generate_reservations()
        self._generate_payments()
        self._generate_notifications()
        self._generate_audit_logs()
        self._generate_additional_data()
        
        # Write to output
        self._write_output()
        
        self.stats['end_time'] = datetime.utcnow()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Test data generation completed in {duration:.2f} seconds")
        logger.info(f"Generated: {self.stats}")
        
        return self.stats
    
    def _clean_database(self) -> None:
        """Clean existing data from database."""
        logger.info("Cleaning existing database...")
        
        with self.Session() as session:
            # Disable foreign key checks
            if 'postgresql' in self.db_url:
                session.execute(text("SET session_replication_role = 'replica';"))
            elif 'mysql' in self.db_url:
                session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            elif 'sqlite' in self.db_url:
                session.execute(text("PRAGMA foreign_keys = OFF;"))
            
            # Get all tables
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            # Delete in reverse order
            for table in reversed(tables):
                session.execute(text(f"DELETE FROM {table};"))
                logger.debug(f"Cleared table: {table}")
            
            # Re-enable foreign key checks
            if 'postgresql' in self.db_url:
                session.execute(text("SET session_replication_role = 'origin';"))
            elif 'mysql' in self.db_url:
                session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            elif 'sqlite' in self.db_url:
                session.execute(text("PRAGMA foreign_keys = ON;"))
            
            session.commit()
        
        logger.info("Database cleaned")
    
    def _write_output(self) -> None:
        """Write generated data to output."""
        if self.output_format == 'db':
            self._write_to_database()
        elif self.output_format == 'json':
            self._write_to_json()
        elif self.output_format == 'csv':
            self._write_to_csv()
    
    def _write_to_database(self) -> None:
        """Write data to database."""
        if not self.Session:
            logger.error("No database session available")
            return
        
        logger.info("Writing data to database...")
        
        with self.Session() as session:
            for table_name, rows in self.data.items():
                if not rows:
                    continue
                
                logger.info(f"Inserting {len(rows)} rows into {table_name}")
                
                # Insert in batches
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i+self.batch_size]
                    session.bulk_insert_mappings(
                        self._get_model_class(table_name),
                        batch
                    )
                    session.flush()
                    
                    logger.debug(f"  Inserted batch {i//self.batch_size + 1}")
            
            session.commit()
        
        logger.info("Database write completed")
    
    def _get_model_class(self, table_name: str):
        """Get SQLAlchemy model class for table name."""
        model_map = {
            'users': User,
            'user_profiles': UserProfile,
            'user_preferences': UserPreference,
            'roles': Role,
            'permissions': Permission,
            'role_assignments': RoleAssignment,
            'vehicles': Vehicle,
            'vehicle_registrations': VehicleRegistration,
            'vehicle_insurance': VehicleInsurance,
            'vehicle_inspections': VehicleInspection,
            'vehicle_ownership': VehicleOwnership,
            'parking_zones': ParkingZone,
            'parking_spots': ParkingSpot,
            'reservations': Reservation,
            'payments': Payment,
            'notifications': Notification,
            'audit_logs': AuditLog
        }
        return model_map.get(table_name)
    
    def _write_to_json(self) -> None:
        """Write data to JSON file."""
        output_file = Path(self.output_path or 'test_data.json')
        
        logger.info(f"Writing data to JSON: {output_file}")
        
        # Convert datetime objects to strings
        serializable_data = {}
        for table_name, rows in self.data.items():
            serializable_rows = []
            for row in rows:
                serializable_row = {}
                for key, value in row.items():
                    if isinstance(value, (datetime, date)):
                        serializable_row[key] = value.isoformat()
                    elif isinstance(value, Enum):
                        serializable_row[key] = value.value
                    else:
                        serializable_row[key] = value
                serializable_rows.append(serializable_row)
            serializable_data[table_name] = serializable_rows
        
        with open(output_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        logger.info(f"JSON write completed: {output_file}")
    
    def _write_to_csv(self) -> None:
        """Write data to CSV files."""
        output_dir = Path(self.output_path or 'test_data_csv')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Writing data to CSV: {output_dir}")
        
        for table_name, rows in self.data.items():
            if not rows:
                continue
            
            output_file = output_dir / f"{table_name}.csv"
            
            with open(output_file, 'w', newline='') as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    
                    for row in rows:
                        # Convert non-serializable values
                        serializable_row = {}
                        for key, value in row.items():
                            if isinstance(value, (datetime, date)):
                                serializable_row[key] = value.isoformat()
                            elif isinstance(value, Enum):
                                serializable_row[key] = value.value
                            else:
                                serializable_row[key] = value
                        writer.writerow(serializable_row)
            
            logger.info(f"  Wrote {len(rows)} rows to {output_file}")
    
    # ========================================================================
    # Data Generation Methods
    # ========================================================================
    
    def _generate_roles_and_permissions(self) -> None:
        """Generate roles and permissions."""
        logger.info("Generating roles and permissions...")
        
        roles = [
            {'name': 'user', 'description': 'Regular user', 'priority': 0},
            {'name': 'operator', 'description': 'Parking operator', 'priority': 10},
            {'name': 'manager', 'description': 'Parking manager', 'priority': 20},
            {'name': 'admin', 'description': 'Administrator', 'priority': 100},
            {'name': 'super_admin', 'description': 'Super administrator', 'priority': 1000}
        ]
        
        for role in roles:
            role['created_at'] = datetime.utcnow() - timedelta(days=self.history_days)
            self.data['roles'].append(role)
        
        # Generate permissions
        resources = ['user', 'vehicle', 'parking', 'reservation', 'payment', 'report', 'admin']
        actions = ['view', 'create', 'edit', 'delete', 'manage', 'configure']
        
        for resource in resources:
            for action in actions:
                permission = {
                    'name': f"{resource}:{action}",
                    'resource_type': resource,
                    'action': action,
                    'description': f"{action.capitalize()} {resource}s",
                    'created_at': datetime.utcnow() - timedelta(days=self.history_days)
                }
                self.data['permissions'].append(permission)
    
    def _generate_parking_zones(self) -> None:
        """Generate parking zones."""
        logger.info("Generating parking zones...")
        
        zone_configs = [
            # name, type, total_spots, hourly_rate, description
            ('Main Lot A', 'surface', 100, 2.50, 'Main parking lot - Section A', 'North Entrance'),
            ('Main Lot B', 'surface', 100, 2.50, 'Main parking lot - Section B', 'South Entrance'),
            ('Garage Level 1', 'structure', 150, 3.00, 'Parking garage - Level 1', 'West Building'),
            ('Garage Level 2', 'structure', 150, 3.00, 'Parking garage - Level 2', 'West Building'),
            ('Garage Level 3', 'structure', 150, 3.00, 'Parking garage - Level 3', 'West Building'),
            ('VIP Section', 'reserved', 50, 5.00, 'VIP reserved parking', 'Near Entrance'),
            ('EV Charging Station', 'covered', 40, 3.50, 'Electric vehicle charging', 'East Side'),
            ('Motorcycle Parking', 'surface', 30, 1.50, 'Dedicated motorcycle parking', 'South Side'),
            ('Oversize Vehicle Lot', 'surface', 25, 5.00, 'For trucks, RVs, oversize vehicles', 'Remote Lot'),
            ('Staff Parking', 'reserved', 60, 0.00, 'Employee parking', 'Back Lot'),
            ('Visitor Center', 'surface', 80, 3.00, 'Visitor parking', 'Main Entrance'),
            ('Overflow Lot', 'surface', 200, 2.00, 'Overflow parking', 'Far East')
        ]
        
        for name, zone_type, total_spots, rate, description, location in zone_configs:
            zone = {
                'name': name,
                'zone_type': ZoneType(zone_type),
                'total_spots': total_spots,
                'available_spots': total_spots,
                'hourly_rate': rate,
                'daily_max': rate * 8,
                'description': description,
                'location': location,
                'is_active': True,
                'created_at': datetime.utcnow() - timedelta(days=self.history_days)
            }
            self.data['parking_zones'].append(zone)
        
        logger.info(f"Generated {len(self.data['parking_zones'])} parking zones")
    
    def _generate_parking_spots(self) -> None:
        """Generate parking spots for each zone."""
        logger.info("Generating parking spots...")
        
        spot_count = 0
        
        for zone_idx, zone in enumerate(self.data['parking_zones']):
            zone_id = zone_idx + 1  # Will be replaced with actual ID
            total_spots = zone['total_spots']
            
            for i in range(1, total_spots + 1):
                # Determine spot type based on zone and position
                if zone['name'].startswith('VIP'):
                    spot_type = SpotType.VIP
                elif zone['name'].startswith('EV'):
                    spot_type = SpotType.ELECTRIC
                elif zone['name'].startswith('Motorcycle'):
                    spot_type = SpotType.MOTORCYCLE
                elif zone['name'].startswith('Oversize'):
                    spot_type = SpotType.OVERSIZE
                elif i <= total_spots * 0.05:  # 5% handicapped spots
                    spot_type = SpotType.HANDICAPPED
                elif i % 10 == 0:  # Every 10th spot is compact
                    spot_type = SpotType.COMPACT
                else:
                    spot_type = SpotType.STANDARD
                
                # Generate spot number
                if 'Garage' in zone['name']:
                    level = zone['name'].split()[-1]
                    spot_number = f"{level}-{i:03d}"
                else:
                    prefix = zone['name'][0]
                    spot_number = f"{prefix}{i:03d}"
                
                # Determine if covered
                is_covered = zone['zone_type'] in [ZoneType.STRUCTURE, ZoneType.COVERED]
                
                # Determine if has EV charging
                has_ev_charging = spot_type == SpotType.ELECTRIC
                
                # Dimensions based on spot type
                if spot_type == SpotType.COMPACT:
                    width, length = 2.2, 4.5
                elif spot_type == SpotType.HANDICAPPED:
                    width, length = 3.0, 5.0
                elif spot_type == SpotType.MOTORCYCLE:
                    width, length = 1.2, 2.5
                elif spot_type == SpotType.OVERSIZE:
                    width, length = 3.5, 7.0
                else:
                    width, length = 2.5, 5.0
                
                spot = {
                    'zone_id': zone_id,
                    'spot_number': spot_number,
                    'spot_type': spot_type,
                    'status': SpotStatus.AVAILABLE,
                    'is_covered': is_covered,
                    'has_ev_charging': has_ev_charging,
                    'width': width,
                    'length': length,
                    'created_at': datetime.utcnow() - timedelta(days=self.history_days)
                }
                
                # Add features based on spot type
                if spot_type == SpotType.ELECTRIC:
                    spot['features'] = {
                        'charger_type': random.choice(['Level 2', 'DC Fast']),
                        'charger_power': random.choice([7.2, 11, 22, 50])
                    }
                elif spot_type == SpotType.HANDICAPPED:
                    spot['features'] = {
                        'wider_aisle': True,
                        'near_elevator': random.choice([True, False])
                    }
                
                self.data['parking_spots'].append(spot)
                spot_count += 1
        
        logger.info(f"Generated {spot_count} parking spots")
    
    def _generate_users(self) -> None:
        """Generate users."""
        logger.info(f"Generating {self.num_users} users...")
        
        # Determine role distribution
        num_operators = max(1, self.num_users // 20)
        num_managers = max(1, self.num_users // 50)
        num_admins = max(1, self.num_users // 100)
        num_users = self.num_users - num_operators - num_managers - num_admins
        
        # Generate regular users
        for i in range(num_users):
            user = self._create_user(UserRole.USER)
            self.data['users'].append(user)
            self._create_user_profile(user)
            self._create_user_preferences(user)
            self._create_user_sessions(user)
            
            if i % 100 == 0:
                logger.debug(f"  Generated {i} users...")
        
        # Generate operators
        for i in range(num_operators):
            user = self._create_user(UserRole.OPERATOR)
            self.data['users'].append(user)
            self._create_user_profile(user)
            self._create_user_preferences(user)
            self._create_user_sessions(user)
        
        # Generate managers
        for i in range(num_managers):
            user = self._create_user(UserRole.MANAGER)
            self.data['users'].append(user)
            self._create_user_profile(user)
            self._create_user_preferences(user)
            self._create_user_sessions(user)
        
        # Generate admins
        for i in range(num_admins):
            user = self._create_user(UserRole.ADMIN)
            self.data['users'].append(user)
            self._create_user_profile(user)
            self._create_user_preferences(user)
            self._create_user_sessions(user)
        
        self.stats['users'] = len(self.data['users'])
        logger.info(f"Generated {self.stats['users']} users")
    
    def _create_user(self, role: UserRole) -> Dict:
        """Create a single user."""
        # Generate name
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        
        # Generate email
        email_domain = random.choice(['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'company.com'])
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}@{email_domain}"
        
        # Generate username
        username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
        
        # Determine status
        if role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]:
            status = UserStatus.ACTIVE
            email_verified = True
            phone_verified = True
        else:
            status_choices = [UserStatus.ACTIVE, UserStatus.ACTIVE, UserStatus.ACTIVE,
                             UserStatus.INACTIVE, UserStatus.PENDING]
            status = random.choice(status_choices)
            email_verified = status == UserStatus.ACTIVE and random.random() > 0.2
            phone_verified = email_verified and random.random() > 0.3
        
        # Generate creation date (spread over history)
        days_ago = random.randint(0, self.history_days)
        created_at = datetime.utcnow() - timedelta(days=days_ago)
        
        # Generate last login
        last_login_at = None
        if status == UserStatus.ACTIVE and random.random() > 0.3:
            last_login_days = random.randint(0, min(days_ago, 30))
            last_login_at = created_at + timedelta(days=last_login_days)
        
        user = {
            'id': len(self.data['users']) + 1,
            'email': email,
            'username': username,
            'password_hash': hash_password('Password123!'),
            'first_name': first_name,
            'last_name': last_name,
            'phone': self.fake.phone_number(),
            'status': status,
            'email_verified_at': created_at + timedelta(minutes=random.randint(5, 60)) if email_verified else None,
            'phone_verified_at': created_at + timedelta(minutes=random.randint(60, 120)) if phone_verified else None,
            'last_login_at': last_login_at,
            'last_login_ip': self.fake.ipv4() if last_login_at else None,
            'failed_login_attempts': 0 if status == UserStatus.ACTIVE else random.randint(1, 5),
            'created_at': created_at,
            'updated_at': created_at + timedelta(days=random.randint(0, days_ago)) if random.random() > 0.5 else None,
            'metadata': {
                'source': 'test_data_generator',
                'batch': 'initial'
            } if not self.anonymize else {}
        }
        
        # Assign role
        role_assignment = {
            'user_id': user['id'],
            'role_id': self._get_role_id(role),
            'assigned_at': created_at
        }
        self.data['role_assignments'].append(role_assignment)
        
        return user
    
    def _get_role_id(self, role: UserRole) -> int:
        """Get role ID by name."""
        role_map = {
            UserRole.USER: 1,
            UserRole.OPERATOR: 2,
            UserRole.MANAGER: 3,
            UserRole.ADMIN: 4,
            UserRole.SUPER_ADMIN: 5
        }
        return role_map.get(role, 1)
    
    def _create_user_profile(self, user: Dict) -> None:
        """Create user profile."""
        profile = {
            'user_id': user['id'],
            'date_of_birth': self.fake.date_of_birth(minimum_age=18, maximum_age=80),
            'address': self.fake.street_address(),
            'city': self.fake.city(),
            'state': self.fake.state(),
            'zip_code': self.fake.zipcode(),
            'country': random.choice([c.value for c in CountryCode]),
            'avatar_url': f"https://randomuser.me/api/portraits/{random.choice(['men', 'women'])}/{random.randint(1, 99)}.jpg",
            'preferred_language': random.choice([l.value for l in Language]),
            'timezone': random.choice([t.value for t in Timezone]),
            'created_at': user['created_at']
        }
        self.data['user_profiles'].append(profile)
    
    def _create_user_preferences(self, user: Dict) -> None:
        """Create user preferences."""
        preferences = {
            'user_id': user['id'],
            'notification_email': random.choice([True, False]),
            'notification_sms': random.choice([True, False]),
            'notification_push': random.choice([True, False]),
            'marketing_emails': random.choice([True, False]),
            'theme': random.choice(['light', 'dark', 'auto']),
            'language': random.choice([l.value for l in Language]),
            'timezone': random.choice([t.value for t in Timezone]),
            'created_at': user['created_at']
        }
        self.data['user_preferences'].append(preferences)
    
    def _create_user_sessions(self, user: Dict) -> None:
        """Create user sessions."""
        if user['status'] != UserStatus.ACTIVE:
            return
        
        num_sessions = random.randint(0, 20)
        
        for i in range(num_sessions):
            session_date = user['created_at'] + timedelta(
                days=random.randint(0, min(30, (datetime.utcnow() - user['created_at']).days))
            )
            
            session = {
                'user_id': user['id'],
                'session_id': str(uuid.uuid4()),
                'created_at': session_date,
                'expires_at': session_date + timedelta(hours=random.randint(1, 24)),
                'last_activity': session_date + timedelta(minutes=random.randint(5, 120)),
                'ip_address': self.fake.ipv4(),
                'user_agent': self.fake.user_agent(),
                'is_active': random.random() > 0.7
            }
            self.data['user_sessions'].append(session)
    
    def _generate_vehicles(self) -> None:
        """Generate vehicles for users."""
        logger.info("Generating vehicles...")
        
        vehicle_count = 0
        
        for user in self.data['users']:
            # Determine number of vehicles for this user
            num_vehicles = random.randint(
                self.vehicles_per_user[0],
                self.vehicles_per_user[1]
            )
            
            for i in range(num_vehicles):
                vehicle = self._create_vehicle(user)
                self.data['vehicles'].append(vehicle)
                vehicle_count += 1
                
                # Add ownership
                ownership = {
                    'vehicle_id': vehicle['id'],
                    'user_id': user['id'],
                    'ownership_type': OwnershipType.OWNER,
                    'is_primary': i == 0,
                    'start_date': vehicle['created_at'].date(),
                    'created_at': vehicle['created_at']
                }
                self.data['vehicle_ownership'].append(ownership)
                
                # Add registration
                self._create_vehicle_registration(vehicle)
                
                # Add insurance
                self._create_vehicle_insurance(vehicle)
                
                # Add inspection
                self._create_vehicle_inspection(vehicle)
        
        self.stats['vehicles'] = vehicle_count
        logger.info(f"Generated {vehicle_count} vehicles")
    
    def _create_vehicle(self, user: Dict) -> Dict:
        """Create a single vehicle."""
        # Select make and model
        make = random.choice(list(self.vehicle_makes.keys()))
        model = random.choice(self.vehicle_makes[make])
        
        # Determine vehicle type based on make/model
        if make == 'Tesla':
            vehicle_type = VehicleType.EV
        elif model in ['F-150', 'Silverado', 'Tacoma', 'Tundra']:
            vehicle_type = VehicleType.TRUCK
        elif model in ['Mustang', 'Camaro', 'M4']:
            vehicle_type = VehicleType.LUXURY
        elif make in ['Harley-Davidson']:
            vehicle_type = VehicleType.MOTORCYCLE
        else:
            vehicle_type = random.choice([VehicleType.CAR, VehicleType.SUV])
        
        # Determine fuel type
        if vehicle_type == VehicleType.EV:
            fuel_type = FuelType.ELECTRIC
        elif vehicle_type == VehicleType.HYBRID:
            fuel_type = FuelType.HYBRID
        elif random.random() > 0.7:
            fuel_type = FuelType.DIESEL
        else:
            fuel_type = FuelType.GASOLINE
        
        # Generate license plate
        license_plate = self.fake.license_plate()
        
        # Determine status
        if random.random() > 0.9:
            status = VehicleStatus.INACTIVE
        elif random.random() > 0.95:
            status = VehicleStatus.BANNED
        else:
            status = VehicleStatus.ACTIVE
        
        # Vehicle age
        current_year = datetime.utcnow().year
        year = random.randint(max(2000, current_year - 15), current_year)
        
        vehicle = {
            'id': len(self.data['vehicles']) + 1,
            'license_plate': license_plate,
            'vin': self.fake.vin(),
            'make': make,
            'model': model,
            'year': year,
            'color': random.choice(self.colors),
            'vehicle_type': vehicle_type,
            'fuel_type': fuel_type,
            'status': status,
            'current_mileage': random.randint(0, 100000),
            'created_at': user['created_at'] + timedelta(days=random.randint(1, 30))
        }
        
        return vehicle
    
    def _create_vehicle_registration(self, vehicle: Dict) -> None:
        """Create vehicle registration."""
        issue_date = vehicle['created_at'].date()
        expiry_date = issue_date + timedelta(days=365)
        
        registration = {
            'vehicle_id': vehicle['id'],
            'registration_number': f"REG-{vehicle['license_plate']}",
            'issue_date': issue_date,
            'expiry_date': expiry_date,
            'issuing_authority': f"DMV {self.fake.state()}",
            'status': RegistrationStatus.CURRENT,
            'is_current': True,
            'created_at': vehicle['created_at']
        }
        self.data['vehicle_registrations'].append(registration)
    
    def _create_vehicle_insurance(self, vehicle: Dict) -> None:
        """Create vehicle insurance."""
        providers = ['Geico', 'Progressive', 'State Farm', 'Allstate', 'Farmers', 'Liberty Mutual']
        
        issue_date = vehicle['created_at'].date()
        expiry_date = issue_date + timedelta(days=365)
        
        insurance = {
            'vehicle_id': vehicle['id'],
            'policy_number': f"POL-{random.randint(100000, 999999)}",
            'provider': random.choice(providers),
            'coverage_type': random.choice(['Liability', 'Full Coverage', 'Comprehensive']),
            'issue_date': issue_date,
            'expiry_date': expiry_date,
            'status': InsuranceStatus.ACTIVE,
            'is_current': True,
            'created_at': vehicle['created_at']
        }
        self.data['vehicle_insurance'].append(insurance)
    
    def _create_vehicle_inspection(self, vehicle: Dict) -> None:
        """Create vehicle inspection."""
        inspection_date = vehicle['created_at'].date()
        
        inspection = {
            'vehicle_id': vehicle['id'],
            'inspection_date': inspection_date,
            'result': InspectionStatus.PASSED,
            'inspector': f"Inspector {random.randint(1, 20)}",
            'next_inspection_date': inspection_date + timedelta(days=365),
            'notes': self.fake.sentence() if random.random() > 0.7 else None,
            'created_at': vehicle['created_at']
        }
        self.data['vehicle_inspections'].append(inspection)
    
    def _generate_reservations(self) -> None:
        """Generate reservations."""
        logger.info("Generating reservations...")
        
        if not self.data['users'] or not self.data['vehicles'] or not self.data['parking_spots']:
            logger.warning("Missing required data for reservations")
            return
        
        reservation_count = 0
        spot_status_updates = defaultdict(list)
        
        for user_idx, user in enumerate(self.data['users']):
            # Get user's vehicles
            user_vehicles = [v for v in self.data['vehicles'] 
                           if any(o['user_id'] == user['id'] and o['vehicle_id'] == v['id'] 
                                 for o in self.data['vehicle_ownership'])]
            
            if not user_vehicles:
                continue
            
            # Determine number of reservations
            min_res = self.reservations_per_user[0]
            max_res = self.reservations_per_user[1]
            num_reservations = random.randint(min_res, max_res)
            
            for i in range(num_reservations):
                vehicle = random.choice(user_vehicles)
                spot = random.choice(self.data['parking_spots'])
                
                reservation = self._create_reservation(user, vehicle, spot, i)
                
                if reservation:
                    self.data['reservations'].append(reservation)
                    reservation_count += 1
                    
                    # Track spot status for this time
                    spot_status_updates[spot['id']].append({
                        'start': reservation['start_time'],
                        'end': reservation['end_time'],
                        'status': reservation['status']
                    })
            
            if user_idx % 100 == 0 and user_idx > 0:
                logger.debug(f"  Generated reservations for {user_idx} users...")
        
        self.stats['reservations'] = reservation_count
        logger.info(f"Generated {reservation_count} reservations")
    
    def _create_reservation(self, user: Dict, vehicle: Dict, spot: Dict, index: int) -> Optional[Dict]:
        """Create a single reservation."""
        now = datetime.utcnow()
        
        # Determine if this is past, present, or future
        r = random.random()
        
        if r < 0.3:  # Past reservation
            days_ago = random.randint(1, self.history_days)
            base_time = now - timedelta(days=days_ago)
            status = ReservationStatus.COMPLETED
        elif r < 0.5:  # Current/near future
            hours_from_now = random.randint(-2, 4)
            base_time = now + timedelta(hours=hours_from_now)
            if base_time < now:
                status = random.choice([ReservationStatus.CHECKED_IN, ReservationStatus.COMPLETED])
            else:
                status = ReservationStatus.CONFIRMED
        else:  # Future reservation
            days_ahead = random.randint(1, self.future_days)
            base_time = now + timedelta(days=days_ahead)
            status = ReservationStatus.CONFIRMED
        
        # Random duration (1-8 hours)
        duration_hours = random.choices(
            [1, 2, 3, 4, 6, 8, 12, 24],
            weights=[0.2, 0.2, 0.15, 0.1, 0.1, 0.1, 0.05, 0.05]
        )[0]
        
        start_time = base_time.replace(minute=0, second=0, microsecond=0)
        start_time += timedelta(hours=random.randint(8, 20))  # Between 8 AM and 8 PM
        
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Occasionally create cancelled or no-show
        if random.random() < 0.1 and status == ReservationStatus.CONFIRMED:
            status = ReservationStatus.CANCELLED
        elif random.random() < 0.05 and status == ReservationStatus.CONFIRMED:
            status = ReservationStatus.NO_SHOW
        
        # Calculate amount
        zone_id = spot['zone_id']
        zone = next((z for z in self.data['parking_zones'] if z.get('id') == zone_id), None)
        
        if zone:
            hourly_rate = zone.get('hourly_rate', 2.5)
            amount = duration_hours * hourly_rate
        else:
            amount = duration_hours * 2.5
        
        # Add multipliers for special spot types
        if spot['spot_type'] == SpotType.VIP:
            amount *= 2.0
        elif spot['spot_type'] == SpotType.ELECTRIC:
            amount *= 1.2
        
        # Round to 2 decimals
        amount = round(amount, 2)
        
        reservation = {
            'id': len(self.data['reservations']) + 1,
            'user_id': user['id'],
            'spot_id': spot['id'],
            'vehicle_id': vehicle['id'],
            'confirmation_code': self._generate_confirmation_code(),
            'start_time': start_time,
            'end_time': end_time,
            'status': status,
            'reservation_type': ReservationType.STANDARD,
            'total_amount': amount,
            'created_at': start_time - timedelta(days=random.randint(1, 14)) if start_time > now else now - timedelta(days=random.randint(1, 30))
        }
        
        # Add check-in/out times if applicable
        if status == ReservationStatus.CHECKED_IN:
            check_in_offset = random.randint(-30, 0)
            reservation['checked_in_at'] = start_time + timedelta(minutes=check_in_offset)
        elif status == ReservationStatus.COMPLETED:
            reservation['checked_in_at'] = start_time
            reservation['checked_out_at'] = end_time
        elif status == ReservationStatus.CANCELLED:
            reservation['cancelled_at'] = start_time - timedelta(hours=random.randint(1, 48))
            reservation['cancellation_reason'] = random.choice([
                'Change of plans', 'Found better rate', 'Vehicle issues', 'Schedule conflict'
            ])
        elif status == ReservationStatus.NO_SHOW:
            reservation['no_show_at'] = start_time + timedelta(minutes=30)
        
        return reservation
    
    def _generate_confirmation_code(self) -> str:
        """Generate unique confirmation code."""
        letters = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=4))
        numbers = ''.join(random.choices('0123456789', k=4))
        return f"{letters}{numbers}"
    
    def _generate_payments(self) -> None:
        """Generate payments for reservations."""
        logger.info("Generating payments...")
        
        if not self.data['reservations']:
            return
        
        payment_count = 0
        
        for reservation in self.data['reservations']:
            # Only create payments for completed or checked-in reservations
            if reservation['status'] not in [ReservationStatus.COMPLETED, ReservationStatus.CHECKED_IN]:
                # Sometimes create payments for confirmed reservations
                if reservation['status'] != ReservationStatus.CONFIRMED or random.random() > 0.3:
                    continue
            
            # Determine payment status
            if reservation['status'] == ReservationStatus.COMPLETED:
                status = PaymentStatus.PAID
            elif reservation['status'] == ReservationStatus.CHECKED_IN:
                status = random.choices(
                    [PaymentStatus.PAID, PaymentStatus.AUTHORIZED, PaymentStatus.PENDING],
                    weights=[0.7, 0.2, 0.1]
                )[0]
            else:
                status = PaymentStatus.PENDING
            
            payment_method = random.choice(self.payment_methods)
            provider = random.choice([p for p in PaymentProvider])
            
            payment = {
                'id': len(self.data['payments']) + 1,
                'user_id': reservation['user_id'],
                'reservation_id': reservation['id'],
                'amount': reservation['total_amount'],
                'currency': random.choice(self.currencies),
                'payment_method_type': payment_method,
                'provider': provider,
                'transaction_id': f"TXN{random.randint(10000000, 99999999)}",
                'status': status,
                'created_at': reservation['created_at'] + timedelta(minutes=random.randint(1, 60))
            }
            
            self.data['payments'].append(payment)
            payment_count += 1
            
            # Add transaction
            transaction = {
                'payment_id': payment['id'],
                'transaction_type': TransactionType.SALE,
                'amount': payment['amount'],
                'provider': provider,
                'provider_transaction_id': f"PROV{random.randint(1000000, 9999999)}",
                'status': status,
                'created_at': payment['created_at']
            }
            self.data['payment_transactions'].append(transaction)
        
        self.stats['payments'] = payment_count
        logger.info(f"Generated {payment_count} payments")
    
    def _generate_notifications(self) -> None:
        """Generate notifications."""
        logger.info("Generating notifications...")
        
        if not self.data['users']:
            return
        
        notification_count = 0
        notification_types = list(NotificationType)
        channels = list(NotificationChannel)
        priorities = list(NotificationPriority)
        
        # Generate notifications for each user
        for user in self.data['users']:
            # Number of notifications per user
            num_notifications = random.randint(0, 30)
            
            for i in range(num_notifications):
                notification_type = random.choice(notification_types)
                channel = random.choice(channels)
                
                # Create notification date (spread over history)
                days_ago = random.randint(0, self.history_days)
                created_at = datetime.utcnow() - timedelta(days=days_ago)
                
                # Determine status based on age
                if days_ago < 1:
                    status = random.choice([NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.PENDING])
                elif days_ago < 7:
                    status = random.choice([NotificationStatus.DELIVERED, NotificationStatus.OPENED])
                else:
                    status = random.choice([NotificationStatus.DELIVERED, NotificationStatus.OPENED, NotificationStatus.CLICKED])
                
                notification = {
                    'id': len(self.data['notifications']) + 1,
                    'user_id': user['id'],
                    'notification_type': notification_type,
                    'channel': channel,
                    'subject': f"Notification {i} - {notification_type.value}",
                    'content': self.fake.text(max_nb_chars=200),
                    'priority': random.choice(priorities),
                    'status': status,
                    'created_at': created_at,
                    'sent_at': created_at + timedelta(minutes=random.randint(1, 5)) if status != NotificationStatus.PENDING else None,
                    'delivered_at': created_at + timedelta(minutes=random.randint(5, 10)) if status in [NotificationStatus.DELIVERED, NotificationStatus.OPENED, NotificationStatus.CLICKED] else None,
                    'opened_at': created_at + timedelta(minutes=random.randint(10, 60)) if status in [NotificationStatus.OPENED, NotificationStatus.CLICKED] else None,
                    'clicked_at': created_at + timedelta(hours=random.randint(1, 24)) if status == NotificationStatus.CLICKED else None
                }
                
                self.data['notifications'].append(notification)
                notification_count += 1
        
        self.stats['notifications'] = notification_count
        logger.info(f"Generated {notification_count} notifications")
    
    def _generate_audit_logs(self) -> None:
        """Generate audit logs."""
        logger.info("Generating audit logs...")
        
        if not self.data['users']:
            return
        
        audit_count = 0
        actions = list(AuditAction)
        categories = list(AuditCategory)
        severities = list(AuditSeverity)
        resource_types = list(AuditResourceType)
        
        # Generate audit logs
        num_logs = min(self.num_users * 50, 10000)  # Cap at 10k logs
        
        for i in range(num_logs):
            user = random.choice(self.data['users']) if random.random() > 0.3 else None
            
            # Create log date (spread over history)
            days_ago = random.randint(0, self.history_days)
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            
            log = {
                'id': len(self.data['audit_logs']) + 1,
                'actor_id': user['id'] if user else None,
                'actor_email': user['email'] if user else 'system@parking.com',
                'action': random.choice(actions),
                'category': random.choice(categories),
                'resource_type': random.choice(resource_types),
                'resource_id': str(random.randint(1, 1000)) if random.random() > 0.3 else None,
                'severity': random.choice(severities),
                'status': random.choice(list(AuditStatus)),
                'details': {'message': self.fake.sentence()},
                'ip_address': self.fake.ipv4() if random.random() > 0.5 else None,
                'user_agent': self.fake.user_agent() if random.random() > 0.5 else None,
                'created_at': created_at
            }
            
            self.data['audit_logs'].append(log)
            audit_count += 1
        
        self.stats['audit_logs'] = audit_count
        logger.info(f"Generated {audit_count} audit logs")
    
    def _generate_additional_data(self) -> None:
        """Generate additional data like waitlist, maintenance, etc."""
        logger.info("Generating additional data...")
        
        # Generate waitlist entries
        self._generate_waitlist()
        
        # Generate maintenance records
        self._generate_maintenance()
        
        # Generate discounts
        self._generate_discounts()
        
        # Generate subscriptions
        self._generate_subscriptions()
    
    def _generate_waitlist(self) -> None:
        """Generate waitlist entries."""
        if not self.data['users'] or not self.data['parking_spots']:
            return
        
        num_waitlist = min(self.num_users * 2, 500)
        
        for i in range(num_waitlist):
            user = random.choice(self.data['users'])
            spot = random.choice(self.data['parking_spots'])
            
            desired_date = datetime.utcnow() + timedelta(days=random.randint(1, 30))
            
            waitlist = {
                'user_id': user['id'],
                'spot_id': spot['id'],
                'date_from': desired_date,
                'date_to': desired_date + timedelta(hours=random.randint(1, 4)),
                'status': random.choice([WaitlistStatus.ACTIVE, WaitlistStatus.NOTIFIED, WaitlistStatus.EXPIRED]),
                'position': i + 1,
                'created_at': desired_date - timedelta(days=random.randint(1, 7))
            }
            self.data['waitlist'].append(waitlist)
        
        logger.info(f"Generated {num_waitlist} waitlist entries")
    
    def _generate_maintenance(self) -> None:
        """Generate maintenance records."""
        if not self.data['parking_spots']:
            return
        
        num_maintenance = len(self.data['parking_spots']) // 20  # 5% of spots have maintenance
        
        maintenance_types = ['cleaning', 'repair', 'inspection', 'upgrade', 'painting', 'sensor_calibration']
        
        for i in range(num_maintenance):
            spot = random.choice(self.data['parking_spots'])
            
            start_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))
            end_date = start_date + timedelta(hours=random.randint(2, 48))
            
            status = 'completed' if end_date < datetime.utcnow() else random.choice(['scheduled', 'in_progress'])
            
            maintenance = {
                'spot_id': spot['id'],
                'maintenance_type': random.choice(maintenance_types),
                'started_at': start_date if status != 'scheduled' else None,
                'completed_at': end_date if status == 'completed' else None,
                'scheduled_start': start_date,
                'scheduled_end': end_date,
                'status': status,
                'notes': self.fake.sentence(),
                'created_at': start_date - timedelta(days=random.randint(1, 7))
            }
            self.data['spot_maintenance'].append(maintenance)
        
        logger.info(f"Generated {num_maintenance} maintenance records")
    
    def _generate_discounts(self) -> None:
        """Generate discounts and coupons."""
        num_discounts = 20
        
        discount_types = list(DiscountType)
        
        for i in range(num_discounts):
            discount_type = random.choice(discount_types)
            
            if discount_type == DiscountType.PERCENTAGE:
                value = random.uniform(5, 30)
            else:
                value = random.uniform(5, 50)
            
            valid_from = datetime.utcnow() - timedelta(days=random.randint(0, 30))
            valid_until = valid_from + timedelta(days=random.randint(30, 90))
            
            discount = {
                'code': self.fake.bothify(text='???-######').upper(),
                'description': self.fake.sentence(),
                'discount_type': discount_type,
                'discount_value': round(value, 2),
                'valid_from': valid_from,
                'valid_until': valid_until,
                'max_uses': random.randint(10, 1000),
                'used_count': random.randint(0, 50),
                'is_active': True,
                'created_at': valid_from - timedelta(days=random.randint(1, 10))
            }
            self.data['discounts'].append(discount)
        
        logger.info(f"Generated {num_discounts} discounts")
    
    def _generate_subscriptions(self) -> None:
        """Generate subscriptions."""
        # First create subscription plans
        plans = [
            {
                'name': 'Basic',
                'description': 'Basic monthly plan',
                'price': 29.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 10, 'discount': 5}
            },
            {
                'name': 'Premium',
                'description': 'Premium monthly plan',
                'price': 49.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 30, 'discount': 10, 'priority': True}
            },
            {
                'name': 'Business',
                'description': 'Business monthly plan',
                'price': 99.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {'max_reservations': 100, 'discount': 15, 'priority': True, 'dedicated': True}
            },
            {
                'name': 'Annual Premium',
                'description': 'Annual premium plan',
                'price': 499.99,
                'currency': 'USD',
                'interval': 'year',
                'features': {'max_reservations': 30, 'discount': 20, 'priority': True, 'two_months_free': True}
            }
        ]
        
        for plan in plans:
            plan['created_at'] = datetime.utcnow() - timedelta(days=self.history_days)
            self.data['subscription_plans'].append(plan)
        
        # Create subscriptions for users
        num_subscriptions = min(self.num_users // 3, 200)  # 33% of users have subscriptions
        
        for i in range(num_subscriptions):
            user = random.choice(self.data['users'])
            plan = random.choice(self.data['subscription_plans'])
            
            start_date = datetime.utcnow() - timedelta(days=random.randint(0, 180))
            
            # Determine end date based on interval
            if plan['interval'] == 'month':
                end_date = start_date + timedelta(days=30)
            else:
                end_date = start_date + timedelta(days=365)
            
            # Determine status
            now = datetime.utcnow()
            if end_date < now:
                status = SubscriptionStatus.CANCELED
            elif start_date > now:
                status = SubscriptionStatus.ACTIVE
            else:
                status = SubscriptionStatus.ACTIVE
            
            subscription = {
                'user_id': user['id'],
                'plan_id': i + 1,  # Simplified
                'status': status,
                'current_period_start': start_date,
                'current_period_end': end_date,
                'cancel_at_period_end': random.random() > 0.8,
                'created_at': start_date
            }
            self.data['subscriptions'].append(subscription)
        
        logger.info(f"Generated {num_subscriptions} subscriptions")


# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate test data for parking management system')
    
    # Data volume options
    parser.add_argument('--scale', type=int, default=1, help='Scale factor (1-100)')
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate')
    parser.add_argument('--vehicles', type=str, default='1-3', help='Vehicles per user range (min-max)')
    parser.add_argument('--reservations', type=str, default='5-20', help='Reservations per user range (min-max)')
    parser.add_argument('--days', type=int, default=180, help='Days of history to generate')
    parser.add_argument('--future', type=int, default=90, help='Days of future reservations')
    
    # Processing options
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for inserts')
    parser.add_argument('--clean', action='store_true', help='Clean existing data before generating')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--profile', action='store_true', help='Generate performance profile data')
    parser.add_argument('--anonymize', action='store_true', help='Anonymize personal data')
    
    # Output options
    parser.add_argument('--format', choices=['db', 'json', 'csv'], default='db', help='Output format')
    parser.add_argument('--output', help='Output file/directory')
    parser.add_argument('--db-url', help='Database URL (for db format)')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Parse vehicle range
    try:
        v_min, v_max = map(int, args.vehicles.split('-'))
        vehicles_per_user = (v_min, v_max)
    except:
        vehicles_per_user = (1, 3)
    
    # Parse reservation range
    try:
        r_min, r_max = map(int, args.reservations.split('-'))
        reservations_per_user = (r_min, r_max)
    except:
        reservations_per_user = (5, 20)
    
    # Create generator
    generator = TestDataGenerator(
        db_url=args.db_url,
        scale=args.scale,
        num_users=args.users,
        vehicles_per_user=vehicles_per_user,
        reservations_per_user=reservations_per_user,
        history_days=args.days,
        future_days=args.future,
        batch_size=args.batch_size,
        clean=args.clean,
        output_format=args.format,
        output_path=args.output,
        seed=args.seed,
        anonymize=args.anonymize
    )
    
    # Generate data
    try:
        stats = generator.generate_all()
        
        print("\n" + "="*60)
        print("TEST DATA GENERATION COMPLETED")
        print("="*60)
        print(f"Users: {stats['users']:,}")
        print(f"Vehicles: {stats['vehicles']:,}")
        print(f"Reservations: {stats['reservations']:,}")
        print(f"Payments: {stats['payments']:,}")
        print(f"Notifications: {stats['notifications']:,}")
        print(f"Audit Logs: {stats['audit_logs']:,}")
        print(f"Duration: {(stats['end_time'] - stats['start_time']).total_seconds():.2f}s")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Test data generation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()