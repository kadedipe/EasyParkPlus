"""
Datetime utility functions.
"""

from datetime import datetime, timedelta, date, time
from typing import Optional, Tuple, List, Union
import calendar
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta


def utc_now() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        datetime: Current UTC datetime
    """
    return datetime.utcnow()


def format_datetime(
    dt: datetime,
    format: str = "%Y-%m-%d %H:%M:%S",
    tz_info: Optional[str] = None
) -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime object
        format: Output format
        tz_info: Timezone information
        
    Returns:
        str: Formatted datetime string
    """
    if tz_info:
        dt = dt.astimezone(tz.gettz(tz_info))
    return dt.strftime(format)


def parse_datetime(
    dt_str: str,
    tz_info: Optional[str] = None
) -> datetime:
    """
    Parse datetime from string.
    
    Args:
        dt_str: Datetime string
        tz_info: Timezone information
        
    Returns:
        datetime: Parsed datetime
    """
    dt = parser.parse(dt_str)
    if tz_info:
        dt = dt.astimezone(tz.gettz(tz_info))
    return dt


def get_date_range(
    start_date: Union[datetime, date],
    end_date: Union[datetime, date],
    inclusive: bool = True
) -> List[date]:
    """
    Get list of dates between start and end.
    
    Args:
        start_date: Start date
        end_date: End date
        inclusive: Include end date
        
    Returns:
        List[date]: List of dates
    """
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    delta = end_date - start_date
    days = delta.days + (1 if inclusive else 0)
    
    return [start_date + timedelta(days=i) for i in range(days)]


def get_week_range(date_obj: Union[datetime, date]) -> Tuple[date, date]:
    """
    Get start and end of week for given date.
    
    Args:
        date_obj: Reference date
        
    Returns:
        Tuple[date, date]: (week_start, week_end)
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    start = date_obj - timedelta(days=date_obj.weekday())
    end = start + timedelta(days=6)
    
    return start, end


def get_month_range(date_obj: Union[datetime, date]) -> Tuple[date, date]:
    """
    Get start and end of month for given date.
    
    Args:
        date_obj: Reference date
        
    Returns:
        Tuple[date, date]: (month_start, month_end)
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    start = date_obj.replace(day=1)
    _, last_day = calendar.monthrange(date_obj.year, date_obj.month)
    end = date_obj.replace(day=last_day)
    
    return start, end


def get_quarter_range(date_obj: Union[datetime, date]) -> Tuple[date, date]:
    """
    Get start and end of quarter for given date.
    
    Args:
        date_obj: Reference date
        
    Returns:
        Tuple[date, date]: (quarter_start, quarter_end)
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    quarter = (date_obj.month - 1) // 3 + 1
    start_month = 3 * quarter - 2
    start = date_obj.replace(month=start_month, day=1)
    
    end_month = start_month + 2
    _, last_day = calendar.monthrange(date_obj.year, end_month)
    end = date_obj.replace(month=end_month, day=last_day)
    
    return start, end


def get_year_range(date_obj: Union[datetime, date]) -> Tuple[date, date]:
    """
    Get start and end of year for given date.
    
    Args:
        date_obj: Reference date
        
    Returns:
        Tuple[date, date]: (year_start, year_end)
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    start = date_obj.replace(month=1, day=1)
    end = date_obj.replace(month=12, day=31)
    
    return start, end


def days_between(
    start: Union[datetime, date],
    end: Union[datetime, date]
) -> int:
    """
    Calculate days between two dates.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        int: Number of days
    """
    if isinstance(start, datetime):
        start = start.date()
    if isinstance(end, datetime):
        end = end.date()
    
    return (end - start).days


def hours_between(start: datetime, end: datetime) -> float:
    """
    Calculate hours between two datetimes.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        float: Number of hours
    """
    delta = end - start
    return delta.total_seconds() / 3600


def minutes_between(start: datetime, end: datetime) -> float:
    """
    Calculate minutes between two datetimes.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        float: Number of minutes
    """
    delta = end - start
    return delta.total_seconds() / 60


def add_days(dt: datetime, days: int) -> datetime:
    """
    Add days to datetime.
    
    Args:
        dt: Datetime object
        days: Number of days to add
        
    Returns:
        datetime: New datetime
    """
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    Add hours to datetime.
    
    Args:
        dt: Datetime object
        hours: Number of hours to add
        
    Returns:
        datetime: New datetime
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Add minutes to datetime.
    
    Args:
        dt: Datetime object
        minutes: Number of minutes to add
        
    Returns:
        datetime: New datetime
    """
    return dt + timedelta(minutes=minutes)


def is_weekend(dt: Union[datetime, date]) -> bool:
    """
    Check if date is weekend.
    
    Args:
        dt: Date to check
        
    Returns:
        bool: True if weekend
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.weekday() >= 5


def is_business_hours(
    dt: datetime,
    start_hour: int = 9,
    end_hour: int = 17
) -> bool:
    """
    Check if time is within business hours.
    
    Args:
        dt: Datetime to check
        start_hour: Business hours start
        end_hour: Business hours end
        
    Returns:
        bool: True if within business hours
    """
    if is_weekend(dt):
        return False
    
    hour = dt.hour
    minute = dt.minute
    
    time_value = hour + minute / 60
    return start_hour <= time_value <= end_hour


def get_age(birth_date: Union[datetime, date]) -> int:
    """
    Calculate age from birth date.
    
    Args:
        birth_date: Birth date
        
    Returns:
        int: Age in years
    """
    today = date.today()
    
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    age = today.year - birth_date.year
    
    # Adjust if birthday hasn't occurred this year
    if today.month < birth_date.month or (
        today.month == birth_date.month and today.day < birth_date.day
    ):
        age -= 1
    
    return age


def get_next_occurrence(
    target_date: Union[datetime, date],
    day_of_week: int
) -> date:
    """
    Get next occurrence of specified weekday.
    
    Args:
        target_date: Reference date
        day_of_week: Day of week (0=Monday, 6=Sunday)
        
    Returns:
        date: Next occurrence date
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    days_ahead = day_of_week - target_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    
    return target_date + timedelta(days=days_ahead)


def get_previous_occurrence(
    target_date: Union[datetime, date],
    day_of_week: int
) -> date:
    """
    Get previous occurrence of specified weekday.
    
    Args:
        target_date: Reference date
        day_of_week: Day of week (0=Monday, 6=Sunday)
        
    Returns:
        date: Previous occurrence date
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    days_behind = target_date.weekday() - day_of_week
    if days_behind < 0:
        days_behind += 7
    
    return target_date - timedelta(days=days_behind)


def to_timezone(dt: datetime, tz_info: str) -> datetime:
    """
    Convert datetime to specified timezone.
    
    Args:
        dt: Datetime to convert
        tz_info: Target timezone
        
    Returns:
        datetime: Converted datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.UTC)
    
    return dt.astimezone(tz.gettz(tz_info))