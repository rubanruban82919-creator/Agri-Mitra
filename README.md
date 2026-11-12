# AgriMitra Full-Stack V8 (Starter MVP)

This project contains the AgriMitra frontend and a working Python FastAPI backend.

## Implemented backend features
- Farm registration with map boundary coordinates.
- Automatic farm-area calculation remains in the browser map UI; calculated area and polygon are stored in SQLite.
- List, view and delete farm API endpoints.
- Photo/video upload endpoint with file validation and a 250 MB per-file limit.
- Uploaded media metadata stored in SQLite; file bytes stored under `backend/uploads/`.
- Direct farmer-to-buyer produce listings with crop, quantity, expected price, location and contact details.
- Harvesting loss calculator with estimated yield gap, percentage and financial value, plus SQLite-backed observation history.
- Buyers can browse listings and contact farmers directly by phone.
- Health-check endpoint.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:
- Website: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## Project layout

```text
AgriMitra_FullStack_V8/
  backend/
    main.py
    uploads/
    agrimitra.db   # created automatically on first run
  frontend/
    index.html
  requirements.txt
  README.md
```

## Important limitations / next production steps
- This is a local full-stack MVP, not yet a publicly hosted website.
- SQLite is used for easy local development. For production, move to PostgreSQL or Firebase.
- There is no farmer login/role-based access yet; farm records are currently shared by the local app instance. Add authentication and user ownership before public deployment.
- Uploaded media is stored on the backend disk. Use S3, Firebase Storage or another durable object store for production.
- Drone files are uploaded when selected in the browser. Direct automatic transfer from a flying drone requires a compatible drone camera/onboard computer, Wi-Fi/4G link, and a secure upload agent/telemetry integration.
- AI crop recommendation, disease detection, weather and translation modules remain prototype/demo functions until their model/API integrations are configured.
- Leaflet map tiles require an internet connection. Use HTTPS for GPS location in a deployed site.
