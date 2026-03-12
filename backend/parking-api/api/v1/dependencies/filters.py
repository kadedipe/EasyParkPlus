"""
Filter dependencies for list endpoints.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
from pydantic import BaseModel, Field
from fastapi import Query, Request
from sqlalchemy import and_, or_

from ....utils.logger import logger


class FilterParams(BaseModel):
    """
    Base filter parameters.
    """
    search: Optional[str] = Field(None, description="Search term")
    
    class Config:
        arbitrary_types_allowed = True


class DateRangeFilter(BaseModel):
    """
    Date range filter.
    """
    from_date: Optional[Union[datetime, date]] = Field(None, description="Start date")
    to_date: Optional[Union[datetime, date]] = Field(None, description="End date")
    
    def apply(self, model, field_name: str):
        """
        Apply date range filter to query.
        """
        filters = []
        if self.from_date:
            filters.append(getattr(model, field_name) >= self.from_date)
        if self.to_date:
            filters.append(getattr(model, field_name) <= self.to_date)
        return and_(*filters) if filters else None


class SearchFilter:
    """
    Search filter for text fields.
    """
    
    def __init__(self, search_fields: List[str]):
        self.search_fields = search_fields
    
    def apply(self, model, search_term: str):
        """
        Apply search filter to query.
        """
        if not search_term:
            return None
        
        conditions = []
        for field in self.search_fields:
            conditions.append(
                getattr(model, field).ilike(f"%{search_term}%")
            )
        
        return or_(*conditions)


class SortParams(BaseModel):
    """
    Sorting parameters.
    """
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_desc: bool = Field(False, description="Sort in descending order")
    
    def apply(self, model):
        """
        Apply sort to query.
        """
        if not self.sort_by:
            return None
        
        field = getattr(model, self.sort_by, None)
        if not field:
            return None
        
        if self.sort_desc:
            return field.desc()
        return field.asc()


class StatusFilter:
    """
    Status filter for enum fields.
    """
    
    def __init__(self, valid_statuses: List[str]):
        self.valid_statuses = valid_statuses
    
    def apply(self, model, status: Optional[str]):
        """
        Apply status filter to query.
        """
        if not status or status not in self.valid_statuses:
            return None
        
        return getattr(model, 'status') == status


class BooleanFilter:
    """
    Boolean filter for boolean fields.
    """
    
    def __init__(self, field_name: str):
        self.field_name = field_name
    
    def apply(self, model, value: Optional[bool]):
        """
        Apply boolean filter to query.
        """
        if value is None:
            return None
        
        return getattr(model, self.field_name).is_(value)


class NumberRangeFilter:
    """
    Number range filter.
    """
    
    def __init__(self, field_name: str):
        self.field_name = field_name
    
    def apply(self, model, min_val: Optional[float], max_val: Optional[float]):
        """
        Apply number range filter to query.
        """
        filters = []
        if min_val is not None:
            filters.append(getattr(model, self.field_name) >= min_val)
        if max_val is not None:
            filters.append(getattr(model, self.field_name) <= max_val)
        return and_(*filters) if filters else None


class ChoiceFilter:
    """
    Choice filter for multiple choice fields.
    """
    
    def __init__(self, field_name: str, choices: List[str]):
        self.field_name = field_name
        self.choices = choices
    
    def apply(self, model, values: Optional[List[str]]):
        """
        Apply choice filter to query.
        """
        if not values:
            return None
        
        # Filter valid values
        valid_values = [v for v in values if v in self.choices]
        if not valid_values:
            return None
        
        return getattr(model, self.field_name).in_(valid_values)


async def get_filters(
    request: Request
) -> Dict[str, Any]:
    """
    Get all filter parameters from request query params.
    """
    filters = {}
    
    for key, value in request.query_params.items():
        # Skip pagination parameters
        if key in ['page', 'size', 'limit', 'offset', 'sort', 'cursor']:
            continue
        
        # Handle multiple values
        if ',' in value:
            filters[key] = value.split(',')
        else:
            filters[key] = value
    
    return filters


class FilterSet:
    """
    FilterSet class for declarative filter definitions.
    """
    
    def __init__(self, model):
        self.model = model
        self.filters = {}
    
    def add_filter(self, name, filter_class, **kwargs):
        """
        Add a filter to the set.
        """
        self.filters[name] = filter_class(**kwargs)
    
    async def apply(self, query, params: Dict[str, Any]):
        """
        Apply all filters to query.
        """
        conditions = []
        
        for param_name, param_value in params.items():
            if param_name in self.filters:
                filter_obj = self.filters[param_name]
                condition = filter_obj.apply(self.model, param_value)
                if condition is not None:
                    conditions.append(condition)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query


def create_filter_set(model):
    """
    Decorator to create a filter set class.
    """
    def decorator(cls):
        filter_set = FilterSet(model)
        
        # Process filter definitions
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, 'filter_config'):
                config = attr.filter_config
                filter_set.add_filter(
                    config['name'],
                    config['class'],
                    **config.get('kwargs', {})
                )
        
        return filter_set
    
    return decorator


def filter_field(name: str, filter_class, **kwargs):
    """
    Decorator to mark a field as filterable.
    """
    def decorator(func):
        func.filter_config = {
            'name': name,
            'class': filter_class,
            'kwargs': kwargs
        }
        return func
    return decorator


# Example usage:
# @create_filter_set(User)
# class UserFilters:
#     @filter_field('search', SearchFilter, fields=['email', 'full_name'])
#     def search_filter(self):
#         pass
#     
#     @filter_field('status', BooleanFilter, field_name='is_active')
#     def status_filter(self):
#         pass