"""Timezone utilities for IST (Indian Standard Time) handling"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# IST is UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Get current datetime in IST timezone"""
    return datetime.now(IST)


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST datetime"""
    if utc_dt.tzinfo is None:
        # If naive, assume it's UTC
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(IST)


def ist_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC datetime"""
    if ist_dt.tzinfo is None:
        # If naive, assume it's IST
        ist_dt = ist_dt.replace(tzinfo=IST)
    return ist_dt.astimezone(timezone.utc)


def parse_date_as_ist(date_str: str) -> Optional[datetime]:
    """
    Parse a date string (YYYY-MM-DD) and return the start of that day in IST.
    Also accepts datetime strings - if no timezone info, assumes IST.
    """
    if not date_str:
        return None
    
    try:
        # Try parsing as ISO format datetime
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # If no timezone info, assume IST
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        else:
            # Convert to IST if it has timezone info
            dt = dt.astimezone(IST)
        
        # If only date provided (no time), set to start of day
        if date_str.count(':') == 0:  # Just date, no time
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return dt
    except (ValueError, AttributeError):
        return None


def get_today_start_ist() -> datetime:
    """Get start of today (00:00:00) in IST"""
    now = now_ist()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_today_end_ist() -> datetime:
    """Get end of today (23:59:59.999999) in IST"""
    now = now_ist()
    return now.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_date_range_utc_for_ist_date(ist_start: datetime, ist_end: datetime) -> tuple[datetime, datetime]:
    """
    Convert IST datetime range to UTC datetime range for database queries.
    MongoDB stores dates in UTC, so we need to convert IST dates to UTC.
    """
    # Ensure both are timezone-aware (IST)
    if ist_start.tzinfo is None:
        ist_start = ist_start.replace(tzinfo=IST)
    if ist_end.tzinfo is None:
        ist_end = ist_end.replace(tzinfo=IST)
    
    # Convert to UTC
    utc_start = ist_start.astimezone(timezone.utc)
    utc_end = ist_end.astimezone(timezone.utc)
    
    return utc_start, utc_end

