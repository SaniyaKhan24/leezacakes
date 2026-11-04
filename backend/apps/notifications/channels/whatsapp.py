"""WhatsApp messages behind a small provider interface.

Configuration lives in the admin-edited ``WhatsAppSettings`` singleton. The default
provider is the official Meta WhatsApp Cloud API; another BSP can be added by
implementing the ``MetaCloudProvider`` methods it needs and registering it in
``PROVIDERS``. Business-initiated messages must use approved templates; free-form text
is only allowed within 24 hours of the customer's last message.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import DeliveryResult

name = "whatsapp"
GRAPH_HOST = "graph.facebook.com"
GRAPH_BASE = f"https://{GRAPH_HOST}"
TIMEOUT_SECONDS = 10


class GraphError(Exception):
    def __init__(self, message, status=None, retryable=True):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class MetaCloudProvider:
    """Meta WhatsApp Cloud API (graph.facebook.com)."""

    def __init__(  # nosec B107 - empty defaults mean "not configured", not a credential
        self, access_token, phone_number_id, api_version, business_account_id="", app_secret=""
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version or "v26.0"
        self.business_account_id = business_account_id
        self.app_secret = app_secret

    @classmethod
    def from_config(cls, config):
        return cls(
            config.access_token,
            config.phone_number_id,
            config.api_version,
            config.business_account_id,
            config.app_secret,
        )

    def is_configured(self):
        return bool(self.access_token and self.phone_number_id)

    def url(self, path=""):
        return f"{GRAPH_BASE}/{self.api_version}/{path.lstrip('/')}"

    def redact(self, text):
        text = str(text)
        for secret in (self.access_token, self.app_secret):
            if secret:
                text = text.replace(secret, "[redacted]")
        return text[:500]

    # Transport ----------------------------------------------------------------------------

    def request(self, method, url, body=None):
        """Call the Graph API and return the decoded JSON, or raise GraphError (redacted).

        The token travels only in the Authorization header, never in the URL."""
        if urllib.parse.urlsplit(url).hostname != GRAPH_HOST:
            raise GraphError("Refusing to call a non-Graph URL.", retryable=False)
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            # Only https://graph.facebook.com URLs reach this point (checked above).
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            # 4xx means Meta rejected the request (template, number, permissions):
            # retrying won't help. Rate limits (429) and server errors will clear.
            retryable = exc.code == 429 or exc.code >= 500
            raise GraphError(self.redact(self._graph_error(exc)), exc.code, retryable) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            reason = getattr(exc, "reason", exc)
            raise GraphError(self.redact(f"WhatsApp request failed: {reason}")) from None

    @staticmethod
    def _graph_error(exc):
        try:
            error = json.loads(exc.read().decode()).get("error") or {}
        except (ValueError, AttributeError, OSError):
            error = {}
        message = error.get("message") or exc.reason or "Unknown error"
        details = (error.get("error_data") or {}).get("details")
        code = error.get("code")
        text = f"Graph API error {code or exc.code}: {message}"
        return f"{text} ({details})" if details and details not in message else text

    # Messages -----------------------------------------------------------------------------

    def _send(self, body):
        try:
            data = self.request("POST", self.url(f"{self.phone_number_id}/messages"), body)
        except GraphError as exc:
            return DeliveryResult.failed(str(exc), exc.retryable)
        messages = data.get("messages") or [{}]
        return DeliveryResult.sent(str(messages[0].get("id", "")))

    def send_template(self, to, template, language, params):
        template_body = {"name": template, "language": {"code": language}}
        if params:
            template_body["components"] = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in params],
                }
            ]
        return self._send(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": template_body,
            }
        )

    def send_text(self, to, text):
        return self._send(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            }
        )

    # Account management (admin) -----------------------------------------------------------

    def phone_number_info(self):
        fields = (
            "display_phone_number,verified_name,quality_rating,code_verification_status,"
            "platform_type,throughput"
        )
        query = urllib.parse.urlencode({"fields": fields})
        return self.request("GET", self.url(f"{self.phone_number_id}?{query}"))

    def list_templates(self, max_pages=10):
        query = urllib.parse.urlencode(
            {"fields": "name,status,language,category,rejected_reason", "limit": 200}
        )
        url = self.url(f"{self.business_account_id}/message_templates?{query}")
        templates = []
        for _ in range(max_pages):
            data = self.request("GET", url)
            templates.extend(data.get("data") or [])
            url = (data.get("paging") or {}).get("next")
            if not url:
                break
        return templates

    def create_template(self, template_name, language, body, samples):
        payload = {
            "name": template_name,
            "language": language,
            "category": "UTILITY",
            "components": [
                {"type": "BODY", "text": body, "example": {"body_text": [list(samples)]}}
            ],
        }
        return self.request(
            "POST", self.url(f"{self.business_account_id}/message_templates"), payload
        )


PROVIDERS = {"meta_cloud": MetaCloudProvider}


def get_config():
    from ..models import WhatsAppSettings

    return WhatsAppSettings.load()


def get_provider(config=None):
    config = config or get_config()
    provider = PROVIDERS.get(config.provider or "meta_cloud")
    return provider.from_config(config) if provider else None


def is_enabled():
    return bool(get_config().sending_enabled)


def send(message, recipient):
    if not recipient:
        return DeliveryResult.skipped("No valid WhatsApp number for this recipient.")
    config = get_config()
    template = config.template_for(message.get("event_key"))
    if template is None:
        return DeliveryResult.skipped(
            "No WhatsApp template is enabled for this event (Admin → WhatsApp & alert settings)."
        )
    provider = get_provider(config)
    if provider is None:
        return DeliveryResult.skipped(f"Unknown WhatsApp provider '{config.provider}'.")
    if not provider.is_configured():
        return DeliveryResult.skipped("WhatsApp phone number ID or access token is not set.")
    return provider.send_template(
        recipient,
        template.template_name,
        config.template_language or "en",
        message["whatsapp_params"],
    )
