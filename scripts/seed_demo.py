from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date, timedelta
from sqlalchemy import select
from app.db import SessionLocal, Base, engine
from app.models import (
    Worker, Client, IndividualService, Event, EventWorker, EventParticipant,
    DailyNote, IndicatorRecord, ProjectOutput, AnonymousFeedbackAggregate,
    WebAnalyticsAggregate,
)
from app.catalog_seed import seed_catalog
from app.config import settings
from app.security import hash_password, ROLE_ADMIN, ROLE_WORKER, ROLE_READER
from app.main import BASE_DIR, sync_indicator_records, make_catalog_snapshot


def get_worker(db, email: str):
    return db.scalar(select(Worker).where(Worker.email == email))


def ensure_demo():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_catalog(db, BASE_DIR / "data/catalog_seed.json")
        if settings.app_env == "production":
            raise SystemExit("Demo data se nesmějí seedovat v produkčním režimu.")
        if not get_worker(db, "admin@example.test"):
            db.add(Worker(email="admin@example.test", name="Demo správce", role=ROLE_ADMIN, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.add(Worker(email="worker@example.test", name="Demo pracovnice", role=ROLE_WORKER, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.add(Worker(email="reader@example.test", name="Demo čtenář", role=ROLE_READER, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.commit()
        admin = get_worker(db, "admin@example.test")
        worker = get_worker(db, "worker@example.test") or admin

        people = [
            ("DEMO-001", "Alice", "Nováková", date(2002, 4, 12)),
            ("DEMO-002", "Boris", "Malý", date(1998, 9, 5)),
            ("DEMO-003", "Cecílie", "Veselá", date(2008, 2, 17)),
            ("DEMO-004", "Daniel", "Horák", date(2006, 6, 22)),
            ("DEMO-005", "Eva", "Bílá", date(1994, 11, 8)),
            ("DEMO-006", "Filip", "Krejčí", date(2004, 1, 30)),
        ]
        clients = []
        for idx, (code, first, last, birth) in enumerate(people, start=1):
            c = db.scalar(select(Client).where(Client.code == code))
            if not c:
                c = Client(
                    client_id=f"CLI-DEMO-{idx:03d}", code=code, first_name=first, last_name=last,
                    birth_date=birth, entry_date=date(2026, 10, 1) + timedelta(days=idx),
                    contact=None, fewer_opportunities=True if idx in {2, 4} else None,
                    document_status="unknown", status="active",
                    notes="Syntetická demo osoba – nejde o skutečného klienta.",
                )
                db.add(c); db.flush()
            clients.append(c)

        if not db.scalar(select(IndividualService).where(IndividualService.service_id == "VYK-DEMO-001")):
            values = {
                "area_id": "OBL001", "activity_id": "CIN001", "form_id": None,
                "place_id": None, "method_id": None, "language_id": None,
                "outcome_id": None, "next_step_id": None, "progress_id": None, "referral_id": None,
            }
            s = IndividualService(
                service_id="VYK-DEMO-001", client_id=clients[0].id, service_date=date(2026, 10, 8),
                minutes=45, worker_id=worker.id, ka="KA3", subactivity="3.1",
                area_id="OBL001", activity_id="CIN001", description="Demo kariérní konzultace.",
                eligible_project=True, attendance_sheet_ref="ML-DEMO-001", transcribed_from_sheet=True,
                catalog_snapshot_json=make_catalog_snapshot(db, values),
            )
            db.add(s); db.flush()
            sync_indicator_records(db, "service", s.service_id, s.service_date, [s.client_id], ["026300"], True, s.attendance_sheet_ref)

        if not db.scalar(select(IndividualService).where(IndividualService.service_id == "VYK-DEMO-002")):
            values = {
                "area_id": "OBL001", "activity_id": "CIN001", "form_id": None,
                "place_id": None, "method_id": None, "language_id": None,
                "outcome_id": None, "next_step_id": None, "progress_id": None, "referral_id": None,
            }
            s = IndividualService(
                service_id="VYK-DEMO-002", client_id=clients[1].id, service_date=date(2026, 10, 9),
                minutes=30, worker_id=worker.id, ka="KA3", subactivity="3.2",
                area_id="OBL001", activity_id="CIN001", description="Demo mentoring.",
                eligible_project=True, catalog_snapshot_json=make_catalog_snapshot(db, values),
            )
            db.add(s)

        ev = db.scalar(select(Event).where(Event.event_id == "AKC-DEMO-001"))
        if not ev:
            ev = Event(
                event_id="AKC-DEMO-001", title="Demo občanská orientace", event_date=date(2026, 10, 12),
                duration_minutes=90, ka="KA2", subactivity="2.3", event_type="civic_orientation",
                attendance_sheet_ref="PL-DEMO-001", notes="Syntetická demo akce.", created_by_id=admin.id,
            )
            db.add(ev); db.flush()
            db.add(EventWorker(event_id=ev.id, worker_id=worker.id))
            for c in clients[:4]:
                db.add(EventParticipant(event_id=ev.id, client_id=c.id, participant_kind="project", attendance_status="present", eligible_project=True, transcribed_from_sheet=True))
            db.add(EventParticipant(event_id=ev.id, client_id=None, display_name="host – demo", participant_kind="guest", attendance_status="present", eligible_project=False))
            sync_indicator_records(db, "event", ev.event_id, ev.event_date, [c.id for c in clients[:4]], ["026200"], True, ev.attendance_sheet_ref)

        if not db.scalar(select(DailyNote).where(DailyNote.note_id == "DEN-DEMO-001")):
            db.add(DailyNote(note_id="DEN-DEMO-001", note_date=date(2026, 10, 12), worker_id=worker.id, summary="Proběhl klub a občanská orientace. Syntetický demo zápis."))
        if not db.scalar(select(DailyNote).where(DailyNote.note_id == "DEN-DEMO-002")):
            db.add(DailyNote(note_id="DEN-DEMO-002", note_date=date(2026, 10, 12), worker_id=admin.id, summary="Druhý demo zápis téhož dne – ověření více zápisů v kalendáři."))

        if not db.scalar(select(ProjectOutput).where(ProjectOutput.title == "Demo metodický list")):
            db.add(ProjectOutput(output_date=date(2026, 10, 15), title="Demo metodický list", output_type="document", reference="DEMO", created_by_id=admin.id))
        if not db.scalar(select(WebAnalyticsAggregate).where(WebAnalyticsAggregate.source == "demo-web")):
            db.add(WebAnalyticsAggregate(period_start=date(2026, 10, 1), period_end=date(2026, 10, 31), source="demo-web", visits=321, created_by_id=admin.id))
        if not db.scalar(select(AnonymousFeedbackAggregate).where(AnonymousFeedbackAggregate.methodology == "Syntetická demo zpětná vazba")):
            db.add(AnonymousFeedbackAggregate(period_start=date(2026, 10, 1), period_end=date(2026, 10, 31), denominator=10, positive_count=8, methodology="Syntetická demo zpětná vazba", created_by_id=admin.id))

        db.commit()
        print("Demo data jsou připravena. Všechna jména a záznamy jsou syntetické.")


if __name__ == "__main__":
    ensure_demo()
