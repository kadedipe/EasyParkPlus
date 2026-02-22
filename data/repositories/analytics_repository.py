# parking-management/data/migrations/repositories/analytics_repository.py
"""
Analytics repository module for the parking management system.

This module provides repository classes for managing analytics, reports,
dashboards, and business intelligence with comprehensive integration
with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import hashlib
import secrets
from uuid import uuid4
from enum import Enum
from collections import defaultdict

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Interval,
    Date, Text, JSON, BigInteger, Index, distinct
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.sql import expression, label

from .base_repository import (
    BaseRepository,
    AuditableRepository,
    CacheableRepository,
    SearchableRepository,
    FullFeatureRepository,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    RepositoryException,
    QueryBuilder
)
from .parking_spot_repository import ParkingSpotRepository
from .reservation_repository import ReservationRepository
from .payment_repository import PaymentRepository
from .user_repository import UserRepository
from .vehicle_repository import VehicleRepository
from ..models.enums import (
    # Analytics enums
    ReportType,
    ReportFormat,
    DashboardType,
    MetricType,
    TimeGranularity,
    
    # Reservation enums
    ReservationStatus,
    ReservationType,
    
    # Payment enums
    PaymentStatus,
    PaymentMethodType,
    Currency,
    
    # Parking enums
    SpotType,
    SpotStatus,
    ZoneType,
    
    # Vehicle enums
    VehicleType,
    FuelType,
    
    # User enums
    UserRole,
    UserStatus,
    
    # Audit enums
    AuditAction,
    AuditSeverity
)
from ..models.analytics_models import (
    # Analytics models
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsDimension,
    AnalyticsFact,
    AnalyticsAggregate,
    
    # Report models
    Report,
    ReportSchedule,
    ReportExecution,
    ReportTemplate,
    ReportParameter,
    ReportOutput,
    
    # Dashboard models
    Dashboard,
    DashboardWidget,
    DashboardLayout,
    DashboardRefresh,
    
    # Metric models
    MetricDefinition,
    MetricValue,
    MetricThreshold,
    MetricAlert,
    
    # Forecast models
    Forecast,
    ForecastModel,
    ForecastPrediction,
    ForecastAccuracy,
    
    # KPI models
    KPI,
    KPITarget,
    KPIValue,
    KPITrend,
    
    # Export models
    DataExport,
    ExportFormat,
    ExportJob,
    
    # Cache models
    AnalyticsCache,
    QueryCache
)
from ..models.parking_models import (
    ParkingSpot,
    ParkingZone,
    SpotOccupancy
)
from ..models.reservation_models import (
    Reservation,
    ReservationPayment
)
from ..models.payment_models import (
    Payment,
    Invoice
)
from ..models.user_models import (
    User,
    UserSession
)
from ..models.vehicle_models import (
    Vehicle
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class ReportNotFoundException(EntityNotFoundException):
    """Raised when a report is not found."""
    def __init__(self, report_id: Any):
        super().__init__("Report", report_id)


class DashboardNotFoundException(EntityNotFoundException):
    """Raised when a dashboard is not found."""
    def __init__(self, dashboard_id: Any):
        super().__init__("Dashboard", dashboard_id)


class MetricNotFoundException(EntityNotFoundException):
    """Raised when a metric is not found."""
    def __init__(self, metric_id: Any):
        super().__init__("Metric", metric_id)


class ReportGenerationException(RepositoryException):
    """Raised when report generation fails."""
    def __init__(self, message: str, report_id: Optional[int] = None):
        self.report_id = report_id
        super().__init__(f"Report generation failed: {message}")


class DataExportException(RepositoryException):
    """Raised when data export fails."""
    def __init__(self, message: str):
        super().__init__(f"Data export failed: {message}")


class MetricThresholdExceededException(RepositoryException):
    """Raised when a metric exceeds its threshold."""
    def __init__(self, metric_name: str, value: float, threshold: float):
        self.metric_name = metric_name
        self.value = value
        self.threshold = threshold
        super().__init__(
            f"Metric {metric_name} exceeded threshold: {value} > {threshold}"
        )


class ForecastGenerationException(RepositoryException):
    """Raised when forecast generation fails."""
    def __init__(self, message: str):
        super().__init__(f"Forecast generation failed: {message}")


# ============================================================================
# Analytics Repository
# ============================================================================

class AnalyticsRepository(FullFeatureRepository[AnalyticsEvent, int]):
    """
    Repository for analytics events and metrics with comprehensive business intelligence features.
    
    This repository provides methods for tracking analytics events, calculating metrics,
    generating reports, and managing dashboards.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, AnalyticsEvent)
        
        # Initialize sub-repositories
        self.spot_repo = ParkingSpotRepository(session)
        self.reservation_repo = ReservationRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.user_repo = UserRepository(session)
        self.vehicle_repo = VehicleRepository(session)
        
        # Cache configuration
        self.cache_ttl = 300  # 5 minutes default
        self.enable_query_cache = True
    
    # ========================================================================
    # Event Tracking Methods
    # ========================================================================
    
    def track_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """
        Track an analytics event.
        
        Args:
            event_type: Type of event
            user_id: Optional user ID
            session_id: Optional session ID
            properties: Event properties
            context: Event context (browser, device, location, etc.)
            
        Returns:
            Created analytics event
        """
        event = AnalyticsEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            context=context or {},
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        self.session.add(event)
        self.session.flush()
        
        logger.debug(f"Tracked analytics event: {event_type}")
        return event
    
    def track_page_view(
        self,
        page: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        referrer: Optional[str] = None,
        duration: Optional[int] = None,
        **kwargs
    ) -> AnalyticsEvent:
        """Track a page view event."""
        properties = {
            'page': page,
            'referrer': referrer,
            'duration': duration,
            **kwargs
        }
        
        return self.track_event('page_view', user_id, session_id, properties)
    
    def track_user_action(
        self,
        action: str,
        user_id: int,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        result: Optional[str] = None,
        **kwargs
    ) -> AnalyticsEvent:
        """Track a user action event."""
        properties = {
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'result': result,
            **kwargs
        }
        
        return self.track_event('user_action', user_id, None, properties)
    
    def track_conversion(
        self,
        conversion_type: str,
        user_id: int,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        **kwargs
    ) -> AnalyticsEvent:
        """Track a conversion event."""
        properties = {
            'conversion_type': conversion_type,
            'value': value,
            'currency': currency,
            **kwargs
        }
        
        return self.track_event('conversion', user_id, None, properties)
    
    def get_user_events(
        self,
        user_id: int,
        event_types: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AnalyticsEvent]:
        """Get events for a specific user."""
        query = self.session.query(AnalyticsEvent).filter(
            AnalyticsEvent.user_id == user_id
        )
        
        if event_types:
            query = query.filter(AnalyticsEvent.event_type.in_(event_types))
        
        if from_date:
            query = query.filter(AnalyticsEvent.timestamp >= from_date)
        
        if to_date:
            query = query.filter(AnalyticsEvent.timestamp <= to_date)
        
        return query.order_by(desc(AnalyticsEvent.timestamp)).limit(limit).all()
    
    def get_event_funnel(
        self,
        steps: List[Dict[str, Any]],
        from_date: datetime,
        to_date: datetime,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze conversion funnel.
        
        Args:
            steps: List of funnel steps with event_type and optional filters
            from_date: Start date
            to_date: End date
            group_by: Optional grouping (day, week, month)
            
        Returns:
            Funnel analysis results
        """
        result = {
            'steps': [],
            'conversions': [],
            'dropoff_rates': []
        }
        
        previous_count = None
        
        for i, step in enumerate(steps):
            # Build query for this step
            query = self.session.query(AnalyticsEvent).filter(
                AnalyticsEvent.event_type == step['event_type'],
                AnalyticsEvent.timestamp.between(from_date, to_date)
            )
            
            # Apply step filters
            if 'filters' in step:
                for key, value in step['filters'].items():
                    query = query.filter(AnalyticsEvent.properties[key].astext == str(value))
            
            # Get unique users for this step
            if group_by == 'day':
                users = query.distinct(AnalyticsEvent.user_id, func.date(AnalyticsEvent.timestamp)).count()
            else:
                users = query.distinct(AnalyticsEvent.user_id).count()
            
            step_data = {
                'step': i + 1,
                'name': step.get('name', step['event_type']),
                'event_type': step['event_type'],
                'users': users
            }
            
            result['steps'].append(step_data)
            
            # Calculate conversion
            if previous_count is not None:
                conversion_rate = (users / previous_count * 100) if previous_count > 0 else 0
                dropoff_rate = 100 - conversion_rate
                
                result['conversions'].append({
                    'from_step': i,
                    'to_step': i + 1,
                    'rate': round(conversion_rate, 2)
                })
                
                result['dropoff_rates'].append({
                    'step': i + 1,
                    'rate': round(dropoff_rate, 2)
                })
            
            previous_count = users
        
        return result
    
    # ========================================================================
    # Metric Calculation Methods
    # ========================================================================
    
    def calculate_metric(
        self,
        metric_name: str,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[str] = None
    ) -> MetricValue:
        """
        Calculate a metric value.
        
        Args:
            metric_name: Name of the metric to calculate
            from_date: Start date
            to_date: End date
            filters: Additional filters
            group_by: Optional grouping
            
        Returns:
            Calculated metric value
        """
        # Get metric definition
        metric_def = self._get_metric_definition(metric_name)
        
        # Calculate based on metric type
        if metric_def.metric_type == MetricType.COUNT:
            value = self._calculate_count_metric(metric_def, from_date, to_date, filters)
        elif metric_def.metric_type == MetricType.SUM:
            value = self._calculate_sum_metric(metric_def, from_date, to_date, filters)
        elif metric_def.metric_type == MetricType.AVERAGE:
            value = self._calculate_avg_metric(metric_def, from_date, to_date, filters)
        elif metric_def.metric_type == MetricType.RATIO:
            value = self._calculate_ratio_metric(metric_def, from_date, to_date, filters)
        elif metric_def.metric_type == MetricType.PERCENTAGE:
            value = self._calculate_percentage_metric(metric_def, from_date, to_date, filters)
        else:
            value = 0
        
        # Create metric value record
        metric_value = MetricValue(
            metric_id=metric_def.id,
            value=value,
            from_date=from_date,
            to_date=to_date,
            filters=filters,
            group_by=group_by,
            calculated_at=datetime.utcnow()
        )
        
        self.session.add(metric_value)
        self.session.flush()
        
        # Check thresholds
        self._check_metric_thresholds(metric_def, value)
        
        return metric_value
    
    def get_daily_metrics(
        self,
        metric_names: List[str],
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get daily values for multiple metrics.
        
        Args:
            metric_names: List of metric names
            days: Number of days to retrieve
            
        Returns:
            Dictionary mapping metric names to daily values
        """
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days - 1)
        
        result = {}
        
        for metric_name in metric_names:
            metric_def = self._get_metric_definition(metric_name)
            
            values = (
                self.session.query(MetricValue)
                .filter(
                    MetricValue.metric_id == metric_def.id,
                    func.date(MetricValue.to_date) >= start_date
                )
                .order_by(MetricValue.to_date)
                .all()
            )
            
            result[metric_name] = [
                {
                    'date': v.to_date.isoformat() if isinstance(v.to_date, datetime) else v.to_date,
                    'value': float(v.value)
                }
                for v in values
            ]
        
        return result
    
    def get_metric_trend(
        self,
        metric_name: str,
        periods: int = 7,
        period_type: str = 'day'
    ) -> KPITrend:
        """
        Calculate trend for a metric.
        
        Args:
            metric_name: Metric name
            periods: Number of periods to analyze
            period_type: Type of period ('day', 'week', 'month')
            
        Returns:
            KPI trend analysis
        """
        metric_def = self._get_metric_definition(metric_name)
        
        end_date = datetime.utcnow()
        
        if period_type == 'day':
            start_date = end_date - timedelta(days=periods)
            interval = timedelta(days=1)
        elif period_type == 'week':
            start_date = end_date - timedelta(weeks=periods)
            interval = timedelta(days=7)
        elif period_type == 'month':
            start_date = end_date - timedelta(days=30 * periods)
            interval = timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=periods)
            interval = timedelta(days=1)
        
        # Get values for each period
        values = []
        current_date = start_date
        
        while current_date <= end_date:
            period_end = current_date + interval
            
            value = self._get_metric_value_for_period(
                metric_def,
                current_date,
                period_end
            )
            
            values.append({
                'period': current_date.isoformat(),
                'value': float(value)
            })
            
            current_date = period_end
        
        # Calculate trend
        if len(values) >= 2:
            first_value = values[0]['value']
            last_value = values[-1]['value']
            
            if first_value > 0:
                percent_change = ((last_value - first_value) / first_value) * 100
            else:
                percent_change = 0
            
            # Determine direction
            if last_value > first_value:
                direction = 'up'
            elif last_value < first_value:
                direction = 'down'
            else:
                direction = 'flat'
        else:
            percent_change = 0
            direction = 'flat'
        
        trend = KPITrend(
            metric_id=metric_def.id,
            period_type=period_type,
            values=values,
            percent_change=round(percent_change, 2),
            direction=direction,
            calculated_at=datetime.utcnow()
        )
        
        return trend
    
    def _get_metric_definition(self, metric_name: str) -> MetricDefinition:
        """Get metric definition by name."""
        metric_def = (
            self.session.query(MetricDefinition)
            .filter(MetricDefinition.name == metric_name)
            .first()
        )
        
        if not metric_def:
            # Create default metric definition
            metric_def = MetricDefinition(
                name=metric_name,
                display_name=metric_name.replace('_', ' ').title(),
                metric_type=MetricType.COUNT,
                unit='count',
                is_active=True
            )
            self.session.add(metric_def)
            self.session.flush()
        
        return metric_def
    
    def _calculate_count_metric(
        self,
        metric_def: MetricDefinition,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict]
    ) -> float:
        """Calculate count metric."""
        # Implementation depends on the metric
        if metric_def.name == 'total_reservations':
            return self.reservation_repo.count(
                created_at_between=(from_date, to_date),
                **(filters or {})
            )
        elif metric_def.name == 'active_users':
            return self.user_repo.count(
                status=UserStatus.ACTIVE,
                **(filters or {})
            )
        elif metric_def.name == 'total_parking_spots':
            return self.spot_repo.count(**filters or {})
        elif metric_def.name == 'occupied_spots':
            return self.spot_repo.count(
                status=SpotStatus.OCCUPIED,
                **(filters or {})
            )
        else:
            return 0
    
    def _calculate_sum_metric(
        self,
        metric_def: MetricDefinition,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict]
    ) -> float:
        """Calculate sum metric."""
        if metric_def.name == 'total_revenue':
            payments = self.payment_repo.get_payments_by_date_range(
                from_date, to_date,
                statuses=[PaymentStatus.PAID]
            )
            return float(sum(p.amount for p in payments))
        elif metric_def.name == 'total_parking_duration':
            reservations = self.reservation_repo.get_reservations_in_range(
                from_date, to_date,
                statuses=[ReservationStatus.COMPLETED]
            )
            total_minutes = sum(
                (r.end_time - r.start_time).total_seconds() / 60
                for r in reservations
            )
            return float(total_minutes)
        else:
            return 0
    
    def _calculate_avg_metric(
        self,
        metric_def: MetricDefinition,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict]
    ) -> float:
        """Calculate average metric."""
        if metric_def.name == 'avg_parking_duration':
            reservations = self.reservation_repo.get_reservations_in_range(
                from_date, to_date,
                statuses=[ReservationStatus.COMPLETED]
            )
            if not reservations:
                return 0
            total_minutes = sum(
                (r.end_time - r.start_time).total_seconds() / 60
                for r in reservations
            )
            return float(total_minutes / len(reservations))
        elif metric_def.name == 'avg_revenue_per_reservation':
            payments = self.payment_repo.get_payments_by_date_range(
                from_date, to_date,
                statuses=[PaymentStatus.PAID]
            )
            if not payments:
                return 0
            total = sum(p.amount for p in payments)
            return float(total / len(payments))
        else:
            return 0
    
    def _calculate_ratio_metric(
        self,
        metric_def: MetricDefinition,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict]
    ) -> float:
        """Calculate ratio metric."""
        if metric_def.name == 'occupancy_rate':
            total_spots = self.spot_repo.count()
            occupied_spots = self.spot_repo.count(status=SpotStatus.OCCUPIED)
            return (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        elif metric_def.name == 'conversion_rate':
            # Visitors to reservations
            visitors = self.session.query(func.count(distinct(AnalyticsEvent.user_id))).filter(
                AnalyticsEvent.event_type == 'page_view',
                AnalyticsEvent.timestamp.between(from_date, to_date)
            ).scalar() or 0
            
            reservations = self.reservation_repo.count(
                created_at_between=(from_date, to_date)
            )
            
            return (reservations / visitors * 100) if visitors > 0 else 0
        else:
            return 0
    
    def _calculate_percentage_metric(
        self,
        metric_def: MetricDefinition,
        from_date: datetime,
        to_date: datetime,
        filters: Optional[Dict]
    ) -> float:
        """Calculate percentage metric."""
        if metric_def.name == 'cancellation_rate':
            total = self.reservation_repo.count(
                created_at_between=(from_date, to_date)
            )
            cancelled = self.reservation_repo.count(
                created_at_between=(from_date, to_date),
                status=ReservationStatus.CANCELLED
            )
            return (cancelled / total * 100) if total > 0 else 0
        elif metric_def.name == 'no_show_rate':
            total = self.reservation_repo.count(
                created_at_between=(from_date, to_date)
            )
            no_show = self.reservation_repo.count(
                created_at_between=(from_date, to_date),
                status=ReservationStatus.NO_SHOW
            )
            return (no_show / total * 100) if total > 0 else 0
        else:
            return 0
    
    def _get_metric_value_for_period(
        self,
        metric_def: MetricDefinition,
        period_start: datetime,
        period_end: datetime
    ) -> float:
        """Get metric value for a specific period."""
        # Check cache first
        cache_key = f"metric:{metric_def.name}:{period_start}:{period_end}"
        
        if self.enable_query_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # Calculate value
        value = self.calculate_metric(
            metric_def.name,
            period_start,
            period_end
        ).value
        
        # Cache result
        if self.enable_query_cache:
            self._put_in_cache(cache_key, value)
        
        return value
    
    def _check_metric_thresholds(
        self,
        metric_def: MetricDefinition,
        value: float
    ) -> None:
        """Check if metric exceeds any thresholds."""
        thresholds = (
            self.session.query(MetricThreshold)
            .filter(
                MetricThreshold.metric_id == metric_def.id,
                MetricThreshold.is_active == True
            )
            .all()
        )
        
        for threshold in thresholds:
            exceeded = False
            
            if threshold.operator == 'gt' and value > threshold.value:
                exceeded = True
            elif threshold.operator == 'lt' and value < threshold.value:
                exceeded = True
            elif threshold.operator == 'gte' and value >= threshold.value:
                exceeded = True
            elif threshold.operator == 'lte' and value <= threshold.value:
                exceeded = True
            elif threshold.operator == 'eq' and value == threshold.value:
                exceeded = True
            
            if exceeded:
                # Create alert
                alert = MetricAlert(
                    metric_id=metric_def.id,
                    threshold_id=threshold.id,
                    value=value,
                    threshold_value=threshold.value,
                    severity=threshold.severity,
                    message=f"Metric {metric_def.name} {threshold.operator} {threshold.value}",
                    created_at=datetime.utcnow()
                )
                self.session.add(alert)
                self.session.flush()
                
                logger.warning(f"Metric threshold exceeded: {metric_def.name} = {value}")
                
                # Optionally raise exception for critical thresholds
                if threshold.severity == 'critical':
                    raise MetricThresholdExceededException(
                        metric_def.name,
                        value,
                        threshold.value
                    )
    
    # ========================================================================
    # KPI Methods
    # ========================================================================
    
    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """
        Get key performance indicators for dashboard.
        
        Returns:
            Dictionary with KPI values
        """
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # Current occupancy
        total_spots = self.spot_repo.count()
        occupied_spots = self.spot_repo.count(status=SpotStatus.OCCUPIED)
        available_spots = self.spot_repo.count(
            status=SpotStatus.AVAILABLE
        )
        occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        
        # Today's performance
        reservations_today = self.reservation_repo.count(
            start_time_between=(today_start, today_end)
        )
        
        revenue_today = sum(
            p.amount for p in self.payment_repo.get_payments_by_date_range(
                today_start, today_end,
                statuses=[PaymentStatus.PAID]
            )
        )
        
        # Weekly trends
        reservations_week = self.reservation_repo.count(
            created_at_between=(week_start, now)
        )
        
        revenue_week = sum(
            p.amount for p in self.payment_repo.get_payments_by_date_range(
                week_start, now,
                statuses=[PaymentStatus.PAID]
            )
        )
        
        # User metrics
        active_users = self.user_repo.count(status=UserStatus.ACTIVE)
        new_users_week = self.user_repo.count(
            created_at_between=(week_start, now)
        )
        
        # Vehicle metrics
        total_vehicles = self.vehicle_repo.count()
        
        # Average values
        avg_duration = self._calculate_avg_metric(
            self._get_metric_definition('avg_parking_duration'),
            week_start, now, None
        )
        
        avg_revenue = self._calculate_avg_metric(
            self._get_metric_definition('avg_revenue_per_reservation'),
            week_start, now, None
        )
        
        return {
            'current': {
                'total_spots': total_spots,
                'occupied_spots': occupied_spots,
                'available_spots': available_spots,
                'occupancy_rate': round(occupancy_rate, 2),
                'active_users': active_users,
                'total_vehicles': total_vehicles
            },
            'today': {
                'reservations': reservations_today,
                'revenue': float(revenue_today)
            },
            'week': {
                'reservations': reservations_week,
                'revenue': float(revenue_week),
                'new_users': new_users_week,
                'avg_duration_minutes': round(avg_duration, 2),
                'avg_revenue': round(avg_revenue, 2)
            }
        }
    
    def get_revenue_analytics(
        self,
        from_date: datetime,
        to_date: datetime,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get revenue analytics.
        
        Args:
            from_date: Start date
            to_date: End date
            group_by: Grouping period ('day', 'week', 'month')
            
        Returns:
            Revenue analytics
        """
        payments = self.payment_repo.get_payments_by_date_range(
            from_date, to_date,
            statuses=[PaymentStatus.PAID]
        )
        
        # Group by period
        period_revenue = defaultdict(float)
        period_count = defaultdict(int)
        
        for payment in payments:
            if group_by == 'day':
                key = payment.created_at.date().isoformat()
            elif group_by == 'week':
                # Get week start (Monday)
                week_start = payment.created_at.date() - timedelta(
                    days=payment.created_at.weekday()
                )
                key = week_start.isoformat()
            elif group_by == 'month':
                key = payment.created_at.strftime('%Y-%m')
            else:
                key = payment.created_at.date().isoformat()
            
            period_revenue[key] += float(payment.amount)
            period_count[key] += 1
        
        # Payment methods breakdown
        method_revenue = defaultdict(float)
        for payment in payments:
            method = payment.payment_method_type.value
            method_revenue[method] += float(payment.amount)
        
        # Daily average
        num_days = (to_date - from_date).days or 1
        daily_avg = sum(period_revenue.values()) / num_days
        
        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'summary': {
                'total_revenue': float(sum(period_revenue.values())),
                'total_transactions': len(payments),
                'average_transaction': float(sum(p.amount for p in payments) / len(payments)) if payments else 0,
                'daily_average': float(daily_avg)
            },
            'by_period': [
                {'period': k, 'revenue': v, 'transactions': period_count[k]}
                for k, v in sorted(period_revenue.items())
            ],
            'by_method': [
                {'method': k, 'revenue': v}
                for k, v in method_revenue.items()
            ]
        }
    
    def get_occupancy_analytics(
        self,
        from_date: datetime,
        to_date: datetime,
        group_by: str = 'hour'
    ) -> Dict[str, Any]:
        """
        Get occupancy analytics.
        
        Args:
            from_date: Start date
            to_date: End date
            group_by: Grouping period ('hour', 'day', 'week')
            
        Returns:
            Occupancy analytics
        """
        # Get all spots
        total_spots = self.spot_repo.count()
        
        # Get occupancy data from SpotOccupancy
        occupancies = (
            self.session.query(SpotOccupancy)
            .filter(
                SpotOccupancy.start_time < to_date,
                or_(
                    SpotOccupancy.end_time.is_(None),
                    SpotOccupancy.end_time > from_date
                )
            )
            .all()
        )
        
        # Group by period
        period_occupancy = defaultdict(list)
        
        for occ in occupancies:
            occ_start = max(occ.start_time, from_date)
            occ_end = min(occ.end_time or to_date, to_date)
            
            # Generate time points based on grouping
            current = occ_start
            while current < occ_end:
                if group_by == 'hour':
                    key = current.strftime('%Y-%m-%d %H:00')
                    next_point = current + timedelta(hours=1)
                elif group_by == 'day':
                    key = current.date().isoformat()
                    next_point = current + timedelta(days=1)
                elif group_by == 'week':
                    week_start = current.date() - timedelta(days=current.weekday())
                    key = week_start.isoformat()
                    next_point = current + timedelta(days=7)
                else:
                    key = current.date().isoformat()
                    next_point = current + timedelta(days=1)
                
                period_occupancy[key].append(1)
                current = next_point
        
        # Calculate occupancy rates
        period_rates = {}
        for period, count in period_occupancy.items():
            # Estimate number of time slots in period
            if group_by == 'hour':
                slots = 1
            elif group_by == 'day':
                slots = 24
            elif group_by == 'week':
                slots = 168
            else:
                slots = 24
            
            max_occupancy = total_spots * slots
            actual_occupancy = len(count)
            rate = (actual_occupancy / max_occupancy * 100) if max_occupancy > 0 else 0
            
            period_rates[period] = rate
        
        # Spot type breakdown
        spot_type_occupancy = {}
        for spot_type in SpotType:
            type_spots = self.spot_repo.count(spot_type=spot_type)
            type_occupied = self.spot_repo.count(
                spot_type=spot_type,
                status=SpotStatus.OCCUPIED
            )
            spot_type_occupancy[spot_type.value] = {
                'total': type_spots,
                'occupied': type_occupied,
                'rate': (type_occupied / type_spots * 100) if type_spots > 0 else 0
            }
        
        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'summary': {
                'total_spots': total_spots,
                'average_occupancy_rate': round(sum(period_rates.values()) / len(period_rates), 2) if period_rates else 0,
                'peak_occupancy': max(period_rates.values()) if period_rates else 0,
                'lowest_occupancy': min(period_rates.values()) if period_rates else 0
            },
            'by_period': [
                {'period': k, 'occupancy_rate': round(v, 2)}
                for k, v in sorted(period_rates.items())
            ],
            'by_spot_type': spot_type_occupancy
        }
    
    def get_user_analytics(
        self,
        from_date: datetime,
        to_date: datetime,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get user analytics.
        
        Args:
            from_date: Start date
            to_date: End date
            group_by: Grouping period
            
        Returns:
            User analytics
        """
        # New user signups
        new_users = (
            self.session.query(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            )
            .filter(User.created_at.between(from_date, to_date))
            .group_by(func.date(User.created_at))
            .all()
        )
        
        # Active users (with sessions)
        active_users = (
            self.session.query(
                func.date(UserSession.last_activity).label('date'),
                func.count(distinct(UserSession.user_id)).label('count')
            )
            .filter(UserSession.last_activity.between(from_date, to_date))
            .group_by(func.date(UserSession.last_activity))
            .all()
        )
        
        # User role distribution
        role_distribution = {}
        for role in UserRole:
            count = self.user_repo.count(role=role)
            if count > 0:
                role_distribution[role.value] = count
        
        # User status distribution
        status_distribution = {}
        for status in UserStatus:
            count = self.user_repo.count(status=status)
            if count > 0:
                status_distribution[status.value] = count
        
        # Convert to dictionaries
        new_users_dict = {str(r.date): r.count for r in new_users}
        active_users_dict = {str(r.date): r.count for r in active_users}
        
        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'summary': {
                'total_users': self.user_repo.count(),
                'new_users': sum(new_users_dict.values()),
                'active_users': sum(active_users_dict.values()),
                'avg_daily_new_users': sum(new_users_dict.values()) / ((to_date - from_date).days or 1)
            },
            'by_day': [
                {
                    'date': date_str,
                    'new_users': new_users_dict.get(date_str, 0),
                    'active_users': active_users_dict.get(date_str, 0)
                }
                for date_str in sorted(set(new_users_dict.keys()) | set(active_users_dict.keys()))
            ],
            'by_role': role_distribution,
            'by_status': status_distribution
        }
    
    def get_vehicle_analytics(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Get vehicle analytics.
        
        Args:
            from_date: Start date
            to_date: End date
            
        Returns:
            Vehicle analytics
        """
        # Vehicle type distribution
        type_distribution = {}
        for vtype in VehicleType:
            count = self.vehicle_repo.count(vehicle_type=vtype)
            if count > 0:
                type_distribution[vtype.value] = count
        
        # Fuel type distribution
        fuel_distribution = {}
        for fuel in FuelType:
            count = self.vehicle_repo.count(fuel_type=fuel)
            if count > 0:
                fuel_distribution[fuel.value] = count
        
        # Top vehicle makes
        top_makes = (
            self.session.query(
                Vehicle.make,
                func.count(Vehicle.id).label('count')
            )
            .group_by(Vehicle.make)
            .order_by(desc('count'))
            .limit(10)
            .all()
        )
        
        # Vehicle age distribution
        current_year = datetime.utcnow().year
        vehicles = self.vehicle_repo.get_all()
        
        age_groups = {
            '0-2 years': 0,
            '3-5 years': 0,
            '6-10 years': 0,
            '10+ years': 0
        }
        
        for vehicle in vehicles:
            age = current_year - vehicle.year
            if age <= 2:
                age_groups['0-2 years'] += 1
            elif age <= 5:
                age_groups['3-5 years'] += 1
            elif age <= 10:
                age_groups['6-10 years'] += 1
            else:
                age_groups['10+ years'] += 1
        
        return {
            'summary': {
                'total_vehicles': len(vehicles)
            },
            'by_type': type_distribution,
            'by_fuel': fuel_distribution,
            'by_age': age_groups,
            'top_makes': [
                {'make': m[0], 'count': m[1]}
                for m in top_makes
            ]
        }
    
    # ========================================================================
    # Report Methods
    # ========================================================================
    
    def create_report(
        self,
        name: str,
        report_type: ReportType,
        parameters: Dict[str, Any],
        schedule: Optional[Dict] = None,
        created_by: Optional[int] = None
    ) -> Report:
        """
        Create a new report.
        
        Args:
            name: Report name
            report_type: Type of report
            parameters: Report parameters
            schedule: Optional schedule configuration
            created_by: User creating the report
            
        Returns:
            Created report
        """
        report = Report(
            name=name,
            report_type=report_type,
            parameters=parameters,
            schedule=schedule,
            created_by=created_by,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(report)
        self.session.flush()
        
        logger.info(f"Created report {report.id}: {name}")
        return report
    
    def generate_report(
        self,
        report_id: int,
        format: ReportFormat = ReportFormat.JSON,
        parameters: Optional[Dict] = None
    ) -> ReportExecution:
        """
        Generate a report.
        
        Args:
            report_id: Report ID
            format: Output format
            parameters: Override parameters
            
        Returns:
            Report execution record
        """
        report = self.session.query(Report).get(report_id)
        if not report:
            raise ReportNotFoundException(report_id)
        
        # Create execution record
        execution = ReportExecution(
            report_id=report_id,
            format=format,
            parameters=parameters or report.parameters,
            status='running',
            started_at=datetime.utcnow()
        )
        
        self.session.add(execution)
        self.session.flush()
        
        try:
            # Generate report data based on type
            if report.report_type == ReportType.REVENUE:
                data = self._generate_revenue_report(execution)
            elif report.report_type == ReportType.OCCUPANCY:
                data = self._generate_occupancy_report(execution)
            elif report.report_type == ReportType.USER_ACTIVITY:
                data = self._generate_user_report(execution)
            elif report.report_type == ReportType.VEHICLE:
                data = self._generate_vehicle_report(execution)
            elif report.report_type == ReportType.RESERVATION:
                data = self._generate_reservation_report(execution)
            else:
                data = self._generate_custom_report(execution)
            
            # Format output
            output = self._format_report_output(data, format)
            
            # Create output record
            report_output = ReportOutput(
                execution_id=execution.id,
                format=format,
                data=output,
                file_size=len(str(output)) if output else 0
            )
            self.session.add(report_output)
            
            execution.status = 'completed'
            execution.completed_at = datetime.utcnow()
            execution.row_count = len(data) if isinstance(data, list) else 1
            
            logger.info(f"Generated report {report_id} in {format.value}")
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            logger.error(f"Report generation failed: {e}")
            raise ReportGenerationException(str(e), report_id)
        
        self.session.flush()
        return execution
    
    def schedule_report(
        self,
        report_id: int,
        cron_expression: str,
        recipients: List[str],
        format: ReportFormat = ReportFormat.PDF
    ) -> ReportSchedule:
        """
        Schedule a report for regular execution.
        
        Args:
            report_id: Report ID
            cron_expression: Cron schedule expression
            recipients: Email recipients
            format: Output format
            
        Returns:
            Report schedule
        """
        report = self.session.query(Report).get(report_id)
        if not report:
            raise ReportNotFoundException(report_id)
        
        schedule = ReportSchedule(
            report_id=report_id,
            cron_expression=cron_expression,
            recipients=recipients,
            format=format,
            is_active=True,
            next_run_at=self._calculate_next_run(cron_expression),
            created_at=datetime.utcnow()
        )
        
        self.session.add(schedule)
        self.session.flush()
        
        logger.info(f"Scheduled report {report_id} with cron: {cron_expression}")
        return schedule
    
    def get_scheduled_reports(self) -> List[ReportSchedule]:
        """Get all scheduled reports due for execution."""
        now = datetime.utcnow()
        
        return (
            self.session.query(ReportSchedule)
            .filter(
                ReportSchedule.is_active == True,
                ReportSchedule.next_run_at <= now
            )
            .all()
        )
    
    def _generate_revenue_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate revenue report."""
        params = execution.parameters
        
        from_date = datetime.fromisoformat(params.get('from_date')) if params.get('from_date') else datetime.utcnow() - timedelta(days=30)
        to_date = datetime.fromisoformat(params.get('to_date')) if params.get('to_date') else datetime.utcnow()
        group_by = params.get('group_by', 'day')
        
        return self.get_revenue_analytics(from_date, to_date, group_by)
    
    def _generate_occupancy_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate occupancy report."""
        params = execution.parameters
        
        from_date = datetime.fromisoformat(params.get('from_date')) if params.get('from_date') else datetime.utcnow() - timedelta(days=7)
        to_date = datetime.fromisoformat(params.get('to_date')) if params.get('to_date') else datetime.utcnow()
        group_by = params.get('group_by', 'hour')
        
        return self.get_occupancy_analytics(from_date, to_date, group_by)
    
    def _generate_user_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate user activity report."""
        params = execution.parameters
        
        from_date = datetime.fromisoformat(params.get('from_date')) if params.get('from_date') else datetime.utcnow() - timedelta(days=30)
        to_date = datetime.fromisoformat(params.get('to_date')) if params.get('to_date') else datetime.utcnow()
        group_by = params.get('group_by', 'day')
        
        return self.get_user_analytics(from_date, to_date, group_by)
    
    def _generate_vehicle_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate vehicle report."""
        params = execution.parameters
        
        from_date = datetime.fromisoformat(params.get('from_date')) if params.get('from_date') else datetime.utcnow() - timedelta(days=30)
        to_date = datetime.fromisoformat(params.get('to_date')) if params.get('to_date') else datetime.utcnow()
        
        return self.get_vehicle_analytics(from_date, to_date)
    
    def _generate_reservation_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate reservation report."""
        params = execution.parameters
        
        from_date = datetime.fromisoformat(params.get('from_date')) if params.get('from_date') else datetime.utcnow() - timedelta(days=30)
        to_date = datetime.fromisoformat(params.get('to_date')) if params.get('to_date') else datetime.utcnow()
        
        # Get reservation statistics
        stats = self.reservation_repo.get_reservation_statistics(from_date, to_date)
        
        # Get detailed reservations
        reservations = self.reservation_repo.get_reservations_in_range(
            from_date, to_date
        )
        
        return {
            'statistics': stats,
            'reservations': [
                {
                    'id': r.id,
                    'confirmation_code': r.confirmation_code,
                    'user_id': r.user_id,
                    'spot_id': r.spot_id,
                    'start_time': r.start_time.isoformat(),
                    'end_time': r.end_time.isoformat(),
                    'status': r.status.value,
                    'total_amount': float(r.total_amount) if r.total_amount else None
                }
                for r in reservations
            ]
        }
    
    def _generate_custom_report(self, execution: ReportExecution) -> List[Dict]:
        """Generate custom report based on query."""
        # This would handle custom SQL or query building
        return []
    
    def _format_report_output(
        self,
        data: Any,
        format: ReportFormat
    ) -> Any:
        """Format report output."""
        if format == ReportFormat.JSON:
            return json.dumps(data, default=str)
        elif format == ReportFormat.CSV:
            # Convert to CSV
            if isinstance(data, dict):
                # Flatten dictionary for CSV
                rows = []
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        rows.append({key: json.dumps(value, default=str)})
                    else:
                        rows.append({key: value})
                return rows
            return data
        elif format == ReportFormat.PDF:
            # Would generate PDF
            return data
        elif format == ReportFormat.EXCEL:
            # Would generate Excel
            return data
        else:
            return data
    
    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression."""
        # This is a placeholder - implement actual cron parsing
        return datetime.utcnow() + timedelta(days=1)
    
    # ========================================================================
    # Dashboard Methods
    # ========================================================================
    
    def create_dashboard(
        self,
        name: str,
        dashboard_type: DashboardType,
        layout: Dict[str, Any],
        created_by: Optional[int] = None
    ) -> Dashboard:
        """
        Create a new dashboard.
        
        Args:
            name: Dashboard name
            dashboard_type: Type of dashboard
            layout: Dashboard layout configuration
            created_by: User creating the dashboard
            
        Returns:
            Created dashboard
        """
        dashboard = Dashboard(
            name=name,
            dashboard_type=dashboard_type,
            layout=layout,
            created_by=created_by,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(dashboard)
        self.session.flush()
        
        logger.info(f"Created dashboard {dashboard.id}: {name}")
        return dashboard
    
    def add_widget(
        self,
        dashboard_id: int,
        widget_type: str,
        title: str,
        metric_name: Optional[str] = None,
        configuration: Optional[Dict] = None,
        position: Optional[Dict] = None
    ) -> DashboardWidget:
        """
        Add a widget to a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            widget_type: Type of widget
            title: Widget title
            metric_name: Optional metric name
            configuration: Widget configuration
            position: Widget position
            
        Returns:
            Created widget
        """
        dashboard = self.session.query(Dashboard).get(dashboard_id)
        if not dashboard:
            raise DashboardNotFoundException(dashboard_id)
        
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            widget_type=widget_type,
            title=title,
            metric_name=metric_name,
            configuration=configuration or {},
            position=position or {},
            created_at=datetime.utcnow()
        )
        
        self.session.add(widget)
        self.session.flush()
        
        logger.info(f"Added widget {widget.id} to dashboard {dashboard_id}")
        return widget
    
    def refresh_dashboard(self, dashboard_id: int) -> DashboardRefresh:
        """
        Refresh dashboard data.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard refresh record
        """
        dashboard = self.session.query(Dashboard).get(dashboard_id)
        if not dashboard:
            raise DashboardNotFoundException(dashboard_id)
        
        refresh = DashboardRefresh(
            dashboard_id=dashboard_id,
            status='running',
            started_at=datetime.utcnow()
        )
        
        self.session.add(refresh)
        self.session.flush()
        
        try:
            # Refresh each widget
            for widget in dashboard.widgets:
                if widget.metric_name:
                    # Calculate metric value
                    value = self.calculate_metric(
                        widget.metric_name,
                        datetime.utcnow() - timedelta(days=30),
                        datetime.utcnow()
                    )
                    
                    # Store in widget data
                    if not widget.data:
                        widget.data = {}
                    widget.data['last_value'] = float(value.value)
                    widget.data['last_refresh'] = datetime.utcnow().isoformat()
            
            refresh.status = 'completed'
            refresh.completed_at = datetime.utcnow()
            refresh.widgets_updated = len(dashboard.widgets)
            
            logger.info(f"Refreshed dashboard {dashboard_id}")
            
        except Exception as e:
            refresh.status = 'failed'
            refresh.error_message = str(e)
            logger.error(f"Dashboard refresh failed: {e}")
        
        self.session.flush()
        return refresh
    
    def get_dashboard_data(self, dashboard_id: int) -> Dict[str, Any]:
        """
        Get current data for a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard data
        """
        dashboard = self.session.query(Dashboard).get(dashboard_id)
        if not dashboard:
            raise DashboardNotFoundException(dashboard_id)
        
        widgets_data = []
        
        for widget in dashboard.widgets:
            widget_data = {
                'id': widget.id,
                'type': widget.widget_type,
                'title': widget.title,
                'position': widget.position,
                'data': widget.data or {}
            }
            
            # Get current metric value if applicable
            if widget.metric_name and widget.data and 'last_value' in widget.data:
                widget_data['value'] = widget.data['last_value']
            
            widgets_data.append(widget_data)
        
        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'type': dashboard.dashboard_type.value,
                'layout': dashboard.layout
            },
            'widgets': widgets_data,
            'last_refresh': max(
                (r.completed_at for r in dashboard.refreshes if r.completed_at),
                default=None
            )
        }
    
    # ========================================================================
    # Forecast Methods
    # ========================================================================
    
    def generate_forecast(
        self,
        metric_name: str,
        periods: int = 30,
        model_type: str = 'arima',
        confidence_level: float = 0.95
    ) -> Forecast:
        """
        Generate forecast for a metric.
        
        Args:
            metric_name: Metric to forecast
            periods: Number of periods to forecast
            model_type: Forecasting model type
            confidence_level: Confidence level for intervals
            
        Returns:
            Forecast result
        """
        metric_def = self._get_metric_definition(metric_name)
        
        # Get historical data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=periods * 3)  # Use 3x periods for training
        
        historical = self.get_daily_metrics([metric_name], (end_date - start_date).days)
        
        if not historical or metric_name not in historical:
            raise ForecastGenerationException(f"No historical data for {metric_name}")
        
        historical_values = [v['value'] for v in historical[metric_name]]
        
        # This is a placeholder - implement actual forecasting model
        # In production, use statsmodels, prophet, or similar
        
        # Simple linear trend forecast
        import numpy as np
        from scipy import stats
        
        x = np.arange(len(historical_values))
        y = np.array(historical_values)
        
        # Fit linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Generate forecasts
        forecasts = []
        lower_bounds = []
        upper_bounds = []
        
        last_x = len(historical_values)
        
        for i in range(1, periods + 1):
            x_pred = last_x + i
            y_pred = intercept + slope * x_pred
            
            # Simple confidence interval
            std_error = std_err * np.sqrt(1 + 1/len(x) + (x_pred - np.mean(x))**2 / np.sum((x - np.mean(x))**2))
            margin = stats.t.ppf((1 + confidence_level) / 2, len(x) - 2) * std_error
            
            forecasts.append(float(y_pred))
            lower_bounds.append(float(y_pred - margin))
            upper_bounds.append(float(y_pred + margin))
        
        # Create forecast record
        forecast = Forecast(
            metric_id=metric_def.id,
            model_type=model_type,
            periods=periods,
            confidence_level=confidence_level,
            forecasts=forecasts,
            lower_bounds=lower_bounds,
            upper_bounds=upper_bounds,
            historical_data=historical_values,
            generated_at=datetime.utcnow()
        )
        
        self.session.add(forecast)
        self.session.flush()
        
        # Calculate accuracy if we have actual values
        self._calculate_forecast_accuracy(forecast)
        
        logger.info(f"Generated forecast for {metric_name}")
        return forecast
    
    def _calculate_forecast_accuracy(self, forecast: Forecast) -> None:
        """Calculate forecast accuracy against actual values."""
        # This would compare forecasted vs actual values
        # Placeholder implementation
        pass
    
    # ========================================================================
    # Data Export Methods
    # ========================================================================
    
    def export_data(
        self,
        export_type: str,
        format: str,
        parameters: Dict[str, Any],
        requested_by: Optional[int] = None
    ) -> ExportJob:
        """
        Export data to file.
        
        Args:
            export_type: Type of data to export
            format: Export format
            parameters: Export parameters
            requested_by: User requesting export
            
        Returns:
            Export job
        """
        job = ExportJob(
            job_id=str(uuid4()),
            export_type=export_type,
            format=format,
            parameters=parameters,
            requested_by=requested_by,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(job)
        self.session.flush()
        
        try:
            # Get data based on export type
            if export_type == 'reservations':
                data = self._export_reservations(parameters)
            elif export_type == 'payments':
                data = self._export_payments(parameters)
            elif export_type == 'users':
                data = self._export_users(parameters)
            elif export_type == 'vehicles':
                data = self._export_vehicles(parameters)
            elif export_type == 'audit_logs':
                data = self._export_audit_logs(parameters)
            else:
                data = []
            
            # Format data
            formatted_data = self._format_export_data(data, format)
            
            # Store result
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.result = {
                'row_count': len(data),
                'file_size': len(str(formatted_data))
            }
            job.file_data = formatted_data
            
            logger.info(f"Exported {len(data)} records to {format}")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            logger.error(f"Export failed: {e}")
            raise DataExportException(str(e))
        
        self.session.flush()
        return job
    
    def _export_reservations(self, parameters: Dict) -> List[Dict]:
        """Export reservation data."""
        from_date = parameters.get('from_date')
        to_date = parameters.get('to_date')
        
        if from_date:
            from_date = datetime.fromisoformat(from_date)
        if to_date:
            to_date = datetime.fromisoformat(to_date)
        
        reservations = self.reservation_repo.get_reservations_in_range(
            from_date or datetime.utcnow() - timedelta(days=30),
            to_date or datetime.utcnow()
        )
        
        return [
            {
                'id': r.id,
                'confirmation_code': r.confirmation_code,
                'user_id': r.user_id,
                'spot_id': r.spot_id,
                'vehicle_id': r.vehicle_id,
                'start_time': r.start_time.isoformat(),
                'end_time': r.end_time.isoformat(),
                'status': r.status.value,
                'total_amount': float(r.total_amount) if r.total_amount else None,
                'created_at': r.created_at.isoformat()
            }
            for r in reservations
        ]
    
    def _export_payments(self, parameters: Dict) -> List[Dict]:
        """Export payment data."""
        from_date = parameters.get('from_date')
        to_date = parameters.get('to_date')
        
        if from_date:
            from_date = datetime.fromisoformat(from_date)
        if to_date:
            to_date = datetime.fromisoformat(to_date)
        
        payments = self.payment_repo.get_payments_by_date_range(
            from_date or datetime.utcnow() - timedelta(days=30),
            to_date or datetime.utcnow()
        )
        
        return [
            {
                'id': p.id,
                'user_id': p.user_id,
                'amount': float(p.amount),
                'currency': p.currency.value,
                'status': p.status.value,
                'payment_method': p.payment_method_type.value,
                'transaction_id': p.transaction_id,
                'created_at': p.created_at.isoformat()
            }
            for p in payments
        ]
    
    def _export_users(self, parameters: Dict) -> List[Dict]:
        """Export user data."""
        users = self.user_repo.get_all()
        
        return [
            {
                'id': u.id,
                'email': u.email,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'status': u.status.value,
                'created_at': u.created_at.isoformat(),
                'last_login': u.last_login_at.isoformat() if u.last_login_at else None
            }
            for u in users
        ]
    
    def _export_vehicles(self, parameters: Dict) -> List[Dict]:
        """Export vehicle data."""
        vehicles = self.vehicle_repo.get_all()
        
        return [
            {
                'id': v.id,
                'license_plate': v.license_plate,
                'make': v.make,
                'model': v.model,
                'year': v.year,
                'vehicle_type': v.vehicle_type.value,
                'status': v.status.value,
                'created_at': v.created_at.isoformat()
            }
            for v in vehicles
        ]
    
    def _export_audit_logs(self, parameters: Dict) -> List[Dict]:
        """Export audit log data."""
        from_date = parameters.get('from_date')
        to_date = parameters.get('to_date')
        
        if from_date:
            from_date = datetime.fromisoformat(from_date)
        if to_date:
            to_date = datetime.fromisoformat(to_date)
        
        query = self.session.query(AuditLog)
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        logs = query.limit(parameters.get('limit', 10000)).all()
        
        return [
            {
                'id': l.id,
                'actor_id': l.actor_id,
                'action': l.action.value if l.action else None,
                'resource_type': l.resource_type.value if l.resource_type else None,
                'resource_id': l.resource_id,
                'severity': l.severity.value if l.severity else None,
                'ip_address': l.ip_address,
                'created_at': l.created_at.isoformat()
            }
            for l in logs
        ]
    
    def _format_export_data(self, data: List[Dict], format: str) -> str:
        """Format data for export."""
        if format == 'json':
            return json.dumps(data, default=str, indent=2)
        elif format == 'csv':
            if not data:
                return ""
            # Simple CSV conversion
            headers = data[0].keys()
            rows = [",".join(headers)]
            for row in data:
                rows.append(",".join(str(row.get(h, "")) for h in headers))
            return "\n".join(rows)
        else:
            return str(data)
    
    # ========================================================================
    # Cache Methods
    # ========================================================================
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_entry = (
            self.session.query(AnalyticsCache)
            .filter(
                AnalyticsCache.cache_key == key,
                AnalyticsCache.expires_at > datetime.utcnow()
            )
            .first()
        )
        
        if cache_entry:
            return json.loads(cache_entry.cache_value)
        return None
    
    def _put_in_cache(self, key: str, value: Any) -> None:
        """Put value in cache."""
        cache_entry = AnalyticsCache(
            cache_key=key,
            cache_value=json.dumps(value, default=str),
            expires_at=datetime.utcnow() + timedelta(seconds=self.cache_ttl),
            created_at=datetime.utcnow()
        )
        
        self.session.add(cache_entry)
        self.session.flush()
    
    def clear_cache(self) -> int:
        """Clear expired cache entries."""
        result = (
            self.session.query(AnalyticsCache)
            .filter(AnalyticsCache.expires_at <= datetime.utcnow())
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# Report Repository
# ============================================================================

class ReportRepository(BaseRepository[Report, int]):
    """Repository for Report entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Report)
    
    def get_reports_by_type(
        self,
        report_type: ReportType,
        active_only: bool = True
    ) -> List[Report]:
        """Get reports by type."""
        query = self.session.query(Report).filter(
            Report.report_type == report_type
        )
        
        if active_only:
            query = query.filter(Report.is_active == True)
        
        return query.all()
    
    def get_user_reports(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Report]:
        """Get reports created by a user."""
        query = self.session.query(Report).filter(
            Report.created_by == user_id
        )
        
        if active_only:
            query = query.filter(Report.is_active == True)
        
        return query.all()
    
    def get_recent_executions(
        self,
        report_id: int,
        limit: int = 10
    ) -> List[ReportExecution]:
        """Get recent executions of a report."""
        return (
            self.session.query(ReportExecution)
            .filter(ReportExecution.report_id == report_id)
            .order_by(desc(ReportExecution.started_at))
            .limit(limit)
            .all()
        )


# ============================================================================
# Dashboard Repository
# ============================================================================

class DashboardRepository(BaseRepository[Dashboard, int]):
    """Repository for Dashboard entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Dashboard)
    
    def get_dashboards_by_type(
        self,
        dashboard_type: DashboardType,
        active_only: bool = True
    ) -> List[Dashboard]:
        """Get dashboards by type."""
        query = self.session.query(Dashboard).filter(
            Dashboard.dashboard_type == dashboard_type
        )
        
        if active_only:
            query = query.filter(Dashboard.is_active == True)
        
        return query.all()
    
    def get_user_dashboards(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Dashboard]:
        """Get dashboards created by a user."""
        query = self.session.query(Dashboard).filter(
            Dashboard.created_by == user_id
        )
        
        if active_only:
            query = query.filter(Dashboard.is_active == True)
        
        return query.all()
    
    def clone_dashboard(
        self,
        dashboard_id: int,
        new_name: str,
        user_id: int
    ) -> Dashboard:
        """Clone an existing dashboard."""
        original = self.get_or_fail(dashboard_id)
        
        # Create new dashboard
        new_dashboard = Dashboard(
            name=new_name,
            dashboard_type=original.dashboard_type,
            layout=original.layout,
            created_by=user_id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(new_dashboard)
        self.session.flush()
        
        # Clone widgets
        for widget in original.widgets:
            new_widget = DashboardWidget(
                dashboard_id=new_dashboard.id,
                widget_type=widget.widget_type,
                title=widget.title,
                metric_name=widget.metric_name,
                configuration=widget.configuration,
                position=widget.position
            )
            self.session.add(new_widget)
        
        self.session.flush()
        
        logger.info(f"Cloned dashboard {dashboard_id} to {new_dashboard.id}")
        return new_dashboard


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'AnalyticsRepository',
    'ReportRepository',
    'DashboardRepository',
    
    # Exceptions
    'ReportNotFoundException',
    'DashboardNotFoundException',
    'MetricNotFoundException',
    'ReportGenerationException',
    'DataExportException',
    'MetricThresholdExceededException',
    'ForecastGenerationException',
]