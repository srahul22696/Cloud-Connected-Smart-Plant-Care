# Cloud-Connected Smart Plant Care & Watering System

A full-stack IoT cloud-computing project that monitors plant conditions, stores time-stamped readings, raises alerts, and queues safe watering actions. It is fully usable without physical hardware: a Python simulator sends plausible sensor readings and responds to virtual pump commands.

## What it demonstrates

- Authenticated users and owner-scoped plant/device access
- Per-device API credentials stored as hashes, separate from user login
- REST ingestion with range, timestamp, timezone, and event-ID validation
- SQL database design for users, devices, readings, watering events, and alerts
- Idempotent ingestion, alert de-duplication, offline detection, and retry handling
- Threshold automation with plant profiles, low-reservoir protection, a watering cooldown, and bounded pump pulses
- Responsive React dashboard with trends, activity, device state, threshold settings, manual control, and alerts
- Local SQLite development and PostgreSQL cloud deployment

## Architecture

```text
Python virtual sensor (or ESP32)
            │ HTTPS + per-device key
            ▼
FastAPI REST service ───── PostgreSQL / SQLite
       │                          │
       ├── validation             ├── readings + history
       ├── watering rules         ├── alerts + events
       └── queued device action ◄─┘
            │
            ▼
React dashboard (authenticated user)
```

For Vercel, `api/index.py` exposes the FastAPI application and `vercel.json` builds/serves the Vite frontend. Configure a hosted PostgreSQL URL (for example, a Supabase PostgreSQL connection string) because Vercel's local filesystem is ephemeral. The dashboard and API are served from one origin.

## Requirements

- Python 3.9+
- Node.js 20+
- A browser
- No ESP32, sensor, pump, or cloud account needed for local simulation

## Run locally

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Set `APP_SECRET` in `.env` to a randomly generated value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Then run the backend:

```bash
uvicorn backend.app:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, create an account, and add a plant. The device key is shown once and copied to the clipboard. In a third terminal, with the Python environment active, start the virtual sensor using that key:

```bash
DEVICE_ID=PLANT-001 DEVICE_KEY='paste-the-one-time-key' API_URL=http://127.0.0.1:8000 INTERVAL_SECONDS=10 python -m sensor_simulator.simulator
```

Use the exact device ID entered in the dashboard. Soil moisture drifts down gradually; a reading below the chosen target queues a three-second virtual pump pulse, subject to a five-minute cooldown. The simulator polls the secure device action endpoint and increases its soil value after receiving the pulse.

For offline-only simulator output (no API calls), use `OFFLINE_MODE=true` with `DEVICE_ID` and run the same command. To reset the local demo database, stop the backend and remove `plantcare.db`.

## API overview

All user endpoints require `Authorization: Bearer <access_token>`. Device endpoints require `X-Device-Key`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | Create account / receive signed token |
| GET | `/api/auth/me` | Current account |
| GET/POST | `/api/devices` | List owned devices / create device (returns key once) |
| GET | `/api/devices/{id}` | Device state and latest reading |
| POST | `/api/sensors/data` | Authenticated, validated, idempotent reading ingestion |
| GET | `/api/devices/{id}/latest` | Latest reading |
| GET | `/api/devices/{id}/history?limit=100` | Bounded time-series history |
| PUT | `/api/devices/{id}/threshold` | Change moisture target (5–90%) |
| PUT | `/api/devices/{id}/auto-water` | Enable or disable automatic watering |
| POST | `/api/devices/{id}/water` | Queue a manual bounded pulse |
| GET | `/api/devices/{id}/watering-history` | Recent watering events |
| GET | `/api/devices/{id}/actions` | Device-authenticated, one-time action polling |
| POST | `/api/devices/{id}/heartbeat` | Device-authenticated heartbeat |
| GET | `/api/alerts` | Alerts for the signed-in user's devices |
| PUT | `/api/alerts/{id}/acknowledge` | Acknowledge an owned alert |
| GET | `/api/health` | Service/database health check |

## Data and safety rules

- Soil, humidity, light, and tank level are 0–100%; temperature is −20 to 70 °C.
- Sensor timestamps must include a timezone, be no more than five minutes in the future, and no older than seven days.
- Event IDs are unique per device. Replayed readings are acknowledged without duplicate storage or watering.
- Device secrets are high-entropy random values; only SHA-256 hashes are stored. User passwords use PBKDF2-SHA256. Access tokens are signed, expiring bearer tokens.
- A low reservoir (5% or less) blocks watering. Every pulse is bounded by `MAX_PUMP_SECONDS` (default 10 sec), and the cooldown prevents rapid repeat activations.
- Production must set a strong `APP_SECRET`, use PostgreSQL, HTTPS, a restricted CORS origin list, backups, and provider-managed database encryption. Never commit `.env` or device keys.
- Registration can be disabled with `ALLOW_REGISTRATION=false` after account provisioning.

Plant profile defaults: succulent 20%, indoor 30%, herb 35%, tomato 40%. They are starting points, not horticultural guarantees; adjust for the plant and sensor calibration.

## Tests and build

```bash
pytest -q
cd frontend && npm run build
```

The automated API tests cover authentication, ownership isolation, unusual/out-of-range values, timestamp rules, duplicate delivery, watering thresholds/cooldown, action one-time delivery, low tank blocking, threshold updates, manual watering, and alert acknowledgement.

## Deploy to Vercel

1. Push this repository to GitHub, then import it into Vercel.
2. Set the project root to the repository root. The included config builds `frontend` and routes `/api/*` to the FastAPI function.
3. Create a managed PostgreSQL database (Supabase is one option) and set `DATABASE_URL` to its SQLAlchemy-compatible PostgreSQL connection URI (`postgresql+psycopg://...`). Confirm the database accepts Vercel's runtime connections; use its pooled URL when offered.
4. Add `APP_SECRET` (at least 32 random characters), `APP_ENV=production`, `CORS_ORIGINS` to the deployed origin, `ALLOW_REGISTRATION=true` for first account creation, and the watering settings as Vercel environment variables.
5. Deploy. Check `/api/health`, create the owner account, and add the device from the dashboard. Set the simulator's `API_URL` to the deployed origin and use the one-time device key. Disable public registration after the account is created if that fits your use.

Vercel deployment needs your own GitHub, Vercel, and managed database accounts and environment values. No credentials or cloud resources are included in this repository. Do not use local SQLite for a persistent Vercel deployment.

## Optional ESP32 hardware

Replace the Python simulator with an ESP32 using a capacitive soil sensor on an ADC1 pin, a DHT22/SHT31, and optional light/tank sensors. Send the same JSON fields to `POST /api/sensors/data` over HTTPS with `X-Device-Key`; poll `/api/devices/{id}/actions` with the same key. Use a low-voltage DC pump, a properly rated MOSFET/relay and flyback protection, fuse the pump supply, and keep mains voltage out of student prototypes. Add a local firmware cutoff as an independent safety guard. Calibrate the capacitive sensor's dry/wet endpoints. The API and dashboard data contract stays the same.

## Cloud concepts and growth path

The deployed app is a small SaaS/PaaS-style service. REST is the device/API transport; MQTT can replace polling at higher device counts. FastAPI is the API layer, PostgreSQL is the managed cloud database, and Vercel functions provide serverless request execution. Authentication, authorization, secrets, structured logs, health checks, and CI build steps are represented directly. At larger scale, put devices behind an IoT broker/API gateway, enqueue readings for workers, partition/aggregate time-series data, cache dashboard summaries, define retention, and use managed alert/monitoring services. The data contract supports Azure IoT Hub/Functions/Cosmos DB or AWS IoT Core/API Gateway/Lambda/Timestream/DynamoDB/SNS equivalents.

## Limitations and next steps

This portfolio build simulates pump execution and does not send real email/SMS/push notifications. Offline status is derived from the last received reading when the dashboard refreshes. For production hardware, add firmware-side interlocks, rotating device credentials, rate limiting/WAF, database migrations, audit logs, background scheduled offline checks, and end-to-end tests against a staging database.

## Project layout

```text
api/index.py                 Vercel FastAPI entry point
backend/                     Auth, database models, validation, REST routes, automation
frontend/src/                React dashboard and styles
sensor_simulator/            Gradual synthetic readings, retry, virtual pump response
tests/                       Automated API/security/automation checks
docs/                        Architecture and project report
screenshots/                 Dashboard images for project evidence
```
