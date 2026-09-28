import os
from dataclasses import dataclass

@dataclass
class Config:
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:8000")
    device_id: str = os.getenv("DEVICE_ID", "")
    device_key: str = os.getenv("DEVICE_KEY", "")
    interval_seconds: float = float(os.getenv("INTERVAL_SECONDS", "10"))
    offline: bool = os.getenv("OFFLINE_MODE", "false").lower() == "true"

config = Config()
