from __future__ import annotations
import hashlib, os, shutil, sqlite3, subprocess, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from .config import settings
from .models import BackupRun


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def _s3_client():
    import boto3
    kwargs={}
    if settings.backup_s3_endpoint: kwargs['endpoint_url']=settings.backup_s3_endpoint
    if settings.backup_s3_region: kwargs['region_name']=settings.backup_s3_region
    return boto3.client('s3',**kwargs)


def cleanup_remote_backups(days: int):
    if not settings.backup_s3_bucket:
        return
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    client=_s3_client(); prefix=settings.backup_s3_prefix.rstrip('/')+'/'
    token=None
    while True:
        kwargs={'Bucket':settings.backup_s3_bucket,'Prefix':prefix}
        if token: kwargs['ContinuationToken']=token
        result=client.list_objects_v2(**kwargs)
        old=[{'Key':x['Key']} for x in result.get('Contents',[]) if x.get('LastModified') and x['LastModified'] < cutoff]
        if old: client.delete_objects(Bucket=settings.backup_s3_bucket,Delete={'Objects':old,'Quiet':True})
        if not result.get('IsTruncated'): break
        token=result.get('NextContinuationToken')


def perform_backup(db: Session, backup_dir: str | None=None):
    backup_dir=backup_dir or settings.backup_dir
    Path(backup_dir).mkdir(parents=True,exist_ok=True)
    run=BackupRun(kind='backup',status='running'); db.add(run); db.commit(); db.refresh(run)
    stamp=utcnow_naive().strftime('%Y%m%dT%H%M%SZ')
    try:
        # In production a copy left only on the web/cron instance is not a real
        # disaster-recovery backup. Fail closed unless separate object storage
        # is configured. Development/test may intentionally use local files.
        if settings.app_env == 'production' and not settings.backup_s3_bucket:
            raise RuntimeError('Produkční záloha vyžaduje oddělené objektové úložiště (BACKUP_S3_BUCKET).')
        if settings.database_url.startswith('sqlite'):
            src=settings.database_url.replace('sqlite:///','',1)
            dest=Path(backup_dir)/f'vesna-club-{stamp}.sqlite3'
            src_conn=sqlite3.connect(src)
            dst_conn=sqlite3.connect(dest)
            with dst_conn: src_conn.backup(dst_conn)
            src_conn.close(); dst_conn.close()
        else:
            dest=Path(backup_dir)/f'vesna-club-{stamp}.dump'
            subprocess.run(['pg_dump','--format=custom','--no-owner','--no-acl','--file',str(dest),settings.database_url],check=True,capture_output=True,text=True)
        run.size_bytes=dest.stat().st_size; run.checksum=_sha256(dest); run.path=str(dest)
        remote_msg=''
        if settings.backup_s3_bucket:
            client=_s3_client(); key=f"{settings.backup_s3_prefix.rstrip('/')}/{dest.name}"
            extra={'ServerSideEncryption':settings.backup_s3_sse} if settings.backup_s3_sse else {}
            client.upload_file(str(dest),settings.backup_s3_bucket,key,ExtraArgs=extra)
            run.path=f's3://{settings.backup_s3_bucket}/{key}'
            remote_msg=' Oddělená kopie byla uložena do objektového úložiště.'
            cleanup_remote_backups(settings.backup_retention_days)
        run.status='ok'; run.message='Záloha databáze dokončena.'+remote_msg
    except Exception as e:
        run.status='error'; run.message=str(e)
    run.finished_at=utcnow_naive(); db.commit()
    cleanup_old_backups(backup_dir, settings.backup_retention_days)
    return run


def cleanup_old_backups(backup_dir: str, days: int):
    cutoff=utcnow_naive()-timedelta(days=days)
    for p in Path(backup_dir).glob('vesna-club-*'):
        try:
            ts=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).replace(tzinfo=None)
            if ts < cutoff: p.unlink()
        except FileNotFoundError: pass


def _materialize_backup(backup_ref: str, temp_dir: str) -> Path:
    if not backup_ref.startswith('s3://'):
        p=Path(backup_ref)
        if not p.exists(): raise RuntimeError(f'Záložní soubor neexistuje: {p}')
        return p
    rest=backup_ref[5:]
    bucket,key=rest.split('/',1)
    if settings.backup_s3_bucket and bucket != settings.backup_s3_bucket:
        raise RuntimeError('Záloha ukazuje na jiné než nakonfigurované úložiště.')
    suffix=Path(key).suffix or '.dump'; target=Path(temp_dir)/('restore-source'+suffix)
    _s3_client().download_file(bucket,key,str(target))
    return target


def _assert_safe_restore_target(prod_url: str, test_url: str):
    prod=make_url(prod_url); test=make_url(test_url)
    if str(prod)==str(test): raise RuntimeError('RESTORE_TEST_DATABASE_URL nesmí být produkční databáze.')
    if not test.database: raise RuntimeError('Testovací databáze nemá název.')
    # Explicit safety rail: accidental production targets should fail closed.
    if not any(mark in test.database.lower() for mark in ('restore','test','obnova')):
        raise RuntimeError('Název testovací databáze musí obsahovat restore, test nebo obnova.')


def test_restore(db: Session, backup_path: str):
    run=BackupRun(kind='restore_test',status='running',path=backup_path); db.add(run); db.commit(); db.refresh(run)
    try:
        with tempfile.TemporaryDirectory() as td:
            source=_materialize_backup(backup_path,td)
            if settings.database_url.startswith('sqlite'):
                restored=Path(td)/'restored.sqlite3'; shutil.copy2(source,restored)
                conn=sqlite3.connect(restored)
                tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                required={'workers','clients','catalog_items','audit_log'}
                missing=required-tables
                if missing: raise RuntimeError('Obnovená databáze postrádá tabulky: '+', '.join(sorted(missing)))
                conn.execute('SELECT COUNT(*) FROM catalog_items').fetchone(); conn.close()
            else:
                if not settings.restore_test_database_url:
                    raise RuntimeError('Pro skutečný produkční test obnovy nastavte samostatnou RESTORE_TEST_DATABASE_URL.')
                _assert_safe_restore_target(settings.database_url,settings.restore_test_database_url)
                # The target is disposable and dedicated to restore testing.
                subprocess.run(['pg_restore','--clean','--if-exists','--no-owner','--no-acl','--dbname',settings.restore_test_database_url,str(source)],check=True,capture_output=True,text=True)
                restore_sa_url=('postgresql+psycopg://'+settings.restore_test_database_url[len('postgresql://'):]) if settings.restore_test_database_url.startswith('postgresql://') else settings.restore_test_database_url
                eng=create_engine(restore_sa_url,pool_pre_ping=True)
                inspector=inspect(eng); tables=set(inspector.get_table_names())
                required={'workers','clients','catalog_items','audit_log'}; missing=required-tables
                if missing: raise RuntimeError('Obnovená PostgreSQL databáze postrádá tabulky: '+', '.join(sorted(missing)))
                with eng.connect() as conn:
                    n=conn.execute(text('SELECT COUNT(*) FROM catalog_items')).scalar_one()
                    if n < 216: raise RuntimeError(f'Obnovený číselník má pouze {n} položek; očekává se alespoň 216.')
                eng.dispose()
        run.status='ok'; run.message='Obnova byla skutečně provedena a ověřena v odděleném testovacím prostředí.'
    except Exception as e:
        run.status='error'; run.message=str(e)
    run.finished_at=utcnow_naive(); db.commit(); return run
