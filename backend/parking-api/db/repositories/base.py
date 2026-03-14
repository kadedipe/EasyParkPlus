"""
Base repository pattern implementation.
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Union
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from ..base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository with common database operations.
    """
    
    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db_session: Database session
        """
        self.model = model
        self.db = db_session
    
    async def get(self, id: str) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Optional[ModelType]: Found record or None
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            **filters: Additional filters
            
        Returns:
            List[ModelType]: List of records
        """
        query = select(self.model)
        
        # Apply filters
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create new record.
        
        Args:
            obj_in: Creation data
            
        Returns:
            ModelType: Created record
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update record.
        
        Args:
            db_obj: Existing database object
            obj_in: Update data
            
        Returns:
            ModelType: Updated record
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: str) -> Optional[ModelType]:
        """
        Delete record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Optional[ModelType]: Deleted record or None
        """
        db_obj = await self.get(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.flush()
        return db_obj
    
    async def count(self, **filters) -> int:
        """
        Count records with optional filters.
        
        Args:
            **filters: Filters to apply
            
        Returns:
            int: Total count
        """
        query = select(func.count()).select_from(self.model)
        
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def exists(self, id: str) -> bool:
        """
        Check if record exists by ID.
        
        Args:
            id: Record ID
            
        Returns:
            bool: True if exists
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.first() is not None
    
    async def bulk_create(self, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        Create multiple records.
        
        Args:
            objs_in: List of creation data
            
        Returns:
            List[ModelType]: Created records
        """
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump()
            db_obj = self.model(**obj_in_data)
            self.db.add(db_obj)
            db_objs.append(db_obj)
        
        await self.db.flush()
        
        for db_obj in db_objs:
            await self.db.refresh(db_obj)
        
        return db_objs
    
    async def update_multi(
        self,
        *,
        filters: Dict[str, Any],
        values: Dict[str, Any]
    ) -> int:
        """
        Update multiple records matching filters.
        
        Args:
            filters: Filters to identify records
            values: Values to update
            
        Returns:
            int: Number of records updated
        """
        stmt = update(self.model)
        
        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        
        # Set values
        stmt = stmt.values(**values)
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
    
    async def delete_multi(self, **filters) -> int:
        """
        Delete multiple records matching filters.
        
        Args:
            **filters: Filters to identify records
            
        Returns:
            int: Number of records deleted
        """
        stmt = delete(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount