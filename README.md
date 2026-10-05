# 🚧 Pharos

### AI-Assisted Road Hazard Early-Warning & Risk Assessment System

Pharos is a mobile-based road safety platform designed to warn drivers about potential road hazards such as **landslides, falling rocks, waterlogging, heavy rainfall, traffic congestion, and road blockages before they reach the danger zone**.

The project combines **real-time citizen reports, weather forecasts, terrain data, historical incidents, and route information** to calculate an explainable risk score for roads ahead.

> ⚠️ **Pharos is an advisory prototype. It does not replace official government warnings, traffic instructions, or emergency services.**

---

## 🎯 Problem

Mountain and ghat roads can become dangerous due to rapidly changing weather and road conditions.

Existing navigation applications primarily focus on:

* Distance and travel time
* Traffic congestion
* Turn-by-turn navigation

Pharos focuses on a different question:

> **"What risks might I encounter on the road ahead?"**

The system analyzes upcoming road segments and provides an understandable risk level along with the reasons behind the score.

---

## 💡 Solution

Pharos:

1. Detects the user's current location and destination.
2. Obtains possible routes using OpenStreetMap-based routing.
3. Divides the route into approximately **1 km segments**.
4. Collects relevant weather, terrain, historical incident, and citizen-report data.
5. Calculates a risk score for each road segment.
6. Explains why a segment has a particular risk level.
7. Highlights hazardous areas on the map.
8. Allows users to report new hazards.
9. Provides nearby safe places such as hospitals, police stations, petrol stations, and shelters.
10. Can hand off turn-by-turn navigation to Google Maps.

---

# 🧠 Explainable Risk Engine

The core of Pharos is an **explainable, rule-based risk engine**.

Each road segment receives a score between **0 and 100**.

| Risk Score | Level       |
| ---------: | ----------- |
|       0–30 | 🟢 Low      |
|      31–50 | 🟡 Moderate |
|      51–75 | 🟠 High     |
|     76–100 | 🔴 Critical |

### Example factors

| Risk Factor                            | Maximum Points |
| -------------------------------------- | -------------: |
| Heavy rainfall expected at ETA         |            +30 |
| Historical landslide activity          |            +25 |
| Steep terrain                          |            +20 |
| Recent landslide / falling-rock report |            +40 |
| Heavy traffic                          |            +25 |
| Low visibility / fog                   |            +15 |

The final score is capped at **100**.

### Why ETA matters

pharos does not only consider the weather **right now**.
Pharos does not only consider the weather **right now**.

If a driver is expected to reach a particular road segment at 2:30 PM, the risk engine uses the **forecast around the estimated arrival time**.

This allows Pharos to focus on potential hazards **ahead of the driver**, rather than only describing the current location.

---

# 🔍 Explainable Risk

Every risk score contains a list of reasons.

Example:

```text
Risk Score: 78 — Critical

Reasons:
• Heavy rainfall expected around 14:30
• Steep slope detected
• 2 historical landslide incidents
• Recent citizen report nearby
```

The scoring rules are designed to be **config-driven**, allowing the team to tune weights without modifying the core scoring logic.

---

# 🗺️ Core Features

### 🏠 Risk Dashboard

* Current road risk
* Risk for next 10 / 20 / 50 km
* Risk level
* Explanation of contributing factors

### 🛣️ Risk-Aware Routing

* Main route
* Alternative routes
* Hazard locations
* Risk score along each route
* Estimated delay
* Open route in Google Maps

### 🚨 Citizen Hazard Reporting

Users can report:

* Landslides
* Falling rocks
* Road blockages
* Waterlogging
* Accidents
* Heavy traffic
* Other road hazards

Reports can include:

* GPS location
* Hazard type
* Severity
* Description
* Photo

### 🤝 Community Verification

Reports can be:

* Confirmed by other users
* Marked as cleared
* Automatically expired after a period of time
* Given different trust levels

This helps reduce false or outdated reports.

### 🌧️ Weather & Terrain Analysis

Pharos combines:

* Rainfall forecasts
* Visibility / fog information
* Elevation
* Road slope
* Historical incidents

### 📍 Safe Places

Find nearby:

* 🏥 Hospitals
* ⛽ Petrol stations
* 👮 Police stations
* 🛟 Shelters / safe locations

### 🔔 Safety Alerts

Push notifications can be triggered when:

* Risk increases significantly
* A severe hazard is reported nearby
* A dangerous condition appears along a saved route

### 📡 Offline Support

The application is designed for areas with unreliable connectivity.

Cached information can include:

* Previously loaded map data
* Safe places
* Recent reports
* Saved route information

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │     Flutter App      │
                    │   Android Client     │
                    └──────────┬───────────┘
                               │
                               │ REST / Polling
                               ▼
                    ┌──────────────────────┐
                    │    FastAPI Backend   │
                    │                      │
                    │ Auth • Reports       │
                    │ Places • Routes      │
                    │ Notifications        │
                    └───────┬───────┬──────┘
                            │       │
                ┌───────────┘       └────────────┐
                ▼                                ▼
       ┌──────────────────┐             ┌──────────────────┐
       │ PostgreSQL +     │             │   Risk Engine    │
       │     PostGIS      │             │                  │
       │                  │             │ Weather          │
       │ Reports          │             │ Terrain          │
       │ Road Segments    │             │ History          │
       │ Incidents        │             │ Reports          │
       │ Places           │             │ YAML Rules       │
       └──────────────────┘             └────────┬─────────┘
                                                 │
                    ┌────────────────────────────┼──────────────────┐
                    ▼                            ▼                  ▼
             Open-Meteo                       OSRM                OSM
             Weather API                  Routing API          Overpass API
```

---

# 🛠️ Tech Stack

## Mobile

* Flutter
* Dart
* flutter_map
* OpenStreetMap
* Firebase Cloud Messaging
* GPS / Location services
* Offline caching

## Backend

* Python
* FastAPI
* SQLAlchemy
* GeoAlchemy2
* REST APIs

## Database

* PostgreSQL
* PostGIS

PostGIS enables geospatial operations such as:

* Reports within a radius
* Hazards near a route
* Points near road segments
* Route-to-incident proximity analysis

## Risk Engine

* Python
* YAML-based configuration
* Weather APIs
* Elevation data
* Historical incident data
* Rule-based scoring
* Backtesting

## External Services

* Open-Meteo — weather forecasts
* OSRM / OpenRouteService — routing
* OpenStreetMap — map data
* Overpass API — nearby places
* Firebase Cloud Messaging — push notifications
* Google Maps — external turn-by-turn navigation

## DevOps

* Docker
* GitHub Actions
* GitHub
* Cloud deployment

## Testing

* pytest
* Flutter widget tests
* Risk-engine unit tests
* API tests

---

# 📂 Repository Structure

```text
pharos/
Pharos/
│
├── app/
│   └── Flutter mobile application
│
├── backend/
│   ├── FastAPI service
│   ├── database
│   ├── API routes
│   ├── authentication
│   └── tests
│
├── risk_engine/
│   ├── scoring logic
│   ├── rules.yaml
│   ├── data processing
│   ├── backtesting
│   └── tests
│
├── data/
│   ├── historical incidents
│   ├── sample GeoJSON
│   └── corridor data
│
├── docs/
│   ├── architecture
│   ├── API contract
│   ├── wireframes
│   └── implementation plan
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

# 🔌 API Overview

| Endpoint                     | Purpose                                |
| ---------------------------- | -------------------------------------- |
| `POST /reports`              | Create a road hazard report            |
| `GET /reports`               | Retrieve reports by area / type / time |
| `POST /reports/{id}/confirm` | Confirm a report                       |
| `POST /reports/{id}/clear`   | Mark a report as cleared               |
| `POST /route`                | Calculate routes and route risk        |
| `GET /risk`                  | Get upcoming road risk                 |
| `GET /places`                | Find nearby safe places                |
| `POST /devices`              | Register device for notifications      |

Interactive API documentation will be available through **FastAPI Swagger UI** after deployment.

---

# 👥 Team

Pharos is being developed as a **3-member engineering project**, with each member owning an end-to-end technical area.

| Member       | Role                             | Responsibility                                                                      |
| ------------ | -------------------------------- | ----------------------------------------------------------------------------------- |
| **Member 1** | Backend & Database Lead          | FastAPI, PostgreSQL/PostGIS, authentication, reports API, notifications, deployment |
| **Member 2** | Mobile App & UX Lead             | Flutter, UI/UX, maps, reporting, offline support, multilingual interface            |
| **Member 3** | Risk Engine, Routing & Data Lead | Risk scoring, weather/elevation data, routing, historical incidents, backtesting    |

### Engineering Workflow

* `main` → stable branch
* `feature/<name>` → feature development
* Pull requests for merging
* At least one review from another team member
* GitHub Issues for tasks
* GitHub Projects for project tracking
* GitHub Actions for CI
* Small, meaningful commits

Example:

```text
feat: add hazard reporting API
fix: handle expired reports
docs: update risk engine documentation
test: add route risk tests
```

---

# 📊 Evaluation

Pharos will measure the system using actual project data rather than invented metrics.

Planned evaluation metrics:

| Metric                    | Result |
| ------------------------- | ------ |
| Historical incidents used | TBD    |
| Risk-engine precision     | TBD    |
| Risk-engine recall        | TBD    |
| API response time         | TBD    |
| Automated tests           | TBD    |
| Backtesting period        | TBD    |

> **Metrics will be added only after they are actually measured.**

---

# 🧪 Backtesting

Historical road incidents will be replayed against the risk engine to determine whether Pharos would have generated a sufficiently high risk score before an incident.

The evaluation will measure:

* Precision
* Recall
* False positives
* False negatives
* Warning lead time

This allows the risk engine to be evaluated using measurable results rather than only demonstrating the UI.

---

# 🚀 Development Roadmap

### Phase 1 — Foundation

* [ ] Select initial ghat corridor
* [ ] Design database schema
* [ ] Define OpenAPI contract
* [ ] Create Flutter application
* [ ] Set up FastAPI
* [ ] Configure PostgreSQL + PostGIS

### Phase 2 — MVP

* [ ] User authentication
* [ ] Hazard reporting
* [ ] Live hazard map
* [ ] Risk engine
* [ ] Home risk card
* [ ] Weather integration
* [ ] Basic route risk

### Phase 3 — Routing & Safety

* [ ] Alternative routes
* [ ] Risk along route
* [ ] Safe places
* [ ] Google Maps handoff
* [ ] Community confirmation
* [ ] Report expiry

### Phase 4 — Alerts & Offline

* [ ] Firebase push notifications
* [ ] Offline cache
* [ ] Notification thresholds
* [ ] Improved GPS handling

### Phase 5 — Validation

* [ ] Backtesting
* [ ] Field testing / GPS replay
* [ ] Performance testing
* [ ] Risk-weight tuning
* [ ] UI polish
* [ ] Multilingual support

### Phase 6 — Release

* [ ] Production deployment
* [ ] GitHub Actions CI
* [ ] Signed Android APK
* [ ] Screenshots
* [ ] Demo video
* [ ] Documentation
* [ ] v1.0 release

---

# ⚙️ Local Development

> Setup instructions will be finalized once the project structure and environment configuration are established.

### Planned setup

```bash
git clone https://github.com/bindu-yogesh/Pharos.git
cd Pharos
docker compose up --build
```

Then start the Flutter application:

```bash
cd app
flutter pub get
flutter run
```

Backend API documentation will be available at:

```text
/docs
```

---

# 🔐 Safety & Data Disclaimer

Pharos is an experimental road-safety prototype.

Risk scores are generated from available datasets, forecasts, historical information, and community reports. They may contain inaccuracies or delays.

Users should:

* Follow official government warnings
* Follow traffic signs and instructions
* Avoid dangerous roads when advised
* Contact emergency services when necessary

Pharos should **not be treated as a replacement for official emergency or disaster-management systems**.

---

# 🌱 Future Scope

After the MVP is stable, possible extensions include:

* Machine-learning-based risk prediction
* Comparison between ML and rule-based scoring
* Web dashboard for authorities
* WebSocket-based live updates
* Voice safety alerts
* Night / low-light mode
* Expansion to additional ghat corridors
* Improved incident verification
* More advanced traffic estimation

---

# 📸 Screenshots

Screenshots will be added after the first working MVP.

```text
Home Risk Dashboard
        ↓
Route Risk
        ↓
Live Situation Map
        ↓
Hazard Reporting
        ↓
Safe Places
```

---

# 🎥 Demo

A 2–3 minute demonstration video will showcase:

1. Opening the pharos dashboard
1. Opening the Pharos dashboard
2. Viewing current route risk
3. Viewing reasons behind the risk score
4. Reporting a road hazard
5. Seeing the report appear on the map
6. Comparing route risks
7. Viewing nearby safe places
8. Receiving a safety alert

**Demo:** Coming soon

---

# 📄 Project Documentation

Detailed documentation will be maintained inside the `/docs` directory.

Planned documents:

* Architecture
* Implementation Plan
* API Contract
* Database Schema
* Risk Engine Design
* Data Sources
* Backtesting Methodology
* Testing Strategy
* Demo Script

---

# 📜 License

License information will be added before the first public release.

---

### Built with ❤️ by the Pharos Team

**Pharos — Know the risk before you reach it.**
