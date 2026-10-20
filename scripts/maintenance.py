import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
from app.db import SessionLocal
from app.backups import perform_backup, test_restore

if __name__ == '__main__':
    with SessionLocal() as db:
        backup=perform_backup(db)
        print(f'backup status={backup.status} ref={backup.path or "-"}')
        if backup.status != 'ok':
            raise SystemExit(1)
        # Sunday UTC: after the fresh backup, perform a real restore test.
        if datetime.now(timezone.utc).weekday() == 6:
            restored=test_restore(db,backup.path)
            print(f'restore_test status={restored.status} message={restored.message or ""}')
            if restored.status != 'ok':
                raise SystemExit(1)
