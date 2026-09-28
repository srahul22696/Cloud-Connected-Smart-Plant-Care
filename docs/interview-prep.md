# Interview and viva preparation

## 60-second project explanation

“I built a cloud-connected plant care system that accepts soil moisture, temperature, humidity, and light readings from a Python virtual IoT device. The device sends validated JSON over a device-authenticated REST API. The backend stores time-series readings in SQL, checks plant-specific watering thresholds, and queues a short virtual pump pulse only when the tank and cooldown safety checks pass. A React dashboard lets an authenticated owner monitor history, change thresholds, pause automation, request a manual pulse, and acknowledge alerts. I used a simulator so the whole workflow works without hardware, and the same API contract can later be used by an ESP32.”

## Questions to practice

1. **Why cloud?** Central storage and compute enable remote access, shared device management, history, alerts, and horizontal scaling beyond a single microcontroller.
2. **Why simulate hardware?** It makes the system repeatable, low-cost, and testable without wiring or sensor calibration while preserving the IoT message contract.
3. **Why REST and what about MQTT?** REST is easy to inspect and integrate for an MVP. MQTT is lighter and broker-based, which suits many constrained devices and supports pub/sub fan-out at larger scale.
4. **How is a device authenticated?** Each device has an independent high-entropy key; the server stores only a digest and checks it on ingestion, heartbeat, and action polling. Production deployments must use HTTPS and key rotation.
5. **How do you stop duplicate watering?** Unique device/event IDs make repeated readings idempotent; a per-device cooldown, low tank check, and bounded pulse protect the actuator.
6. **How do you prevent one user seeing another's plants?** Dashboard requests require a signed user token and every device/alert operation checks the authenticated owner in the database.
7. **How does the system scale?** Move ingestion behind an IoT broker/API gateway, buffer bursts with a queue, process statelessly, use time-series partitioning/rollups and retention, then cache dashboard summaries.
8. **What happens during network loss?** The simulator logs samples offline; request retries use bounded exponential backoff. A real device should buffer readings locally and enforce watering safety locally rather than depending on an internet round trip.
9. **Why PostgreSQL on Vercel?** Serverless function disks are ephemeral. A managed database provides durable shared state across invocations; local SQLite is convenient for development only.
10. **What would you improve?** Managed OIDC, database migrations, rate limits, scheduled offline alerts, richer monitoring, audit trails, hardware acknowledgment, sensor calibration, and staged deployment tests.

## Demo outline

1. Register and add a tomato profile; note the generated one-time device key.
2. Start the simulator and show changing telemetry on the dashboard.
3. Show chart history, online indicator, and current moisture target.
4. Toggle auto watering or lower the threshold; show the event in watering history.
5. Explain low-reservoir blocking, per-device authentication, duplicate protection, and cooldown.

Do not claim real pump switching, real notification delivery, or machine-learning prediction: those are not implemented in this MVP.
