# ticket_system/templatetags/duration_filters.py
import datetime
from django import template

register = template.Library()

@register.filter(name='format_duration')
def format_duration(value):
    """Formats a timedelta object to HH:MM:SS"""
    if not isinstance(value, datetime.timedelta):
        return value # Return original value if not timedelta

    total_seconds = int(value.total_seconds())

    if total_seconds < 0:
         # Handle negative durations if necessary, or return as is
         return str(value).split('.')[0] # Default formatting without microseconds

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f'{hours:02}:{minutes:02}:{seconds:02}'
