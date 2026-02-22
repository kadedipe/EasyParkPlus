# parking-management/data/migrations/repositories/audit_repository.py
"""
Audit repository module for the parking management system.

This module provides repository classes for managing audit logs, compliance tracking,
data retention, and security auditing with comprehensive integration with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import hashlib
import hmac
import secrets
from uuid import uuid4
from enum import Enum

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Interval,
    Date, Text, JSON, BigInteger, Index
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.sql import expression

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
from ..models.enums import (
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    ComplianceStandard,
    RetentionAction,
    
    # User enums
    UserRole,
    
    # General enums
    CountryCode
)
from ..models.audit_models import (
    # Audit models
    AuditLog,
    AuditEvent,
    AuditDetail,
    AuditChange,
    AuditMetadata,
    
    # Compliance models
    ComplianceLog,
    ComplianceRequirement,
    ComplianceValidation,
    ComplianceReport,
    ComplianceEvidence,
    
    # Data retention models
    DataRetention,
    DataRetentionPolicy,
    DataRetentionJob,
    DataRetentionArchive,
    
    # Security audit models
    SecurityAudit,
    SecurityEvent,
    SecurityFinding,
    AccessAudit,
    
    # Archive models
    AuditArchive,
    ArchivedAudit,
    
    # Metrics models
    AuditMetrics,
    AuditSummary,
    
    # Export models
    AuditExport,
    AuditExportItem
)
from ..models.user_models import (
    User,
    UserSession
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class AuditLogNotFoundException(EntityNotFoundException):
    """Raised when an audit log is not found."""
    def __init__(self, log_id: Any):
        super().__init__("AuditLog", log_id)


class ComplianceRequirementNotFoundException(EntityNotFoundException):
    """Raised when a compliance requirement is not found."""
    def __init__(self, requirement_id: Any):
        super().__init__("ComplianceRequirement", requirement_id)


class DataRetentionPolicyNotFoundException(EntityNotFoundException):
    """Raised when a data retention policy is not found."""
    def __init__(self, policy_id: Any):
        super().__init__("DataRetentionPolicy", policy_id)


class AuditExportException(RepositoryException):
    """Raised when audit export fails."""
    def __init__(self, message: str):
        super().__init__(f"Audit export failed: {message}")


class ComplianceValidationException(RepositoryException):
    """Raised when compliance validation fails."""
    def __init__(self, requirement: str, details: Dict[str, Any]):
        self.requirement = requirement
        self.details = details
        super().__init__(f"Compliance validation failed for {requirement}: {details}")


class DataRetentionException(RepositoryException):
    """Raised when data retention operations fail."""
    def __init__(self, message: str):
        super().__init__(f"Data retention operation failed: {message}")


class AuditIntegrityException(RepositoryException):
    """Raised when audit log integrity is compromised."""
    def __init__(self, log_id: int, reason: str):
        self.log_id = log_id
        super().__init__(f"Audit log {log_id} integrity check failed: {reason}")


# ============================================================================
# Audit Log Repository
# ============================================================================

class AuditLogRepository(FullFeatureRepository[AuditLog, int]):
    """
    Repository for AuditLog entity with comprehensive audit logging features.
    
    This repository provides methods for creating, querying, and managing audit logs
    with full support for compliance requirements and data retention.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, AuditLog)
        self.searchable_fields = [
            'actor_email', 'actor_name', 'resource_id', 
            'ip_address', 'user_agent', 'details'
        ]
        
        # Retention configuration
        self.default_retention_days = {
            AuditSeverity.DEBUG: 30,
            AuditSeverity.INFO: 90,
            AuditSeverity.NOTICE: 180,
            AuditSeverity.WARNING: 365,
            AuditSeverity.ERROR: 730,
            AuditSeverity.CRITICAL: 1460,
            AuditSeverity.ALERT: 1460,
            AuditSeverity.EMERGENCY: 2555
        }
        
        # Integrity configuration
        self.enable_integrity_checks = True
        self.integrity_salt = secrets.token_hex(16)  # In production, store securely
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def log_action(
        self,
        actor_id: Optional[int],
        action: AuditAction,
        resource_type: AuditResourceType,
        resource_id: Optional[str] = None,
        category: AuditCategory = AuditCategory.SYSTEM,
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        changes: Optional[List[Dict[str, Any]]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            actor_id: ID of user performing action (None for system)
            action: Action being performed
            resource_type: Type of resource being acted upon
            resource_id: ID of resource (optional)
            category: Audit category
            severity: Severity level
            status: Action status
            details: Additional details
            changes: List of changes made
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session ID
            **kwargs: Additional audit attributes
            
        Returns:
            Created audit log
        """
        # Get actor info if user exists
        actor_email = None
        actor_name = None
        actor_role = None
        
        if actor_id:
            user = self.session.query(User).get(actor_id)
            if user:
                actor_email = user.email
                actor_name = f"{user.first_name} {user.last_name}".strip()
                # Get primary role
                if user.role_assignments:
                    actor_role = user.role_assignments[0].role.name
        
        # Create audit log
        audit_log = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            category=category,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=severity,
            status=status,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            created_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(audit_log)
        self.session.flush()
        
        # Add changes if provided
        if changes:
            for change_data in changes:
                change = AuditChange(
                    audit_log_id=audit_log.id,
                    field=change_data.get('field'),
                    old_value=change_data.get('old_value'),
                    new_value=change_data.get('new_value'),
                    change_type=change_data.get('change_type', 'update')
                )
                self.session.add(change)
        
        # Add metadata
        metadata = kwargs.get('metadata', {})
        if metadata:
            for key, value in metadata.items():
                meta = AuditMetadata(
                    audit_log_id=audit_log.id,
                    key=key,
                    value=json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                )
                self.session.add(meta)
        
        # Calculate integrity hash if enabled
        if self.enable_integrity_checks:
            self._calculate_integrity_hash(audit_log)
        
        self.session.flush()
        
        logger.debug(f"Created audit log {audit_log.id}: {action.value} on {resource_type.value}")
        return audit_log
    
    def get_user_audit_trail(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        actions: Optional[List[AuditAction]] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit trail for a specific user.
        
        Args:
            user_id: User ID
            from_date: Optional start date
            to_date: Optional end date
            actions: Optional action filter
            limit: Maximum number to return
            
        Returns:
            List of audit logs for the user
        """
        query = self.session.query(AuditLog).filter(
            AuditLog.actor_id == user_id
        )
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        if actions:
            query = query.filter(AuditLog.action.in_(actions))
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_resource_audit_trail(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit trail for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number to return
            
        Returns:
            List of audit logs for the resource
        """
        query = self.session.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_audit_logs_by_severity(
        self,
        severity: AuditSeverity,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """
        Get audit logs by severity level.
        
        Args:
            severity: Severity level
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number to return
            
        Returns:
            List of audit logs
        """
        query = self.session.query(AuditLog).filter(
            AuditLog.severity == severity
        )
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_audit_logs_by_action(
        self,
        action: AuditAction,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """
        Get audit logs by action type.
        
        Args:
            action: Action type
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number to return
            
        Returns:
            List of audit logs
        """
        query = self.session.query(AuditLog).filter(
            AuditLog.action == action
        )
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def search_audit_logs(
        self,
        query_str: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[AuditLog], Dict[str, Any]]:
        """
        Search audit logs with advanced filtering.
        
        Args:
            query_str: Search query string
            filters: Additional filters
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (audit_logs, pagination_info)
        """
        qb = self.query()
        
        # Apply text search
        if query_str:
            qb.search(query_str, self.searchable_fields)
        
        # Apply filters
        if filters:
            if 'actor_id' in filters and filters['actor_id']:
                qb.filter(AuditLog.actor_id == filters['actor_id'])
            
            if 'action' in filters and filters['action']:
                qb.filter(AuditLog.action == filters['action'])
            
            if 'category' in filters and filters['category']:
                qb.filter(AuditLog.category == filters['category'])
            
            if 'resource_type' in filters and filters['resource_type']:
                qb.filter(AuditLog.resource_type == filters['resource_type'])
            
            if 'resource_id' in filters and filters['resource_id']:
                qb.filter(AuditLog.resource_id == filters['resource_id'])
            
            if 'severity' in filters and filters['severity']:
                qb.filter(AuditLog.severity == filters['severity'])
            
            if 'status' in filters and filters['status']:
                qb.filter(AuditLog.status == filters['status'])
            
            if 'from_date' in filters and filters['from_date']:
                qb.filter(AuditLog.created_at >= filters['from_date'])
            
            if 'to_date' in filters and filters['to_date']:
                qb.filter(AuditLog.created_at <= filters['to_date'])
            
            if 'ip_address' in filters and filters['ip_address']:
                qb.filter(AuditLog.ip_address == filters['ip_address'])
        
        return qb.paginate(page, per_page)
    
    def get_audit_summary(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        group_by: str = 'day'
    ) -> List[AuditSummary]:
        """
        Get audit summary statistics.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            group_by: Grouping period ('hour', 'day', 'week', 'month')
            
        Returns:
            List of audit summaries
        """
        query = self.session.query(AuditLog)
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        # Group by time period
        if group_by == 'hour':
            time_group = func.date_trunc('hour', AuditLog.created_at)
        elif group_by == 'day':
            time_group = func.date_trunc('day', AuditLog.created_at)
        elif group_by == 'week':
            time_group = func.date_trunc('week', AuditLog.created_at)
        elif group_by == 'month':
            time_group = func.date_trunc('month', AuditLog.created_at)
        else:
            time_group = func.date_trunc('day', AuditLog.created_at)
        
        # Get counts by period
        results = []
        summaries = {}
        
        logs = query.order_by(AuditLog.created_at).all()
        
        for log in logs:
            period_key = self._get_period_key(log.created_at, group_by)
            
            if period_key not in summaries:
                summaries[period_key] = {
                    'period': period_key,
                    'total': 0,
                    'by_action': {},
                    'by_severity': {},
                    'by_category': {},
                    'by_status': {}
                }
            
            summaries[period_key]['total'] += 1
            summaries[period_key]['by_action'][log.action.value] = \
                summaries[period_key]['by_action'].get(log.action.value, 0) + 1
            summaries[period_key]['by_severity'][log.severity.value] = \
                summaries[period_key]['by_severity'].get(log.severity.value, 0) + 1
            summaries[period_key]['by_category'][log.category.value] = \
                summaries[period_key]['by_category'].get(log.category.value, 0) + 1
            summaries[period_key]['by_status'][log.status.value] = \
                summaries[period_key]['by_status'].get(log.status.value, 0) + 1
        
        # Convert to list and sort
        for period_key, data in summaries.items():
            summary = AuditSummary(
                period=period_key,
                total_count=data['total'],
                action_counts=data['by_action'],
                severity_counts=data['by_severity'],
                category_counts=data['by_category'],
                status_counts=data['by_status']
            )
            results.append(summary)
        
        return sorted(results, key=lambda x: x.period)
    
    def get_audit_metrics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AuditMetrics:
        """
        Get audit metrics.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            
        Returns:
            Audit metrics
        """
        query = self.session.query(AuditLog)
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        total_logs = query.count()
        
        # Count by severity
        severity_counts = {}
        for severity in AuditSeverity:
            count = query.filter(AuditLog.severity == severity).count()
            if count > 0:
                severity_counts[severity.value] = count
        
        # Count by category
        category_counts = {}
        for category in AuditCategory:
            count = query.filter(AuditLog.category == category).count()
            if count > 0:
                category_counts[category.value] = count
        
        # Count by action
        action_counts = {}
        for action in AuditAction:
            count = query.filter(AuditLog.action == action).count()
            if count > 0:
                action_counts[action.value] = count
        
        # Unique actors
        unique_actors = query.distinct(AuditLog.actor_id).count()
        
        # Failed actions rate
        failed = query.filter(AuditLog.status == AuditStatus.FAILURE).count()
        failure_rate = (failed / total_logs * 100) if total_logs > 0 else 0
        
        # Peak hours
        peak_hours = {}
        logs = query.all()
        for log in logs:
            hour = log.created_at.hour
            peak_hours[hour] = peak_hours.get(hour, 0) + 1
        
        metrics = AuditMetrics(
            period_start=from_date,
            period_end=to_date,
            total_logs=total_logs,
            unique_actors=unique_actors,
            failure_rate=failure_rate,
            severity_counts=severity_counts,
            category_counts=category_counts,
            action_counts=action_counts,
            peak_hours=peak_hours,
            calculated_at=datetime.utcnow()
        )
        
        return metrics
    
    # ========================================================================
    # Integrity Methods
    # ========================================================================
    
    def verify_integrity(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        repair: bool = False
    ) -> Dict[str, Any]:
        """
        Verify integrity of audit logs using hash chaining.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            repair: Whether to attempt repair of broken chains
            
        Returns:
            Dictionary with integrity check results
        """
        if not self.enable_integrity_checks:
            return {'enabled': False, 'message': 'Integrity checks are disabled'}
        
        query = self.session.query(AuditLog).order_by(AuditLog.created_at)
        
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        logs = query.all()
        
        if not logs:
            return {'verified': True, 'message': 'No logs to verify'}
        
        results = {
            'verified': True,
            'total_checked': len(logs),
            'failed': [],
            'repaired': []
        }
        
        previous_hash = None
        
        for i, log in enumerate(logs):
            # Recalculate hash
            calculated_hash = self._calculate_log_hash(log, previous_hash)
            
            if log.integrity_hash != calculated_hash:
                results['verified'] = False
                results['failed'].append({
                    'id': log.id,
                    'created_at': log.created_at.isoformat(),
                    'expected': log.integrity_hash,
                    'calculated': calculated_hash
                })
                
                if repair:
                    # Attempt repair
                    log.integrity_hash = calculated_hash
                    log.previous_hash = previous_hash
                    log.integrity_verified_at = datetime.utcnow()
                    log.integrity_verified_by = 'system'
                    
                    results['repaired'].append(log.id)
            
            previous_hash = calculated_hash
        
        if repair and results['repaired']:
            self.session.flush()
            logger.info(f"Repaired {len(results['repaired'])} audit logs")
        
        return results
    
    def _calculate_integrity_hash(self, audit_log: AuditLog) -> str:
        """Calculate integrity hash for an audit log."""
        # Get previous log's hash
        previous_log = (
            self.session.query(AuditLog)
            .filter(AuditLog.created_at < audit_log.created_at)
            .order_by(desc(AuditLog.created_at))
            .first()
        )
        
        previous_hash = previous_log.integrity_hash if previous_log else None
        audit_log.previous_hash = previous_hash
        
        # Calculate current hash
        hash_value = self._calculate_log_hash(audit_log, previous_hash)
        audit_log.integrity_hash = hash_value
        
        return hash_value
    
    def _calculate_log_hash(self, audit_log: AuditLog, previous_hash: Optional[str]) -> str:
        """Calculate hash for a single log entry."""
        # Create string representation of log data
        log_data = {
            'id': audit_log.id,
            'actor_id': audit_log.actor_id,
            'action': audit_log.action.value if audit_log.action else None,
            'resource_type': audit_log.resource_type.value if audit_log.resource_type else None,
            'resource_id': audit_log.resource_id,
            'created_at': audit_log.created_at.isoformat() if audit_log.created_at else None,
            'previous_hash': previous_hash,
            'salt': self.integrity_salt
        }
        
        # Add details if present
        if audit_log.details:
            log_data['details'] = audit_log.details
        
        # Create hash
        log_json = json.dumps(log_data, sort_keys=True)
        return hashlib.sha256(log_json.encode()).hexdigest()
    
    # ========================================================================
    # Export Methods
    # ========================================================================
    
    def export_audit_logs(
        self,
        export_format: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_changes: bool = True,
        include_metadata: bool = True,
        requested_by: Optional[int] = None
    ) -> AuditExport:
        """
        Export audit logs.
        
        Args:
            export_format: Export format (csv, json, xml)
            from_date: Optional start date
            to_date: Optional end date
            filters: Optional filters
            include_changes: Whether to include field changes
            include_metadata: Whether to include metadata
            requested_by: ID of user requesting export
            
        Returns:
            Audit export record
        """
        # Create export record
        export = AuditExport(
            export_id=str(uuid4()),
            format=export_format,
            filters=filters or {},
            from_date=from_date,
            to_date=to_date,
            include_changes=include_changes,
            include_metadata=include_metadata,
            requested_by=requested_by,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(export)
        self.session.flush()
        
        try:
            # Get logs to export
            query = self.session.query(AuditLog)
            
            if from_date:
                query = query.filter(AuditLog.created_at >= from_date)
            
            if to_date:
                query = query.filter(AuditLog.created_at <= to_date)
            
            if filters:
                if 'actions' in filters:
                    query = query.filter(AuditLog.action.in_(filters['actions']))
                if 'categories' in filters:
                    query = query.filter(AuditLog.category.in_(filters['categories']))
                if 'severities' in filters:
                    query = query.filter(AuditLog.severity.in_(filters['severities']))
                if 'resource_types' in filters:
                    query = query.filter(AuditLog.resource_type.in_(filters['resource_types']))
                if 'actor_ids' in filters:
                    query = query.filter(AuditLog.actor_id.in_(filters['actor_ids']))
            
            logs = query.order_by(AuditLog.created_at).all()
            
            # Create export items
            for log in logs:
                item = AuditExportItem(
                    export_id=export.id,
                    audit_log_id=log.id,
                    exported_data=self._format_log_for_export(log, export_format, include_changes, include_metadata)
                )
                self.session.add(item)
            
            export.total_items = len(logs)
            export.status = 'completed'
            export.completed_at = datetime.utcnow()
            
            logger.info(f"Exported {len(logs)} audit logs to {export_format}")
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            logger.error(f"Audit export failed: {e}")
            raise AuditExportException(str(e))
        
        self.session.flush()
        return export
    
    def _format_log_for_export(
        self,
        log: AuditLog,
        format: str,
        include_changes: bool,
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Format a log entry for export."""
        data = {
            'id': log.id,
            'timestamp': log.created_at.isoformat(),
            'actor_id': log.actor_id,
            'actor_email': log.actor_email,
            'actor_name': log.actor_name,
            'actor_role': log.actor_role,
            'action': log.action.value if log.action else None,
            'category': log.category.value if log.category else None,
            'resource_type': log.resource_type.value if log.resource_type else None,
            'resource_id': log.resource_id,
            'severity': log.severity.value if log.severity else None,
            'status': log.status.value if log.status else None,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'session_id': log.session_id,
            'details': log.details
        }
        
        if include_changes and log.changes:
            data['changes'] = [
                {
                    'field': c.field,
                    'old_value': c.old_value,
                    'new_value': c.new_value,
                    'change_type': c.change_type
                }
                for c in log.changes
            ]
        
        if include_metadata and log.metadata:
            data['metadata'] = {
                m.key: m.value for m in log.metadata
            }
        
        return data
    
    # ========================================================================
    # Archive Methods
    # ========================================================================
    
    def archive_old_logs(self, days: Optional[int] = None) -> DataRetentionJob:
        """
        Archive audit logs older than specified days.
        
        Args:
            days: Number of days (uses severity-based defaults if None)
            
        Returns:
            Data retention job record
        """
        job = DataRetentionJob(
            job_id=str(uuid4()),
            job_type='archive',
            status='running',
            started_at=datetime.utcnow()
        )
        
        self.session.add(job)
        self.session.flush()
        
        try:
            archived_count = 0
            now = datetime.utcnow()
            
            # Archive logs based on severity-specific retention
            for severity, retention_days in self.default_retention_days.items():
                cutoff = now - timedelta(days=days or retention_days)
                
                # Get logs to archive
                logs_to_archive = (
                    self.session.query(AuditLog)
                    .filter(
                        AuditLog.severity == severity,
                        AuditLog.created_at < cutoff
                    )
                    .all()
                )
                
                for log in logs_to_archive:
                    # Create archive record
                    archive = AuditArchive(
                        original_id=log.id,
                        archived_data=self._format_log_for_export(log, 'json', True, True),
                        archived_at=datetime.utcnow(),
                        retention_job_id=job.id,
                        original_created_at=log.created_at,
                        severity=log.severity,
                        action=log.action,
                        actor_id=log.actor_id
                    )
                    self.session.add(archive)
                    
                    # Delete original log
                    self.session.delete(log)
                    archived_count += 1
                
                job.processed_count += len(logs_to_archive)
            
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.result = {'archived_count': archived_count}
            
            logger.info(f"Archived {archived_count} audit logs")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            logger.error(f"Audit archive failed: {e}")
            raise DataRetentionException(str(e))
        
        self.session.flush()
        return job
    
    def restore_archived_log(
        self,
        archive_id: int,
        restored_by: Optional[int] = None
    ) -> ArchivedAudit:
        """
        Restore an archived audit log.
        
        Args:
            archive_id: Archive ID
            restored_by: ID of user restoring
            
        Returns:
            Restored audit record
        """
        archive = self.session.query(AuditArchive).get(archive_id)
        if not archive:
            raise EntityNotFoundException("AuditArchive", archive_id)
        
        # Create restored record
        restored = ArchivedAudit(
            archive_id=archive_id,
            restored_data=archive.archived_data,
            restored_at=datetime.utcnow(),
            restored_by=restored_by
        )
        
        self.session.add(restored)
        self.session.flush()
        
        logger.info(f"Restored archived audit log {archive_id}")
        return restored
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _get_period_key(self, dt: datetime, group_by: str) -> str:
        """Get period key for grouping."""
        if group_by == 'hour':
            return dt.strftime('%Y-%m-%d %H:00')
        elif group_by == 'day':
            return dt.strftime('%Y-%m-%d')
        elif group_by == 'week':
            # Get week start (Monday)
            week_start = dt - timedelta(days=dt.weekday())
            return week_start.strftime('%Y-%m-%d')
        elif group_by == 'month':
            return dt.strftime('%Y-%m')
        else:
            return dt.strftime('%Y-%m-%d')


# ============================================================================
# Compliance Repository
# ============================================================================

class ComplianceRepository(BaseRepository[ComplianceLog, int]):
    """Repository for compliance tracking."""
    
    def __init__(self, session: Session):
        super().__init__(session, ComplianceLog)
    
    def log_compliance_check(
        self,
        standard: ComplianceStandard,
        requirement: str,
        status: str,
        details: Optional[Dict] = None,
        checked_by: Optional[int] = None
    ) -> ComplianceLog:
        """Log a compliance check."""
        log = ComplianceLog(
            standard=standard,
            requirement=requirement,
            status=status,
            details=details or {},
            checked_by=checked_by,
            checked_at=datetime.utcnow()
        )
        
        self.session.add(log)
        self.session.flush()
        
        logger.info(f"Logged compliance check for {standard.value}: {requirement} = {status}")
        return log
    
    def get_compliance_status(
        self,
        standard: Optional[ComplianceStandard] = None
    ) -> Dict[str, Any]:
        """Get current compliance status."""
        query = self.session.query(ComplianceLog)
        
        if standard:
            query = query.filter(ComplianceLog.standard == standard)
        
        # Get latest check for each requirement
        latest_logs = {}
        logs = query.order_by(desc(ComplianceLog.checked_at)).all()
        
        for log in logs:
            key = f"{log.standard.value}:{log.requirement}"
            if key not in latest_logs:
                latest_logs[key] = log
        
        # Calculate overall compliance
        total = len(latest_logs)
        compliant = sum(1 for l in latest_logs.values() if l.status == 'compliant')
        non_compliant = sum(1 for l in latest_logs.values() if l.status == 'non-compliant')
        
        return {
            "total": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "percentage": (compliant / total * 100) if total > 0 else 0
        }