import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.db import SessionLocal
from app.models import BackupRun
from app.backups import test_restore

if __name__ == '__main__':
    with SessionLocal() as db:
        last=db.scalar(select(BackupRun).where(BackupRun.kind=='backup',BackupRun.status=='ok').order_by(BackupRun.finished_at.desc()))
        if not last or not last.path:
            raise SystemExit('Není dostupná úspěšná záloha k testu obnovy.')
        run=test_restore(db,last.path)
        print(f'restore_test status={run.status} message={run.message or ""}')
        if run.status != 'ok':
            raise SystemExit(1)
