from __future__ import annotations
from datetime import date
from sqlalchemy import select, union
from sqlalchemy.orm import Session
from .models import Client, IndividualService, EventParticipant, Event, IndicatorRecord, ProjectOutput, WebAnalyticsAggregate

INDICATORS = {
    "026000": ("Podpořené osoby", 218),
    "026200": ("Účastníci kurzu občanské orientace", 57),
    "026300": ("Osobní profesní poradenství", 20),
    "026400": ("Informace/pomoc k žádosti o sloučení rodiny", 0),
    "026510": ("Užitečnost aktivity pro integraci", 0),
    "026600": ("Žádost o uznání kvalifikace/dovedností", 0),
    "026610": ("Žádost o status dlouhodobě pobývajícího rezidenta", 0),
    "028309": ("Vytvořené projektové dokumenty", 5),
    "028313": ("Návštěvy webu/profilů", 0),
}


def _date_filter(stmt, col, start: date | None, end: date | None):
    if start: stmt = stmt.where(col >= start)
    if end: stmt = stmt.where(col <= end)
    return stmt


def supported_clients(db: Session, start=None, end=None):
    s1 = select(IndividualService.client_id.label("client_id")).where(IndividualService.eligible_project == True)
    s1 = _date_filter(s1, IndividualService.service_date, start, end)
    s2 = select(EventParticipant.client_id.label("client_id")).join(Event, Event.id == EventParticipant.event_id).where(
        EventParticipant.eligible_project == True,
        EventParticipant.participant_kind == "project",
        EventParticipant.client_id.is_not(None),
        EventParticipant.attendance_status == "present",
    )
    s2 = _date_filter(s2, Event.event_date, start, end)
    ids = [r[0] for r in db.execute(union(s1, s2)).all() if r[0] is not None]
    return sorted(set(ids))


def indicator_clients(db: Session, code: str, start=None, end=None):
    if code == "026000":
        return supported_clients(db, start, end)
    stmt = select(IndicatorRecord.client_id).where(IndicatorRecord.indicator_code == code, IndicatorRecord.eligible == True, IndicatorRecord.client_id.is_not(None))
    stmt = _date_filter(stmt, IndicatorRecord.record_date, start, end)
    return sorted(set(db.scalars(stmt).all()))


def indicator_summary(db: Session, start=None, end=None):
    out = []
    for code, (name, target) in INDICATORS.items():
        if code == "028309":
            stmt = select(ProjectOutput.id)
            if start: stmt = stmt.where(ProjectOutput.output_date >= start)
            if end: stmt = stmt.where(ProjectOutput.output_date <= end)
            value = len(db.scalars(stmt).all())
        elif code == "028313":
            stmt = select(WebAnalyticsAggregate)
            if start: stmt = stmt.where(WebAnalyticsAggregate.period_end >= start)
            if end: stmt = stmt.where(WebAnalyticsAggregate.period_start <= end)
            value = sum(x.visits for x in db.scalars(stmt).all())
        elif code == "026510":
            # 026510 needs approved methodology. Do not infer it from named client records.
            value = 0
        else:
            value = len(indicator_clients(db, code, start, end))
        out.append({"code": code, "name": name, "target": target, "value": value})
    return out
