# TRAFICOP - AI Copilot for Bengaluru Traffic Operations

**Predict. Respond. Divert.**

Built for **Flipkart Gridlock 2.0 - Round 2** | Theme: *Event-Driven Congestion (Planned & Unplanned)*

This is my submission for Gridlock 2.0. I took the ASTraM event dataset (8,173 real Bengaluru traffic incidents) and built it into a working Traffic Command Center - it predicts how long an incident will take to resolve, scores how much impact it'll have on the corridor, classifies its risk level, recommends how many officers/barricades/tow vehicles to send, suggests diversion routes around it, and explains every single prediction with SHAP so it's not a black box. Everything runs on an interactive map of Bengaluru.

---

## Key Features

- AI-powered incident resolution time prediction using XGBoost
- Traffic Impact Score calculation
- Risk classification (Low / Medium / High / Critical)
- Traffic Resilience Index (TRI) for corridor analysis
- Resource recommendation engine
- Diversion route suggestions
- Interactive Bengaluru Command Map
- SHAP-based explainable AI
- Incident Simulator for operational planning
- Mappls (MapmyIndia) integration with OpenStreetMap fallback

---

## What's in this repo

| Folder | Contents |
|---|---|
| `notebook/` | `TRAFICOP_Training_Notebook.ipynb` - my full training pipeline, written to run top to bottom in Colab |
| `app/` | The Streamlit dashboard (`app.py`) - **ships with an already-trained model**, so you don't have to touch the notebook to use it |
| `app/data/` | `processed_events.csv` (cleaned + feature-engineered dataset) and `corridor_tri.csv` (per-corridor TRI table) |
| `app/models/` | `resolution_time_model.json` (trained XGBoost model, also used to rebuild the SHAP explainer at runtime), `label_encoders.pkl`, `feature_metadata.json`, `historical_lookups.json` |
| `app/utils/` | `core.py` (data/model loading, inference, recommendation logic) and `map_builder.py` (Folium map construction) |
| `app/pages_content/` | One file per dashboard page (7 pages) |

**You don't need to run the notebook to use the dashboard.** The trained model is already sitting in `app/models/`. I kept the notebook in the repo so anyone (judges included) can see exactly how I built it, retrain it on fresh data, or extend it.

---

## Quick start - run the dashboard locally (5 minutes)

Here's the exact sequence I use, no steps skipped.

### Step 1 - Install Python dependencies

Open a terminal in the `app/` folder and run:

```bash
pip install -r requirements.txt
```

This pulls in Streamlit, XGBoost, SHAP, Folium, and everything else the app needs. Takes 2-3 minutes depending on your connection.

### Step 2 - Run the app

Still inside the `app/` folder:

```bash
python -m streamlit run app.py
```

A browser tab opens automatically at `http://localhost:8501`. If it doesn't, just paste that URL into your browser manually.

### Step 3 - Explore

Use the sidebar to move between the 7 pages. I'd start with **Bengaluru Command Map** - that's the centerpiece of the whole thing.

That's it. No API keys, no signups, no cloud accounts needed just to run it locally.

---

## How I built the model (the notebook)

If you want to retrain the model, see exactly how I engineered the features, or extend this with your own data, open `notebook/TRAFICOP_Training_Notebook.ipynb` in Google Colab.

### Why I mount Google Drive

The notebook mounts Google Drive and creates a `TRAFICOP/` folder there. I did this because:
- I only had to upload the ASTraM CSV **once** - it stays cached in Drive for every future run
- Trained models and processed data survive across Colab sessions (Colab wipes its local disk the moment the runtime disconnects, but Drive doesn't)
- I could pick up exactly where I left off instead of re-running the whole pipeline every session

### What the notebook actually does, step by step

1. **Mounts Drive**, creates `MyDrive/TRAFICOP/{data,models,outputs}`
2. **Loads the ASTraM dataset** - cached after the first run
3. **Cleans the data** - parses 6 datetime columns, coalesces 3 different "resolution end" timestamp columns (none of them was populated for most rows on its own - I explain this fully inside the notebook)
4. **Engineers features** - time-of-day buckets, historical corridor×cause resolution medians, frequency features
5. **Trains XGBoost** on a log-transformed resolution-time target, evaluated honestly against a naive baseline
6. **Runs SHAP** for explainability
7. **Computes the Impact Score** (0–100) using a weighted formula I reasoned through and documented
8. **Classifies Risk** into Low/Medium/High/Critical
9. **Computes the TRI** (Traffic Resilience Index) per corridor
10. **Runs the Recommendation Engine** (officers, barricades, tow vehicles, escalation)
11. **Builds the Diversion Engine** (corridor-based fallback logic)
12. **Saves every artifact** the Streamlit app needs to run

Every formula gets explained inline in the notebook's markdown cells — not just "here's the code," but *why* I picked each weight and threshold, grounded in the actual data distribution (I looked at real value counts and quantiles before settling on numbers, instead of guessing round ones).

---

## The 10 modules, and where each lives

| # | Module | Where it lives |
|---|---|---|
| 1 | Traffic Event Intelligence | `notebook` Steps 5-8, surfaced in `app/pages_content/page_kpis.py` and `page_analytics.py` |
| 2 | Resolution Time Prediction (XGBoost) | `notebook` Step 9, model file `app/models/resolution_time_model.json` |
| 3 | Impact Score Engine | `notebook` Step 11, formula reused in `app/utils/core.py` |
| 4 | Risk Classification | `notebook` Step 12, `classify_risk()` in `app/utils/core.py` |
| 5 | Traffic Resilience Index (TRI) | `notebook` Step 13, table in `app/data/corridor_tri.csv`, dashboard in `page_tri.py` |
| 6 | Recommendation Engine | `notebook` Step 14, `recommend_resources()` in `app/utils/core.py` |
| 7 | Diversion Engine | `notebook` Step 15, `get_diversion_routes()` in `app/utils/core.py` — live-routing version uses Mappls, see "Mappls integration" below |
| 8 | SHAP Explainability | `notebook` Step 10, `app/pages_content/page_shap.py` |
| 9 | Incident Simulator | `notebook` Step 17, `app/pages_content/page_simulator.py` |
| 10 | Traffic Command Center Dashboard | `app/app.py` + all 7 pages |

---

## The Simulator actually feeds the rest of the dashboard, live

Submitting an incident in the **Incident Simulator** doesn't just show a result on that page — it injects the incident into your current browser session, where it then shows up across:

- **Bengaluru Command Map** — as a distinct pulsing ⭐ star marker (red glow), separate from the regular clustered historical incidents, so it's unmistakable during a live demo. Its popup is tagged "🔴 LIVE SIMULATED INCIDENT."
- **Executive KPIs** — Total Incidents, Currently Active, and Critical Risk counts all update to include it.
- **Analytics** — time-of-day, corridor, and impact-score breakdowns include it.
- **Recommendations** — if it's Critical/High risk and active, it shows up in the "Incidents Currently Requiring Escalation" list.

I made this session-only on purpose — nothing gets written to disk or to the original dataset. Reload the app (or open a new tab) and you're back to the clean 8,173-incident baseline. There's a "🔴 N live simulated incidents active" badge and a **Clear live incidents** button in the sidebar whenever you have any active, so it's always obvious what's real data vs. what you just typed in.

**Why session-only instead of a database:** for a 24-hour build, this was the right call — it makes the "type in an incident, watch the whole command center react" demo moment fully real, without the extra complexity (and extra failure surface) of a database or file-write layer this build doesn't actually need.

---

## A note on data honesty (read this before your demo)

Three things I want to be able to explain confidently to judges, because I built this without hiding any of it:

**1. `event_type` is not the incident category.** In the raw ASTraM file, `event_type` only contains `planned`/`unplanned` — that's the theme's planned-vs-unplanned axis. The actual incident category (vehicle breakdown, accident, pot hole, etc.) lives in `event_cause`. I use both correctly throughout — `event_cause` for severity/category logic, `event_type` as a model feature.

**2. Resolution time is only computable for ~37% of rows.** Three different "end" timestamp columns (`end_datetime`, `resolved_datetime`, `closed_datetime`) are each mostly null on their own. I coalesce them (`closed_datetime` → `resolved_datetime` → `end_datetime`) and only train on rows with a clean, positive, ≤7-day duration (3,060 of 8,173 rows). That's disclosed in the notebook, not hidden. Open/active incidents — which by definition don't have a resolution time yet — still get an Impact Score, Risk Level, and recommendations, since those don't need a resolution timestamp.

**3. The XGBoost R² is modest (~0.25-0.35 in log space), and that's honest, not a bug.** Incident resolution time genuinely depends on factors this dataset doesn't capture (exact obstruction severity, tow truck availability, driver behavior). I report MAE against a naive baseline to show the model adds real value over "always guess the median," instead of inflating R² by hiding outliers. If a judge asks about model performance, this is the answer: *defensible, not dressed up.*

---

## How TRAFICOP Works

1. A traffic incident is reported or simulated.
2. The incident details are processed and enriched using historical corridor intelligence.
3. The XGBoost model predicts the expected resolution time.
4. The Impact Score Engine calculates how severely the incident may affect traffic operations.
5. The Risk Engine classifies the incident as Low, Medium, High, or Critical.
6. The Recommendation Engine suggests officers, barricades, tow vehicles, and escalation actions.
7. The Diversion Engine recommends alternative routes around affected corridors.
8. The incident is visualized on the Bengaluru Command Map.
9. Decision-makers can monitor KPIs, corridor resilience, hotspot trends, and recommendations from a single dashboard.

The goal is to provide traffic operators with a unified AI-assisted decision support platform for faster response and better resource allocation.

## Tech stack

- **Modeling:** XGBoost (resolution time regression), SHAP (explainability)
- **Map:** Mappls (MapmyIndia) integration with automatic OpenStreetMap fallback
- **Dashboard:** Streamlit, Plotly, Matplotlib
- **Data:** pandas, numpy, scikit-learn (label encoding)
- **Training environment:** Google Colab + Google Drive

## Mappls Integration (Live, Auto-Detected)

TRAFICOP ships with a real Mappls client (`app/utils/mappls_client.py`) that:

* Uses a **Mappls REST API Key** for authentication.
* Automatically switches the Bengaluru Command Map from OpenStreetMap to live Mappls map tiles when a valid key is detected.
* Supports route intelligence and diversion planning using Mappls mapping services.
* Enhances the traffic command center experience with real Indian mapping infrastructure.
* Falls back automatically and silently to OpenStreetMap if no Mappls key is configured or if a service is temporarily unavailable. The application never crashes because of map connectivity issues.

### Automatic Detection

When a valid Mappls REST API Key is configured in:

```toml
MAPPLS_REST_KEY = "YOUR_REST_API_KEY"
```

the dashboard automatically detects it and activates live Mappls functionality.

The sidebar status changes to:

```text
🟢 Mappls live map: Connected
```

indicating that the application is successfully using Mappls services.

If no key is configured, the dashboard continues to operate normally using OpenStreetMap as a fallback.

### Benefits

* Real Bengaluru map visualization
* Interactive incident monitoring
* Congestion hotspot analysis
* Corridor-level traffic intelligence
* Enhanced command-center experience for traffic operations

---

## Deployment

TRAFICOP is deployed on Streamlit Cloud and can be accessed through the live application URL: https://traficop.streamlit.app/

The deployed application includes:

* Executive KPI Dashboard
* Bengaluru Command Map
* Traffic Resilience Index (TRI) Dashboard
* Analytics Dashboard
* SHAP Explainability
* Incident Simulator
* Resource Recommendation Engine

The application automatically loads the trained XGBoost model, processed dataset, and corridor intelligence data required for inference.

If a valid Mappls REST API Key is configured, the dashboard uses live Mappls map services. Otherwise, it automatically falls back to OpenStreetMap while maintaining full functionality.

No additional setup is required for end users accessing the deployed application.


---

## License / data note

The ASTraM dataset was provided by the competition organizers and is anonymized. This project was built for Flipkart Gridlock 2.0 and isn't affiliated with or endorsed by MapmyIndia, OpenStreetMap Foundation, or Bengaluru Traffic Police.
