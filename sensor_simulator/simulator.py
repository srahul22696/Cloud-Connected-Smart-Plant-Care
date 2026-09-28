"""Synthetic IoT device with gradual environmental changes, retry, and offline mode."""
import json, logging, math, os, random, time, uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from sensor_simulator.config import config

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("plant-simulator")

def clamp(value, low, high): return max(low, min(high, value))

class SensorSimulator:
    def __init__(self, seed=None):
        rng=random.Random(seed)
        self.rng=rng; self.soil=rng.uniform(48,62); self.temp=rng.uniform(21,27); self.humidity=rng.uniform(45,68); self.minute=0
    def reading(self, device_id):
        self.minute += 1
        self.soil=clamp(self.soil-self.rng.uniform(0.15,0.9), 5, 95)
        day_phase=(self.minute % 1440) / 1440 * math.tau
        day_light=max(0, math.sin(day_phase-math.pi/2))
        self.temp=clamp(self.temp+self.rng.uniform(-0.45,0.45), 15, 40)
        self.humidity=clamp(self.humidity+self.rng.uniform(-1.3,1.3),30,90)
        return {"device_id":device_id,"event_id":str(uuid.uuid4()),"soil_moisture":round(self.soil,1),"temperature":round(self.temp,1),"humidity":round(self.humidity,1),"light_level":round(clamp(day_light*85+self.rng.uniform(0,12),0,100),1),"water_tank_level":100,"timestamp":datetime.now(timezone.utc).isoformat()}
    def apply_water(self, seconds): self.soil=clamp(self.soil+seconds*2.4,0,100)

def request(method, url, data=None, key=None, timeout=8):
    body=json.dumps(data).encode() if data is not None else None
    headers={"Content-Type":"application/json"}
    if key: headers["X-Device-Key"]=key
    req=Request(url,data=body,headers=headers,method=method)
    with urlopen(req,timeout=timeout) as response:
        return json.loads(response.read() or b"{}")

def send_with_retry(payload, attempts=4):
    for attempt in range(attempts):
        try:
            return request("POST", config.api_url.rstrip("/")+"/api/sensors/data", payload, config.device_key)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            status = getattr(exc,"code",None)
            if status and 400 <= status < 500 and status != 429:
                log.error("Non-retryable API response %s: %s", status, exc); return None
            delay=min(2**attempt,10)+random.random()
            log.warning("API unavailable (%s); retry %d/%d in %.1fs", exc, attempt+1, attempts, delay)
            if attempt < attempts-1: time.sleep(delay)
    return None

def main():
    if not config.device_id or not config.device_key:
        raise SystemExit("Set DEVICE_ID and DEVICE_KEY from the dashboard before starting the simulator.")
    sim=SensorSimulator()
    log.info("Simulator for %s started (%s)",config.device_id,"offline mode" if config.offline else config.api_url)
    while True:
        reading=sim.reading(config.device_id)
        if config.offline:
            log.info("OFFLINE sample %s", reading)
        else:
            try:
                result=send_with_retry(reading)
                log.info("Uploaded sample soil=%.1f%% response=%s",reading["soil_moisture"],result)
                actions=request("GET",config.api_url.rstrip("/")+f"/api/devices/{config.device_id}/actions",key=config.device_key)
                for action in actions.get("actions",[]):
                    sim.apply_water(action["duration_seconds"])
                    log.info("Virtual pump %s for %ss; simulated moisture -> %.1f%%",action["id"],action["duration_seconds"],sim.soil)
            except (HTTPError, URLError, TimeoutError, OSError) as exc: log.warning("Action poll failed: %s",exc)
        time.sleep(max(1,config.interval_seconds))
if __name__ == "__main__": main()
