"""
JSON Formatter for Structured Logging to Elasticsearch
Usage: Import and configure in your FastAPI/Django applications
"""
import logging
import json
from datetime import datetime
import traceback


class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON for Elasticsearch ingestion.

    Usage:
        import logging
        from json_formatter import JSONFormatter

        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logging.basicConfig(handlers=[handler], level=logging.INFO)

        logger = logging.getLogger(__name__)
        logger.info("User logged in", extra={"user_id": 123, "ip": "192.168.1.1"})
    """

    def format(self, record):
        """
        Format a log record as JSON.

        Args:
            record: LogRecord object

        Returns:
            str: JSON-formatted log entry
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": record.__dict__.get('service', 'unknown'),
            "platform": record.__dict__.get('platform', 'unknown'),
            "component": record.__dict__.get('component', 'unknown'),
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add stack info if present
        if hasattr(record, 'stack_info') and record.stack_info:
            log_data["stack_info"] = record.stack_info

        # Add any extra fields passed to the logger
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'service', 'platform', 'component'):
                try:
                    # Only add JSON-serializable values
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter to automatically add service/platform context to all logs.

    Usage:
        logger = logging.getLogger(__name__)
        logger = LoggerAdapter(logger, {
            'service': 'teams-platform-gateway',
            'platform': 'teams',
            'component': 'gateway'
        })
        logger.info("Starting service")  # Will include service/platform/component
    """

    def process(self, msg, kwargs):
        """Add extra context from adapter to log record."""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs
