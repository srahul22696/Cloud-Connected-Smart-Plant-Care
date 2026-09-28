# Project Report: Cloud-Connected Smart Plant Care & Watering System

**Project domain:** Cloud computing, IoT, automation, and environmental monitoring  
**Implementation:** Python 3, FastAPI, SQLAlchemy, SQLite/PostgreSQL, React, Vite  
**Operation mode:** Synthetic sensor data, no physical hardware required

## Abstract

This project provides a remote plant-monitoring platform. A Python virtual device produces gradually changing soil-moisture, air-temperature, humidity, and light readings, then sends them to an authenticated REST API. The API validates and stores data, applies plant-specific moisture limits, creates alerts, detects offline devices, and queues a bounded virtual watering action. A React dashboard shows current conditions, historical trends, plant health, controls, and recent events. SQLite supports local learning and PostgreSQL supports persistent cloud deployment.

## Problem statement and objectives

Manual care is inconsistent, while standalone sensors do not provide remote history or coordinated automation. The system demonstrates how cloud services can collect device telemetry, preserve it for analysis, apply repeatable policy, expose protected remote controls, and notify an operator. Objectives are to create a fully simulated, repeatable IoT-to-cloud pipeline; isolate each owner's devices; reject implausible or malformed input; prevent duplicate/risky actuator operations; and make the result straightforward to run and deploy.

## Scope and assumptions

All sensor values are synthetic, and watering events simulate a pump rather than switching real hardware. Profiles are configurable starting points. The web app polls every ten seconds. A production system would add managed identity, database migrations, quotas, background offline checks, observability, and verified hardware interlocks. No claim is made that synthetic readings represent a calibrated plant or that profile values are universally correct.

## System design

The virtual device sends JSON via HTTPS/REST using a per-device secret. The API authenticates the device independently from dashboard users. Dashboard routes require an expiring signed bearer token and verify device ownership for every operation. SQL records users, devices, readings, watering events, and alerts. Readings are indexed by device and timestamp and deduplicated by `(device_id, event_id)`. Automation requires a low reading, enabled automatic mode, available tank, and elapsed cooldown; pulses have a configurable upper bound. The simulator polls actions and raises its synthetic soil value after a pulse.

## Data and decision rules

A reading includes device ID, event ID, soil moisture (0–100%), temperature (−20–70 °C), humidity (0–100%), light (0–100%), optional tank level (0–100%), and a timezone-aware timestamp. Timestamps must be at most five minutes in the future and no older than seven days. Defaults are succulent 20%, indoor 30%, herb 35%, and tomato 40%. Automatic watering queues a three-second pulse when moisture is below threshold; the maximum is ten seconds by default, repeated actions are blocked for five minutes, and a tank at or below 5% blocks watering. Threshold changes are limited to 5–90%.

## Security and failure handling

Passwords are PBKDF2-SHA256 hashed; device keys are random and stored as SHA-256 digests. Bearer tokens are HMAC-signed and expire. User/device access is owner-scoped. Strict Pydantic validation blocks NaN/infinity, out-of-range data, malformed IDs, control characters, missing timezone, and unreasonable timestamps. Duplicate delivery is harmless. The simulator retries transient network/server errors with exponential backoff and jitter, but does not retry ordinary client errors. Device keys must use HTTPS outside localhost. Production requires a strong secret, protected environment variables, TLS, managed encryption, quotas/rate limiting, key rotation, and backups.

## Cloud-computing relevance

Vercel hosts the static React output and Python API function; PostgreSQL is external managed state because serverless filesystems are ephemeral. The design shows API-layer compute, PaaS/serverless deployment, cloud database, IoT transport, authentication/authorization, environment-based secrets, time-series indexing, stateless scaling, and health checks. At higher scale, an IoT broker, gateway, queue/event stream, dedicated time-series store, worker fleet, retention/rollup jobs, and alerting/monitoring services decouple ingestion and display.

## Testing and acceptance

Automated tests are in `tests/`. They exercise registration/login, malformed credentials, owner boundaries, device keys, input ranges, future/naive timestamps, deduplication, threshold watering, one-time action delivery, cooldown, low-tank blocking, threshold setting, manual watering, and alert acknowledgment. The manual acceptance path is: register → create device → start simulator → observe readings → lower threshold or wait for gradual drying → observe action/virtual pump → inspect history and alerts. Frontend build and tests should pass using README commands; execution results are reported separately after they run in the available environment.

## Limitations and next work

This MVP has no email/SMS/FCM delivery, physical actuator driver, weather integration, forecasting model, or background scheduled worker. Offline alerts are evaluated when the dashboard requests devices. Production hardening should add migrations, rate limits, audit records, observability and alert routing, token/device-key rotation, action acknowledgment from firmware, and staging deployment tests. Hardware work needs calibrated sensors, separate protected low-voltage pump supply, and independent local cutoff logic.

## Conclusion

The implementation moves beyond an Arduino-only demonstration: simulated devices, protected APIs, persistent telemetry, cloud-ready storage/deployment, automation, and a remote dashboard form one coherent cloud computing project. The same API data contract supports future ESP32 hardware without changing the dashboard architecture.
