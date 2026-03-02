# parking-management/data/services/analytics_service.py
"""
Analytics service module for the parking management system.

This module provides comprehensive analytics capabilities including metrics calculation,
KPI tracking, revenue analysis, occupancy analytics, user behavior analysis,
forecasting, and business intelligence reporting.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, TypeVar, Generic,
    Set, Iterator, Counter
)
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import math
import statistics
from collections import defaultdict
from enum import Enum
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    String, Integer, Float, Boolean, DateTime, Date,
    Text, cast, extract, case
)
from sqlalchemy.orm import Session, Query

from ..repositories import (
    UserRepository,
    VehicleRepository,
    ParkingSpotRepository,
    ReservationRepository,
    PaymentRepository,
    AuditLogRepository,
    AnalyticsRepository
)
from .base_service import BaseService, ServiceException, with_retry
from .cache_service import CacheService, cached
from ..models.enums import (
    # Domain enums
    UserStatus,
    UserRole,
    VehicleStatus,
    VehicleType,
    SpotType,
    SpotStatus,
    ReservationStatus,
    PaymentStatus,
    PaymentMethodType,
    
    # Analytics enums
    MetricType,
    TimeGranularity,
    ReportFormat,
    ChartType
)

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Custom Exceptions
# ============================================================================

class AnalyticsException(ServiceException):
    """Base exception for analytics service."""
    pass


class MetricNotFoundException(AnalyticsException):
    """Raised when a metric is not found."""
    pass


class ReportGenerationException(AnalyticsException):
    """Raised when report generation fails."""
    pass


class ForecastException(AnalyticsException):
    """Raised when forecast generation fails."""
    pass


class DataInsufficientException(AnalyticsException):
    """Raised when insufficient data for analysis."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class TimeSeriesPoint:
    """Represents a single point in a time series."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeries:
    """Represents a time series data set."""
    metric: str
    points: List[TimeSeriesPoint]
    granularity: TimeGranularity
    start_date: datetime
    end_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric': self.metric,
            'granularity': self.granularity.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'points': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'value': p.value,
                    'metadata': p.metadata
                }
                for p in self.points
            ],
            'metadata': self.metadata
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        df = pd.DataFrame([
            {
                'timestamp': p.timestamp,
                'value': p.value,
                **p.metadata
            }
            for p in self.points
        ])
        df.set_index('timestamp', inplace=True)
        return df


@dataclass
class MetricValue:
    """Represents a calculated metric value."""
    name: str
    value: float
    timestamp: datetime
    dimensions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'dimensions': self.dimensions,
            'metadata': self.metadata
        }


@dataclass
class KPIDefinition:
    """Defines a Key Performance Indicator."""
    name: str
    display_name: str
    description: str
    unit: str
    formula: str
    target: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    direction: str = 'up'  # 'up' or 'down' for good performance


@dataclass
class KPIValue:
    """Represents a KPI value with status."""
    kpi: KPIDefinition
    value: float
    timestamp: datetime
    previous_value: Optional[float] = None
    target_met: Optional[bool] = None
    status: str = 'normal'  # 'normal', 'warning', 'critical'
    trend: float = 0.0  # Percentage change
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.kpi.name,
            'display_name': self.kpi.display_name,
            'value': self.value,
            'previous_value': self.previous_value,
            'unit': self.kpi.unit,
            'timestamp': self.timestamp.isoformat(),
            'target_met': self.target_met,
            'status': self.status,
            'trend': self.trend,
            'target': self.kpi.target
        }


@dataclass
class Report:
    """Represents a generated report."""
    id: str
    name: str
    type: str
    format: ReportFormat
    generated_at: datetime
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'format': self.format.value,
            'generated_at': self.generated_at.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }


@dataclass
class Forecast:
    """Represents a forecast prediction."""
    metric: str
    predictions: List[TimeSeriesPoint]
    confidence_intervals: Dict[str, List[float]]
    model_metadata: Dict[str, Any]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric': self.metric,
            'predictions': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'value': p.value,
                    'metadata': p.metadata
                }
                for p in self.predictions
            ],
            'confidence_intervals': self.confidence_intervals,
            'model_metadata': self.model_metadata,
            'generated_at': self.generated_at.isoformat()
        }


# ============================================================================
# Analytics Service
# ============================================================================

class AnalyticsService(BaseService):
    """
    Comprehensive analytics service for business intelligence.
    
    Provides:
    - Metric calculation and tracking
    - KPI monitoring
    - Revenue analytics
    - Occupancy analytics
    - User behavior analysis
    - Forecasting
    - Report generation
    - Data export
    """
    
    def __init__(
        self,
        session: Session,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the analytics service.
        
        Args:
            session: SQLAlchemy session
            cache_service: Optional cache service for caching results
        """
        super().__init__(session)
        self.cache = cache_service
        
        # Initialize repositories
        self.user_repo = UserRepository(session)
        self.vehicle_repo = VehicleRepository(session)
        self.spot_repo = ParkingSpotRepository(session)
        self.reservation_repo = ReservationRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.audit_repo = AuditLogRepository(session)
        self.analytics_repo = AnalyticsRepository(session)
        
        # Initialize KPI definitions
        self.kpis = self._init_kpis()
        
        logger.info("AnalyticsService initialized")
    
    def _init_kpis(self) -> Dict[str, KPIDefinition]:
        """Initialize KPI definitions."""
        return {
            'revenue_daily': KPIDefinition(
                name='revenue_daily',
                display_name='Daily Revenue',
                description='Total revenue per day',
                unit='USD',
                formula='SUM(payment.amount) WHERE status = "paid"',
                direction='up'
            ),
            'occupancy_rate': KPIDefinition(
                name='occupancy_rate',
                display_name='Occupancy Rate',
                description='Percentage of occupied parking spots',
                unit='%',
                formula='(occupied_spots / total_spots) * 100',
                target=85.0,
                warning_threshold=90.0,
                critical_threshold=95.0,
                direction='up'
            ),
            'reservation_conversion': KPIDefinition(
                name='reservation_conversion',
                display_name='Reservation Conversion Rate',
                description='Percentage of visitors who make reservations',
                unit='%',
                formula='(reservations / unique_visitors) * 100',
                direction='up'
            ),
            'avg_parking_duration': KPIDefinition(
                name='avg_parking_duration',
                display_name='Average Parking Duration',
                description='Average duration of parking sessions',
                unit='minutes',
                formula='AVG(reservation.end_time - reservation.start_time)',
                direction='neutral'
            ),
            'customer_satisfaction': KPIDefinition(
                name='customer_satisfaction',
                display_name='Customer Satisfaction',
                description='Average customer rating',
                unit='stars',
                formula='AVG(feedback.rating)',
                target=4.5,
                warning_threshold=4.0,
                critical_threshold=3.0,
                direction='up'
            ),
            'cancellation_rate': KPIDefinition(
                name='cancellation_rate',
                display_name='Cancellation Rate',
                description='Percentage of reservations cancelled',
                unit='%',
                formula='(cancelled_reservations / total_reservations) * 100',
                target=10.0,
                warning_threshold=15.0,
                critical_threshold=20.0,
                direction='down'
            ),
            'repeat_customer_rate': KPIDefinition(
                name='repeat_customer_rate',
                display_name='Repeat Customer Rate',
                description='Percentage of customers with multiple reservations',
                unit='%',
                formula='(repeat_customers / total_customers) * 100',
                direction='up'
            ),
            'revenue_per_spot': KPIDefinition(
                name='revenue_per_spot',
                display_name='Revenue per Parking Spot',
                description='Average daily revenue per parking spot',
                unit='USD',
                formula='total_revenue / total_spots',
                direction='up'
            ),
            'peak_hour_utilization': KPIDefinition(
                name='peak_hour_utilization',
                display_name='Peak Hour Utilization',
                description='Occupancy rate during peak hours',
                unit='%',
                formula='(occupied_spots_during_peak / total_spots) * 100',
                direction='up'
            ),
            'no_show_rate': KPIDefinition(
                name='no_show_rate',
                display_name='No-Show Rate',
                description='Percentage of reservations that are no-shows',
                unit='%',
                formula='(no_show_reservations / total_reservations) * 100',
                target=5.0,
                warning_threshold=8.0,
                critical_threshold=12.0,
                direction='down'
            )
        }
    
    # ========================================================================
    # Metric Calculation Methods
    # ========================================================================
    
    @cached(ttl=300)
    def calculate_metric(
        self,
        metric_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        dimensions: Optional[Dict[str, Any]] = None
    ) -> MetricValue:
        """
        Calculate a specific metric.
        
        Args:
            metric_name: Name of the metric
            start_date: Start date for calculation
            end_date: End date for calculation
            dimensions: Additional dimensions for filtering
            
        Returns:
            Calculated metric value
            
        Raises:
            MetricNotFoundException: If metric not found
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        # Route to appropriate calculator
        if metric_name.startswith('revenue'):
            return self._calculate_revenue_metric(metric_name, start_date, end_date, dimensions)
        elif metric_name.startswith('occupancy'):
            return self._calculate_occupancy_metric(metric_name, start_date, end_date, dimensions)
        elif metric_name.startswith('user') or metric_name.startswith('customer'):
            return self._calculate_user_metric(metric_name, start_date, end_date, dimensions)
        elif metric_name.startswith('reservation'):
            return self._calculate_reservation_metric(metric_name, start_date, end_date, dimensions)
        elif metric_name.startswith('vehicle'):
            return self._calculate_vehicle_metric(metric_name, start_date, end_date, dimensions)
        else:
            raise MetricNotFoundException(f"Unknown metric: {metric_name}")
    
    def _calculate_revenue_metric(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> MetricValue:
        """Calculate revenue-related metrics."""
        query = self.session.query(func.sum(self.payment_repo.model_class.amount))
        query = query.filter(
            self.payment_repo.model_class.status == PaymentStatus.PAID,
            self.payment_repo.model_class.created_at.between(start_date, end_date)
        )
        
        # Apply dimensions
        if dimensions:
            if 'payment_method' in dimensions:
                query = query.filter(
                    self.payment_repo.model_class.payment_method_type == dimensions['payment_method']
                )
            if 'currency' in dimensions:
                query = query.filter(
                    self.payment_repo.model_class.currency == dimensions['currency']
                )
        
        value = query.scalar() or 0.0
        
        if metric_name == 'revenue_daily':
            days = max((end_date - start_date).days, 1)
            value = value / days
        
        return MetricValue(
            name=metric_name,
            value=float(value),
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metadata={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )
    
    def _calculate_occupancy_metric(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> MetricValue:
        """Calculate occupancy-related metrics."""
        total_spots = self.spot_repo.count()
        
        if metric_name == 'occupancy_rate':
            # Get average occupancy over period
            occupied = self._get_average_occupancy(start_date, end_date, dimensions)
            value = (occupied / total_spots * 100) if total_spots > 0 else 0
        
        elif metric_name == 'peak_hour_utilization':
            # Get peak hour occupancy
            occupied = self._get_peak_hour_occupancy(start_date, end_date, dimensions)
            value = (occupied / total_spots * 100) if total_spots > 0 else 0
        
        elif metric_name == 'revenue_per_spot':
            revenue = self._calculate_revenue_metric('revenue_total', start_date, end_date, dimensions).value
            value = revenue / total_spots if total_spots > 0 else 0
        
        else:
            value = 0
        
        return MetricValue(
            name=metric_name,
            value=float(value),
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metadata={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_spots': total_spots
            }
        )
    
    def _calculate_user_metric(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> MetricValue:
        """Calculate user-related metrics."""
        if metric_name == 'customer_satisfaction':
            # Get average rating from feedback
            value = self._get_average_rating(start_date, end_date, dimensions)
        
        elif metric_name == 'repeat_customer_rate':
            # Calculate percentage of customers with multiple reservations
            value = self._get_repeat_customer_rate(start_date, end_date, dimensions)
        
        elif metric_name == 'reservation_conversion':
            # Calculate conversion rate from visitors to reservations
            value = self._get_conversion_rate(start_date, end_date, dimensions)
        
        else:
            value = 0
        
        return MetricValue(
            name=metric_name,
            value=float(value),
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metadata={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )
    
    def _calculate_reservation_metric(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> MetricValue:
        """Calculate reservation-related metrics."""
        total = self.reservation_repo.count(
            created_at_between=(start_date, end_date)
        )
        
        if metric_name == 'avg_parking_duration':
            # Get average duration
            reservations = self.reservation_repo.get_reservations_in_range(
                start_date, end_date,
                statuses=[ReservationStatus.COMPLETED]
            )
            if reservations:
                total_minutes = sum(
                    (r.end_time - r.start_time).total_seconds() / 60
                    for r in reservations
                )
                value = total_minutes / len(reservations)
            else:
                value = 0
        
        elif metric_name == 'cancellation_rate':
            cancelled = self.reservation_repo.count(
                created_at_between=(start_date, end_date),
                status=ReservationStatus.CANCELLED
            )
            value = (cancelled / total * 100) if total > 0 else 0
        
        elif metric_name == 'no_show_rate':
            no_show = self.reservation_repo.count(
                created_at_between=(start_date, end_date),
                status=ReservationStatus.NO_SHOW
            )
            value = (no_show / total * 100) if total > 0 else 0
        
        else:
            value = total
        
        return MetricValue(
            name=metric_name,
            value=float(value),
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metadata={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_reservations': total
            }
        )
    
    def _calculate_vehicle_metric(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> MetricValue:
        """Calculate vehicle-related metrics."""
        if metric_name == 'vehicle_distribution':
            # Get distribution by type
            distribution = self.vehicle_repo.session.query(
                self.vehicle_repo.model_class.vehicle_type,
                func.count(self.vehicle_repo.model_class.id)
            ).group_by(
                self.vehicle_repo.model_class.vehicle_type
            ).all()
            
            value = {str(k): v for k, v in distribution}
        
        else:
            value = self.vehicle_repo.count()
        
        return MetricValue(
            name=metric_name,
            value=float(value) if isinstance(value, (int, float)) else 0,
            timestamp=datetime.utcnow(),
            dimensions=dimensions or {},
            metadata={'distribution': value} if isinstance(value, dict) else {}
        )
    
    # ========================================================================
    # KPI Methods
    # ========================================================================
    
    def get_kpi_dashboard(self) -> Dict[str, KPIValue]:
        """
        Get current KPI values for dashboard.
        
        Returns:
            Dictionary of KPI values
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        previous_start = start_date - timedelta(days=30)
        
        kpis = {}
        
        for name, kpi_def in self.kpis.items():
            try:
                # Get current value
                current = self.calculate_metric(name, start_date, end_date)
                
                # Get previous value for trend
                previous = self.calculate_metric(name, previous_start, start_date)
                
                # Calculate trend
                trend = 0.0
                if previous.value > 0:
                    trend = ((current.value - previous.value) / previous.value) * 100
                
                # Determine status
                status = 'normal'
                target_met = None
                
                if kpi_def.target is not None:
                    if kpi_def.direction == 'up':
                        target_met = current.value >= kpi_def.target
                    else:
                        target_met = current.value <= kpi_def.target
                
                if kpi_def.critical_threshold is not None:
                    if kpi_def.direction == 'up' and current.value >= kpi_def.critical_threshold:
                        status = 'critical'
                    elif kpi_def.direction == 'down' and current.value <= kpi_def.critical_threshold:
                        status = 'critical'
                    elif kpi_def.warning_threshold is not None:
                        if kpi_def.direction == 'up' and current.value >= kpi_def.warning_threshold:
                            status = 'warning'
                        elif kpi_def.direction == 'down' and current.value <= kpi_def.warning_threshold:
                            status = 'warning'
                
                kpis[name] = KPIValue(
                    kpi=kpi_def,
                    value=current.value,
                    previous_value=previous.value,
                    timestamp=datetime.utcnow(),
                    target_met=target_met,
                    status=status,
                    trend=trend
                )
                
            except Exception as e:
                logger.error(f"Failed to calculate KPI {name}: {e}")
        
        return kpis
    
    def get_kpi_history(
        self,
        kpi_name: str,
        days: int = 90,
        granularity: TimeGranularity = TimeGranularity.DAY
    ) -> TimeSeries:
        """
        Get historical values for a KPI.
        
        Args:
            kpi_name: Name of the KPI
            days: Number of days of history
            granularity: Time granularity
            
        Returns:
            Time series of KPI values
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        points = []
        current = start_date
        
        while current <= end_date:
            if granularity == TimeGranularity.HOUR:
                next_point = current + timedelta(hours=1)
            elif granularity == TimeGranularity.DAY:
                next_point = current + timedelta(days=1)
            elif granularity == TimeGranularity.WEEK:
                next_point = current + timedelta(weeks=1)
            elif granularity == TimeGranularity.MONTH:
                # Approximate month
                next_point = current + timedelta(days=30)
            else:
                next_point = current + timedelta(days=1)
            
            try:
                value = self.calculate_metric(kpi_name, current, next_point)
                points.append(TimeSeriesPoint(
                    timestamp=current,
                    value=value.value
                ))
            except Exception as e:
                logger.error(f"Failed to calculate KPI for period {current}: {e}")
            
            current = next_point
        
        return TimeSeries(
            metric=kpi_name,
            points=points,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date
        )
    
    # ========================================================================
    # Revenue Analytics
    # ========================================================================
    
    def get_revenue_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAY,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive revenue analytics.
        
        Args:
            start_date: Start date
            end_date: End date
            granularity: Time granularity
            group_by: Fields to group by (e.g., ['payment_method', 'currency'])
            
        Returns:
            Revenue analytics data
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        # Get time series
        time_series = self._get_revenue_time_series(start_date, end_date, granularity)
        
        # Get breakdowns
        breakdowns = {}
        if group_by:
            for field in group_by:
                breakdowns[field] = self._get_revenue_breakdown(
                    start_date, end_date, field
                )
        
        # Calculate statistics
        values = [p.value for p in time_series.points]
        
        stats = {
            'total': sum(values),
            'average': statistics.mean(values) if values else 0,
            'median': statistics.median(values) if values else 0,
            'min': min(values) if values else 0,
            'max': max(values) if values else 0,
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0
        }
        
        # Calculate growth
        if len(values) >= 2:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            growth = ((sum(second_half) - sum(first_half)) / sum(first_half) * 100) if sum(first_half) > 0 else 0
        else:
            growth = 0
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'granularity': granularity.value,
            'time_series': time_series.to_dict(),
            'breakdowns': breakdowns,
            'statistics': stats,
            'growth_percentage': round(growth, 2),
            'metadata': {
                'currency': 'USD',
                'total_transactions': self._get_transaction_count(start_date, end_date)
            }
        }
    
    def _get_revenue_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity
    ) -> TimeSeries:
        """Get revenue time series data."""
        points = []
        current = start_date
        
        while current < end_date:
            if granularity == TimeGranularity.HOUR:
                next_point = min(current + timedelta(hours=1), end_date)
                date_trunc = func.date_trunc('hour', self.payment_repo.model_class.created_at)
            elif granularity == TimeGranularity.DAY:
                next_point = min(current + timedelta(days=1), end_date)
                date_trunc = func.date_trunc('day', self.payment_repo.model_class.created_at)
            elif granularity == TimeGranularity.WEEK:
                next_point = min(current + timedelta(weeks=1), end_date)
                date_trunc = func.date_trunc('week', self.payment_repo.model_class.created_at)
            elif granularity == TimeGranularity.MONTH:
                next_point = min(current + timedelta(days=30), end_date)
                date_trunc = func.date_trunc('month', self.payment_repo.model_class.created_at)
            else:
                next_point = min(current + timedelta(days=1), end_date)
                date_trunc = func.date_trunc('day', self.payment_repo.model_class.created_at)
            
            # Query revenue for this period
            revenue = self.session.query(
                func.sum(self.payment_repo.model_class.amount)
            ).filter(
                self.payment_repo.model_class.status == PaymentStatus.PAID,
                self.payment_repo.model_class.created_at.between(current, next_point)
            ).scalar() or 0
            
            points.append(TimeSeriesPoint(
                timestamp=current,
                value=float(revenue)
            ))
            
            current = next_point
        
        return TimeSeries(
            metric='revenue',
            points=points,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date
        )
    
    def _get_revenue_breakdown(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str
    ) -> Dict[str, float]:
        """Get revenue breakdown by a field."""
        model = self.payment_repo.model_class
        
        if group_by == 'payment_method':
            column = model.payment_method_type
        elif group_by == 'currency':
            column = model.currency
        elif group_by == 'hour':
            column = extract('hour', model.created_at)
        elif group_by == 'day_of_week':
            column = extract('dow', model.created_at)
        else:
            column = None
        
        if column is None:
            return {}
        
        results = self.session.query(
            column,
            func.sum(model.amount)
        ).filter(
            model.status == PaymentStatus.PAID,
            model.created_at.between(start_date, end_date)
        ).group_by(column).all()
        
        return {str(k): float(v) for k, v in results}
    
    def _get_transaction_count(self, start_date: datetime, end_date: datetime) -> int:
        """Get number of transactions in period."""
        return self.payment_repo.count(
            created_at_between=(start_date, end_date),
            status=PaymentStatus.PAID
        )
    
    # ========================================================================
    # Occupancy Analytics
    # ========================================================================
    
    def get_occupancy_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.HOUR,
        zone_id: Optional[int] = None,
        spot_type: Optional[SpotType] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive occupancy analytics.
        
        Args:
            start_date: Start date
            end_date: End date
            granularity: Time granularity
            zone_id: Optional zone filter
            spot_type: Optional spot type filter
            
        Returns:
            Occupancy analytics data
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=7))
        
        total_spots = self.spot_repo.count(
            zone_id=zone_id,
            spot_type=spot_type
        )
        
        # Get time series
        time_series = self._get_occupancy_time_series(
            start_date, end_date, granularity, zone_id, spot_type
        )
        
        # Get peak hours
        peak_hours = self._get_peak_hours(start_date, end_date, zone_id, spot_type)
        
        # Get spot type distribution
        spot_type_dist = self._get_spot_type_distribution(zone_id)
        
        # Calculate statistics
        values = [p.value for p in time_series.points]
        
        stats = {
            'average_occupancy': statistics.mean(values) if values else 0,
            'peak_occupancy': max(values) if values else 0,
            'lowest_occupancy': min(values) if values else 0,
            'average_rate': (statistics.mean(values) / total_spots * 100) if total_spots > 0 else 0,
            'peak_rate': (max(values) / total_spots * 100) if total_spots > 0 else 0,
            'total_spots': total_spots
        }
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'granularity': granularity.value,
            'time_series': time_series.to_dict(),
            'peak_hours': peak_hours,
            'spot_type_distribution': spot_type_dist,
            'statistics': stats
        }
    
    def _get_occupancy_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity,
        zone_id: Optional[int],
        spot_type: Optional[SpotType]
    ) -> TimeSeries:
        """Get occupancy time series data."""
        points = []
        current = start_date
        
        while current < end_date:
            if granularity == TimeGranularity.HOUR:
                next_point = min(current + timedelta(hours=1), end_date)
            elif granularity == TimeGranularity.DAY:
                next_point = min(current + timedelta(days=1), end_date)
            elif granularity == TimeGranularity.WEEK:
                next_point = min(current + timedelta(weeks=1), end_date)
            else:
                next_point = min(current + timedelta(days=1), end_date)
            
            # Get occupancy for this period
            occupied = self._get_occupancy_for_period(
                current, next_point, zone_id, spot_type
            )
            
            points.append(TimeSeriesPoint(
                timestamp=current,
                value=float(occupied)
            ))
            
            current = next_point
        
        return TimeSeries(
            metric='occupancy',
            points=points,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date
        )
    
    def _get_occupancy_for_period(
        self,
        period_start: datetime,
        period_end: datetime,
        zone_id: Optional[int],
        spot_type: Optional[SpotType]
    ) -> int:
        """Get average occupancy for a period."""
        # This is a simplified calculation
        # In production, you'd want to calculate based on actual occupancy data
        
        # Get all spots
        query = self.session.query(self.spot_repo.model_class.id)
        
        if zone_id:
            query = query.filter(self.spot_repo.model_class.zone_id == zone_id)
        
        if spot_type:
            query = query.filter(self.spot_repo.model_class.spot_type == spot_type)
        
        spot_ids = [r[0] for r in query.all()]
        
        if not spot_ids:
            return 0
        
        # Get reservations that overlap with this period
        reservations = self.reservation_repo.get_reservations_in_range(
            period_start, period_end
        )
        
        # Count unique spots occupied
        occupied_spots = set()
        for r in reservations:
            if r.spot_id in spot_ids:
                occupied_spots.add(r.spot_id)
        
        return len(occupied_spots)
    
    def _get_peak_hours(
        self,
        start_date: datetime,
        end_date: datetime,
        zone_id: Optional[int],
        spot_type: Optional[SpotType]
    ) -> List[Dict[str, Any]]:
        """Get peak hour analysis."""
        hourly_occupancy = defaultdict(list)
        
        current = start_date
        while current < end_date:
            next_hour = current + timedelta(hours=1)
            
            occupied = self._get_occupancy_for_period(
                current, next_hour, zone_id, spot_type
            )
            
            hour = current.hour
            hourly_occupancy[hour].append(occupied)
            
            current = next_hour
        
        # Calculate average per hour
        peak_hours = []
        for hour in range(24):
            if hourly_occupancy[hour]:
                avg = statistics.mean(hourly_occupancy[hour])
                peak_hours.append({
                    'hour': hour,
                    'average_occupancy': avg,
                    'peak_factor': avg / max(hourly_occupancy.values()) if hourly_occupancy else 0
                })
        
        # Sort by occupancy
        peak_hours.sort(key=lambda x: x['average_occupancy'], reverse=True)
        
        return peak_hours
    
    def _get_spot_type_distribution(self, zone_id: Optional[int]) -> Dict[str, int]:
        """Get distribution of spot types."""
        query = self.session.query(
            self.spot_repo.model_class.spot_type,
            func.count(self.spot_repo.model_class.id)
        )
        
        if zone_id:
            query = query.filter(self.spot_repo.model_class.zone_id == zone_id)
        
        results = query.group_by(self.spot_repo.model_class.spot_type).all()
        
        return {str(k): v for k, v in results}
    
    # ========================================================================
    # User Behavior Analytics
    # ========================================================================
    
    def get_user_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAY
    ) -> Dict[str, Any]:
        """
        Get user behavior analytics.
        
        Args:
            start_date: Start date
            end_date: End date
            granularity: Time granularity
            
        Returns:
            User analytics data
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        # User acquisition
        new_users = self._get_new_users_time_series(start_date, end_date, granularity)
        
        # Active users
        active_users = self._get_active_users_time_series(start_date, end_date, granularity)
        
        # User retention
        retention = self._get_user_retention(start_date, end_date)
        
        # User segments
        segments = self._get_user_segments()
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'acquisition': new_users.to_dict(),
            'activity': active_users.to_dict(),
            'retention': retention,
            'segments': segments,
            'total_users': self.user_repo.count()
        }
    
    def _get_new_users_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity
    ) -> TimeSeries:
        """Get new users time series."""
        points = []
        current = start_date
        
        while current < end_date:
            if granularity == TimeGranularity.DAY:
                next_point = min(current + timedelta(days=1), end_date)
            elif granularity == TimeGranularity.WEEK:
                next_point = min(current + timedelta(weeks=1), end_date)
            elif granularity == TimeGranularity.MONTH:
                next_point = min(current + timedelta(days=30), end_date)
            else:
                next_point = min(current + timedelta(days=1), end_date)
            
            count = self.user_repo.count(
                created_at_between=(current, next_point)
            )
            
            points.append(TimeSeriesPoint(
                timestamp=current,
                value=float(count)
            ))
            
            current = next_point
        
        return TimeSeries(
            metric='new_users',
            points=points,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date
        )
    
    def _get_active_users_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity
    ) -> TimeSeries:
        """Get active users time series."""
        points = []
        current = start_date
        
        while current < end_date:
            if granularity == TimeGranularity.DAY:
                next_point = min(current + timedelta(days=1), end_date)
            elif granularity == TimeGranularity.WEEK:
                next_point = min(current + timedelta(weeks=1), end_date)
            else:
                next_point = min(current + timedelta(days=1), end_date)
            
            # Count users with sessions in this period
            from ..models.user_models import UserSession
            
            count = self.session.query(
                func.count(func.distinct(UserSession.user_id))
            ).filter(
                UserSession.last_activity.between(current, next_point)
            ).scalar() or 0
            
            points.append(TimeSeriesPoint(
                timestamp=current,
                value=float(count)
            ))
            
            current = next_point
        
        return TimeSeries(
            metric='active_users',
            points=points,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date
        )
    
    def _get_user_retention(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """Calculate user retention rates."""
        # Get users who joined in the period
        new_users = self.user_repo.get_users_by_date_range(start_date, end_date)
        
        if not new_users:
            return {}
        
        retention = {}
        
        # Calculate retention for each cohort
        for days in [1, 7, 30, 90]:
            cutoff = end_date - timedelta(days=days)
            retained = 0
            
            for user in new_users:
                # Check if user had activity after cutoff
                has_activity = self.session.query(
                    func.count(self.user_repo.user_sessions.property.mapper.class_.id)
                ).filter(
                    self.user_repo.user_sessions.property.mapper.class_.user_id == user.id,
                    self.user_repo.user_sessions.property.mapper.class_.last_activity > cutoff
                ).scalar() > 0
                
                if has_activity:
                    retained += 1
            
            retention[f'{days}_day'] = (retained / len(new_users) * 100) if new_users else 0
        
        return retention
    
    def _get_user_segments(self) -> Dict[str, int]:
        """Get user segmentation data."""
        segments = {}
        
        # By role
        for role in UserRole:
            count = self.user_repo.count(role=role)
            if count > 0:
                segments[f'role_{role.value}'] = count
        
        # By status
        for status in UserStatus:
            count = self.user_repo.count(status=status)
            if count > 0:
                segments[f'status_{status.value}'] = count
        
        # By activity level
        active_30d = self._get_active_users_count(
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        segments['active_last_30d'] = active_30d
        
        return segments
    
    def _get_active_users_count(self, start_date: datetime, end_date: datetime) -> int:
        """Get count of active users in period."""
        from ..models.user_models import UserSession
        
        return self.session.query(
            func.count(func.distinct(UserSession.user_id))
        ).filter(
            UserSession.last_activity.between(start_date, end_date)
        ).scalar() or 0
    
    def _get_average_rating(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> float:
        """Get average rating from feedback."""
        # Placeholder - implement when feedback model exists
        return 4.5
    
    def _get_repeat_customer_rate(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> float:
        """Calculate repeat customer rate."""
        # Get customers with multiple reservations
        from ..models.reservation_models import Reservation
        
        customer_counts = self.session.query(
            Reservation.user_id,
            func.count(Reservation.id).label('reservation_count')
        ).filter(
            Reservation.created_at.between(start_date, end_date)
        ).group_by(Reservation.user_id).having(
            func.count(Reservation.id) > 1
        ).count()
        
        total_customers = self.session.query(
            func.count(func.distinct(Reservation.user_id))
        ).filter(
            Reservation.created_at.between(start_date, end_date)
        ).scalar() or 0
        
        return (customer_counts / total_customers * 100) if total_customers > 0 else 0
    
    def _get_conversion_rate(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> float:
        """Calculate conversion rate from visitors to reservations."""
        # Get unique visitors (from analytics events)
        from ..models.analytics_models import AnalyticsEvent
        
        visitors = self.session.query(
            func.count(func.distinct(AnalyticsEvent.user_id))
        ).filter(
            AnalyticsEvent.event_type == 'page_view',
            AnalyticsEvent.timestamp.between(start_date, end_date)
        ).scalar() or 0
        
        # Get reservations
        reservations = self.reservation_repo.count(
            created_at_between=(start_date, end_date)
        )
        
        return (reservations / visitors * 100) if visitors > 0 else 0
    
    def _get_average_occupancy(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> float:
        """Get average occupancy over period."""
        # Simplified - sample at multiple points
        samples = 24  # Sample 24 times
        interval = (end_date - start_date) / samples
        
        total = 0
        for i in range(samples):
            point = start_date + (interval * i)
            occupied = self._get_occupancy_for_period(
                point, point + timedelta(minutes=5),
                dimensions.get('zone_id') if dimensions else None,
                dimensions.get('spot_type') if dimensions else None
            )
            total += occupied
        
        return total / samples
    
    def _get_peak_hour_occupancy(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[Dict]
    ) -> float:
        """Get peak hour occupancy."""
        peak_hours = self._get_peak_hours(
            start_date, end_date,
            dimensions.get('zone_id') if dimensions else None,
            dimensions.get('spot_type') if dimensions else None
        )
        
        return peak_hours[0]['average_occupancy'] if peak_hours else 0
    
    # ========================================================================
    # Forecasting Methods
    # ========================================================================
    
    def forecast_metric(
        self,
        metric_name: str,
        periods: int = 30,
        confidence_level: float = 0.95,
        method: str = 'arima'
    ) -> Forecast:
        """
        Generate forecast for a metric.
        
        Args:
            metric_name: Metric to forecast
            periods: Number of periods to forecast
            confidence_level: Confidence level for intervals
            method: Forecasting method ('arima', 'holt_winters', 'linear')
            
        Returns:
            Forecast result
            
        Raises:
            ForecastException: If forecast generation fails
            DataInsufficientException: If insufficient data
        """
        # Get historical data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=periods * 3)  # Use 3x periods for training
        
        history = self.get_kpi_history(metric_name, periods * 3, TimeGranularity.DAY)
        
        if len(history.points) < 10:
            raise DataInsufficientException(
                f"Insufficient data for forecasting {metric_name}. Need at least 10 points."
            )
        
        values = [p.value for p in history.points]
        
        try:
            if method == 'linear':
                predictions, intervals = self._linear_forecast(
                    values, periods, confidence_level
                )
            elif method == 'holt_winters':
                predictions, intervals = self._holt_winters_forecast(
                    values, periods, confidence_level
                )
            else:  # arima
                predictions, intervals = self._arima_forecast(
                    values, periods, confidence_level
                )
            
        except Exception as e:
            raise ForecastException(f"Forecast generation failed: {e}")
        
        # Generate prediction timestamps
        last_date = history.points[-1].timestamp
        predictions_points = []
        
        for i, pred in enumerate(predictions):
            pred_date = last_date + timedelta(days=i + 1)
            predictions_points.append(TimeSeriesPoint(
                timestamp=pred_date,
                value=pred
            ))
        
        return Forecast(
            metric=metric_name,
            predictions=predictions_points,
            confidence_intervals=intervals,
            model_metadata={
                'method': method,
                'periods': periods,
                'confidence_level': confidence_level,
                'training_points': len(values)
            },
            generated_at=datetime.utcnow()
        )
    
    def _linear_forecast(
        self,
        values: List[float],
        periods: int,
        confidence_level: float
    ) -> Tuple[List[float], Dict[str, List[float]]]:
        """Simple linear regression forecast."""
        x = np.arange(len(values))
        y = np.array(values)
        
        # Fit linear regression
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        
        # Calculate standard error
        residuals = y - p(x)
        std_err = np.std(residuals)
        
        # Generate forecasts
        predictions = []
        lower_bounds = []
        upper_bounds = []
        
        last_x = len(values)
        
        for i in range(1, periods + 1):
            x_pred = last_x + i
            y_pred = p(x_pred)
            
            # Confidence interval (simplified)
            z_score = 1.96  # For 95% confidence
            margin = z_score * std_err * np.sqrt(1 + 1/len(x) + (x_pred - np.mean(x))**2 / np.sum((x - np.mean(x))**2))
            
            predictions.append(float(y_pred))
            lower_bounds.append(float(y_pred - margin))
            upper_bounds.append(float(y_pred + margin))
        
        return predictions, {'lower': lower_bounds, 'upper': upper_bounds}
    
    def _holt_winters_forecast(
        self,
        values: List[float],
        periods: int,
        confidence_level: float
    ) -> Tuple[List[float], Dict[str, List[float]]]:
        """Holt-Winters exponential smoothing forecast."""
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            
            # Fit model
            model = ExponentialSmoothing(
                values,
                seasonal_periods=7,
                trend='add',
                seasonal='add'
            )
            fitted_model = model.fit()
            
            # Generate forecast
            forecast = fitted_model.forecast(periods)
            
            # Get prediction intervals (simplified)
            residuals = fitted_model.resid
            std_err = np.std(residuals)
            
            predictions = forecast.tolist()
            z_score = 1.96
            
            lower_bounds = [p - z_score * std_err for p in predictions]
            upper_bounds = [p + z_score * std_err for p in predictions]
            
            return predictions, {'lower': lower_bounds, 'upper': upper_bounds}
            
        except ImportError:
            logger.warning("statsmodels not available, falling back to linear forecast")
            return self._linear_forecast(values, periods, confidence_level)
    
    def _arima_forecast(
        self,
        values: List[float],
        periods: int,
        confidence_level: float
    ) -> Tuple[List[float], Dict[str, List[float]]]:
        """ARIMA forecast."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            # Fit model
            model = ARIMA(values, order=(1, 1, 1))
            fitted_model = model.fit()
            
            # Generate forecast
            forecast_result = fitted_model.forecast(periods)
            
            predictions = forecast_result.tolist()
            
            # Get confidence intervals from model if available
            try:
                forecast_result = fitted_model.get_forecast(periods)
                conf_int = forecast_result.conf_int(alpha=1-confidence_level)
                lower_bounds = conf_int[:, 0].tolist()
                upper_bounds = conf_int[:, 1].tolist()
            except:
                # Fallback to simple intervals
                residuals = fitted_model.resid
                std_err = np.std(residuals)
                z_score = 1.96
                lower_bounds = [p - z_score * std_err for p in predictions]
                upper_bounds = [p + z_score * std_err for p in predictions]
            
            return predictions, {'lower': lower_bounds, 'upper': upper_bounds}
            
        except ImportError:
            logger.warning("statsmodels not available, falling back to linear forecast")
            return self._linear_forecast(values, periods, confidence_level)
    
    # ========================================================================
    # Report Generation
    # ========================================================================
    
    def generate_report(
        self,
        report_type: str,
        format: ReportFormat = ReportFormat.JSON,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Report:
        """
        Generate a comprehensive report.
        
        Args:
            report_type: Type of report
            format: Output format
            start_date: Start date
            end_date: End date
            parameters: Additional parameters
            
        Returns:
            Generated report
            
        Raises:
            ReportGenerationException: If report generation fails
        """
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))
        
        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if report_type == 'revenue':
                data = self.get_revenue_analytics(
                    start_date, end_date,
                    granularity=TimeGranularity.DAY,
                    group_by=['payment_method']
                )
            elif report_type == 'occupancy':
                data = self.get_occupancy_analytics(
                    start_date, end_date,
                    granularity=TimeGranularity.HOUR
                )
            elif report_type == 'users':
                data = self.get_user_analytics(start_date, end_date)
            elif report_type == 'kpi':
                data = {
                    'kpis': {k: v.to_dict() for k, v in self.get_kpi_dashboard().items()}
                }
            elif report_type == 'executive_summary':
                data = self._generate_executive_summary(start_date, end_date)
            elif report_type == 'forecast':
                forecast = self.forecast_metric(
                    parameters.get('metric', 'revenue_daily'),
                    periods=parameters.get('periods', 30)
                )
                data = forecast.to_dict()
            else:
                raise ReportGenerationException(f"Unknown report type: {report_type}")
            
            # Format data
            if format == ReportFormat.CSV:
                formatted_data = self._format_as_csv(data)
            elif format == ReportFormat.EXCEL:
                formatted_data = self._format_as_excel(data)
            elif format == ReportFormat.PDF:
                formatted_data = self._format_as_pdf(data)
            else:  # JSON
                formatted_data = data
            
            return Report(
                id=report_id,
                name=f"{report_type}_report",
                type=report_type,
                format=format,
                generated_at=datetime.utcnow(),
                data=formatted_data,
                metadata={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'parameters': parameters
                }
            )
            
        except Exception as e:
            raise ReportGenerationException(f"Failed to generate {report_type} report: {e}")
    
    def _generate_executive_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate executive summary report."""
        kpis = self.get_kpi_dashboard()
        
        # Key metrics
        revenue = self.calculate_metric('revenue_daily', start_date, end_date)
        occupancy = self.calculate_metric('occupancy_rate', start_date, end_date)
        
        # Trends
        revenue_trend = self.get_kpi_history('revenue_daily', 30)
        occupancy_trend = self.get_kpi_history('occupancy_rate', 30)
        
        # Highlights
        highlights = []
        
        if revenue.value > 10000:
            highlights.append(f"Strong revenue: ${revenue.value:,.2f}")
        
        if occupancy.value > 85:
            highlights.append(f"High occupancy: {occupancy.value:.1f}%")
        
        # Concerns
        concerns = []
        
        cancellation_rate = self.calculate_metric('cancellation_rate', start_date, end_date)
        if cancellation_rate.value > 15:
            concerns.append(f"High cancellation rate: {cancellation_rate.value:.1f}%")
        
        no_show_rate = self.calculate_metric('no_show_rate', start_date, end_date)
        if no_show_rate.value > 8:
            concerns.append(f"High no-show rate: {no_show_rate.value:.1f}%")
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'kpis': {k: v.to_dict() for k, v in kpis.items()},
            'revenue': {
                'total': revenue.value,
                'trend': revenue_trend.to_dict()
            },
            'occupancy': {
                'average': occupancy.value,
                'trend': occupancy_trend.to_dict()
            },
            'highlights': highlights,
            'concerns': concerns,
            'recommendations': self._generate_recommendations(kpis)
        }
    
    def _generate_recommendations(self, kpis: Dict[str, KPIValue]) -> List[str]:
        """Generate recommendations based on KPI performance."""
        recommendations = []
        
        # Occupancy recommendations
        if kpis['occupancy_rate'].value < 70:
            recommendations.append(
                "Consider promotional pricing to increase occupancy during off-peak hours"
            )
        elif kpis['occupancy_rate'].value > 90:
            recommendations.append(
                "High occupancy detected - consider expanding capacity or implementing dynamic pricing"
            )
        
        # Cancellation recommendations
        if kpis['cancellation_rate'].value > 15:
            recommendations.append(
                "High cancellation rate - review cancellation policy and consider sending reminders"
            )
        
        # No-show recommendations
        if kpis['no_show_rate'].value > 8:
            recommendations.append(
                "High no-show rate - implement pre-authorization or deposit requirements"
            )
        
        # Customer satisfaction recommendations
        if kpis['customer_satisfaction'].value < 4.0:
            recommendations.append(
                "Customer satisfaction below target - review feedback and address common issues"
            )
        
        return recommendations
    
    def _format_as_csv(self, data: Any) -> str:
        """Format data as CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        if isinstance(data, dict):
            # Write headers
            writer.writerow(data.keys())
            # Write values
            writer.writerow([str(v) for v in data.values()])
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                writer.writerow(data[0].keys())
                for row in data:
                    writer.writerow([str(row.get(k, '')) for k in data[0].keys()])
        
        return output.getvalue()
    
    def _format_as_excel(self, data: Any) -> bytes:
        """Format data as Excel."""
        try:
            import pandas as pd
            
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame()
            
            # Save to bytes
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            return output.getvalue()
            
        except ImportError:
            logger.warning("pandas not available for Excel export")
            return str(data).encode()
    
    def _format_as_pdf(self, data: Any) -> bytes:
        """Format data as PDF."""
        # Placeholder - would use reportlab or similar
        return str(data).encode()
    
    # ========================================================================
    # Data Export
    # ========================================================================
    
    def export_data(
        self,
        entity_type: str,
        format: str = 'json',
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None
    ) -> Tuple[str, bytes]:
        """
        Export data for a specific entity.
        
        Args:
            entity_type: Type of entity to export
            format: Export format (json, csv, excel)
            filters: Optional filters
            fields: Fields to include
            
        Returns:
            Tuple of (filename, data)
        """
        data = []
        
        if entity_type == 'users':
            users = self.user_repo.find(**filters) if filters else self.user_repo.get_all()
            data = [self._serialize_entity(u, fields) for u in users]
        
        elif entity_type == 'vehicles':
            vehicles = self.vehicle_repo.find(**filters) if filters else self.vehicle_repo.get_all()
            data = [self._serialize_entity(v, fields) for v in vehicles]
        
        elif entity_type == 'reservations':
            reservations = self.reservation_repo.find(**filters) if filters else self.reservation_repo.get_all()
            data = [self._serialize_entity(r, fields) for r in reservations]
        
        elif entity_type == 'payments':
            payments = self.payment_repo.find(**filters) if filters else self.payment_repo.get_all()
            data = [self._serialize_entity(p, fields) for p in payments]
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f"{entity_type}_{timestamp}.json"
            content = json.dumps(data, default=str, indent=2).encode()
        elif format == 'csv':
            filename = f"{entity_type}_{timestamp}.csv"
            content = self._format_as_csv(data).encode()
        else:
            filename = f"{entity_type}_{timestamp}.txt"
            content = str(data).encode()
        
        return filename, content
    
    def _serialize_entity(self, entity: Any, fields: Optional[List[str]]) -> Dict:
        """Serialize an entity to dictionary."""
        if hasattr(entity, 'to_dict'):
            data = entity.to_dict()
        else:
            data = {}
            for column in entity.__table__.columns:
                if fields is None or column.name in fields:
                    value = getattr(entity, column.name)
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat()
                    elif isinstance(value, Enum):
                        value = value.value
                    elif isinstance(value, Decimal):
                        value = float(value)
                    data[column.name] = value
        
        return data


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main service
    'AnalyticsService',
    
    # Data models
    'TimeSeriesPoint',
    'TimeSeries',
    'MetricValue',
    'KPIDefinition',
    'KPIValue',
    'Report',
    'Forecast',
    
    # Exceptions
    'AnalyticsException',
    'MetricNotFoundException',
    'ReportGenerationException',
    'ForecastException',
    'DataInsufficientException',
]