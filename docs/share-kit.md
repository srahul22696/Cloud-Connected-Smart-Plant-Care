# GitHub and social sharing kit

## GitHub repository setup

**Repository:** `Cloud-Connected-Smart-Plant-Care`  
**Description:** Cloud-connected smart plant monitoring and watering platform featuring simulated IoT sensors, cloud data storage, automated irrigation logic, real-time monitoring, alerts, and scalable cloud architecture.  
**Suggested topics:** `cloud-computing`, `iot`, `smart-agriculture`, `python`, `fastapi`, `react`, `cloud-database`, `rest-api`, `automation`, `smart-irrigation`, `sensor-data`, `cloud-monitoring`.

The project is published at [github.com/srahul22696/Cloud-Connected-Smart-Plant-Care](https://github.com/srahul22696/Cloud-Connected-Smart-Plant-Care) and the live demo is [smart-plant-care-10ad.onrender.com](https://smart-plant-care-10ad.onrender.com/). Keep `.env`, database files, device keys, and deployment credentials out of commits.

## LinkedIn draft

🌱 **I built a cloud-connected smart plant care system.**

A Python virtual sensor sends gradual soil moisture, temperature, humidity, and light readings to a FastAPI service. The system validates and stores the readings, applies plant-specific watering rules, raises alerts, and queues a safe virtual pump action. A React dashboard brings current status, history, controls, and watering activity together.

A few things I focused on:
• Separate user and device authentication
• Input validation, duplicate protection, and owner-scoped access
• Watering cooldowns, low-tank protection, and maximum pump duration
• Local SQLite development and a live PostgreSQL-backed Render deployment
• Automated API tests for edge cases

This project helped me connect cloud computing concepts to a complete IoT workflow—from device telemetry to a remote dashboard. The included Python simulator makes the full pipeline repeatable without physical hardware, with an ESP32 integration path for later.

Try the live demo: https://smart-plant-care-10ad.onrender.com/  
Source code: https://github.com/srahul22696/Cloud-Connected-Smart-Plant-Care  
#CloudComputing #IoT #FastAPI #React #SmartAgriculture #Python #CloudProjects

## Instagram draft

A tiny garden, a little cloud engineering 🌿☁️

I built a smart plant care dashboard that watches simulated soil moisture, temperature, humidity, and light—then queues a safe virtual watering pulse when the plant needs it.

The project includes a virtual sensor simulator, secure API, database, watering logic, and dashboard. Try it here: https://smart-plant-care-10ad.onrender.com/

Built with Python, FastAPI, React, and SQL. Next stop: ESP32 🌱

Source code: github.com/srahul22696/Cloud-Connected-Smart-Plant-Care  
#IoT #CloudComputing #PlantCare #SmartGarden #PythonProject #WebDevelopment #StudentProject

## Screenshot checklist

Capture the dashboard after adding a plant and generating several simulator readings. Include the moisture chart, current sensor cards, automatic watering control, and recent event. Keep the image free of device credentials and personal account details. Save the final crop as `screenshots/dashboard.png` and add it to the README before publishing the repository.
