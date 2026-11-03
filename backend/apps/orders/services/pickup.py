"""Pickup slot generation.

The functions here are pure: they take ``now`` and a :class:`PickupConfig` so that
tests can exercise any moment without freezing time. Slots live on a fixed grid in
the shop's local timezone (``settings.TIME_ZONE``).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Max


@dataclass(frozen=True)
class PickupConfig:
    timezone: str
    open_hour: int
    close_hour: int
    slot_minutes: int
    days_ahead: int
    min_lead_minutes: int

    @classmethod
    def from_settings(cls):
        return cls(
            timezone=settings.TIME_ZONE,
            open_hour=settings.PICKUP_OPEN_HOUR,
            close_hour=settings.PICKUP_CLOSE_HOUR,
            slot_minutes=settings.PICKUP_SLOT_MINUTES,
            days_ahead=settings.PICKUP_DAYS_AHEAD,
            min_lead_minutes=settings.PICKUP_MIN_LEAD_MINUTES,
        )

    @property
    def tzinfo(self):
        return ZoneInfo(self.timezone)


def lead_time_minutes(preparation_minutes, config):
    """Lead time is the larger of the shop minimum and the slowest product."""
    longest = max((minutes for minutes in preparation_minutes if minutes), default=0)
    return max(config.min_lead_minutes, longest)


def cart_lead_time(cart, config):
    if cart is None:
        return config.min_lead_minutes
    longest = cart.items.aggregate(longest=Max("product__preparation_time"))["longest"]
    return lead_time_minutes([longest], config)


def _day_slots(day, config):
    tz = config.tzinfo
    start = datetime.combine(day, time(config.open_hour), tzinfo=tz)
    closing = (
        datetime.combine(day + timedelta(days=1), time(0), tzinfo=tz)
        if config.close_hour == 24
        else datetime.combine(day, time(config.close_hour), tzinfo=tz)
    )
    step = timedelta(minutes=config.slot_minutes)
    while start + step <= closing:
        yield start, start + step
        start += step


def first_day(now, config):
    return now.astimezone(config.tzinfo).date()


def generate_days(now, lead_minutes, config):
    """Return every day in the booking window with all of its slots.

    Days whose slots are all unavailable are still returned so a UI can show them
    as full or closed.
    """
    earliest = now + timedelta(minutes=lead_minutes)
    today = first_day(now, config)
    days = []
    for offset in range(config.days_ahead):
        day = today + timedelta(days=offset)
        slots = [
            {"start": start, "end": end, "available": start >= earliest}
            for start, end in _day_slots(day, config)
        ]
        days.append({"date": day, "slots": slots})
    return days


def is_available_slot(start, end, now, lead_minutes, config):
    if start is None or end is None or start.tzinfo is None or end.tzinfo is None:
        return False
    local_day = start.astimezone(config.tzinfo).date()
    today = first_day(now, config)
    if not today <= local_day < today + timedelta(days=config.days_ahead):
        return False
    if start < now + timedelta(minutes=lead_minutes):
        return False
    return any(
        slot_start == start and slot_end == end
        for slot_start, slot_end in _day_slots(local_day, config)
    )


def first_available_slot(now, lead_minutes, config):
    for day in generate_days(now, lead_minutes, config):
        for slot in day["slots"]:
            if slot["available"]:
                return slot["start"], slot["end"]
    return None


def serialize_days(days):
    return [
        {
            "date": day["date"].isoformat() if isinstance(day["date"], date) else day["date"],
            "slots": [
                {
                    "start": slot["start"].isoformat(),
                    "end": slot["end"].isoformat(),
                    "available": slot["available"],
                }
                for slot in day["slots"]
            ],
        }
        for day in days
    ]
