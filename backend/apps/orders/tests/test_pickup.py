from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.orders.services.pickup import (
    PickupConfig,
    first_available_slot,
    generate_days,
    is_available_slot,
    lead_time_minutes,
    serialize_days,
)

IST = ZoneInfo("Asia/Kolkata")
CONFIG = PickupConfig(
    timezone="Asia/Kolkata",
    open_hour=10,
    close_hour=20,
    slot_minutes=60,
    days_ahead=14,
    min_lead_minutes=240,
)


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=IST)


def test_lead_time_is_max_of_minimum_and_slowest_product():
    assert lead_time_minutes([], CONFIG) == 240
    assert lead_time_minutes([None, 60], CONFIG) == 240
    assert lead_time_minutes([360, 1440, None], CONFIG) == 1440


def test_generate_days_covers_window_with_full_grid():
    days = generate_days(at(3, 9, 0), 240, CONFIG)
    assert len(days) == 14
    assert days[0]["date"] == date(2026, 11, 3)
    assert days[-1]["date"] == date(2026, 11, 16)
    first = days[0]["slots"]
    assert len(first) == 10
    assert first[0]["start"] == at(3, 10) and first[0]["end"] == at(3, 11)
    assert first[-1]["start"] == at(3, 19) and first[-1]["end"] == at(3, 20)
    # 09:00 + 4h lead -> 13:00 is the first bookable slot today.
    available = [slot["start"] for slot in first if slot["available"]]
    assert available[0] == at(3, 13)
    assert not first[2]["available"]  # 12:00


def test_days_with_no_availability_are_still_returned():
    days = generate_days(at(3, 18, 30), 1440, CONFIG)
    assert days[0]["slots"]
    assert not any(slot["available"] for slot in days[0]["slots"])
    tomorrow = days[1]["slots"]
    assert [slot["available"] for slot in tomorrow[:9]] == [False] * 9
    assert tomorrow[9]["start"] == at(4, 19) and tomorrow[9]["available"]


def test_local_date_is_used_when_now_is_utc():
    # 20:00 UTC on Nov 3 is 01:30 IST on Nov 4.
    now = datetime(2026, 11, 3, 20, 0, tzinfo=ZoneInfo("UTC"))
    days = generate_days(now, 240, CONFIG)
    assert days[0]["date"] == date(2026, 11, 4)
    assert first_available_slot(now, 240, CONFIG) == (at(4, 10), at(4, 11))


def test_is_available_slot_accepts_only_generated_available_slots():
    now = at(3, 9, 0)
    assert is_available_slot(at(3, 13), at(3, 14), now, 240, CONFIG)
    # The same instant expressed in UTC is equally valid.
    utc = ZoneInfo("UTC")
    assert is_available_slot(at(3, 13).astimezone(utc), at(3, 14).astimezone(utc), now, 240, CONFIG)
    assert not is_available_slot(at(3, 12), at(3, 13), now, 240, CONFIG)  # inside lead time
    assert not is_available_slot(at(3, 13, 30), at(3, 14, 30), now, 240, CONFIG)  # off grid
    assert not is_available_slot(at(3, 13), at(3, 15), now, 240, CONFIG)  # wrong length
    assert not is_available_slot(at(3, 20), at(3, 21), now, 240, CONFIG)  # after close
    assert not is_available_slot(at(3, 9), at(3, 10), now, 0, CONFIG)  # before open
    assert not is_available_slot(at(17, 13), at(17, 14), now, 240, CONFIG)  # beyond window
    assert not is_available_slot(at(2, 13), at(2, 14), now, 0, CONFIG)  # in the past
    assert not is_available_slot(None, at(3, 14), now, 240, CONFIG)
    naive = datetime(2026, 11, 3, 13)
    assert not is_available_slot(naive, naive + timedelta(hours=1), now, 240, CONFIG)
    assert is_available_slot(at(16, 19), at(16, 20), now, 240, CONFIG)  # last day, last slot


def test_first_available_slot_returns_none_when_window_is_full():
    assert first_available_slot(at(3, 9), 14 * 24 * 60, CONFIG) is None


def test_midnight_close_and_short_slots():
    config = PickupConfig("Asia/Kolkata", 22, 24, 30, 1, 0)
    days = generate_days(at(3, 21), 0, config)
    starts = [slot["start"] for slot in days[0]["slots"]]
    assert starts == [at(3, 22), at(3, 22, 30), at(3, 23), at(3, 23, 30)]
    assert days[0]["slots"][-1]["end"] == datetime(2026, 11, 4, 0, 0, tzinfo=IST)


def test_serialize_days_uses_iso_strings():
    data = serialize_days(generate_days(at(3, 9), 240, CONFIG))
    assert data[0]["date"] == "2026-11-03"
    assert data[0]["slots"][0] == {
        "start": "2026-11-03T10:00:00+05:30",
        "end": "2026-11-03T11:00:00+05:30",
        "available": False,
    }


@pytest.mark.django_db
def test_config_reads_settings(settings):
    settings.PICKUP_SLOT_MINUTES = 30
    config = PickupConfig.from_settings()
    assert config.slot_minutes == 30
    assert config.timezone == "Asia/Kolkata"
