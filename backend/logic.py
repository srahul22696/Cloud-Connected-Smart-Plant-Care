from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import Device, Reading, WateringEvent, Alert

PROFILE_THRESHOLDS = {"succulent":20.0,"tomato":40.0,"herb":35.0,"indoor":30.0}

def latest_reading(db: Session, device_id: str):
    return db.scalar(select(Reading).where(Reading.device_id == device_id).order_by(Reading.timestamp.desc(), Reading.id.desc()).limit(1))

def add_alert_once(db: Session, device_id: str, alert_type: str, level: str, message: str):
    found = db.scalar(select(Alert).where(Alert.device_id == device_id, Alert.alert_type == alert_type, Alert.acknowledged.is_(False)).limit(1))
    if not found: db.add(Alert(device_id=device_id, alert_type=alert_type, level=level, message=message))

def decide_watering(db: Session, device: Device, reading: Reading, trigger_type="automatic", duration_seconds=None):
    if trigger_type == "automatic":
        if not device.auto_water or reading.soil_moisture >= device.threshold: return None
    # Lock the per-device row in PostgreSQL so simultaneous dry readings/manual requests
    # cannot both pass cooldown and queue two pump pulses.
    locked_device=db.scalar(select(Device).where(Device.id==device.id).with_for_update())
    if locked_device is not None: device=locked_device
    now = datetime.now(timezone.utc)
    recent = db.scalar(select(WateringEvent).where(WateringEvent.device_id == device.id, WateringEvent.created_at >= now - timedelta(seconds=settings.watering_cooldown_seconds)).order_by(WateringEvent.created_at.desc()).limit(1))
    if recent: return None
    if reading.water_tank_level is not None and reading.water_tank_level <= 5:
        add_alert_once(db, device.id, "low_tank", "critical", f"Water tank is nearly empty for {device.plant_name}; watering was blocked.")
        return None
    seconds = min(duration_seconds or settings.default_pump_seconds, settings.max_pump_seconds)
    event = WateringEvent(device_id=device.id, trigger_type=trigger_type, moisture_before=reading.soil_moisture, duration_seconds=seconds, status="queued", created_at=now)
    db.add(event)
    return event

def device_status(device: Device):
    if not device.last_seen: return "offline"
    seen = device.last_seen
    if seen.tzinfo is None: seen = seen.replace(tzinfo=timezone.utc)
    return "online" if (datetime.now(timezone.utc)-seen).total_seconds() <= settings.device_offline_seconds else "offline"
