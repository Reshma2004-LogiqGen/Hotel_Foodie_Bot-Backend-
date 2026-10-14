"""
Food Friend Backend - Restaurant clock
Times are stored as the restaurant's local time, so "today" and order times stay
right even when the server runs in another timezone (most hosts run on UTC).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo(os.getenv('APP_TIMEZONE') or 'Asia/Kolkata')


def local_now():
    return datetime.now(TIMEZONE).replace(tzinfo=None)


def iso(dt):
    """ISO time with the restaurant's UTC offset, so every browser reads it correctly."""
    return dt.replace(tzinfo=TIMEZONE).isoformat() if dt else None
