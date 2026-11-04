from typing import NamedTuple


class DeliveryResult(NamedTuple):
    """Outcome of one channel send: ``(status, provider_message_id, error, retryable)``.

    ``retryable`` only matters for failures: transient problems (timeouts, 5xx, rate
    limits, SMTP outages) are retried by the worker; permanent ones (a rejected
    template or number) are not.
    """

    status: str
    provider_message_id: str = ""
    error: str = ""
    retryable: bool = True

    @classmethod
    def sent(cls, provider_message_id=""):
        return cls("sent", provider_message_id or "", "")

    @classmethod
    def skipped(cls, reason):
        return cls("skipped", "", reason)

    @classmethod
    def failed(cls, error, retryable=True):
        return cls("failed", "", str(error)[:500], retryable)
