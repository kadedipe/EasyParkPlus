"""
Audit log repository.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit import AuditLog, AuditAction
from ...schemas.audit import AuditLogCreate, AuditLogUpdate, AuditLogFilter
from .base import BaseRepository


class AuditRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogUpdate]):
    """
    Repository for audit log operations.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(AuditLog, db_session)
    
    async def create_with_context(
        self,
        obj_in: AuditLogCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Create audit log with request context.
        
        Args:
            obj_in: Audit log data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            AuditLog: Created audit log
        """
        obj_in_data = obj_in.model_dump()
        
        if ip_address:
            obj_in_data["ip_address"] = ip_address
        if user_agent:
            obj_in_data["user_agent"] = user_agent
        
        db_obj = AuditLog(**obj_in_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def get_user_activity(
        self,
        user_id: str,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get user activity logs.
        
        Args:
            user_id: User ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum records
            
        Returns:
            List[AuditLog]: User activity logs
        """
        query = select(AuditLog).where(AuditLog.user_id == user_id)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_resource_history(
        self,
        resource: str,
        resource_id: str,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Get resource modification history.
        
        Args:
            resource: Resource type
            resource_id: Resource ID
            limit: Maximum records
            
        Returns:
            List[AuditLog]: Resource history
        """
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource == resource,
                    AuditLog.resource_id == resource_id
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def filter(
        self,
        filter_params: AuditLogFilter,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AuditLog]:
        """
        Filter audit logs with criteria.
        
        Args:
            filter_params: Filter parameters
            skip: Records to skip
            limit: Maximum records
            sort_by: Sort field
            sort_order: Sort order
            
        Returns:
            List[AuditLog]: Filtered logs
        """
        query = select(AuditLog)
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
                query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def count_filtered(self, filter_params: AuditLogFilter) -> int:
        """
        Count filtered audit logs.
        
        Args:
            filter_params: Filter parameters
            
        Returns:
            int: Count of logs
        """
        query = select(func.count()).select_from(AuditLog)
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
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def cleanup_old_logs(self, days: int) -> int:
        """
        Delete logs older than specified days.
        
        Args:
            days: Number of days to retain
            
        Returns:
            int: Number of deleted logs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(AuditLog).where(AuditLog.created_at < cutoff_date)
        result = await self.db.execute(query)
        old_logs = result.scalars().all()
        
        for log in old_logs:
            await self.db.delete(log)
        
        await self.db.flush()
        return len(old_logs)
    
    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict[str, Any]: Statistics
        """
        # Build date filter
        date_filter = []
        if start_date:
            date_filter.append(AuditLog.created_at >= start_date)
        if end_date:
            date_filter.append(AuditLog.created_at <= end_date)
        
        # Total count
        total_query = select(func.count()).select_from(AuditLog)
        if date_filter:
            total_query = total_query.where(and_(*date_filter))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()
        
        # Actions by type
        type_query = (
            select(AuditLog.action, func.count().label("count"))
            .group_by(AuditLog.action)
        )
        if date_filter:
            type_query = type_query.where(and_(*date_filter))
        type_result = await self.db.execute(type_query)
        by_type = {row[0].value: row[1] for row in type_result}
        
        # Actions by user (top 10)
        user_query = (
            select(AuditLog.username, func.count().label("count"))
            .where(AuditLog.username.isnot(None))
            .group_by(AuditLog.username)
            .order_by(desc("count"))
            .limit(10)
        )
        if date_filter:
            user_query = user_query.where(and_(*date_filter))
        user_result = await self.db.execute(user_query)
        by_user = {row[0] or "Unknown": row[1] for row in user_result}
        
        # Actions by resource
        resource_query = (
            select(AuditLog.resource, func.count().label("count"))
            .group_by(AuditLog.resource)
        )
        if date_filter:
            resource_query = resource_query.where(and_(*date_filter))
        resource_result = await self.db.execute(resource_query)
        by_resource = {row[0]: row[1] for row in resource_result}
        
        return {
            "total_actions": total,
            "actions_by_type": by_type,
            "actions_by_user": by_user,
            "actions_by_resource": by_resource
        }