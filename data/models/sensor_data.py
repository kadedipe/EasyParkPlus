# parking-management/data/migrations/models/sensor_data.py

"""
Sensor Data model for parking management system.

This module defines the SensorData model and related classes for managing
IoT sensors, real-time readings, calibration data, device management,
and sensor analytics.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET, MACADDR
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import math
import statistics
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import json

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class SensorType(str, enum.Enum):
    """Enum for sensor types."""
    ULTRASONIC = 'ultrasonic'
    INFRARED = 'infrared'
    MAGNETIC = 'magnetic'
    INDUCTIVE_LOOP = 'inductive_loop'
    RADAR = 'radar'
    LIDAR = 'lidar'
    CAMERA = 'camera'
    THERMAL = 'thermal'
    PRESSURE = 'pressure'
    PROXIMITY = 'proximity'
    LASER = 'laser'
    MICROWAVE = 'microwave'
    ACOUSTIC = 'acoustic'
    SEISMIC = 'seismic'
    ENVIRONMENTAL = 'environmental'


class SensorStatus(str, enum.Enum):
    """Enum for sensor status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    INSTALLING = 'installing'
    CALIBRATING = 'calibrating'
    MAINTENANCE = 'maintenance'
    FAULTY = 'faulty'
    OFFLINE = 'offline'
    RETIRED = 'retired'
    BATTERY_LOW = 'battery_low'
    COMMUNICATION_ERROR = 'communication_error'


class SensorManufacturer(str, enum.Enum):
    """Enum for sensor manufacturers."""
    BOSCH = 'bosch'
    HONEYWELL = 'honeywell'
    SIEMENS = 'siemens'
    OMRON = 'omron'
    SICK = 'sick'
    IFM = 'ifm'
    PEPPERL_FUCHS = 'pepperl_fuchs'
    BANNER = 'banner'
    KEYENCE = 'keyence'
    TURCK = 'turck'
    BALLUFF = 'balluff'
    CONTRINEX = 'contrinex'
    OTHER = 'other'


class CommunicationProtocol(str, enum.Enum):
    """Enum for communication protocols."""
    MQTT = 'mqtt'
    HTTP = 'http'
    HTTPS = 'https'
    COAP = 'coap'
    LORAWAN = 'lorawan'
    ZIGBEE = 'zigbee'
    Z_WAVE = 'z_wave'
    BLUETOOTH = 'bluetooth'
    BLE = 'ble'
    WIFI = 'wifi'
    ETHERNET = 'ethernet'
    RS485 = 'rs485'
    RS232 = 'rs232'
    CAN_BUS = 'can_bus'
    MODBUS = 'modbus'
    PROFIBUS = 'profibus'
    PROFINET = 'profinet'


class PowerSource(str, enum.Enum):
    """Enum for power sources."""
    BATTERY = 'battery'
    SOLAR = 'solar'
    MAINS = 'mains'
    POE = 'poe'
    USB = 'usb'
    WIRELESS_CHARGING = 'wireless_charging'
    ENERGY_HARVESTING = 'energy_harvesting'


class MeasurementUnit(str, enum.Enum):
    """Enum for measurement units."""
    CENTIMETERS = 'cm'
    METERS = 'm'
    MILLIMETERS = 'mm'
    INCHES = 'in'
    FEET = 'ft'
    KILOGRAMS = 'kg'
    POUNDS = 'lb'
    CELSIUS = 'c'
    FAHRENHEIT = 'f'
    KELVIN = 'k'
    PERCENT = '%'
    VOLTS = 'v'
    AMPS = 'a'
    WATTS = 'w'
    KWH = 'kwh'
    LUX = 'lux'
    DECIBEL = 'db'
    HERTZ = 'hz'
    PASCAL = 'pa'
    BAR = 'bar'
    PSI = 'psi'
    RPM = 'rpm'
    DEGREES = 'deg'


class DataQuality(str, enum.Enum):
    """Enum for data quality."""
    EXCELLENT = 'excellent'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    UNRELIABLE = 'unreliable'
    INVALID = 'invalid'


class CalibrationStatus(str, enum.Enum):
    """Enum for calibration status."""
    CALIBRATED = 'calibrated'
    NEEDS_CALIBRATION = 'needs_calibration'
    CALIBRATING = 'calibrating'
    CALIBRATION_FAILED = 'calibration_failed'
    FACTORY_CALIBRATED = 'factory_calibrated'
    FIELD_CALIBRATED = 'field_calibrated'


class AlertSeverity(str, enum.Enum):
    """Enum for alert severity."""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class Sensor(Base):
    """
    Main sensor model for IoT devices.
    
    Represents physical sensors installed in parking spots,
    with comprehensive tracking of specifications, status, and history.
    """
    
    __tablename__ = 'sensors'
    __table_args__ = (
        # Primary indexes
        Index('ix_sensors_device_id', 'device_id', unique=True),
        Index('ix_sensors_serial_number', 'serial_number', unique=True),
        Index('ix_sensors_mac_address', 'mac_address', unique=True),
        
        # Foreign key indexes
        Index('ix_sensors_spot_id', 'spot_id'),
        Index('ix_sensors_zone_id', 'zone_id'),
        
        # Status indexes
        Index('ix_sensors_type', 'sensor_type'),
        Index('ix_sensors_status', 'status'),
        Index('ix_sensors_manufacturer', 'manufacturer'),
        
        # Time-based indexes
        Index('ix_sensors_last_reading', 'last_reading_at'),
        Index('ix_sensors_last_communication', 'last_communication_at'),
        Index('ix_sensors_installation_date', 'installation_date'),
        
        # Composite indexes
        Index('ix_sensors_spot_type', 'spot_id', 'sensor_type'),
        Index('ix_sensors_status_type', 'status', 'sensor_type'),
        
        # Partial indexes
        Index('ix_sensors_active', 'status', postgresql_where=text("status = 'active'")),
        Index('ix_sensors_faulty', 'status', postgresql_where=text("status IN ('faulty', 'battery_low', 'communication_error')")),
        
        # Check constraints
        CheckConstraint(
            "sensor_type IN ('ultrasonic', 'infrared', 'magnetic', 'inductive_loop', 'radar', "
            "'lidar', 'camera', 'thermal', 'pressure', 'proximity', 'laser', 'microwave', "
            "'acoustic', 'seismic', 'environmental')",
            name='ck_sensors_type'
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'installing', 'calibrating', 'maintenance', "
            "'faulty', 'offline', 'retired', 'battery_low', 'communication_error')",
            name='ck_sensors_status'
        ),
        CheckConstraint(
            "battery_level >= 0 AND battery_level <= 100",
            name='ck_sensors_battery_level'
        ),
        CheckConstraint(
            "signal_strength >= -100 AND signal_strength <= 0",
            name='ck_sensors_signal_strength'
        ),
        
        # Table comment
        {'comment': 'Main sensor model for IoT devices'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # SENSOR IDENTIFICATION
    # =========================================================================
    device_id = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Unique device identifier'
    )
    
    name = Column(
        String(255),
        comment='Human-readable sensor name'
    )
    
    description = Column(
        Text,
        comment='Sensor description'
    )
    
    sensor_type = Column(
        String(20),
        nullable=False,
        comment='Type of sensor'
    )
    
    # =========================================================================
    # LOCATION
    # =========================================================================
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='SET NULL'),
        comment='Associated parking spot'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='SET NULL'),
        comment='Associated parking zone'
    )
    
    location_description = Column(
        Text,
        comment='Physical location description'
    )
    
    latitude = Column(
        Numeric(10, 8),
        comment='Latitude coordinate'
    )
    
    longitude = Column(
        Numeric(11, 8),
        comment='Longitude coordinate'
    )
    
    altitude_meters = Column(
        Float,
        comment='Altitude in meters'
    )
    
    # =========================================================================
    # MANUFACTURING
    # =========================================================================
    manufacturer = Column(
        String(50),
        comment='Sensor manufacturer'
    )
    
    model = Column(
        String(100),
        comment='Sensor model'
    )
    
    serial_number = Column(
        String(100),
        unique=True,
        comment='Manufacturer serial number'
    )
    
    hardware_version = Column(
        String(50),
        comment='Hardware version'
    )
    
    firmware_version = Column(
        String(50),
        comment='Current firmware version'
    )
    
    firmware_history = Column(
        JSONB,
        comment='Firmware update history'
    )
    
    manufacturing_date = Column(
        Date,
        comment='Date of manufacture'
    )
    
    warranty_expiry = Column(
        Date,
        comment='Warranty expiration date'
    )
    
    # =========================================================================
    # NETWORK
    # =========================================================================
    ip_address = Column(
        String(45),
        comment='IP address (IPv4 or IPv6)'
    )
    
    mac_address = Column(
        String(17),
        unique=True,
        comment='MAC address'
    )
    
    communication_protocol = Column(
        String(20),
        comment='Communication protocol'
    )
    
    mqtt_topic = Column(
        String(255),
        comment='MQTT topic for sensor data'
    )
    
    api_endpoint = Column(
        String(500),
        comment='API endpoint for HTTP sensors'
    )
    
    # =========================================================================
    # POWER
    # =========================================================================
    power_source = Column(
        String(20),
        comment='Power source type'
    )
    
    battery_level = Column(
        Integer,
        comment='Battery level percentage'
    )
    
    battery_voltage = Column(
        Float,
        comment='Battery voltage'
    )
    
    battery_last_changed = Column(
        DateTime(timezone=True),
        comment='When battery was last changed'
    )
    
    power_consumption_watts = Column(
        Float,
        comment='Power consumption in watts'
    )
    
    solar_panel = Column(
        Boolean,
        server_default='false',
        comment='Whether sensor has solar panel'
    )
    
    # =========================================================================
    # SENSOR SPECIFICATIONS
    # =========================================================================
    measurement_unit = Column(
        String(20),
        comment='Primary measurement unit'
    )
    
    measurement_range_min = Column(
        Float,
        comment='Minimum measurable value'
    )
    
    measurement_range_max = Column(
        Float,
        comment='Maximum measurable value'
    )
    
    accuracy = Column(
        Float,
        comment='Accuracy (percentage or absolute)'
    )
    
    precision = Column(
        Float,
        comment='Precision/repeatability'
    )
    
    resolution = Column(
        Float,
        comment='Measurement resolution'
    )
    
    sampling_rate_hz = Column(
        Float,
        comment='Sampling rate in Hz'
    )
    
    response_time_ms = Column(
        Integer,
        comment='Response time in milliseconds'
    )
    
    operating_temperature_min = Column(
        Float,
        comment='Minimum operating temperature'
    )
    
    operating_temperature_max = Column(
        Float,
        comment='Maximum operating temperature'
    )
    
    ingress_protection = Column(
        String(10),
        comment='IP rating (e.g., IP67)'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='active',
        comment='Current sensor status'
    )
    
    is_online = Column(
        Boolean,
        server_default='true',
        comment='Whether sensor is online'
    )
    
    last_reading_at = Column(
        DateTime(timezone=True),
        comment='Timestamp of last reading'
    )
    
    last_communication_at = Column(
        DateTime(timezone=True),
        comment='Timestamp of last communication'
    )
    
    last_value = Column(
        Float,
        comment='Last measured value'
    )
    
    last_value_quality = Column(
        String(20),
        comment='Quality of last reading'
    )
    
    signal_strength = Column(
        Integer,
        comment='Signal strength in dBm'
    )
    
    error_count = Column(
        Integer,
        server_default='0',
        comment='Total error count'
    )
    
    last_error = Column(
        Text,
        comment='Last error message'
    )
    
    last_error_at = Column(
        DateTime(timezone=True),
        comment='Timestamp of last error'
    )
    
    # =========================================================================
    # CALIBRATION
    # =========================================================================
    calibration_status = Column(
        String(20),
        server_default='factory_calibrated',
        comment='Calibration status'
    )
    
    calibration_date = Column(
        DateTime(timezone=True),
        comment='Last calibration date'
    )
    
    calibration_due_date = Column(
        Date,
        comment='Next calibration due date'
    )
    
    calibration_offset = Column(
        Float,
        comment='Calibration offset value'
    )
    
    calibration_scale = Column(
        Float,
        server_default='1.0',
        comment='Calibration scale factor'
    )
    
    calibration_coefficients = Column(
        JSONB,
        comment='Calibration polynomial coefficients'
    )
    
    calibration_certificate = Column(
        String(500),
        comment='URL to calibration certificate'
    )
    
    # =========================================================================
    # INSTALLATION
    # =========================================================================
    installation_date = Column(
        DateTime(timezone=True),
        comment='When sensor was installed'
    )
    
    installed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who installed sensor'
    )
    
    installation_notes = Column(
        Text,
        comment='Installation notes'
    )
    
    maintenance_date = Column(
        DateTime(timezone=True),
        comment='Last maintenance date'
    )
    
    maintenance_due_date = Column(
        Date,
        comment='Next maintenance due date'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    tags = Column(
        ARRAY(String(50)),
        comment='Custom tags'
    )
    
    configuration = Column(
        JSONB,
        server_default='{}',
        comment='Sensor configuration parameters'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this record'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    spot = relationship(
        'ParkingSpot',
        foreign_keys=[spot_id],
        back_populates='sensors',
        comment='Associated parking spot'
    )
    
    zone = relationship(
        'ParkingZone',
        foreign_keys=[zone_id],
        comment='Associated parking zone'
    )
    
    installer = relationship(
        'User',
        foreign_keys=[installed_by],
        comment='User who installed sensor'
    )
    
    readings = relationship(
        'SensorReading',
        back_populates='sensor',
        cascade='all, delete-orphan',
        order_by='desc(SensorReading.timestamp)',
        comment='Sensor readings'
    )
    
    alerts = relationship(
        'SensorAlert',
        back_populates='sensor',
        cascade='all, delete-orphan',
        order_by='desc(SensorAlert.created_at)',
        comment='Sensor alerts'
    )
    
    maintenance_records = relationship(
        'SensorMaintenance',
        back_populates='sensor',
        cascade='all, delete-orphan',
        order_by='desc(SensorMaintenance.maintenance_date)',
        comment='Maintenance records'
    )
    
    calibration_records = relationship(
        'SensorCalibration',
        back_populates='sensor',
        cascade='all, delete-orphan',
        order_by='desc(SensorCalibration.calibration_date)',
        comment='Calibration records'
    )
    
    diagnostics = relationship(
        'SensorDiagnostic',
        back_populates='sensor',
        cascade='all, delete-orphan',
        order_by='desc(SensorDiagnostic.timestamp)',
        comment='Diagnostic data'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if sensor is active."""
        return self.status == 'active' and self.is_online
    
    @hybrid_property
    def needs_maintenance(self) -> bool:
        """Check if sensor needs maintenance."""
        if self.maintenance_due_date:
            return date.today() >= self.maintenance_due_date
        return False
    
    @hybrid_property
    def needs_calibration(self) -> bool:
        """Check if sensor needs calibration."""
        if self.calibration_due_date:
            return date.today() >= self.calibration_due_date
        return self.calibration_status == 'needs_calibration'
    
    @hybrid_property
    def battery_low(self) -> bool:
        """Check if battery is low."""
        if self.battery_level is not None:
            return self.battery_level < 20
        return False
    
    @hybrid_property
    def uptime_days(self) -> Optional[float]:
        """Calculate uptime in days."""
        if self.installation_date:
            delta = datetime.now(self.installation_date.tzinfo) - self.installation_date
            return delta.total_seconds() / 86400
        return None
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('device_id')
    def validate_device_id(self, key, device_id):
        """Validate device ID format."""
        if not device_id or len(device_id) < 3:
            raise ValueError('Device ID must be at least 3 characters')
        return device_id
    
    @validates('ip_address')
    def validate_ip(self, key, ip):
        """Validate IP address format."""
        if ip:
            import ipaddress
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise ValueError(f'Invalid IP address: {ip}')
        return ip
    
    @validates('mac_address')
    def validate_mac(self, key, mac):
        """Validate MAC address format."""
        if mac:
            import re
            if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac):
                raise ValueError(f'Invalid MAC address: {mac}')
        return mac.upper() if mac else mac
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def record_reading(
        self,
        value: float,
        timestamp: Optional[datetime] = None,
        quality: str = 'good',
        metadata: Optional[Dict] = None
    ) -> 'SensorReading':
        """
        Record a sensor reading.
        
        Args:
            value: Measured value
            timestamp: Reading timestamp (defaults to now)
            quality: Data quality
            metadata: Additional reading metadata
            
        Returns:
            Created SensorReading instance
        """
        from models.sensor_data import SensorReading
        
        reading = SensorReading(
            sensor_id=self.id,
            value=value,
            timestamp=timestamp or datetime.now(),
            quality=quality,
            metadata=metadata
        )
        
        object_session(self).add(reading)
        
        # Update sensor status
        self.last_reading_at = reading.timestamp
        self.last_value = value
        self.last_value_quality = quality
        self.last_communication_at = reading.timestamp
        
        return reading
    
    def record_error(self, error_message: str) -> 'SensorAlert':
        """
        Record a sensor error.
        
        Args:
            error_message: Error description
            
        Returns:
            Created SensorAlert instance
        """
        from models.sensor_data import SensorAlert
        
        alert = SensorAlert(
            sensor_id=self.id,
            severity='error',
            message=error_message,
            alert_type='error',
            timestamp=datetime.now()
        )
        
        object_session(self).add(alert)
        
        self.error_count += 1
        self.last_error = error_message
        self.last_error_at = datetime.now()
        self.status = 'faulty'
        
        return alert
    
    def update_firmware(self, new_version: str, user_id: Optional[uuid.UUID] = None) -> None:
        """Update sensor firmware."""
        firmware_entry = {
            'version': new_version,
            'updated_at': datetime.now().isoformat(),
            'updated_by': str(user_id) if user_id else None
        }
        
        if not self.firmware_history:
            self.firmware_history = []
        
        self.firmware_history.append(firmware_entry)
        self.firmware_version = new_version
        self.updated_by = user_id
        self.updated_at = datetime.now()
    
    def apply_calibration(
        self,
        offset: float = 0.0,
        scale: float = 1.0,
        coefficients: Optional[Dict] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Apply calibration to sensor.
        
        Args:
            offset: Calibration offset
            scale: Calibration scale factor
            coefficients: Polynomial coefficients
            user_id: User performing calibration
        """
        from models.sensor_data import SensorCalibration
        
        calibration = SensorCalibration(
            sensor_id=self.id,
            calibration_date=datetime.now(),
            calibrated_by=user_id,
            old_offset=self.calibration_offset,
            new_offset=offset,
            old_scale=self.calibration_scale,
            new_scale=scale,
            old_coefficients=self.calibration_coefficients,
            new_coefficients=coefficients,
            notes='Applied calibration'
        )
        
        object_session(self).add(calibration)
        
        self.calibration_offset = offset
        self.calibration_scale = scale
        self.calibration_coefficients = coefficients
        self.calibration_status = 'calibrated'
        self.calibration_date = datetime.now()
        self.updated_by = user_id
    
    def get_calibrated_value(self, raw_value: float) -> float:
        """
        Apply calibration to raw sensor value.
        
        Args:
            raw_value: Raw sensor reading
            
        Returns:
            Calibrated value
        """
        if self.calibration_coefficients:
            # Polynomial calibration
            value = 0
            for i, coeff in enumerate(self.calibration_coefficients):
                value += coeff * (raw_value ** i)
            return value
        else:
            # Linear calibration
            return (raw_value * self.calibration_scale) + self.calibration_offset
    
    def check_health(self) -> Dict[str, Any]:
        """
        Perform health check on sensor.
        
        Returns:
            Health check results
        """
        health = {
            'sensor_id': str(self.id),
            'device_id': self.device_id,
            'status': self.status,
            'is_online': self.is_online,
            'last_communication': self.last_communication_at.isoformat() if self.last_communication_at else None,
            'last_reading': self.last_reading_at.isoformat() if self.last_reading_at else None,
            'battery_level': self.battery_level,
            'battery_low': self.battery_low,
            'signal_strength': self.signal_strength,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'needs_maintenance': self.needs_maintenance,
            'needs_calibration': self.needs_calibration,
            'issues': []
        }
        
        # Check for issues
        if not self.is_online:
            health['issues'].append('Sensor is offline')
        
        if self.battery_low:
            health['issues'].append(f'Battery low ({self.battery_level}%)')
        
        if self.needs_maintenance:
            health['issues'].append('Maintenance due')
        
        if self.needs_calibration:
            health['issues'].append('Calibration due')
        
        if self.error_count > 10:
            health['issues'].append(f'High error count ({self.error_count})')
        
        if self.status == 'faulty':
            health['issues'].append('Sensor is faulty')
        
        health['health_score'] = self._calculate_health_score(health)
        
        return health
    
    def _calculate_health_score(self, health: Dict[str, Any]) -> int:
        """Calculate overall health score (0-100)."""
        score = 100
        
        # Deduct for issues
        if not health['is_online']:
            score -= 30
        
        if health['battery_low']:
            score -= 20
        
        if health['needs_maintenance']:
            score -= 15
        
        if health['needs_calibration']:
            score -= 10
        
        if health['error_count'] > 0:
            score -= min(20, health['error_count'] * 2)
        
        if health['signal_strength'] and health['signal_strength'] < -80:
            score -= 10
        
        return max(0, score)
    
    def to_dict(self, include_readings: bool = False) -> Dict[str, Any]:
        """Convert sensor to dictionary."""
        data = {
            'id': str(self.id),
            'device_id': self.device_id,
            'name': self.name,
            'description': self.description,
            'sensor_type': self.sensor_type,
            'location': {
                'spot_id': str(self.spot_id) if self.spot_id else None,
                'zone_id': str(self.zone_id) if self.zone_id else None,
                'description': self.location_description,
                'coordinates': {
                    'latitude': float(self.latitude) if self.latitude else None,
                    'longitude': float(self.longitude) if self.longitude else None,
                    'altitude': self.altitude_meters
                }
            },
            'manufacturing': {
                'manufacturer': self.manufacturer,
                'model': self.model,
                'serial_number': self.serial_number,
                'hardware_version': self.hardware_version,
                'firmware_version': self.firmware_version,
                'manufacturing_date': self.manufacturing_date.isoformat() if self.manufacturing_date else None,
                'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None
            },
            'network': {
                'ip_address': self.ip_address,
                'mac_address': self.mac_address,
                'protocol': self.communication_protocol,
                'mqtt_topic': self.mqtt_topic,
                'signal_strength': self.signal_strength
            },
            'power': {
                'source': self.power_source,
                'battery_level': self.battery_level,
                'battery_voltage': self.battery_voltage,
                'battery_low': self.battery_low,
                'power_consumption_watts': self.power_consumption_watts,
                'solar_panel': self.solar_panel
            },
            'specifications': {
                'measurement_unit': self.measurement_unit,
                'range': {
                    'min': self.measurement_range_min,
                    'max': self.measurement_range_max
                },
                'accuracy': self.accuracy,
                'precision': self.precision,
                'resolution': self.resolution,
                'sampling_rate_hz': self.sampling_rate_hz,
                'response_time_ms': self.response_time_ms,
                'operating_temperature': {
                    'min': self.operating_temperature_min,
                    'max': self.operating_temperature_max
                },
                'ingress_protection': self.ingress_protection
            },
            'status': {
                'current': self.status,
                'is_online': self.is_online,
                'is_active': self.is_active,
                'last_reading': self.last_reading_at.isoformat() if self.last_reading_at else None,
                'last_communication': self.last_communication_at.isoformat() if self.last_communication_at else None,
                'last_value': self.last_value,
                'last_value_quality': self.last_value_quality,
                'error_count': self.error_count,
                'last_error': self.last_error,
                'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None
            },
            'calibration': {
                'status': self.calibration_status,
                'last_calibration': self.calibration_date.isoformat() if self.calibration_date else None,
                'due_date': self.calibration_due_date.isoformat() if self.calibration_due_date else None,
                'needs_calibration': self.needs_calibration,
                'offset': self.calibration_offset,
                'scale': self.calibration_scale
            },
            'maintenance': {
                'installation_date': self.installation_date.isoformat() if self.installation_date else None,
                'last_maintenance': self.maintenance_date.isoformat() if self.maintenance_date else None,
                'due_date': self.maintenance_due_date.isoformat() if self.maintenance_due_date else None,
                'needs_maintenance': self.needs_maintenance,
                'uptime_days': self.uptime_days
            },
            'tags': self.tags,
            'configuration': self.configuration,
            'health_score': self._calculate_health_score(self.check_health()),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_readings:
            data['recent_readings'] = [r.to_dict() for r in self.readings[:10]] if self.readings else []
        
        return data
    
    def __repr__(self) -> str:
        return f"<Sensor(id={self.id}, device_id={self.device_id}, type={self.sensor_type})>"


class SensorReading(Base):
    """
    Individual sensor readings.
    
    Stores time-series data from sensors with quality metrics.
    """
    
    __tablename__ = 'sensor_readings'
    __table_args__ = (
        Index('ix_sensor_readings_sensor', 'sensor_id'),
        Index('ix_sensor_readings_timestamp', 'timestamp'),
        Index('ix_sensor_readings_sensor_time', 'sensor_id', 'timestamp'),
        Index('ix_sensor_readings_quality', 'quality'),
        
        # Check constraints
        CheckConstraint(
            "quality IN ('excellent', 'good', 'fair', 'poor', 'unreliable', 'invalid')",
            name='ck_sensor_readings_quality'
        ),
        
        # Table comment
        {'comment': 'Individual sensor readings'},
        
        # Partition by month for large datasets
        postgresql_partition_by='RANGE (timestamp)',
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # READING DATA
    # =========================================================================
    value = Column(
        Float,
        nullable=False,
        comment='Measured value'
    )
    
    calibrated_value = Column(
        Float,
        comment='Calibrated value'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Reading timestamp'
    )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    quality = Column(
        String(20),
        nullable=False,
        server_default='good',
        comment='Data quality assessment'
    )
    
    confidence = Column(
        Float,
        comment='Confidence level (0-1)'
    )
    
    signal_strength = Column(
        Integer,
        comment='Signal strength at reading time'
    )
    
    temperature = Column(
        Float,
        comment='Temperature at reading time'
    )
    
    # =========================================================================
    # PROCESSING
    # =========================================================================
    is_processed = Column(
        Boolean,
        server_default='false',
        comment='Whether reading has been processed'
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        comment='When reading was processed'
    )
    
    processing_result = Column(
        JSONB,
        comment='Processing results'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor', back_populates='readings')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if reading is valid."""
        return self.quality not in ['invalid', 'unreliable']
    
    def apply_calibration(self, sensor: Sensor) -> None:
        """Apply sensor calibration to reading."""
        if sensor:
            self.calibrated_value = sensor.get_calibrated_value(self.value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reading to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'value': self.value,
            'calibrated_value': self.calibrated_value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'quality': self.quality,
            'confidence': self.confidence,
            'signal_strength': self.signal_strength,
            'temperature': self.temperature,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorReading(id={self.id}, sensor={self.sensor_id}, value={self.value})>"


class SensorAlert(Base):
    """
    Alerts generated from sensor data.
    
    Tracks alerts, warnings, and errors from sensors.
    """
    
    __tablename__ = 'sensor_alerts'
    __table_args__ = (
        Index('ix_sensor_alerts_sensor', 'sensor_id'),
        Index('ix_sensor_alerts_timestamp', 'timestamp'),
        Index('ix_sensor_alerts_severity', 'severity'),
        Index('ix_sensor_alerts_resolved', 'resolved_at'),
        
        # Check constraints
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name='ck_sensor_alerts_severity'
        ),
        
        # Table comment
        {'comment': 'Alerts from sensors'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # ALERT DETAILS
    # =========================================================================
    severity = Column(
        String(20),
        nullable=False,
        comment='Alert severity'
    )
    
    alert_type = Column(
        String(50),
        nullable=False,
        comment='Type of alert'
    )
    
    message = Column(
        Text,
        nullable=False,
        comment='Alert message'
    )
    
    details = Column(
        JSONB,
        comment='Additional details'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When alert occurred'
    )
    
    # =========================================================================
    # RESOLUTION
    # =========================================================================
    is_resolved = Column(
        Boolean,
        server_default='false',
        comment='Whether alert is resolved'
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        comment='When alert was resolved'
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who resolved alert'
    )
    
    resolution_notes = Column(
        Text,
        comment='Resolution notes'
    )
    
    # =========================================================================
    # ACKNOWLEDGMENT
    # =========================================================================
    acknowledged = Column(
        Boolean,
        server_default='false',
        comment='Whether alert has been acknowledged'
    )
    
    acknowledged_at = Column(
        DateTime(timezone=True),
        comment='When alert was acknowledged'
    )
    
    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who acknowledged alert'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor', back_populates='alerts')
    resolver = relationship('User', foreign_keys=[resolved_by])
    acknowledger = relationship('User', foreign_keys=[acknowledged_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def acknowledge(self, user_id: uuid.UUID) -> None:
        """Acknowledge alert."""
        self.acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user_id
    
    def resolve(self, user_id: uuid.UUID, notes: Optional[str] = None) -> None:
        """Resolve alert."""
        self.is_resolved = True
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'severity': self.severity,
            'alert_type': self.alert_type,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_resolved': self.is_resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': str(self.resolved_by) if self.resolved_by else None,
            'resolution_notes': self.resolution_notes,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorAlert(id={self.id}, severity={self.severity}, type={self.alert_type})>"


class SensorMaintenance(Base):
    """
    Maintenance records for sensors.
    
    Tracks all maintenance activities performed on sensors.
    """
    
    __tablename__ = 'sensor_maintenance'
    __table_args__ = (
        Index('ix_sensor_maintenance_sensor', 'sensor_id'),
        Index('ix_sensor_maintenance_date', 'maintenance_date'),
        Index('ix_sensor_maintenance_type', 'maintenance_type'),
        
        # Table comment
        {'comment': 'Maintenance records for sensors'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # MAINTENANCE DETAILS
    # =========================================================================
    maintenance_type = Column(
        String(50),
        nullable=False,
        comment='Type of maintenance'
    )
    
    description = Column(
        Text,
        comment='Maintenance description'
    )
    
    maintenance_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When maintenance was performed'
    )
    
    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who performed maintenance'
    )
    
    # =========================================================================
    # PARTS
    # =========================================================================
    parts_replaced = Column(
        JSONB,
        comment='Parts that were replaced'
    )
    
    parts_cost = Column(
        Numeric(10, 2),
        comment='Cost of parts'
    )
    
    # =========================================================================
    # LABOR
    # =========================================================================
    labor_hours = Column(
        Float,
        comment='Labor hours'
    )
    
    labor_cost = Column(
        Numeric(10, 2),
        comment='Cost of labor'
    )
    
    # =========================================================================
    # TOTAL COST
    # =========================================================================
    total_cost = Column(
        Numeric(10, 2),
        comment='Total maintenance cost'
    )
    
    # =========================================================================
    # OUTCOME
    # =========================================================================
    outcome = Column(
        String(20),
        comment='Maintenance outcome (successful, failed, partial)'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    follow_up_required = Column(
        Boolean,
        server_default='false',
        comment='Whether follow-up is required'
    )
    
    follow_up_date = Column(
        DateTime(timezone=True),
        comment='Follow-up date'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor', back_populates='maintenance_records')
    maintainer = relationship('User', foreign_keys=[performed_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert maintenance record to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'maintenance_date': self.maintenance_date.isoformat() if self.maintenance_date else None,
            'performed_by': str(self.performed_by) if self.performed_by else None,
            'parts_replaced': self.parts_replaced,
            'parts_cost': float(self.parts_cost) if self.parts_cost else None,
            'labor_hours': self.labor_hours,
            'labor_cost': float(self.labor_cost) if self.labor_cost else None,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'outcome': self.outcome,
            'notes': self.notes,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorMaintenance(id={self.id}, type={self.maintenance_type})>"


class SensorCalibration(Base):
    """
    Calibration records for sensors.
    
    Tracks calibration history and parameters.
    """
    
    __tablename__ = 'sensor_calibration'
    __table_args__ = (
        Index('ix_sensor_calibration_sensor', 'sensor_id'),
        Index('ix_sensor_calibration_date', 'calibration_date'),
        
        # Table comment
        {'comment': 'Calibration records for sensors'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # CALIBRATION DETAILS
    # =========================================================================
    calibration_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When calibration was performed'
    )
    
    calibrated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who performed calibration'
    )
    
    # =========================================================================
    # CALIBRATION VALUES
    # =========================================================================
    old_offset = Column(
        Float,
        comment='Previous offset value'
    )
    
    new_offset = Column(
        Float,
        comment='New offset value'
    )
    
    old_scale = Column(
        Float,
        comment='Previous scale factor'
    )
    
    new_scale = Column(
        Float,
        comment='New scale factor'
    )
    
    old_coefficients = Column(
        JSONB,
        comment='Previous polynomial coefficients'
    )
    
    new_coefficients = Column(
        JSONB,
        comment='New polynomial coefficients'
    )
    
    # =========================================================================
    # CALIBRATION DATA
    # =========================================================================
    calibration_points = Column(
        JSONB,
        comment='Calibration points used'
    )
    
    reference_standard = Column(
        String(255),
        comment='Reference standard used'
    )
    
    traceability = Column(
        String(255),
        comment='Calibration traceability'
    )
    
    uncertainty = Column(
        Float,
        comment='Calibration uncertainty'
    )
    
    # =========================================================================
    # CERTIFICATE
    # =========================================================================
    certificate_number = Column(
        String(100),
        comment='Calibration certificate number'
    )
    
    certificate_url = Column(
        String(500),
        comment='URL to calibration certificate'
    )
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor', back_populates='calibration_records')
    calibrator = relationship('User', foreign_keys=[calibrated_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert calibration record to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'calibration_date': self.calibration_date.isoformat() if self.calibration_date else None,
            'calibrated_by': str(self.calibrated_by) if self.calibrated_by else None,
            'old_offset': self.old_offset,
            'new_offset': self.new_offset,
            'old_scale': self.old_scale,
            'new_scale': self.new_scale,
            'calibration_points': self.calibration_points,
            'reference_standard': self.reference_standard,
            'traceability': self.traceability,
            'uncertainty': self.uncertainty,
            'certificate_number': self.certificate_number,
            'certificate_url': self.certificate_url,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorCalibration(id={self.id}, date={self.calibration_date})>"


class SensorDiagnostic(Base):
    """
    Diagnostic data from sensors.
    
    Stores detailed diagnostic information for troubleshooting.
    """
    
    __tablename__ = 'sensor_diagnostics'
    __table_args__ = (
        Index('ix_sensor_diagnostics_sensor', 'sensor_id'),
        Index('ix_sensor_diagnostics_timestamp', 'timestamp'),
        
        # Table comment
        {'comment': 'Diagnostic data from sensors'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # DIAGNOSTIC DATA
    # =========================================================================
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Diagnostic timestamp'
    )
    
    diagnostic_type = Column(
        String(50),
        nullable=False,
        comment='Type of diagnostic'
    )
    
    data = Column(
        JSONB,
        nullable=False,
        comment='Diagnostic data'
    )
    
    # =========================================================================
    # SYSTEM METRICS
    # =========================================================================
    cpu_usage = Column(
        Float,
        comment='CPU usage percentage'
    )
    
    memory_usage = Column(
        Float,
        comment='Memory usage percentage'
    )
    
    storage_usage = Column(
        Float,
        comment='Storage usage percentage'
    )
    
    uptime_seconds = Column(
        Integer,
        comment='Device uptime in seconds'
    )
    
    # =========================================================================
    # NETWORK METRICS
    # =========================================================================
    network_latency_ms = Column(
        Float,
        comment='Network latency in milliseconds'
    )
    
    packets_sent = Column(
        Integer,
        comment='Packets sent'
    )
    
    packets_received = Column(
        Integer,
        comment='Packets received'
    )
    
    packets_lost = Column(
        Integer,
        comment='Packets lost'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor', back_populates='diagnostics')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostic to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'diagnostic_type': self.diagnostic_type,
            'data': self.data,
            'system': {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'storage_usage': self.storage_usage,
                'uptime_seconds': self.uptime_seconds
            },
            'network': {
                'latency_ms': self.network_latency_ms,
                'packets_sent': self.packets_sent,
                'packets_received': self.packets_received,
                'packets_lost': self.packets_lost,
                'packet_loss_percent': (self.packets_lost / self.packets_sent * 100) if self.packets_sent else 0
            },
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorDiagnostic(id={self.id}, type={self.diagnostic_type})>"


class SensorAggregate(Base):
    """
    Aggregated sensor data for analytics.
    
    Stores pre-computed aggregates for faster querying and reporting.
    """
    
    __tablename__ = 'sensor_aggregates'
    __table_args__ = (
        Index('ix_sensor_aggregates_sensor', 'sensor_id'),
        Index('ix_sensor_aggregates_period', 'aggregation_period'),
        Index('ix_sensor_aggregates_start', 'period_start'),
        Index('ix_sensor_aggregates_sensor_period', 'sensor_id', 'aggregation_period', 'period_start'),
        
        # Table comment
        {'comment': 'Aggregated sensor data'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensors.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the sensor'
    )
    
    # =========================================================================
    # AGGREGATION PERIOD
    # =========================================================================
    aggregation_period = Column(
        String(20),
        nullable=False,
        comment='Aggregation period (hour, day, week, month)'
    )
    
    period_start = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Start of aggregation period'
    )
    
    period_end = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='End of aggregation period'
    )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    count = Column(
        Integer,
        nullable=False,
        comment='Number of readings'
    )
    
    min_value = Column(
        Float,
        comment='Minimum value'
    )
    
    max_value = Column(
        Float,
        comment='Maximum value'
    )
    
    avg_value = Column(
        Float,
        comment='Average value'
    )
    
    median_value = Column(
        Float,
        comment='Median value'
    )
    
    stddev_value = Column(
        Float,
        comment='Standard deviation'
    )
    
    percentile_25 = Column(
        Float,
        comment='25th percentile'
    )
    
    percentile_75 = Column(
        Float,
        comment='75th percentile'
    )
    
    percentile_95 = Column(
        Float,
        comment='95th percentile'
    )
    
    percentile_99 = Column(
        Float,
        comment='99th percentile'
    )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    valid_count = Column(
        Integer,
        comment='Number of valid readings'
    )
    
    invalid_count = Column(
        Integer,
        comment='Number of invalid readings'
    )
    
    quality_distribution = Column(
        JSONB,
        comment='Distribution of quality values'
    )
    
    # =========================================================================
    # TIME SERIES
    # =========================================================================
    hourly_breakdown = Column(
        JSONB,
        comment='Hourly breakdown (for daily aggregates)'
    )
    
    daily_breakdown = Column(
        JSONB,
        comment='Daily breakdown (for monthly aggregates)'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    sensor = relationship('Sensor')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    @staticmethod
    def calculate_aggregate(
        session,
        sensor_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime
    ) -> 'SensorAggregate':
        """Calculate aggregate for a sensor over a period."""
        from models.sensor_data import SensorReading
        
        readings = session.query(SensorReading).filter(
            SensorReading.sensor_id == sensor_id,
            SensorReading.timestamp >= period_start,
            SensorReading.timestamp < period_end
        ).all()
        
        if not readings:
            return None
        
        values = [r.value for r in readings if r.is_valid]
        qualities = [r.quality for r in readings]
        
        # Calculate statistics
        aggregate = SensorAggregate(
            sensor_id=sensor_id,
            aggregation_period='custom',
            period_start=period_start,
            period_end=period_end,
            count=len(readings),
            min_value=min(values) if values else None,
            max_value=max(values) if values else None,
            avg_value=statistics.mean(values) if values else None,
            median_value=statistics.median(values) if values else None,
            stddev_value=statistics.stdev(values) if len(values) > 1 else None,
            valid_count=len(values),
            invalid_count=len(readings) - len(values),
            quality_distribution={q: qualities.count(q) for q in set(qualities)}
        )
        
        if len(values) > 0:
            values_sorted = sorted(values)
            n = len(values_sorted)
            aggregate.percentile_25 = values_sorted[int(n * 0.25)]
            aggregate.percentile_75 = values_sorted[int(n * 0.75)]
            aggregate.percentile_95 = values_sorted[int(n * 0.95)]
            aggregate.percentile_99 = values_sorted[int(n * 0.99)]
        
        return aggregate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary."""
        return {
            'id': str(self.id),
            'sensor_id': str(self.sensor_id),
            'period': {
                'aggregation': self.aggregation_period,
                'start': self.period_start.isoformat() if self.period_start else None,
                'end': self.period_end.isoformat() if self.period_end else None
            },
            'statistics': {
                'count': self.count,
                'min': self.min_value,
                'max': self.max_value,
                'avg': self.avg_value,
                'median': self.median_value,
                'stddev': self.stddev_value,
                'p25': self.percentile_25,
                'p75': self.percentile_75,
                'p95': self.percentile_95,
                'p99': self.percentile_99
            },
            'quality': {
                'valid_count': self.valid_count,
                'invalid_count': self.invalid_count,
                'valid_percent': (self.valid_count / self.count * 100) if self.count else 0,
                'distribution': self.quality_distribution
            },
            'breakdown': {
                'hourly': self.hourly_breakdown,
                'daily': self.daily_breakdown
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SensorAggregate(id={self.id}, period={self.aggregation_period})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Sensor, 'before_insert')
def sensor_before_insert(mapper, connection, target):
    """Set default values for new sensors."""
    if not target.device_id:
        # Generate device ID based on type and timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        type_prefix = target.sensor_type[:3].upper()
        target.device_id = f"SENSOR-{type_prefix}-{timestamp}"
    
    if not target.installation_date:
        target.installation_date = datetime.now()


@event.listens_for(Sensor, 'after_update')
def sensor_after_update(mapper, connection, target):
    """Handle sensor status changes."""
    # Check if sensor went offline
    if not target.is_online and target.last_communication_at:
        time_since_last = datetime.now() - target.last_communication_at
        if time_since_last > timedelta(minutes=5):
            # Create offline alert
            connection.execute(
                text("""
                    INSERT INTO sensor_alerts (
                        id, sensor_id, severity, alert_type, message, timestamp
                    ) VALUES (
                        gen_random_uuid(), :sensor_id, 'warning', 'offline',
                        'Sensor has been offline for over 5 minutes', CURRENT_TIMESTAMP
                    )
                """),
                {'sensor_id': target.id}
            )


@event.listens_for(SensorReading, 'after_insert')
def sensor_reading_after_insert(mapper, connection, target):
    """Process new sensor reading."""
    # Update sensor last reading
    connection.execute(
        text("""
            UPDATE sensors
            SET last_reading_at = :timestamp,
                last_value = :value,
                last_communication_at = :timestamp
            WHERE id = :sensor_id
        """),
        {
            'sensor_id': target.sensor_id,
            'timestamp': target.timestamp,
            'value': target.value
        }
    )
    
    # Check for anomalous readings
    if target.quality == 'poor' or target.quality == 'unreliable':
        connection.execute(
            text("""
                INSERT INTO sensor_alerts (
                    id, sensor_id, severity, alert_type, message, timestamp, details
                ) VALUES (
                    gen_random_uuid(), :sensor_id, 'warning', 'poor_quality',
                    'Poor quality reading detected', CURRENT_TIMESTAMP,
                    jsonb_build_object('value', :value, 'quality', :quality)
                )
            """),
            {
                'sensor_id': target.sensor_id,
                'value': target.value,
                'quality': target.quality
            }
        )


@event.listens_for(Sensor, 'before_update')
def sensor_before_update(mapper, connection, target):
    """Track battery level changes."""
    if target.battery_level is not None:
        old_values = object_session(target).get_changes(target)
        if 'battery_level' in old_values:
            old_level = old_values['battery_level'][0]
            if old_level is not None and target.battery_level < old_level:
                # Battery level decreased
                if target.battery_level < 20:
                    # Create low battery alert
                    connection.execute(
                        text("""
                            INSERT INTO sensor_alerts (
                                id, sensor_id, severity, alert_type, message, timestamp, details
                            ) VALUES (
                                gen_random_uuid(), :sensor_id, 'warning', 'battery_low',
                                'Battery level is low', CURRENT_TIMESTAMP,
                                jsonb_build_object('level', :level)
                            )
                        """),
                        {
                            'sensor_id': target.id,
                            'level': target.battery_level
                        }
                    )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_sensor(
    device_id: str,
    sensor_type: str,
    spot_id: Optional[uuid.UUID] = None,
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> Sensor:
    """
    Factory function to create a new sensor.
    
    Args:
        device_id: Unique device identifier
        sensor_type: Type of sensor
        spot_id: Associated parking spot
        manufacturer: Sensor manufacturer
        model: Sensor model
        **kwargs: Additional sensor attributes
        
    Returns:
        New Sensor instance
    """
    sensor = Sensor(
        device_id=device_id,
        sensor_type=sensor_type,
        spot_id=spot_id,
        manufacturer=manufacturer,
        model=model,
        **kwargs
    )
    
    return sensor


def create_standard_sensors(session) -> List[Sensor]:
    """
    Create standard sensor configurations.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created sensors
    """
    from models.parking_spot import ParkingSpot
    
    sensors = []
    
    # Get some parking spots
    spots = session.query(ParkingSpot).limit(5).all()
    
    sensor_configs = [
        {
            'device_id': 'US-001',
            'name': 'Ultrasonic Sensor 1',
            'sensor_type': 'ultrasonic',
            'manufacturer': 'pepperl_fuchs',
            'model': 'UC2000-30GM',
            'measurement_unit': 'cm',
            'measurement_range_min': 20,
            'measurement_range_max': 200,
            'accuracy': 0.5,
            'power_source': 'mains',
            'communication_protocol': 'rs485',
            'ingress_protection': 'IP67'
        },
        {
            'device_id': 'MG-001',
            'name': 'Magnetic Sensor 1',
            'sensor_type': 'magnetic',
            'manufacturer': 'ifm',
            'model': 'MK5101',
            'measurement_unit': 'mT',
            'measurement_range_min': 0,
            'measurement_range_max': 5,
            'accuracy': 0.1,
            'power_source': 'battery',
            'battery_level': 100,
            'communication_protocol': 'lorawan',
            'ingress_protection': 'IP68'
        },
        {
            'device_id': 'CAM-001',
            'name': 'Camera Sensor 1',
            'sensor_type': 'camera',
            'manufacturer': 'bosch',
            'model': 'AUTODOME-7000',
            'measurement_unit': 'px',
            'power_source': 'poe',
            'communication_protocol': 'ethernet',
            'ingress_protection': 'IP66'
        },
        {
            'device_id': 'RAD-001',
            'name': 'Radar Sensor 1',
            'sensor_type': 'radar',
            'manufacturer': 'sick',
            'model': 'LMS-1000',
            'measurement_unit': 'm',
            'measurement_range_min': 0.5,
            'measurement_range_max': 50,
            'accuracy': 0.05,
            'power_source': 'mains',
            'communication_protocol': 'ethernet',
            'ingress_protection': 'IP65'
        },
        {
            'device_id': 'ENV-001',
            'name': 'Environmental Sensor',
            'sensor_type': 'environmental',
            'manufacturer': 'honeywell',
            'model': 'HPM-100',
            'measurement_unit': 'c',
            'measurement_range_min': -40,
            'measurement_range_max': 85,
            'accuracy': 0.5,
            'power_source': 'solar',
            'battery_level': 95,
            'communication_protocol': 'wifi',
            'ingress_protection': 'IP65'
        },
    ]
    
    for i, config in enumerate(sensor_configs):
        spot = spots[i % len(spots)] if spots else None
        
        sensor = Sensor(
            device_id=config['device_id'],
            name=config['name'],
            sensor_type=config['sensor_type'],
            spot_id=spot.id if spot else None,
            manufacturer=config['manufacturer'],
            model=config['model'],
            measurement_unit=config.get('measurement_unit'),
            measurement_range_min=config.get('measurement_range_min'),
            measurement_range_max=config.get('measurement_range_max'),
            accuracy=config.get('accuracy'),
            power_source=config.get('power_source'),
            battery_level=config.get('battery_level'),
            communication_protocol=config.get('communication_protocol'),
            ingress_protection=config.get('ingress_protection'),
            is_online=True,
            status='active'
        )
        
        existing = session.query(Sensor).filter_by(device_id=sensor.device_id).first()
        if not existing:
            sensors.append(sensor)
            session.add(sensor)
    
    session.commit()
    return sensors


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    # Main models
    'Sensor',
    'SensorReading',
    'SensorAlert',
    'SensorMaintenance',
    'SensorCalibration',
    'SensorDiagnostic',
    'SensorAggregate',
    
    # Enums
    'SensorType',
    'SensorStatus',
    'SensorManufacturer',
    'CommunicationProtocol',
    'PowerSource',
    'MeasurementUnit',
    'DataQuality',
    'CalibrationStatus',
    'AlertSeverity',
    
    # Factory functions
    'create_sensor',
    'create_standard_sensors',
]