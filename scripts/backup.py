import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal
from app.backups import perform_backup

if __name__ == '__main__':
    with SessionLocal() as db:
        run=perform_backup(db)
        print(f'backup status={run.status} ref={run.path or "-"} message={run.message or ""}')
        if run.status != 'ok':
            raise SystemExit(1)
