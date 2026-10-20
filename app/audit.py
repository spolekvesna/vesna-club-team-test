from __future__ import annotations
import json
from datetime import date, datetime
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session
from .models import AuditLog


def _plain(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def snapshot(obj) -> dict:
    out = {}
    for attr in inspect(obj).mapper.column_attrs:
        out[attr.key] = _plain(getattr(obj, attr.key))
    return out


def log(db: Session, actor_id: int | None, action: str, entity_type: str, entity_id: str, before=None, after=None, remote_ip=None):
    db.add(AuditLog(
        actor_id=actor_id, action=action, entity_type=entity_type, entity_id=str(entity_id),
        before_json=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        after_json=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        remote_ip=remote_ip,
    ))
