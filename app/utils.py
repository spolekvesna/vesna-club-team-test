from __future__ import annotations
from datetime import date, datetime
import uuid


def uid(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"


def parse_date(value: str | None):
    if not value:
        return None
    return date.fromisoformat(value)


def as_bool(value) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on", "ano"}


def csv_safe(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        text = "'" + text
    return text
