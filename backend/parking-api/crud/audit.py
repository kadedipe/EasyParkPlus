"""
Audit log CRUD operations.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, asc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select, func

from ..models.audit import AuditLog, AuditAction
from ..schemas.audit import (
    AuditLogCreate,
    AuditLogUpdate,
    AuditLogFilter,
    AuditRetentionPolicy
)
from .base import CRUDBase


class CRUDAuditLog(CRUDBase[AuditLog, AuditLogCreate, AuditLogUpdate]):
    """
    CRUD operations for AuditLog model.
    """
    
    def __init__(self):
        super().__init__(AuditLog)
    
    async def create_audit_log(
        self,
        db: AsyncSession,
        *,
        obj_in: AuditLogCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Create a new audit log entry.
        
        Args:
            db: Database session
            obj_in: Audit log creation data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            AuditLog: Created audit log entry
        """
        # Add IP and user agent if provided
        obj_in_data = obj_in.model_dump()
        if ip_address:
            obj_in_data["ip_address"] = ip_address
        if user_agent:
            obj_in_data["user_agent"] = user_agent
        
        db_obj = AuditLog(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """
        Get audit logs by user ID.
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List[AuditLog]: List of audit logs
        """
        query = select(AuditLog).where(AuditLog.user_id == user_id)
        
        # Apply date filters
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_resource(
        self,
        db: AsyncSession,
        *,
        resource: str,
        resource_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs by resource.
        
        Args:
            db: Database session
            resource: Resource name
            resource_id: Optional resource ID
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[AuditLog]: List of audit logs
        """
        query = select(AuditLog).where(AuditLog.resource == resource)
        
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_action(
        self,
        db: AsyncSession,
        *,
        action: AuditAction,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs by action type.
        
        Args:
            db: Database session
            action: Audit action
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[AuditLog]: List of audit logs
        """
        query = select(AuditLog).where(AuditLog.action == action)
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def filter_audit_logs(
        self,
        db: AsyncSession,
        *,
        filter_params: AuditLogFilter,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AuditLog]:
        """
        Filter audit logs based on criteria.
        
        Args:
            db: Database session
            filter_params: Filter parameters
            skip: Number of records to skip
            limit: Maximum number of records
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            List[AuditLog]: Filtered audit logs
        """
        query = select(AuditLog)
        
        # Build filter conditions
        conditions = []
        
        if filter_params.user_id:
            conditions.append(AuditLog.user_id == filter_params.user_id)
        
        if filter_params.username:
            conditions.append(AuditLog.username.ilike(f"%{filter_params.username}%"))
        
        if filter_params.action:
            conditions.append(AuditLog.action == filter_params.action)
        
        if filter_params.resource:
            conditions.append(AuditLog.resource == filter_params.resource)
        
        if filter_params.resource_id:
            conditions.append(AuditLog.resource_id == filter_params.resource_id)
        
        if filter_params.ip_address:
            conditions.append(AuditLog.ip_address == filter_params.ip_address)
        
        if filter_params.start_date:
            conditions.append(AuditLog.created_at >= filter_params.start_date)
        
        if filter_params.end_date:
            conditions.append(AuditLog.created_at <= filter_params.end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        if hasattr(AuditLog, sort_by):
            sort_column = getattr(AuditLog, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(AuditLog.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        filter_params: AuditLogFilter
    ) -> int:
        """
        Count filtered audit logs.
        
        Args:
            db: Database session
            filter_params: Filter parameters
            
        Returns:
            int: Count of filtered logs
        """
        query = select(func.count()).select_from(AuditLog)
        
        # Build filter conditions
        conditions = []
        
        if filter_params.user_id:
            conditions.append(AuditLog.user_id == filter_params.user_id)
        
        if filter_params.username:
            conditions.append(AuditLog.username.ilike(f"%{filter_params.username}%"))
        
        if filter_params.action:
            conditions.append(AuditLog.action == filter_params.action)
        
        if filter_params.resource:
            conditions.append(AuditLog.resource == filter_params.resource)
        
        if filter_params.resource_id:
            conditions.append(AuditLog.resource_id == filter_params.resource_id)
        
        if filter_params.ip_address:
            conditions.append(AuditLog.ip_address == filter_params.ip_address)
        
        if filter_params.start_date:
            conditions.append(AuditLog.created_at >= filter_params.start_date)
        
        if filter_params.end_date:
            conditions.append(AuditLog.created_at <= filter_params.end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        return result.scalar()
    
    async def get_statistics(
        self,
        db: AsyncSession,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            db: Database session
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        # Base query with date filters
        base_query = select(AuditLog)
        conditions = []
        
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Total count
        total_count_query = select(func.count()).select_from(AuditLog)
        if conditions:
            total_count_query = total_count_query.where(and_(*conditions))
        total_count_result = await db.execute(total_count_query)
        total_count = total_count_result.scalar()
        
        # Actions by type
        actions_query = (
            select(AuditLog.action, func.count().label("count"))
            .group_by(AuditLog.action)
        )
        if conditions:
            actions_query = actions_query.where(and_(*conditions))
        actions_result = await db.execute(actions_query)
        actions_by_type = {str(row[0]): row[1] for row in actions_result}
        
        # Actions by user
        users_query = (
            select(AuditLog.username, func.count().label("count"))
            .where(AuditLog.username.isnot(None))
            .group_by(AuditLog.username)
            .order_by(desc("count"))
            .limit(10)
        )
        if conditions:
            users_query = users_query.where(and_(*conditions))
        users_result = await db.execute(users_query)
        actions_by_user = {row[0] or "Unknown": row[1] for row in users_result}
        
        # Actions by resource
        resources_query = (
            select(AuditLog.resource, func.count().label("count"))
            .group_by(AuditLog.resource)
        )
        if conditions:
            resources_query = resources_query.where(and_(*conditions))
        resources_result = await db.execute(resources_query)
        actions_by_resource = {row[0]: row[1] for row in resources_result}
        
        # Top users
        top_users_query = (
            select(
                AuditLog.user_id,
                AuditLog.username,
                func.count().label("count")
            )
            .where(AuditLog.user_id.isnot(None))
            .group_by(AuditLog.user_id, AuditLog.username)
            .order_by(desc("count"))
            .limit(5)
        )
        if conditions:
            top_users_query = top_users_query.where(and_(*conditions))
        top_users_result = await db.execute(top_users_query)
        top_users = [
            {
                "user_id": str(row[0]) if row[0] else None,
                "username": row[1],
                "count": row[2]
            }
            for row in top_users_result
        ]
        
        # Recent actions
        recent_actions_query = (
            select(AuditLog.action)
            .order_by(desc(AuditLog.created_at))
            .limit(10)
        )
        if conditions:
            recent_actions_query = recent_actions_query.where(and_(*conditions))
        recent_actions_result = await db.execute(recent_actions_query)
        recent_actions = [str(row[0]) for row in recent_actions_result]
        
        return {
            "total_actions": total_count,
            "actions_by_type": actions_by_type,
            "actions_by_user": actions_by_user,
            "actions_by_resource": actions_by_resource,
            "top_users": top_users,
            "recent_actions": recent_actions
        }
    
    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        *,
        policy: AuditRetentionPolicy
    ) -> int:
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            db: Database session
            policy: Retention policy
            
        Returns:
            int: Number of logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=policy.days)
        
        # Delete old logs
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    
    async def get_user_activity_summary(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dict[str, Any]: User activity summary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total actions
        total_query = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date
                )
            )
        )
        total_result = await db.execute(total_query)
        total_actions = total_result.scalar()
        
        # Actions by type
        actions_query = (
            select(AuditLog.action, func.count().label("count"))
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date
                )
            )
            .group_by(AuditLog.action)
        )
        actions_result = await db.execute(actions_query)
        actions_by_type = {str(row[0]): row[1] for row in actions_result}
        
        # Daily activity
        daily_query = (
            select(
                func.date(AuditLog.created_at).label("date"),
                func.count().label("count")
            )
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date
                )
            )
            .group_by(func.date(AuditLog.created_at))
            .order_by("date")
        )
        daily_result = await db.execute(daily_query)
        daily_activity = {str(row[0]): row[1] for row in daily_result}
        
        # Last login
        last_login_query = (
            select(AuditLog.created_at)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.action == AuditAction.LOGIN
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        last_login_result = await db.execute(last_login_query)
        last_login = last_login_result.scalar_one_or_none()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_actions": total_actions,
            "actions_by_type": actions_by_type,
            "daily_activity": daily_activity,
            "last_login": last_login.isoformat() if last_login else None
        }


# Create singleton instance
audit = CRUDAuditLog()