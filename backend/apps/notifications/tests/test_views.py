import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification

INBOX = "/api/v1/notifications/inbox/"
COUNT = "/api/v1/notifications/inbox/unread-count/"
READ = "/api/v1/notifications/inbox/read/"


def _notify(user, event_key="order_created", audience=Notification.CUSTOMER, **payload):
    payload.setdefault("order_id", str(uuid.uuid4()))
    payload.setdefault("order_number", "LZ-1")
    return Notification.objects.create(
        user=user,
        event_key=event_key,
        audience=audience,
        payload=payload,
        deduplication_key=f"test:{uuid.uuid4()}",
    )


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def people(db):
    customer = User.objects.create_user(email="inbox@example.com")
    other = User.objects.create_user(email="other@example.com")
    staff = User.objects.create_user(email="staff-inbox@example.com", is_staff=True)
    return customer, other, staff


def test_inbox_requires_authentication(db):
    client = APIClient()
    assert client.get(INBOX).status_code == 401
    assert client.get(COUNT).status_code == 401
    assert client.post(READ, {"all": True}, format="json").status_code == 401


def test_inbox_lists_own_rows_newest_first_with_rendered_copy(people):
    customer, other, _ = people
    first = _notify(customer, "order_created", order_number="LZ-A")
    second = _notify(customer, "ready", order_number="LZ-A")
    _notify(other, "order_created")
    response = _client(customer).get(INBOX)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["unread_count"] == 2
    assert data["next"] is None and data["previous"] is None
    assert [row["id"] for row in data["results"]] == [second.id, first.id]
    row = data["results"][1]
    assert set(row) == {
        "id",
        "event_key",
        "audience",
        "title",
        "body",
        "link",
        "created_at",
        "read_at",
    }
    assert row["event_key"] == "order_created"
    assert row["audience"] == "customer"
    assert row["title"] == "Order LZ-A received"
    assert row["link"] == f"/orders/{first.payload['order_id']}"
    assert row["read_at"] is None


def test_inbox_pagination(people):
    customer = people[0]
    for _ in range(3):
        _notify(customer)
    data = _client(customer).get(INBOX, {"page": 1, "page_size": 2}).json()
    assert data["count"] == 3
    assert len(data["results"]) == 2
    assert data["next"].endswith("page=2&page_size=2")
    assert data["unread_count"] == 3


def test_staff_sees_staff_rows_and_own_customer_rows(people):
    customer, _, staff = people
    _notify(staff, "staff_order_created", Notification.STAFF, customer_name="Aarav")
    _notify(staff, "order_created")
    _notify(customer, "order_created")
    _notify(None, "staff_order_created", Notification.STAFF)  # broadcast row: no inbox
    client = _client(staff)
    data = client.get(INBOX).json()
    assert data["count"] == 2
    assert {row["audience"] for row in data["results"]} == {"staff", "customer"}
    staff_only = client.get(INBOX, {"audience": "staff"}).json()
    assert [row["event_key"] for row in staff_only["results"]] == ["staff_order_created"]
    assert staff_only["results"][0]["link"].startswith("/admin/orders/order/")
    assert client.get(COUNT).json() == {"unread_count": 2}
    assert client.get(COUNT, {"audience": "staff"}).json() == {"unread_count": 1}
    assert client.get(COUNT, {"audience": "customer"}).json() == {"unread_count": 1}


def test_former_staff_no_longer_sees_staff_rows(people):
    customer = people[0]
    _notify(customer, "staff_order_created", Notification.STAFF)
    _notify(customer, "order_created")
    data = _client(customer).get(INBOX).json()
    assert [row["audience"] for row in data["results"]] == ["customer"]
    assert data["unread_count"] == 1


def test_unread_filter_and_count(people):
    customer = people[0]
    read = _notify(customer)
    read.read_at = timezone.now()
    read.save()
    unread = _notify(customer)
    client = _client(customer)
    assert client.get(COUNT).json() == {"unread_count": 1}
    data = client.get(INBOX, {"unread": "true"}).json()
    assert [row["id"] for row in data["results"]] == [unread.id]
    assert client.get(INBOX).json()["results"][1]["read_at"] is not None


def test_mark_read_by_ids_is_scoped_to_the_user(people):
    customer, other, _ = people
    mine = [_notify(customer) for _ in range(3)]
    theirs = _notify(other)
    client = _client(customer)
    response = client.post(READ, {"ids": [mine[0].id, mine[1].id, theirs.id]}, format="json")
    assert response.status_code == 200
    assert response.json() == {"unread_count": 1}
    theirs.refresh_from_db()
    assert theirs.read_at is None
    mine[0].refresh_from_db()
    first_read_at = mine[0].read_at
    assert first_read_at is not None
    client.post(READ, {"ids": [mine[0].id]}, format="json")
    mine[0].refresh_from_db()
    assert mine[0].read_at == first_read_at  # already-read rows keep their timestamp


def test_mark_all_read(people):
    customer, other, _ = people
    for _ in range(2):
        _notify(customer)
    _notify(other)
    response = _client(customer).post(READ, {"all": True}, format="json")
    assert response.json() == {"unread_count": 0}
    assert _client(other).get(COUNT).json() == {"unread_count": 1}


@pytest.mark.parametrize(
    "body", [{}, {"ids": []}, {"all": False}, {"ids": ["x"]}, {"ids": [0]}], ids=str
)
def test_mark_read_validates_body(people, body):
    response = _client(people[0]).post(READ, body, format="json")
    assert response.status_code == 400


def test_session_authenticated_staff_can_poll(people):
    staff = people[2]
    client = APIClient()
    client.force_login(staff)
    response = client.get(COUNT, {"audience": "staff"})
    assert response.status_code == 200
    assert response.json() == {"unread_count": 0}
