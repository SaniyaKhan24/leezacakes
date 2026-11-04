import io
import json
import urllib.error
import urllib.request

import pytest


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeGraph:
    """Stands in for urllib.request.urlopen. Routes are matched by (method, URL substring);
    the most recently added matching route wins."""

    def __init__(self):
        self.routes = []
        self.calls = []

    def respond(self, method, fragment, body=None, status=200):
        self.routes.insert(0, (method, fragment, body if body is not None else {}, status))

    def __call__(self, request, timeout=None):
        body = json.loads(request.data) if request.data else None
        self.calls.append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": body,
                "timeout": timeout,
            }
        )
        for method, fragment, payload, status in self.routes:
            if method == request.get_method() and fragment in request.full_url:
                data = json.dumps(payload).encode()
                if status >= 400:
                    raise urllib.error.HTTPError(
                        request.full_url, status, "Error", {}, io.BytesIO(data)
                    )
                return FakeResponse(data)
        raise urllib.error.URLError("no fake route")


@pytest.fixture
def graph(monkeypatch):
    fake = FakeGraph()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake
