from unittest.mock import patch

from apps.common.health import database_ready


def test_live_is_database_independent(client):
    with patch("apps.common.views.database_ready", side_effect=AssertionError):
        response = client.get("/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_minimal_and_returns_503_when_database_unavailable(client):
    with patch("apps.common.views.database_ready", return_value=False):
        response = client.get("/health/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "database" not in response.content.decode().lower()


def test_readiness_returns_ok_when_dependency_is_available(client):
    with patch("apps.common.views.database_ready", return_value=True):
        response = client.get("/health/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_ready_handles_success_and_failure():
    cursor = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    cursor.fetchone.return_value = (1,)
    connection = __import__("django.db", fromlist=["connection"]).connection
    with patch.object(connection, "cursor") as cursor_factory:
        cursor_factory.return_value.__enter__.return_value = cursor
        assert database_ready() is True
    with patch.object(connection, "cursor", side_effect=RuntimeError):
        assert database_ready() is False
