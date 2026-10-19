import json
import logging


class SafeJSONFormatter(logging.Formatter):
    """Allow metadata only; raw messages and requests may contain secrets."""

    def format(self, record):
        return json.dumps(
            {
                "time": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "status": getattr(record, "status_code", None),
                "exception_type": record.exc_info[0].__name__ if record.exc_info else None,
            }
        )
