import re
import uuid

_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        value = request.headers.get("X-Correlation-ID", "")
        correlation_id = value if _CORRELATION_ID.fullmatch(value) else str(uuid.uuid4())
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response
