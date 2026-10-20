from __future__ import annotations
import calendar, csv, io, json, os, secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import httpx
from oauthlib.oauth2 import WebApplicationClient
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import Base, engine, get_db, SessionLocal
from .models import *
from .security import *
from .audit import log as audit_log, snapshot
from .utils import uid, parse_date, as_bool, csv_safe
from .catalog_seed import seed_catalog
from .indicators import INDICATORS, indicator_summary, indicator_clients, supported_clients
from .importer import save_import_upload, apply_import
from .backups import perform_backup, test_restore

BASE_DIR = Path(__file__).resolve().parent.parent

def initialize_app():
    Path("runtime").mkdir(exist_ok=True)
    if settings.app_env == "production":
        if settings.database_url.startswith("sqlite"):
            raise RuntimeError("Produkční provoz musí používat serverovou relační databázi (PostgreSQL), nikoli SQLite.")
        if settings.secret == "dev-only-change-me" or len(settings.secret) < 40:
            raise RuntimeError("APP_SECRET musí být v produkci náhodný a alespoň 40 znaků dlouhý.")
        if not settings.allow_local_login and (not settings.google_client_id or not settings.google_client_secret):
            raise RuntimeError("V produkci bez lokálního přihlášení musí být nastaveno Google Workspace OAuth.")
    else:
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_catalog(db, BASE_DIR / "data/catalog_seed.json")
        if settings.app_env == "production" and settings.bootstrap_admin_email:
            email=settings.bootstrap_admin_email.strip().lower()
            if not db.scalar(select(Worker).where(func.lower(Worker.email)==email)):
                db.add(Worker(email=email,name=settings.bootstrap_admin_name.strip() or "První správce",role=ROLE_ADMIN,active=True))
                db.commit()
        if settings.app_env != "production" and not db.scalar(select(Worker).where(Worker.email == "admin@example.test")):
            db.add(Worker(email="admin@example.test", name="Demo správce", role=ROLE_ADMIN, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.add(Worker(email="worker@example.test", name="Demo pracovnice", role=ROLE_WORKER, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.add(Worker(email="reader@example.test", name="Demo čtenář", role=ROLE_READER, active=True, password_hash=hash_password("VesnaDemo!2026")))
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_app()
    yield


app = FastAPI(title="Vesna Club", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret, https_only=settings.app_env == "production", same_site="lax", max_age=60*60*12)
if settings.allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app/static")), name="static")

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="same-origin"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"]="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if settings.app_env=="production": response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response

templates = Jinja2Templates(directory=str(BASE_DIR / "app/templates"))


def ctx(request: Request, db: Session, **extra):
    user = get_current_user(request, db)
    out = {"request": request, "user": user, "csrf": ensure_csrf(request), "app_env": settings.app_env}
    out.update(extra)
    return out


def ip(request: Request):
    return request.client.host if request.client else None


def active_workers(db):
    return db.scalars(select(Worker).where(Worker.active == True).order_by(Worker.name)).all()


def catalogs(db: Session, include_inactive=False):
    stmt = select(CatalogItem).where(CatalogItem.visible == True)
    if not include_inactive:
        stmt = stmt.where(CatalogItem.active == True)
    rows = db.scalars(stmt.order_by(CatalogItem.category_key, CatalogItem.sort_order, CatalogItem.name)).all()
    out = {}
    for x in rows: out.setdefault(x.category_key, []).append(x)
    return out


def catalog_name_map(db):
    return {x.item_id: x.name for x in db.scalars(select(CatalogItem)).all()}


def worker_name_map(db):
    return {x.id: x.name for x in db.scalars(select(Worker)).all()}




def make_catalog_snapshot(db: Session, values: dict) -> str:
    keys=["area_id","activity_id","form_id","place_id","method_id","language_id","outcome_id","next_step_id","progress_id","referral_id"]
    ids=[values.get(k) for k in keys if values.get(k)]
    names={x.item_id:x.name for x in db.scalars(select(CatalogItem).where(CatalogItem.item_id.in_(ids))).all()} if ids else {}
    return json.dumps({k:{"id":values.get(k),"name":names.get(values.get(k))} for k in keys if values.get(k)},ensure_ascii=False)

def selectable_indicators():
    codes=["026200","026300","026400","026600","026610"]
    return [(c,INDICATORS[c][0]) for c in codes]


def sync_indicator_records(db: Session, source_type: str, source_id: str, record_date: date, client_ids: list[int], codes: list[str], transcribed=False, sheet_ref=None):
    db.execute(delete(IndicatorRecord).where(IndicatorRecord.source_type==source_type, IndicatorRecord.source_id==source_id))
    for client_id in client_ids:
        for code in sorted(set(codes)):
            db.add(IndicatorRecord(indicator_code=code, client_id=client_id, record_date=record_date, source_type=source_type, source_id=source_id, eligible=True, transcribed_from_sheet=transcribed, attendance_sheet_ref=sheet_ref))


def historical_catalog_name(service: IndividualService, field: str, current_names: dict) -> str:
    try:
        snap=json.loads(service.catalog_snapshot_json or '{}')
        if field in snap and snap[field].get('name'):
            return snap[field]['name']
    except Exception:
        pass
    return current_names.get(getattr(service,field,None),'')


def catalog_item_used(db: Session, item_id: str):
    cols=[IndividualService.area_id,IndividualService.activity_id,IndividualService.form_id,IndividualService.place_id,IndividualService.method_id,IndividualService.language_id,IndividualService.outcome_id,IndividualService.next_step_id,IndividualService.progress_id,IndividualService.referral_id]
    if any(db.scalar(select(func.count()).select_from(IndividualService).where(col==item_id)) for col in cols):
        return True
    return bool(db.scalar(select(func.count()).select_from(CatalogItem).where(CatalogItem.parent_item_id==item_id)))

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session=Depends(get_db)):
    if get_current_user(request, db): return RedirectResponse("/",303)
    return templates.TemplateResponse(request,"login.html", ctx(request,db,local_enabled=settings.allow_local_login,google_enabled=bool(settings.google_client_id),error=request.query_params.get("error")))

@app.post("/login")
async def login_local(request: Request, db: Session=Depends(get_db)):
    if not settings.allow_local_login: raise HTTPException(404)
    form=await request.form(); check_csrf(request,form.get("csrf"))
    user=db.scalar(select(Worker).where(func.lower(Worker.email)==str(form.get("email","")).lower()))
    if not user or not user.active or not verify_password(str(form.get("password","")),user.password_hash):
        return RedirectResponse("/login?error=Neplatné+přihlašovací+údaje",303)
    request.session.clear(); request.session["user_id"]=user.id; ensure_csrf(request)
    audit_log(db,user.id,"login","worker",user.id,remote_ip=ip(request)); db.commit()
    return RedirectResponse("/",303)

@app.get("/auth/google")
def auth_google(request: Request):
    if not settings.google_client_id or not settings.google_client_secret: raise HTTPException(404)
    state=secrets.token_urlsafe(24); request.session["oauth_state"]=state
    params={"client_id":settings.google_client_id,"redirect_uri":settings.base_url.rstrip('/')+"/auth/google/callback","response_type":"code","scope":"openid email profile","state":state,"hd":settings.google_allowed_domain,"access_type":"online","prompt":"select_account"}
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(params),302)

@app.get("/auth/google/callback")
def auth_google_callback(request: Request, code: str, state: str, db: Session=Depends(get_db)):
    if state != request.session.get("oauth_state"): raise HTTPException(400,"Neplatný OAuth state")
    redirect_uri=settings.base_url.rstrip('/')+"/auth/google/callback"
    with httpx.Client(timeout=15) as client:
        token=client.post("https://oauth2.googleapis.com/token",data={"code":code,"client_id":settings.google_client_id,"client_secret":settings.google_client_secret,"redirect_uri":redirect_uri,"grant_type":"authorization_code"}).json()
        if "access_token" not in token: raise HTTPException(400,"Google přihlášení se nezdařilo")
        info=client.get("https://openidconnect.googleapis.com/v1/userinfo",headers={"Authorization":"Bearer "+token["access_token"]}).json()
    email=str(info.get("email","")).lower(); domain=email.split("@")[-1] if "@" in email else ""
    if not info.get("email_verified") or domain != settings.google_allowed_domain.lower(): raise HTTPException(403,"Účet není schválený Workspace Vesny")
    user=db.scalar(select(Worker).where(func.lower(Worker.email)==email))
    if not user or not user.active: raise HTTPException(403,"Tento účet nemá aktivní přístup do evidence")
    request.session.clear(); request.session["user_id"]=user.id; ensure_csrf(request)
    audit_log(db,user.id,"login_google","worker",user.id,remote_ip=ip(request)); db.commit()
    return RedirectResponse("/",303)

@app.get("/logout")
def logout(request: Request, db: Session=Depends(get_db)):
    user=get_current_user(request,db)
    if user: audit_log(db,user.id,"logout","worker",user.id,remote_ip=ip(request)); db.commit()
    request.session.clear(); return RedirectResponse("/login",303)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session=Depends(get_db)):
    user=require_user(request,db)
    today=date.today(); first=today.replace(day=1)
    last_backup=db.scalar(select(BackupRun).where(BackupRun.kind=='backup',BackupRun.status=='ok').order_by(BackupRun.finished_at.desc()))
    last_restore=db.scalar(select(BackupRun).where(BackupRun.kind=='restore_test',BackupRun.status=='ok').order_by(BackupRun.finished_at.desc()))
    stats={
        "clients":db.scalar(select(func.count()).select_from(Client).where(Client.status=='active')) or 0,
        "services":db.scalar(select(func.count()).select_from(IndividualService).where(IndividualService.service_date>=first)) or 0,
        "events":db.scalar(select(func.count()).select_from(Event).where(Event.event_date>=first)) or 0,
        "supported":len(supported_clients(db)),
        "last_backup":last_backup.finished_at.strftime('%d.%m.%Y %H:%M') if last_backup and last_backup.finished_at else None,
        "last_restore":last_restore.finished_at.strftime('%d.%m.%Y %H:%M') if last_restore and last_restore.finished_at else None,
        "open_followups":db.scalar(select(func.count()).select_from(IndividualService).where(IndividualService.follow_up_date.is_not(None),IndividualService.follow_up_date<=today)) or 0,
    }
    return templates.TemplateResponse(request,"dashboard.html",ctx(request,db,title="Přehled",stats=stats))

@app.get("/clients",response_class=HTMLResponse)
def clients_list(request:Request,q:str="",status:str="",db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER])
    stmt=select(Client).order_by(Client.last_name,Client.first_name)
    if q:
        term=f"%{q.strip()}%"; stmt=stmt.where(or_(Client.code.ilike(term),Client.first_name.ilike(term),Client.last_name.ilike(term)))
    if status: stmt=stmt.where(Client.status==status)
    return templates.TemplateResponse(request,"clients.html",ctx(request,db,title="Klienti",clients=db.scalars(stmt).all(),q=q,status=status))

@app.get("/clients/new",response_class=HTMLResponse)
def client_new(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); n=(db.scalar(select(func.count()).select_from(Client)) or 0)+1
    return templates.TemplateResponse(request,"client_form.html",ctx(request,db,client=None,suggested_code=f"V-{n:04d}",conflict=False,duplicate_warning=False))

@app.post("/clients/new")
async def client_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f=await request.form(); check_csrf(request,f.get('csrf'))
    birth=parse_date(f.get('birth_date'))
    duplicate=db.scalar(select(Client).where(func.lower(Client.first_name)==str(f.get('first_name')).lower(),func.lower(Client.last_name)==str(f.get('last_name')).lower(),Client.birth_date==birth)) if birth else None
    c=Client(client_id=uid('CLI'),code=str(f['code']).strip(),first_name=str(f['first_name']).strip(),last_name=str(f['last_name']).strip(),birth_date=birth,entry_date=parse_date(f.get('entry_date')),contact=f.get('contact') or None,fewer_opportunities=True if f.get('fewer')=='yes' else False if f.get('fewer')=='no' else None,document_status=f.get('document_status') or 'unknown',drive_ref=f.get('drive_ref') or None,status=f.get('status') or 'active',notes=f.get('notes') or None)
    db.add(c); db.flush(); audit_log(db,user.id,'create','client',c.client_id,after=snapshot(c),remote_ip=ip(request)); db.commit()
    return RedirectResponse(f"/clients/{c.id}"+('?duplicate=1' if duplicate else ''),303)

@app.get("/clients/{client_id}/edit",response_class=HTMLResponse)
def client_edit(client_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); c=db.get(Client,client_id)
    if not c: raise HTTPException(404)
    return templates.TemplateResponse(request,"client_form.html",ctx(request,db,client=c,suggested_code='',conflict=False,duplicate_warning=False))

@app.post("/clients/{client_id}/edit")
async def client_update(client_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f=await request.form(); check_csrf(request,f.get('csrf')); c=db.get(Client,client_id)
    if not c: raise HTTPException(404)
    expected=int(f.get('version',0)); before=snapshot(c)
    values=dict(code=str(f['code']).strip(),first_name=str(f['first_name']).strip(),last_name=str(f['last_name']).strip(),birth_date=parse_date(f.get('birth_date')),entry_date=parse_date(f.get('entry_date')),contact=f.get('contact') or None,fewer_opportunities=True if f.get('fewer')=='yes' else False if f.get('fewer')=='no' else None,document_status=f.get('document_status') or 'unknown',drive_ref=f.get('drive_ref') or None,status=f.get('status') or 'active',notes=f.get('notes') or None,version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    res=db.execute(update(Client).where(Client.id==client_id,Client.version==expected).values(**values))
    if res.rowcount!=1:
        db.rollback(); c=db.get(Client,client_id); return templates.TemplateResponse(request,"client_form.html",ctx(request,db,client=c,suggested_code='',conflict=True,duplicate_warning=False),status_code=409)
    db.flush(); c=db.get(Client,client_id); audit_log(db,user.id,'update','client',c.client_id,before=before,after=snapshot(c),remote_ip=ip(request)); db.commit(); return RedirectResponse(f"/clients/{client_id}",303)

@app.get("/clients/{client_id}",response_class=HTMLResponse)
def client_detail(client_id:int,request:Request,start:str="",end:str="",kind:str="",worker:str="",activity:str="",db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); c=db.get(Client,client_id)
    if not c: raise HTTPException(404)
    services=db.scalars(select(IndividualService).options(selectinload(IndividualService.worker)).where(IndividualService.client_id==c.id).order_by(IndividualService.service_date.desc())).all()
    parts=db.scalars(select(EventParticipant).options(selectinload(EventParticipant.event)).where(EventParticipant.client_id==c.id).order_by(EventParticipant.id.desc())).all()
    docs=db.scalars(select(Document).options(selectinload(Document.worker)).where(Document.client_id==c.id).order_by(Document.inserted_date.desc())).all()
    event_ids=sorted({p.event_id for p in parts})
    event_workers={}
    if event_ids:
        for event_id,name in db.execute(select(EventWorker.event_id,Worker.name).join(Worker,Worker.id==EventWorker.worker_id).where(EventWorker.event_id.in_(event_ids))).all():
            event_workers.setdefault(event_id,[]).append(name)
    names=catalog_name_map(db); timeline=[]; ka_summary={}
    for svc in services:
        activity_name=historical_catalog_name(svc,'activity_id',names) or ''
        ka_name=svc.subactivity or svc.ka
        ka_summary[ka_name]=ka_summary.get(ka_name,0)+1
        timeline.append({"date":svc.service_date,"kind":"individuální podpora","text":svc.description or activity_name or 'Výkon',"meta":f"{svc.minutes} min · {ka_name} · {svc.worker.name}","worker":svc.worker.name,"activity":activity_name})
    for part in parts:
        ka_name=part.event.subactivity or part.event.ka
        ka_summary[ka_name]=ka_summary.get(ka_name,0)+1
        workers=', '.join(event_workers.get(part.event_id,[]))
        timeline.append({"date":part.event.event_date,"kind":"skupinová účast","text":part.event.title,"meta":f"{ka_name}"+(f" · {workers}" if workers else ''),"worker":workers,"activity":f"{part.event.event_type} {part.event.title}"})
    for doc in docs:
        timeline.append({"date":doc.inserted_date,"kind":"dokument","text":doc.name,"meta":f"{doc.kind or ''}"+(f" · {doc.worker.name}" if doc.worker else ''),"worker":doc.worker.name if doc.worker else '',"activity":""})
    sd=parse_date(start); ed=parse_date(end); worker_q=worker.strip().lower(); activity_q=activity.strip().lower()
    timeline=[x for x in timeline if (not sd or x['date']>=sd) and (not ed or x['date']<=ed) and (not kind or x['kind']==kind) and (not worker_q or worker_q in (x.get('worker') or '').lower()) and (not activity_q or activity_q in (x.get('activity') or '').lower())]
    timeline.sort(key=lambda x:x['date'] or date.min,reverse=True)
    audits=db.scalars(select(AuditLog).where(AuditLog.entity_type=='client',AuditLog.entity_id==c.client_id).order_by(AuditLog.created_at.desc())).all()
    totals={"service_count":len(services),"minutes":sum(s.minutes for s in services),"event_count":len(parts),"document_count":len(docs),"followups":sum(1 for s in services if s.follow_up_date)}
    filters={'start':start,'end':end,'kind':kind,'worker':worker,'activity':activity}
    return templates.TemplateResponse(request,"client_detail.html",ctx(request,db,client=c,timeline=timeline,audits=audits,worker_names=worker_name_map(db),totals=totals,ka_summary=sorted(ka_summary.items()),filters=filters,duplicate_warning=request.query_params.get('duplicate')=='1'))

@app.get("/services",response_class=HTMLResponse)
def services_list(request:Request,start:str="",end:str="",ka:str="",db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); stmt=select(IndividualService).options(selectinload(IndividualService.client),selectinload(IndividualService.worker)).order_by(IndividualService.service_date.desc(),IndividualService.id.desc())
    if start: stmt=stmt.where(IndividualService.service_date>=parse_date(start))
    if end: stmt=stmt.where(IndividualService.service_date<=parse_date(end))
    if ka: stmt=stmt.where(or_(IndividualService.ka==ka,IndividualService.subactivity==ka))
    services=db.scalars(stmt).all(); names=catalog_name_map(db)
    for svc in services: svc.display_activity=historical_catalog_name(svc,'activity_id',names)
    return templates.TemplateResponse(request,"services.html",ctx(request,db,services=services,catalog_names=names,start=start,end=end,ka=ka))


def service_form_ctx(request,db,service=None,selected_client=0,conflict=False,limit_warning=None):
    cata=catalogs(db,include_inactive=bool(service))
    selected=[]
    if service: selected=db.scalars(select(IndicatorRecord.indicator_code).where(IndicatorRecord.source_type=='service',IndicatorRecord.source_id==service.service_id)).all()
    return ctx(request,db,service=service,clients=db.scalars(select(Client).where(Client.status=='active').order_by(Client.last_name)).all(),workers=active_workers(db),catalog=cata,selected_client=selected_client,today=date.today(),selectable_indicators=selectable_indicators(),selected_indicators=selected,conflict=conflict,limit_warning=limit_warning)

@app.get("/services/new",response_class=HTMLResponse)
def service_new(request:Request,client_id:int=0,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); return templates.TemplateResponse(request,"service_form.html",service_form_ctx(request,db,selected_client=client_id))

async def parse_service_form(request):
    f=await request.form(); return f, f.getlist('indicators')

@app.post("/services/new")
async def service_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f,inds=await parse_service_form(request); check_csrf(request,f.get('csrf'))
    s=IndividualService(service_id=uid('VYK'),client_id=int(f['client_id']),service_date=parse_date(f['service_date']),minutes=int(f['minutes']),worker_id=int(f['worker_id']),ka=f.get('ka') or 'KA3',subactivity=f.get('subactivity') or None,area_id=f.get('area_id') or None,activity_id=f.get('activity_id') or None,form_id=f.get('form_id') or None,place_id=f.get('place_id') or None,method_id=f.get('method_id') or None,language_id=f.get('language_id') or None,outcome_id=f.get('outcome_id') or None,next_step_id=f.get('next_step_id') or None,follow_up_date=parse_date(f.get('follow_up_date')),progress_id=f.get('progress_id') or None,referral_id=f.get('referral_id') or None,description=f.get('description') or None,eligible_project=as_bool(f.get('eligible_project')),attendance_sheet_ref=f.get('attendance_sheet_ref') or None,transcribed_from_sheet=as_bool(f.get('transcribed_from_sheet')))
    s.catalog_snapshot_json=make_catalog_snapshot(db,{k:getattr(s,k) for k in ['area_id','activity_id','form_id','place_id','method_id','language_id','outcome_id','next_step_id','progress_id','referral_id']})
    db.add(s); db.flush(); sync_indicator_records(db,'service',s.service_id,s.service_date,[s.client_id],inds if s.eligible_project else [],s.transcribed_from_sheet,s.attendance_sheet_ref); audit_log(db,user.id,'create','service',s.service_id,after=snapshot(s),remote_ip=ip(request)); db.commit()
    return RedirectResponse('/services',303)

@app.get("/services/{service_id}/edit",response_class=HTMLResponse)
def service_edit(service_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); s=db.get(IndividualService,service_id)
    if not s: raise HTTPException(404)
    warning=None
    if s.subactivity in {'3.1','3.2'}:
        total=db.scalar(select(func.sum(IndividualService.minutes)).where(IndividualService.client_id==s.client_id,IndividualService.subactivity.in_(['3.1','3.2']))) or 0
        if total>settings.ka31_32_limit_minutes: warning=f"Součet KA3.1 + 3.2 je {total/60:.1f} h. Nastavené upozornění je {settings.ka31_32_limit_minutes/60:.1f} h; záznam není blokován, protože výklad limitu musí potvrdit správkyně."
    if s.subactivity=='3.3':
        total=db.scalar(select(func.sum(IndividualService.minutes)).where(IndividualService.client_id==s.client_id,IndividualService.subactivity=='3.3')) or 0
        if total>settings.ka33_limit_minutes: warning=f"Součet KA3.3 je {total/60:.1f} h; nastavené upozornění je {settings.ka33_limit_minutes/60:.1f} h."
    return templates.TemplateResponse(request,"service_form.html",service_form_ctx(request,db,service=s,limit_warning=warning))

@app.post("/services/{service_id}/edit")
async def service_update(service_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f,inds=await parse_service_form(request); check_csrf(request,f.get('csrf')); s=db.get(IndividualService,service_id)
    if not s: raise HTTPException(404)
    before=snapshot(s); expected=int(f.get('version',0)); values=dict(client_id=int(f['client_id']),service_date=parse_date(f['service_date']),minutes=int(f['minutes']),worker_id=int(f['worker_id']),ka=f.get('ka') or 'KA3',subactivity=f.get('subactivity') or None,area_id=f.get('area_id') or None,activity_id=f.get('activity_id') or None,form_id=f.get('form_id') or None,place_id=f.get('place_id') or None,method_id=f.get('method_id') or None,language_id=f.get('language_id') or None,outcome_id=f.get('outcome_id') or None,next_step_id=f.get('next_step_id') or None,follow_up_date=parse_date(f.get('follow_up_date')),progress_id=f.get('progress_id') or None,referral_id=f.get('referral_id') or None,description=f.get('description') or None,eligible_project=as_bool(f.get('eligible_project')),attendance_sheet_ref=f.get('attendance_sheet_ref') or None,transcribed_from_sheet=as_bool(f.get('transcribed_from_sheet')),version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    values['catalog_snapshot_json']=make_catalog_snapshot(db,values)
    res=db.execute(update(IndividualService).where(IndividualService.id==service_id,IndividualService.version==expected).values(**values))
    if res.rowcount!=1:
        db.rollback(); s=db.get(IndividualService,service_id); return templates.TemplateResponse(request,"service_form.html",service_form_ctx(request,db,service=s,conflict=True),status_code=409)
    db.flush(); s=db.get(IndividualService,service_id); sync_indicator_records(db,'service',s.service_id,s.service_date,[s.client_id],inds if s.eligible_project else [],s.transcribed_from_sheet,s.attendance_sheet_ref); audit_log(db,user.id,'update','service',s.service_id,before=before,after=snapshot(s),remote_ip=ip(request)); db.commit(); return RedirectResponse('/services',303)

@app.get("/events",response_class=HTMLResponse)
def events_list(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); events=db.scalars(select(Event).order_by(Event.event_date.desc(),Event.id.desc())).all(); counts=dict(db.execute(select(EventParticipant.event_id,func.count()).where(EventParticipant.client_id.is_not(None),EventParticipant.attendance_status=='present').group_by(EventParticipant.event_id)).all()); return templates.TemplateResponse(request,"events.html",ctx(request,db,events=events,counts=counts))

def event_form_ctx(request,db,event=None,conflict=False):
    selected_clients=[]; selected_workers=[]; selected_inds=[]; guest_note=''
    if event:
        selected_clients=db.scalars(select(EventParticipant.client_id).where(EventParticipant.event_id==event.id,EventParticipant.client_id.is_not(None))).all(); selected_workers=db.scalars(select(EventWorker.worker_id).where(EventWorker.event_id==event.id)).all(); selected_inds=db.scalars(select(IndicatorRecord.indicator_code).where(IndicatorRecord.source_type=='event',IndicatorRecord.source_id==event.event_id)).all(); guests=db.scalars(select(EventParticipant.display_name).where(EventParticipant.event_id==event.id,EventParticipant.client_id.is_(None))).all(); guest_note='; '.join(x for x in guests if x)
    return ctx(request,db,event=event,clients=db.scalars(select(Client).where(Client.status=='active').order_by(Client.last_name)).all(),workers=active_workers(db),today=date.today(),selected_clients=selected_clients,selected_workers=selected_workers,selected_indicators=selected_inds,guest_note=guest_note,selectable_indicators=selectable_indicators(),conflict=conflict)

@app.get("/events/new",response_class=HTMLResponse)
def event_new(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); return templates.TemplateResponse(request,"event_form.html",event_form_ctx(request,db))

async def parse_event_form(request):
    f=await request.form(); return f,[int(x) for x in f.getlist('client_ids')],[int(x) for x in f.getlist('worker_ids')],f.getlist('indicators')

@app.post("/events/new")
async def event_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f,client_ids,worker_ids,inds=await parse_event_form(request); check_csrf(request,f.get('csrf'))
    if f.get('event_type')=='civic_orientation' and '026200' not in inds: inds.append('026200')
    e=Event(event_id=uid('AKC'),title=f['title'],event_date=parse_date(f['event_date']),start_time=f.get('start_time') or None,duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,ka=f.get('ka') or 'KA2',subactivity=f.get('subactivity') or None,event_type=f.get('event_type') or 'group_program',attendance_sheet_ref=f.get('attendance_sheet_ref') or None,notes=f.get('notes') or None,created_by_id=user.id)
    db.add(e); db.flush();
    for wid in sorted(set(worker_ids)): db.add(EventWorker(event_id=e.id,worker_id=wid))
    for cid in sorted(set(client_ids)): db.add(EventParticipant(event_id=e.id,client_id=cid,participant_kind='project',attendance_status='present',eligible_project=True,transcribed_from_sheet=True if e.attendance_sheet_ref else False))
    if f.get('guest_note'): db.add(EventParticipant(event_id=e.id,client_id=None,display_name=f.get('guest_note'),participant_kind='guest',attendance_status='present',eligible_project=False))
    sync_indicator_records(db,'event',e.event_id,e.event_date,client_ids,inds,bool(e.attendance_sheet_ref),e.attendance_sheet_ref); audit_log(db,user.id,'create','event',e.event_id,after=snapshot(e),remote_ip=ip(request)); db.commit(); return RedirectResponse(f'/events/{e.id}',303)

@app.get("/events/{event_id}",response_class=HTMLResponse)
def event_detail(event_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); e=db.get(Event,event_id)
    if not e: raise HTTPException(404)
    participants=db.scalars(select(EventParticipant).options(selectinload(EventParticipant.client)).where(EventParticipant.event_id==e.id,EventParticipant.client_id.is_not(None))).all(); wids=db.scalars(select(EventWorker.worker_id).where(EventWorker.event_id==e.id)).all(); names=worker_name_map(db); return templates.TemplateResponse(request,"event_detail.html",ctx(request,db,event=e,participants=participants,worker_names=[names.get(x,'') for x in wids]))

@app.get("/events/{event_id}/edit",response_class=HTMLResponse)
def event_edit(event_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); e=db.get(Event,event_id)
    if not e: raise HTTPException(404)
    return templates.TemplateResponse(request,"event_form.html",event_form_ctx(request,db,e))

@app.post("/events/{event_id}/edit")
async def event_update(event_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f,client_ids,worker_ids,inds=await parse_event_form(request); check_csrf(request,f.get('csrf'));
    if f.get('event_type')=='civic_orientation' and '026200' not in inds: inds.append('026200')
    e=db.get(Event,event_id)
    if not e: raise HTTPException(404)
    before=snapshot(e); expected=int(f.get('version',0)); values=dict(title=f['title'],event_date=parse_date(f['event_date']),start_time=f.get('start_time') or None,duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,ka=f.get('ka') or 'KA2',subactivity=f.get('subactivity') or None,event_type=f.get('event_type') or 'group_program',attendance_sheet_ref=f.get('attendance_sheet_ref') or None,notes=f.get('notes') or None,version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    res=db.execute(update(Event).where(Event.id==event_id,Event.version==expected).values(**values))
    if res.rowcount!=1:
        db.rollback(); e=db.get(Event,event_id); return templates.TemplateResponse(request,"event_form.html",event_form_ctx(request,db,e,True),status_code=409)
    db.execute(delete(EventWorker).where(EventWorker.event_id==event_id)); db.execute(delete(EventParticipant).where(EventParticipant.event_id==event_id))
    for wid in sorted(set(worker_ids)): db.add(EventWorker(event_id=event_id,worker_id=wid))
    for cid in sorted(set(client_ids)): db.add(EventParticipant(event_id=event_id,client_id=cid,participant_kind='project',attendance_status='present',eligible_project=True,transcribed_from_sheet=True if f.get('attendance_sheet_ref') else False))
    if f.get('guest_note'): db.add(EventParticipant(event_id=event_id,client_id=None,display_name=f.get('guest_note'),participant_kind='guest',attendance_status='present',eligible_project=False))
    db.flush(); e=db.get(Event,event_id); sync_indicator_records(db,'event',e.event_id,e.event_date,client_ids,inds,bool(e.attendance_sheet_ref),e.attendance_sheet_ref); audit_log(db,user.id,'update','event',e.event_id,before=before,after=snapshot(e),remote_ip=ip(request)); db.commit(); return RedirectResponse(f'/events/{event_id}',303)

@app.get("/daily-notes",response_class=HTMLResponse)
def daily_calendar(request:Request,year:int=0,month:int=0,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); today=date.today(); year=year or today.year; month=month or today.month; cal=calendar.Calendar(firstweekday=0); weeks=cal.monthdatescalendar(year,month); counts=dict(db.execute(select(DailyNote.note_date,func.count()).where(func.strftime('%Y',DailyNote.note_date)==str(year),func.strftime('%m',DailyNote.note_date)==f'{month:02d}').group_by(DailyNote.note_date)).all()) if settings.database_url.startswith('sqlite') else {}
    if not settings.database_url.startswith('sqlite'):
        first=date(year,month,1); last=weeks[-1][-1]; counts=dict(db.execute(select(DailyNote.note_date,func.count()).where(DailyNote.note_date>=first,DailyNote.note_date<=last).group_by(DailyNote.note_date)).all())
    days=[{"day":d.day,"iso":d.isoformat(),"other":d.month!=month,"count":counts.get(d,0)} for w in weeks for d in w]
    prev_m=12 if month==1 else month-1; prev_y=year-1 if month==1 else year; next_m=1 if month==12 else month+1; next_y=year+1 if month==12 else year
    return templates.TemplateResponse(request,"daily_notes.html",ctx(request,db,year=year,month=month,days=days,prev_m=prev_m,prev_y=prev_y,next_m=next_m,next_y=next_y))

@app.get("/daily-notes/day/{day}",response_class=HTMLResponse)
def daily_day(day:str,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); d=parse_date(day); notes=db.scalars(select(DailyNote).options(selectinload(DailyNote.worker)).where(DailyNote.note_date==d).order_by(DailyNote.created_at)).all(); return templates.TemplateResponse(request,"daily_day.html",ctx(request,db,day=d,notes=notes))

@app.get("/daily-notes/new",response_class=HTMLResponse)
def daily_new(request:Request,date:str="",db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); return templates.TemplateResponse(request,"daily_form.html",ctx(request,db,note=None,selected_date=parse_date(date) if date else __import__('datetime').date.today(),history=[],worker_names={},conflict=False))

@app.post("/daily-notes/new")
async def daily_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); f=await request.form(); check_csrf(request,f.get('csrf')); n=DailyNote(note_id=uid('DEN'),note_date=parse_date(f['note_date']),worker_id=user.id,summary=f['summary']); db.add(n); db.flush(); audit_log(db,user.id,'create','daily_note',n.note_id,after=snapshot(n),remote_ip=ip(request)); db.commit(); return RedirectResponse(f'/daily-notes/day/{n.note_date.isoformat()}',303)

@app.get("/daily-notes/{note_id}/edit",response_class=HTMLResponse)
def daily_edit(note_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); n=db.get(DailyNote,note_id)
    if not n: raise HTTPException(404)
    if user.role!=ROLE_ADMIN and n.worker_id!=user.id: raise HTTPException(403,"Upravovat může autor nebo správce")
    hist=db.scalars(select(AuditLog).where(AuditLog.entity_type=='daily_note',AuditLog.entity_id==n.note_id).order_by(AuditLog.created_at.desc())).all(); return templates.TemplateResponse(request,"daily_form.html",ctx(request,db,note=n,selected_date=n.note_date,history=hist,worker_names=worker_name_map(db),conflict=False))

@app.post("/daily-notes/{note_id}/edit")
async def daily_update(note_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); n=db.get(DailyNote,note_id)
    if not n: raise HTTPException(404)
    if user.role!=ROLE_ADMIN and n.worker_id!=user.id: raise HTTPException(403)
    f=await request.form(); check_csrf(request,f.get('csrf')); before=snapshot(n); expected=int(f.get('version',0)); values=dict(note_date=parse_date(f['note_date']),summary=f['summary'],version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    res=db.execute(update(DailyNote).where(DailyNote.id==note_id,DailyNote.version==expected).values(**values))
    if res.rowcount!=1:
        db.rollback(); n=db.get(DailyNote,note_id); hist=db.scalars(select(AuditLog).where(AuditLog.entity_type=='daily_note',AuditLog.entity_id==n.note_id).order_by(AuditLog.created_at.desc())).all(); return templates.TemplateResponse(request,"daily_form.html",ctx(request,db,note=n,selected_date=n.note_date,history=hist,worker_names=worker_name_map(db),conflict=True),status_code=409)
    db.flush(); n=db.get(DailyNote,note_id); audit_log(db,user.id,'update','daily_note',n.note_id,before=before,after=snapshot(n),remote_ip=ip(request)); db.commit(); return RedirectResponse(f'/daily-notes/day/{n.note_date.isoformat()}',303)

@app.get("/reports",response_class=HTMLResponse)
def reports(request:Request,start:str="",end:str="",db:Session=Depends(get_db)):
    require_user(request,db); s=parse_date(start); e=parse_date(end); return templates.TemplateResponse(request,"reports.html",ctx(request,db,summary=indicator_summary(db,s,e),start=start,end=end))

@app.get("/reports/{code}",response_class=HTMLResponse)
def report_detail(code:str,request:Request,start:str="",end:str="",db:Session=Depends(get_db)):
    user=require_user(request,db)
    if code not in INDICATORS: raise HTTPException(404)
    show_pii=user.role in {ROLE_ADMIN,ROLE_WORKER}
    sd=parse_date(start); ed=parse_date(end); ids=indicator_clients(db,code,sd,ed); clients=db.scalars(select(Client).where(Client.id.in_(ids)).order_by(Client.code)).all() if ids else []
    records=[]
    def client_label(c):
        if not c: return '—'
        return f'{c.code} · {c.first_name} {c.last_name}' if show_pii else c.code
    if code=='026000':
        q=select(IndividualService).options(selectinload(IndividualService.client)).where(IndividualService.eligible_project==True)
        if sd: q=q.where(IndividualService.service_date>=sd)
        if ed: q=q.where(IndividualService.service_date<=ed)
        for x in db.scalars(q).all(): records.append({'date':x.service_date,'client':client_label(x.client),'source':'individuální výkon','ka':x.subactivity or x.ka,'sheet':x.attendance_sheet_ref,'transcribed':x.transcribed_from_sheet})
        q=select(EventParticipant).options(selectinload(EventParticipant.client),selectinload(EventParticipant.event)).join(Event,Event.id==EventParticipant.event_id).where(EventParticipant.eligible_project==True,EventParticipant.participant_kind=='project',EventParticipant.attendance_status=='present',EventParticipant.client_id.is_not(None))
        if sd: q=q.where(Event.event_date>=sd)
        if ed: q=q.where(Event.event_date<=ed)
        for x in db.scalars(q).all(): records.append({'date':x.event.event_date,'client':client_label(x.client),'source':x.event.title,'ka':x.event.subactivity or x.event.ka,'sheet':x.event.attendance_sheet_ref,'transcribed':x.transcribed_from_sheet})
    else:
        q=select(IndicatorRecord).where(IndicatorRecord.indicator_code==code,IndicatorRecord.eligible==True)
        if sd: q=q.where(IndicatorRecord.record_date>=sd)
        if ed: q=q.where(IndicatorRecord.record_date<=ed)
        for ir in db.scalars(q.order_by(IndicatorRecord.record_date.desc())).all():
            c=db.get(Client,ir.client_id) if ir.client_id else None; ka=''; source=ir.source_type
            if ir.source_type=='service':
                src=db.scalar(select(IndividualService).where(IndividualService.service_id==ir.source_id)); ka=(src.subactivity or src.ka) if src else ''; source='individuální výkon'
            elif ir.source_type=='event':
                src=db.scalar(select(Event).where(Event.event_id==ir.source_id)); ka=(src.subactivity or src.ka) if src else ''; source=src.title if src else 'skupinová akce'
            records.append({'date':ir.record_date,'client':client_label(c),'source':source,'ka':ka,'sheet':ir.attendance_sheet_ref,'transcribed':ir.transcribed_from_sheet})
    records.sort(key=lambda r:r['date'],reverse=True)
    return templates.TemplateResponse(request,"report_detail.html",ctx(request,db,code=code,name=INDICATORS[code][0],clients=clients,records=records,show_pii=show_pii,start=start,end=end))

@app.get("/exports/reports.csv")
def reports_export(request:Request,start:str="",end:str="",db:Session=Depends(get_db)):
    require_user(request,db); rows=indicator_summary(db,parse_date(start),parse_date(end)); buf=io.StringIO(); w=csv.writer(buf,delimiter=';'); w.writerow(['Vytvořeno',datetime.now().isoformat(timespec='minutes')]); w.writerow(['Filtr od',start,'do',end]); w.writerow(['Kód','Indikátor','Výsledek','Cíl']);
    for r in rows: w.writerow([csv_safe(r['code']),csv_safe(r['name']),r['value'],r['target']])
    data='\ufeff'+buf.getvalue(); return StreamingResponse(iter([data.encode('utf-8')]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="vesna-indikatory.csv"'})

@app.get("/admin/workers",response_class=HTMLResponse)
def admin_workers(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); return templates.TemplateResponse(request,"admin_workers.html",ctx(request,db,workers=db.scalars(select(Worker).order_by(Worker.name)).all()))

@app.get("/admin/workers/new",response_class=HTMLResponse)
def admin_worker_new(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); return templates.TemplateResponse(request,"admin_worker_form.html",ctx(request,db,worker=None))

@app.post("/admin/workers/new")
async def admin_worker_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); w=Worker(email=f['email'].strip().lower(),name=f['name'].strip(),role=f['role'],active=as_bool(f.get('active')),password_hash=hash_password(f['password']) if f.get('password') else None); db.add(w); db.flush(); audit_log(db,user.id,'create','worker',w.email,after=snapshot(w),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/workers',303)

@app.get("/admin/workers/{worker_id}/edit",response_class=HTMLResponse)
def admin_worker_edit(worker_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); w=db.get(Worker,worker_id)
    if not w: raise HTTPException(404)
    return templates.TemplateResponse(request,"admin_worker_form.html",ctx(request,db,worker=w))

@app.post("/admin/workers/{worker_id}/edit")
async def admin_worker_update(worker_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); w=db.get(Worker,worker_id)
    if not w: raise HTTPException(404)
    before=snapshot(w); expected=int(f.get('version',0)); vals=dict(email=f['email'].strip().lower(),name=f['name'].strip(),role=f['role'],active=as_bool(f.get('active')),version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None));
    if f.get('password'): vals['password_hash']=hash_password(f['password'])
    res=db.execute(update(Worker).where(Worker.id==worker_id,Worker.version==expected).values(**vals));
    if res.rowcount!=1: db.rollback(); raise HTTPException(409,'Pracovníka mezitím změnil jiný uživatel')
    db.flush(); w=db.get(Worker,worker_id); audit_log(db,user.id,'update','worker',w.email,before=before,after=snapshot(w),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/workers',303)

@app.get("/admin/catalog",response_class=HTMLResponse)
def admin_catalog(request:Request,category:str="",active:str="",db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); stmt=select(CatalogItem).order_by(CatalogItem.category_key,CatalogItem.sort_order,CatalogItem.name)
    if category: stmt=stmt.where(CatalogItem.category_key==category)
    if active in {'0','1'}: stmt=stmt.where(CatalogItem.active==(active=='1'))
    cats=db.scalars(select(CatalogCategory).order_by(CatalogCategory.sort_order)).all(); items=db.scalars(stmt).all(); names={x.item_id:x.name for x in db.scalars(select(CatalogItem)).all()}; return templates.TemplateResponse(request,"admin_catalog.html",ctx(request,db,categories=cats,items=items,names=names,category=category,active=active))

@app.get("/admin/catalog/new",response_class=HTMLResponse)
def admin_catalog_new(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); cats=db.scalars(select(CatalogCategory).order_by(CatalogCategory.sort_order)).all(); areas=db.scalars(select(CatalogItem).where(CatalogItem.category_key=='Oblast').order_by(CatalogItem.sort_order)).all(); return templates.TemplateResponse(request,"admin_catalog_form.html",ctx(request,db,item=None,categories=cats,areas=areas,used=False,suggested_id='NEW'+secrets.token_hex(3).upper(),impact_count=0,merge_targets=[]))

@app.post("/admin/catalog/new")
async def admin_catalog_create(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=CatalogItem(item_id=f['item_id'].strip(),category_key=f['category_key'],parent_item_id=f.get('parent_item_id') or None,name=f['name'].strip(),sort_order=int(f.get('sort_order') or 0),active=as_bool(f.get('active')),visible=as_bool(f.get('visible'))); db.add(x); db.flush(); audit_log(db,user.id,'create','catalog_item',x.item_id,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/catalog',303)

@app.get("/admin/catalog/{item_pk}/edit",response_class=HTMLResponse)
def admin_catalog_edit(item_pk:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); x=db.get(CatalogItem,item_pk)
    if not x: raise HTTPException(404)
    cats=db.scalars(select(CatalogCategory).order_by(CatalogCategory.sort_order)).all(); areas=db.scalars(select(CatalogItem).where(CatalogItem.category_key=='Oblast').order_by(CatalogItem.sort_order)).all(); merge_targets=db.scalars(select(CatalogItem).where(CatalogItem.category_key==x.category_key,CatalogItem.id!=x.id,CatalogItem.active==True).order_by(CatalogItem.name)).all(); return templates.TemplateResponse(request,"admin_catalog_form.html",ctx(request,db,item=x,categories=cats,areas=areas,used=catalog_item_used(db,x.item_id),suggested_id='',impact_count=catalog_item_impact_count(db,x.item_id),merge_targets=merge_targets))

@app.post("/admin/catalog/{item_pk}/edit")
async def admin_catalog_update(item_pk:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=db.get(CatalogItem,item_pk)
    if not x: raise HTTPException(404)
    before=snapshot(x); expected=int(f.get('version',0)); vals=dict(category_key=f['category_key'],parent_item_id=f.get('parent_item_id') or None,name=f['name'].strip(),sort_order=int(f.get('sort_order') or 0),active=as_bool(f.get('active')),visible=as_bool(f.get('visible')),version=expected+1,updated_at=datetime.now(timezone.utc).replace(tzinfo=None)); res=db.execute(update(CatalogItem).where(CatalogItem.id==item_pk,CatalogItem.version==expected).values(**vals));
    if res.rowcount!=1: db.rollback(); raise HTTPException(409,'Položku mezitím změnil jiný uživatel')
    db.flush(); x=db.get(CatalogItem,item_pk); audit_log(db,user.id,'update','catalog_item',x.item_id,before=before,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/catalog',303)

@app.post("/admin/catalog/{item_pk}/delete")
async def admin_catalog_delete(item_pk:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=db.get(CatalogItem,item_pk)
    if not x: raise HTTPException(404)
    if catalog_item_used(db,x.item_id): raise HTTPException(409,'Použitou položku nelze fyzicky smazat; deaktivujte ji.')
    before=snapshot(x); db.delete(x); audit_log(db,user.id,'delete','catalog_item',x.item_id,before=before,remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/catalog',303)

@app.post("/admin/catalog/bulk")
async def admin_catalog_bulk(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); ids=[int(x) for x in f.getlist('item_ids')]; target=f.get('action')=='activate'
    if ids:
        for x in db.scalars(select(CatalogItem).where(CatalogItem.id.in_(ids))).all():
            before=snapshot(x); x.active=target; x.version+=1; audit_log(db,user.id,'bulk_activate' if target else 'bulk_deactivate','catalog_item',x.item_id,before=before,after=snapshot(x),remote_ip=ip(request))
        db.commit()
    return RedirectResponse('/admin/catalog',303)

@app.get("/admin/import",response_class=HTMLResponse)
def admin_import(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); return templates.TemplateResponse(request,"admin_import.html",ctx(request,db,preview=None,token=None,result=None))

@app.post("/admin/import",response_class=HTMLResponse)
async def admin_import_preview(request:Request,file:UploadFile=File(...),db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); form=await request.form(); check_csrf(request,form.get('csrf')); content=await file.read(); batch,preview=save_import_upload(content,str(BASE_DIR/'runtime/imports'),db,user.id); return templates.TemplateResponse(request,"admin_import.html",ctx(request,db,preview=preview,token=batch.token,result=None))

@app.post("/admin/import/{token}/apply",response_class=HTMLResponse)
async def admin_import_apply(token:str,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); batch=db.scalar(select(ImportBatch).where(ImportBatch.token==token,ImportBatch.created_by_id==user.id))
    if not batch or batch.status!='preview': raise HTTPException(404)
    result=apply_import(batch,db); audit_log(db,user.id,'apply_import','import_batch',token,after=result,remote_ip=ip(request)); db.commit(); return templates.TemplateResponse(request,"admin_import.html",ctx(request,db,preview=None,token=None,result=json.dumps(result,ensure_ascii=False,indent=2)))

@app.get("/admin/backups",response_class=HTMLResponse)
def admin_backups(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); runs=db.scalars(select(BackupRun).order_by(BackupRun.started_at.desc()).limit(50)).all(); last_ok=next((r for r in runs if r.kind=='backup' and r.status=='ok'),None); return templates.TemplateResponse(request,"admin_backups.html",ctx(request,db,runs=runs,last_ok=last_ok))

@app.post("/admin/backups/run")
async def admin_backup_run(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); r=perform_backup(db); audit_log(db,user.id,'backup','backup_run',r.id,after={'status':r.status,'path':r.path},remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/backups',303)

@app.post("/admin/backups/test")
async def admin_backup_test(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); r=test_restore(db,f.get('path')); audit_log(db,user.id,'restore_test','backup_run',r.id,after={'status':r.status},remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/backups',303)

@app.get("/admin/audit",response_class=HTMLResponse)
def admin_audit(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); rows=db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(300)).all(); return templates.TemplateResponse(request,"admin_audit.html",ctx(request,db,rows=rows,worker_names=worker_name_map(db)))

@app.get("/health")
def health(db:Session=Depends(get_db)):
    db.execute(select(1)); return {"status":"ok"}

@app.get("/clients/{client_id}/documents/new", response_class=HTMLResponse)
def document_new(client_id:int,request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); c=db.get(Client,client_id)
    if not c: raise HTTPException(404)
    return templates.TemplateResponse(request,"document_form.html",ctx(request,db,client=c,today=date.today()))

@app.post("/clients/{client_id}/documents/new")
async def document_create(client_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); c=db.get(Client,client_id)
    if not c: raise HTTPException(404)
    f=await request.form(); check_csrf(request,f.get('csrf'))
    d=Document(document_id=uid('DOK'),client_id=c.id,name=f['name'].strip(),kind=f.get('kind') or None,drive_ref=f.get('drive_ref') or None,inserted_date=parse_date(f.get('inserted_date')) or date.today(),worker_id=user.id,notes=f.get('notes') or None)
    db.add(d); db.flush(); audit_log(db,user.id,'create','document',d.document_id,after=snapshot(d),remote_ip=ip(request)); db.commit(); return RedirectResponse(f'/clients/{client_id}',303)


def activity_report_data(db:Session, filters:dict):
    start=parse_date(filters.get('start')); end=parse_date(filters.get('end')); ka=filters.get('ka') or ''; worker_id=filters.get('worker_id') or ''; area_id=filters.get('area_id') or ''; activity_id=filters.get('activity_id') or ''; event_type=filters.get('event_type') or ''; status=filters.get('status') or ''; indicator=filters.get('indicator') or ''
    names=catalog_name_map(db); rows=[]; client_ids=set(); total_minutes=0
    ss=select(IndividualService).options(selectinload(IndividualService.client),selectinload(IndividualService.worker)).join(Client,Client.id==IndividualService.client_id)
    if start: ss=ss.where(IndividualService.service_date>=start)
    if end: ss=ss.where(IndividualService.service_date<=end)
    if ka: ss=ss.where(or_(IndividualService.ka==ka,IndividualService.subactivity==ka))
    if worker_id: ss=ss.where(IndividualService.worker_id==int(worker_id))
    if area_id: ss=ss.where(IndividualService.area_id==area_id)
    if activity_id: ss=ss.where(IndividualService.activity_id==activity_id)
    if status: ss=ss.where(Client.status==status)
    if indicator:
        ids=select(IndicatorRecord.source_id).where(IndicatorRecord.source_type=='service',IndicatorRecord.indicator_code==indicator,IndicatorRecord.eligible==True)
        if indicator=='026000':
            ss=ss.where(IndividualService.eligible_project==True)
        else: ss=ss.where(IndividualService.service_id.in_(ids))
    for x in db.scalars(ss.order_by(IndividualService.service_date.desc())).all():
        rows.append({'date':x.service_date,'kind':'individuální','ka':x.subactivity or x.ka,'client':f'{x.client.code} · {x.client.first_name} {x.client.last_name}','client_id':x.client_id,'worker':x.worker.name,'detail':historical_catalog_name(x,'activity_id',names) or x.description or '', 'minutes':x.minutes})
        client_ids.add(x.client_id); total_minutes+=x.minutes
    if not area_id and not activity_id:
        es=select(EventParticipant).options(selectinload(EventParticipant.client),selectinload(EventParticipant.event)).join(Event,Event.id==EventParticipant.event_id).join(Client,Client.id==EventParticipant.client_id).where(EventParticipant.client_id.is_not(None),EventParticipant.attendance_status=='present')
        if start: es=es.where(Event.event_date>=start)
        if end: es=es.where(Event.event_date<=end)
        if ka: es=es.where(or_(Event.ka==ka,Event.subactivity==ka))
        if event_type: es=es.where(Event.event_type==event_type)
        if status: es=es.where(Client.status==status)
        if worker_id: es=es.where(Event.id.in_(select(EventWorker.event_id).where(EventWorker.worker_id==int(worker_id))))
        if indicator=='026000': es=es.where(EventParticipant.eligible_project==True,EventParticipant.participant_kind=='project')
        elif indicator: es=es.where(Event.event_id.in_(select(IndicatorRecord.source_id).where(IndicatorRecord.source_type=='event',IndicatorRecord.indicator_code==indicator,IndicatorRecord.eligible==True)))
        for p in db.scalars(es.order_by(Event.event_date.desc())).all():
            rows.append({'date':p.event.event_date,'kind':'skupinová účast','ka':p.event.subactivity or p.event.ka,'client':f'{p.client.code} · {p.client.first_name} {p.client.last_name}','client_id':p.client_id,'worker':p.event.title,'detail':p.event.event_type,'minutes':0}); client_ids.add(p.client_id)
    rows.sort(key=lambda r:r['date'], reverse=True)
    return rows,len(client_ids),total_minutes


def quality_issues(db: Session):
    issues=[]
    parents={x.item_id:x.parent_item_id for x in db.scalars(select(CatalogItem).where(CatalogItem.category_key=='Cinnost')).all()}
    for svc in db.scalars(select(IndividualService)).all():
        if svc.ka == 'legacy':
            issues.append({'kind':'výkon','id':svc.service_id,'text':'Importovaný historický výkon nemá ve zdrojovém XLSX uvedenou KA/podaktivitu; před vykazováním je nutná ruční kontrola.'})
        if svc.activity_id and svc.area_id and parents.get(svc.activity_id) and parents.get(svc.activity_id)!=svc.area_id:
            issues.append({'kind':'výkon','id':svc.service_id,'text':'Činnost nepatří do zvolené oblasti.'})
        if svc.minutes <= 0:
            issues.append({'kind':'výkon','id':svc.service_id,'text':'Počet minut není kladný.'})
    for ir in db.scalars(select(IndicatorRecord).where(IndicatorRecord.eligible==True)).all():
        if ir.source_type=='service':
            src=db.scalar(select(IndividualService).where(IndividualService.service_id==ir.source_id))
            if not src:
                issues.append({'kind':'indikátor','id':f'{ir.indicator_code}/{ir.source_id}','text':'Chybí zdrojový individuální výkon.'})
            elif not src.eligible_project or src.client_id!=ir.client_id:
                issues.append({'kind':'indikátor','id':f'{ir.indicator_code}/{ir.source_id}','text':'Indikátor není v souladu se způsobilostí/klientem zdrojového výkonu.'})
        elif ir.source_type=='event':
            ev=db.scalar(select(Event).where(Event.event_id==ir.source_id))
            if not ev:
                issues.append({'kind':'indikátor','id':f'{ir.indicator_code}/{ir.source_id}','text':'Chybí zdrojová skupinová akce.'})
            elif ir.client_id and not db.scalar(select(EventParticipant.id).where(EventParticipant.event_id==ev.id,EventParticipant.client_id==ir.client_id,EventParticipant.eligible_project==True,EventParticipant.attendance_status=='present')):
                issues.append({'kind':'indikátor','id':f'{ir.indicator_code}/{ir.source_id}','text':'Osoba indikátoru není způsobilým přítomným účastníkem zdrojové akce.'})
    return issues[:200]

@app.get("/activity-report",response_class=HTMLResponse)
def activity_report(request:Request,start:str='',end:str='',ka:str='',worker_id:str='',area_id:str='',activity_id:str='',event_type:str='',status:str='',indicator:str='',db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); filters={k:v for k,v in locals().copy().items() if k in {'start','end','ka','worker_id','area_id','activity_id','event_type','status','indicator'}}; rows,unique_clients,minutes=activity_report_data(db,filters); q=urlencode({k:v for k,v in filters.items() if v}); cats=catalogs(db,include_inactive=True)
    service_count=sum(1 for r in rows if r['kind']=='individuální'); participation_count=sum(1 for r in rows if r['kind']=='skupinová účast'); issues=quality_issues(db); return templates.TemplateResponse(request,"activity_report.html",ctx(request,db,rows=rows,unique_clients=unique_clients,minutes=minutes,hours=round(minutes/60,2),service_count=service_count,participation_count=participation_count,issues=issues,filters=filters,query=q,workers=db.scalars(select(Worker).order_by(Worker.name)).all(),areas=cats.get('Oblast',[]),activities=cats.get('Cinnost',[]),indicators=[(c,n) for c,(n,t) in INDICATORS.items()]))

@app.get("/exports/activity.csv")
def activity_export_csv(request:Request,start:str='',end:str='',ka:str='',worker_id:str='',area_id:str='',activity_id:str='',event_type:str='',status:str='',indicator:str='',db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); filters={k:v for k,v in locals().copy().items() if k in {'start','end','ka','worker_id','area_id','activity_id','event_type','status','indicator'}}; rows,_,_=activity_report_data(db,filters); buf=io.StringIO(); w=csv.writer(buf,delimiter=';'); w.writerow(['Vytvořeno',datetime.now().isoformat(timespec='minutes')]); w.writerow(['Filtry',json.dumps(filters,ensure_ascii=False)]); w.writerow(['Datum','Typ','KA','Klient','Pracovník/akce','Detail','Minuty']);
    for r in rows: w.writerow([r['date'],r['kind'],r['ka'],csv_safe(r['client']),csv_safe(r['worker']),csv_safe(r['detail']),r['minutes']])
    data='\ufeff'+buf.getvalue(); return StreamingResponse(iter([data.encode('utf-8')]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="vesna-kontrolni-vypis.csv"'})

@app.get("/exports/activity.xlsx")
def activity_export_xlsx(request:Request,start:str='',end:str='',ka:str='',worker_id:str='',area_id:str='',activity_id:str='',event_type:str='',status:str='',indicator:str='',db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN,ROLE_WORKER]); from openpyxl import Workbook
    filters={k:v for k,v in locals().copy().items() if k in {'start','end','ka','worker_id','area_id','activity_id','event_type','status','indicator'}}; rows,_,_=activity_report_data(db,filters); wb=Workbook(); ws=wb.active; ws.title='Kontrolní výpis'; ws.append(['Datum','Typ','KA','Klient','Pracovník/akce','Detail','Minuty']);
    for r in rows: ws.append([r['date'],r['kind'],r['ka'],csv_safe(r['client']),csv_safe(r['worker']),csv_safe(r['detail']),r['minutes']])
    meta=wb.create_sheet('Filtry'); meta.append(['Vytvořeno',datetime.now().isoformat(timespec='minutes')]);
    for k,v in filters.items(): meta.append([k,v])
    out=io.BytesIO(); wb.save(out); out.seek(0); return StreamingResponse(out,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="vesna-kontrolni-vypis.xlsx"'})

@app.get("/admin/metrics",response_class=HTMLResponse)
def admin_metrics(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); outputs=db.scalars(select(ProjectOutput).order_by(ProjectOutput.output_date.desc())).all(); feedback=db.scalars(select(AnonymousFeedbackAggregate).order_by(AnonymousFeedbackAggregate.period_end.desc())).all(); den=sum(x.denominator for x in feedback); pos=sum(x.positive_count for x in feedback); pct=round(100*pos/den,1) if den else 0
    return templates.TemplateResponse(request,"admin_metrics.html",ctx(request,db,today=date.today(),outputs=outputs,feedback=feedback,feedback_pct=pct))

@app.post("/admin/metrics/output")
async def admin_metrics_output(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=ProjectOutput(output_date=parse_date(f['output_date']),title=f['title'].strip(),output_type=f.get('output_type') or 'document',reference=f.get('reference') or None,created_by_id=user.id); db.add(x); db.flush(); audit_log(db,user.id,'create','project_output',x.id,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/metrics',303)

@app.post("/admin/metrics/web")
async def admin_metrics_web(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=WebAnalyticsAggregate(period_start=parse_date(f['period_start']),period_end=parse_date(f['period_end']),source=f['source'].strip(),visits=int(f['visits']),created_by_id=user.id); db.add(x); db.flush(); audit_log(db,user.id,'create','web_analytics',x.id,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/metrics',303)

@app.post("/admin/metrics/feedback")
async def admin_metrics_feedback(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); den=int(f['denominator']); pos=int(f['positive_count']);
    if pos>den: raise HTTPException(400,'Počet kladných odpovědí nesmí být vyšší než jmenovatel.')
    x=AnonymousFeedbackAggregate(period_start=parse_date(f['period_start']),period_end=parse_date(f['period_end']),denominator=den,positive_count=pos,methodology=f['methodology'].strip(),created_by_id=user.id); db.add(x); db.flush(); audit_log(db,user.id,'create','anonymous_feedback',x.id,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/metrics',303)

@app.get("/admin/categories",response_class=HTMLResponse)
def admin_categories(request:Request,db:Session=Depends(get_db)):
    require_user(request,db,[ROLE_ADMIN]); return templates.TemplateResponse(request,"admin_categories.html",ctx(request,db,categories=db.scalars(select(CatalogCategory).order_by(CatalogCategory.sort_order)).all()))

@app.post("/admin/categories/new")
async def admin_categories_new(request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=CatalogCategory(key=f['key'].strip(),name=f['name'].strip(),sort_order=int(f.get('sort_order') or 0),active=True); db.add(x); db.flush(); audit_log(db,user.id,'create','catalog_category',x.key,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/categories',303)

@app.post("/admin/categories/{category_id}/edit")
async def admin_categories_edit(category_id:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); x=db.get(CatalogCategory,category_id)
    if not x: raise HTTPException(404)
    before=snapshot(x); expected=int(f.get('version',0)); res=db.execute(update(CatalogCategory).where(CatalogCategory.id==category_id,CatalogCategory.version==expected).values(name=f['name'].strip(),sort_order=int(f.get('sort_order') or 0),active=as_bool(f.get('active')),version=expected+1));
    if res.rowcount!=1: db.rollback(); raise HTTPException(409,'Kategorie byla mezitím změněna.')
    db.flush(); x=db.get(CatalogCategory,category_id); audit_log(db,user.id,'update','catalog_category',x.key,before=before,after=snapshot(x),remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/categories',303)

def catalog_item_impact_count(db:Session,item_id:str)->int:
    cols=[IndividualService.area_id,IndividualService.activity_id,IndividualService.form_id,IndividualService.place_id,IndividualService.method_id,IndividualService.language_id,IndividualService.outcome_id,IndividualService.next_step_id,IndividualService.progress_id,IndividualService.referral_id]
    return sum(db.scalar(select(func.count()).select_from(IndividualService).where(col==item_id)) or 0 for col in cols) + (db.scalar(select(func.count()).select_from(CatalogItem).where(CatalogItem.parent_item_id==item_id)) or 0)

@app.post("/admin/catalog/{item_pk}/merge")
async def admin_catalog_merge(item_pk:int,request:Request,db:Session=Depends(get_db)):
    user=require_user(request,db,[ROLE_ADMIN]); f=await request.form(); check_csrf(request,f.get('csrf')); src=db.get(CatalogItem,item_pk); target=db.get(CatalogItem,int(f['target_id']))
    if not src or not target: raise HTTPException(404)
    if src.id==target.id or src.category_key!=target.category_key: raise HTTPException(400,'Položky musí být různé a ze stejné kategorie.')
    before=snapshot(src); moved=0
    fields=['area_id','activity_id','form_id','place_id','method_id','language_id','outcome_id','next_step_id','progress_id','referral_id']
    for field in fields:
        col=getattr(IndividualService,field)
        res=db.execute(update(IndividualService).where(col==src.item_id).values({field:target.item_id}))
        moved+=res.rowcount or 0
    child_res=db.execute(update(CatalogItem).where(CatalogItem.parent_item_id==src.item_id).values(parent_item_id=target.item_id))
    moved+=child_res.rowcount or 0
    src.active=False; src.visible=False; src.version+=1
    audit_log(db,user.id,'merge','catalog_item',src.item_id,before=before,after={'target':target.item_id,'moved_references':moved,'source_active':False},remote_ip=ip(request)); db.commit(); return RedirectResponse('/admin/catalog',303)
