"""Date and time utility functions."""

from datetime import datetime, timedelta, date, time
from typing import Optional, Tuple, List, Union
import calendar


def now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def today() -> date:
    """Get current UTC date."""
    return datetime.utcnow().date()


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    return dt.strftime(format)


def parse_datetime(dt_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse datetime from string."""
    try:
        return datetime.strptime(dt_str, format)
    except (ValueError, TypeError):
        return None


def is_business_hours(check_time: Optional[datetime] = None) -> bool:
    """Check if given time is within business hours."""
    from ..constants.config import Config
    
    if check_time is None:
        check_time = now()
    
    day_name = check_time.strftime("%A").lower()
    business_hours = Config.BUSINESS_HOURS.get(day_name)
    
    if not business_hours:
        return False
    
    open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
    close_time = datetime.strptime(business_hours["close"], "%H:%M").time()
    check_time_only = check_time.time()
    
    return open_time <= check_time_only <= close_time


def get_next_business_open(dt: Optional[datetime] = None) -> datetime:
    """Get next business opening time."""
    from ..constants.config import Config
    
    if dt is None:
        dt = now()
    
    current_date = dt.date()
    current_time = dt.time()
    
    for days_ahead in range(7):
        check_date = current_date + timedelta(days=days_ahead)
        day_name = check_date.strftime("%A").lower()
        business_hours = Config.BUSINESS_HOURS.get(day_name)
        
        if business_hours:
            open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
            
            if days_ahead == 0 and current_time > open_time:
                continue
            
            return datetime.combine(check_date, open_time)
    
    # If no business day found in next 7 days, return tomorrow at 9 AM
    return datetime.combine(current_date + timedelta(days=1), time(9, 0))


def calculate_duration_minutes(start_time: datetime, end_time: datetime) -> int:
    """Calculate duration in minutes between two times."""
    delta = end_time - start_time
    return int(delta.total_seconds() / 60)


def calculate_duration_hours(start_time: datetime, end_time: datetime) -> float:
    """Calculate duration in hours between two times."""
    delta = end_time - start_time
    return delta.total_seconds() / 3600


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """Add minutes to datetime."""
    return dt + timedelta(minutes=minutes)


def add_hours(dt: datetime, hours: int) -> datetime:
    """Add hours to datetime."""
    return dt + timedelta(hours=hours)


def add_days(dt: datetime, days: int) -> datetime:
    """Add days to datetime."""
    return dt + timedelta(days=days)


def get_date_range(start_date: date, end_date: date) -> List[date]:
    """Get list of dates between start_date and end_date (inclusive)."""
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]


def get_month_dates(year: int, month: int) -> Tuple[date, date]:
    """Get first and last date of the month."""
    first_date = date(year, month, 1)
    last_date = date(year, month, calendar.monthrange(year, month)[1])
    return first_date, last_date


def is_overlapping(
    start1: datetime, 
    end1: datetime, 
    start2: datetime, 
    end2: datetime,
    inclusive: bool = False
) -> bool:
    """Check if two time ranges overlap."""
    if inclusive:
        return start1 <= end2 and start2 <= end1
    return start1 < end2 and start2 < end1


def get_overlap_duration(
    start1: datetime, 
    end1: datetime, 
    start2: datetime, 
    end2: datetime
) -> timedelta:
    """Get duration of overlap between two time ranges."""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    if overlap_start < overlap_end:
        return overlap_end - overlap_start
    return timedelta(0)


def to_timezone_naive(dt: datetime) -> datetime:
    """Convert timezone-aware datetime to naive UTC."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt