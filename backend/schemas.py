from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class RegisterIn(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        v = v.strip().lower()
        import re
        pattern=r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
        if not re.fullmatch(pattern, v): raise ValueError("Enter a valid email address")
        local = v.split("@", 1)[0]
        if local.startswith(".") or local.endswith(".") or ".." in local: raise ValueError("Enter a valid email address")
        return v

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DeviceCreate(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,47}$")
    plant_name: str = Field(min_length=1, max_length=80)
    plant_type: Literal["succulent", "tomato", "herb", "indoor"] = "indoor"
    location: str = Field(default="", max_length=100)
    threshold: Optional[float] = Field(default=None, ge=5, le=90)
    auto_water: bool = True
    @field_validator("plant_name", "location")
    @classmethod
    def clean_text(cls, v):
        v = v.strip()
        if any(ord(c) < 32 for c in v): raise ValueError("Control characters are not allowed")
        return v

class ThresholdIn(BaseModel):
    threshold: float = Field(ge=5, le=90)

class AutoWaterIn(BaseModel):
    enabled: bool

class ReadingIn(BaseModel):
    device_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,47}$")
    event_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    soil_moisture: float = Field(ge=0, le=100, allow_inf_nan=False)
    temperature: float = Field(ge=-20, le=70, allow_inf_nan=False)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False)
    light_level: float = Field(default=50, ge=0, le=100, allow_inf_nan=False)
    water_tank_level: Optional[float] = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    timestamp: datetime
    @field_validator("timestamp")
    @classmethod
    def valid_timestamp(cls, v):
        if v.tzinfo is None or v.utcoffset() is None: raise ValueError("timestamp must include a timezone")
        now = datetime.now(timezone.utc)
        if (v.astimezone(timezone.utc) - now).total_seconds() > 300: raise ValueError("timestamp is too far in the future")
        if (now - v.astimezone(timezone.utc)).total_seconds() > 7*86400: raise ValueError("timestamp is older than 7 days")
        return v.astimezone(timezone.utc)

class WaterIn(BaseModel):
    duration_seconds: int = Field(default=3, ge=1, le=10)

class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    plant_name: str
    plant_type: str
    location: str
    threshold: float
    auto_water: bool
    last_seen: Optional[datetime]

class AlertOut(BaseModel):
    id: int
    device_id: str
    alert_type: str
    level: str
    message: str
    acknowledged: bool
    created_at: datetime
