from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Depends, HTTPException, Header, status, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.config import settings
from backend.database import Base, engine, get_db
from backend.models import User, Device, Reading, WateringEvent, Alert
from backend.schemas import RegisterIn, LoginIn, TokenOut, DeviceCreate, DeviceOut, ThresholdIn, AutoWaterIn, ReadingIn, WaterIn
from backend.security import hash_password, verify_password, issue_token, read_token, new_device_key, hash_device_key
from backend.logic import PROFILE_THRESHOLDS, latest_reading, decide_watering, add_alert_once, device_status

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("plantcare")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
app = FastAPI(title="PlantCare IoT API", version="1.0.0", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def safe_validation_error(request: Request, exc: RequestValidationError):
    # Do not echo raw submitted values; NaN/Infinity and secrets must remain serializable/private.
    errors = [{"loc": list(error.get("loc", ())), "msg": error.get("msg", "Invalid value"), "type": error.get("type", "value_error")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","PUT","DELETE"], allow_headers=["Authorization","Content-Type","X-Device-Key"])
bearer = HTTPBearer(auto_error=False)

def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer), db: Session = Depends(get_db)):
    if not creds or creds.scheme.lower() != "bearer": raise HTTPException(401,"Bearer token required",headers={"WWW-Authenticate":"Bearer"})
    uid = read_token(creds.credentials)
    user = db.get(User, uid)
    if not user: raise HTTPException(401,"User no longer exists")
    return user

def owned_device(db: Session, user: User, device_id: str):
    device = db.get(Device, device_id)
    if not device or device.owner_id != user.id: raise HTTPException(404,"Device not found")
    return device

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try: db.execute(select(1))
    except Exception: raise HTTPException(503,"Database unavailable")
    return {"status":"ok","service":"plantcare-api"}

@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if not settings.allow_registration: raise HTTPException(403,"Registration is disabled")
    if db.scalar(select(User).where(User.email == payload.email)): raise HTTPException(409,"Account already exists")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,"Account already exists")
    db.refresh(user)
    return {"access_token":issue_token(user.id)}

@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":issue_token(user.id)}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id":user.id,"email":user.email}

@app.get("/api/devices")
def devices(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Device).where(Device.owner_id == user.id).order_by(Device.created_at)).all()
    result=[]
    for d in rows:
        status_now=device_status(d)
        if status_now == "offline": add_alert_once(db,d.id,"device_offline","warning",f"No recent sensor signal from {d.plant_name}.")
        else:
            for a in db.scalars(select(Alert).where(Alert.device_id==d.id,Alert.alert_type=="device_offline",Alert.acknowledged.is_(False))).all(): a.acknowledged=True
        result.append({**DeviceOut.model_validate(d).model_dump(mode="json"),"status":status_now,"latest":reading_json(latest_reading(db,d.id))})
    db.commit()
    return result

def reading_json(r):
    if not r: return None
    return {"soil_moisture":r.soil_moisture,"temperature":r.temperature,"humidity":r.humidity,"light_level":r.light_level,"water_tank_level":r.water_tank_level,"timestamp":r.timestamp.isoformat()}

@app.post("/api/devices", status_code=201)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if db.get(Device,payload.id): raise HTTPException(409,"Device ID already exists")
    key = new_device_key()
    device = Device(id=payload.id, owner_id=user.id, plant_name=payload.plant_name, plant_type=payload.plant_type, location=payload.location, threshold=payload.threshold if payload.threshold is not None else PROFILE_THRESHOLDS[payload.plant_type], auto_water=payload.auto_water, device_key_hash=hash_device_key(key))
    db.add(device); db.commit()
    return {"device":DeviceOut.model_validate(device).model_dump(mode="json"),"device_key":key,"warning":"Copy this key now. It cannot be retrieved later."}

@app.get("/api/devices/{device_id}")
def get_device(device_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    d=owned_device(db,user,device_id)
    return {**DeviceOut.model_validate(d).model_dump(mode="json"),"status":device_status(d),"latest":reading_json(latest_reading(db,d.id))}

@app.put("/api/devices/{device_id}/threshold")
def set_threshold(device_id: str, payload: ThresholdIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    d=owned_device(db,user,device_id); d.threshold=payload.threshold; db.commit(); return {"device_id":d.id,"threshold":d.threshold}

@app.put("/api/devices/{device_id}/auto-water")
def set_auto(device_id: str, payload: AutoWaterIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    d=owned_device(db,user,device_id); d.auto_water=payload.enabled; db.commit(); return {"device_id":d.id,"auto_water":d.auto_water}

@app.post("/api/sensors/data", status_code=202)
def ingest(payload: ReadingIn, x_device_key: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    if not x_device_key or len(x_device_key)>128: raise HTTPException(401,"X-Device-Key required")
    d=db.get(Device,payload.device_id)
    if not d or hash_device_key(x_device_key) != d.device_key_hash: raise HTTPException(401,"Invalid device credentials")
    existing=db.scalar(select(Reading).where(Reading.device_id==d.id, Reading.event_id==payload.event_id))
    if existing: return {"accepted":True,"duplicate":True,"watering":"unchanged"}
    row=Reading(device_id=d.id,event_id=payload.event_id,soil_moisture=payload.soil_moisture,temperature=payload.temperature,humidity=payload.humidity,light_level=payload.light_level,water_tank_level=payload.water_tank_level,timestamp=payload.timestamp)
    db.add(row); d.last_seen=datetime.now(timezone.utc)
    if row.soil_moisture < d.threshold: add_alert_once(db,d.id,"low_moisture","warning",f"{d.plant_name} moisture is below its {d.threshold:g}% threshold.")
    else:
        for a in db.scalars(select(Alert).where(Alert.device_id==d.id,Alert.alert_type=="low_moisture",Alert.acknowledged.is_(False))).all(): a.acknowledged=True
    if row.temperature > 38: add_alert_once(db,d.id,"high_temperature","warning",f"{d.plant_name} temperature is unusually high ({row.temperature:g} °C).")
    else:
        for a in db.scalars(select(Alert).where(Alert.device_id==d.id,Alert.alert_type=="high_temperature",Alert.acknowledged.is_(False))).all(): a.acknowledged=True
    action=decide_watering(db,d,row)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        return {"accepted":True,"duplicate":True,"watering":"unchanged"}
    log.info("reading_accepted device=%s event=%s",d.id,payload.event_id)
    return {"accepted":True,"duplicate":False,"watering":"queued" if action else "not_required"}

@app.get("/api/devices/{device_id}/latest")
def get_latest(device_id: str, db: Session=Depends(get_db), user: User=Depends(current_user)):
    owned_device(db,user,device_id); return reading_json(latest_reading(db,device_id))

@app.get("/api/devices/{device_id}/history")
def history(device_id: str, limit: int=Query(default=100,ge=1,le=500), db: Session=Depends(get_db), user: User=Depends(current_user)):
    owned_device(db,user,device_id)
    rows=db.scalars(select(Reading).where(Reading.device_id==device_id).order_by(desc(Reading.timestamp),desc(Reading.id)).limit(limit)).all()
    return [ {"id":r.id,"soil_moisture":r.soil_moisture,"temperature":r.temperature,"humidity":r.humidity,"light_level":r.light_level,"water_tank_level":r.water_tank_level,"timestamp":r.timestamp.isoformat()} for r in reversed(rows) ]

@app.post("/api/devices/{device_id}/water", status_code=202)
def water_now(device_id: str, payload: WaterIn, db: Session=Depends(get_db), user: User=Depends(current_user)):
    d=owned_device(db,user,device_id); latest=latest_reading(db,device_id)
    if not latest: raise HTTPException(409,"A sensor reading is required before watering")
    moisture=latest.soil_moisture
    fake=latest or Reading(device_id=device_id,event_id="manual",soil_moisture=moisture,temperature=20,humidity=50,light_level=50,timestamp=datetime.now(timezone.utc))
    event=decide_watering(db,d,fake,trigger_type="manual",duration_seconds=payload.duration_seconds)
    if not event: raise HTTPException(429,"Watering cooldown is active or the tank is too low")
    db.commit(); db.refresh(event); return {"event_id":event.id,"status":event.status,"duration_seconds":event.duration_seconds}

@app.get("/api/devices/{device_id}/watering-history")
def watering_history(device_id: str, db: Session=Depends(get_db), user: User=Depends(current_user)):
    owned_device(db,user,device_id)
    rows=db.scalars(select(WateringEvent).where(WateringEvent.device_id==device_id).order_by(desc(WateringEvent.created_at)).limit(100)).all()
    return [{"id":x.id,"trigger_type":x.trigger_type,"moisture_before":x.moisture_before,"duration_seconds":x.duration_seconds,"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]

@app.get("/api/alerts")
def alerts(db: Session=Depends(get_db), user: User=Depends(current_user)):
    rows=db.scalars(select(Alert).join(Device).where(Device.owner_id==user.id).order_by(desc(Alert.created_at)).limit(100)).all()
    return [{"id":x.id,"device_id":x.device_id,"alert_type":x.alert_type,"level":x.level,"message":x.message,"acknowledged":x.acknowledged,"created_at":x.created_at.isoformat()} for x in rows]

@app.put("/api/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: int, db: Session=Depends(get_db), user: User=Depends(current_user)):
    a=db.get(Alert,alert_id)
    if not a or not db.scalar(select(Device.id).where(Device.id==a.device_id,Device.owner_id==user.id)): raise HTTPException(404,"Alert not found")
    a.acknowledged=True; db.commit(); return {"id":a.id,"acknowledged":True}

@app.get("/api/devices/{device_id}/actions")
def poll_actions(device_id: str, x_device_key: Optional[str]=Header(default=None), db: Session=Depends(get_db)):
    d=db.get(Device,device_id)
    if not d or not x_device_key or hash_device_key(x_device_key)!=d.device_key_hash: raise HTTPException(401,"Invalid device credentials")
    pending=db.scalars(select(WateringEvent).where(WateringEvent.device_id==device_id,WateringEvent.status=="queued").order_by(WateringEvent.created_at).limit(10)).all()
    actions=[]
    for ev in pending:
        ev.status="delivered"
        actions.append({"id":ev.id,"duration_seconds":min(ev.duration_seconds,settings.max_pump_seconds),"trigger_type":ev.trigger_type})
    db.commit(); return {"actions":actions}

@app.post("/api/devices/{device_id}/heartbeat")
def heartbeat(device_id: str, x_device_key: Optional[str]=Header(default=None), db: Session=Depends(get_db)):
    d=db.get(Device,device_id)
    if not d or not x_device_key or hash_device_key(x_device_key)!=d.device_key_hash: raise HTTPException(401,"Invalid device credentials")
    d.last_seen=datetime.now(timezone.utc); db.commit(); return {"ok":True,"server_time":d.last_seen.isoformat()}
