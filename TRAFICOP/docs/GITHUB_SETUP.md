# GitHub Setup Guide

My own notes on how I pushed this to GitHub — keeping them here in case I (or you) need to redo it.

---

## 1. Repository Creation

1. Go to **https://github.com** and sign in (create a free account if you don't have one).
2. Click the **+** icon top-right → **New repository**.
3. Fill in:
   - **Repository name:** `traficop` (or `traficop-gridlock2`)
   - **Description:** `AI Copilot for Bengaluru Traffic Operations — Flipkart Gridlock 2.0`
   - **Visibility:** Public (required for free Streamlit Cloud deployment) or Private (if you have a paid plan / your institution provides one)
   - **Do NOT** check "Add a README" — you already have one, and an auto-generated one will conflict
4. Click **Create repository**. GitHub will show you a page with setup commands — keep that tab open.

## 2. Upload Process

You have two options. **Option A is recommended** since you might not have done this before.

### Option A — GitHub Desktop (easiest, no command line)

1. Download **GitHub Desktop** from https://desktop.github.com and install it.
2. Open it, sign in with your GitHub account.
3. Click **File → Add Local Repository**, browse to your `traficop/` project folder.
4. It will say "This directory does not appear to be a Git repository" — click **create a repository** instead.
5. Fill in the repository name to match what you created on GitHub.com, click **Create Repository**.
6. You'll see all your files listed as changes. Write a commit message like `Initial TRAFICOP submission` and click **Commit to main**.
7. Click **Publish repository** (top bar). Make sure "Keep this code private" is unchecked if you want it public, then click **Publish Repository**.
8. Done — refresh your GitHub.com repository page and your files will be there.

### Option B — Command line (if you're comfortable with terminal)

From inside your `traficop/` project folder:

```bash
git init
git add .
git commit -m "Initial TRAFICOP submission"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/traficop.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username. If prompted for a password, GitHub no longer accepts your account password for git operations — you'll need a **Personal Access Token** instead: go to GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic), check the `repo` scope, copy the token, and paste it as your password when git asks.

## 3. File Organization

Your repository root should look like this after upload:

```
traficop/
├── README.md
├── notebook/
│   └── TRAFICOP_Training_Notebook.ipynb
├── app/
│   ├── app.py
│   ├── requirements.txt
│   ├── .streamlit/
│   │   └── secrets.toml.example
│   ├── data/
│   │   ├── processed_events.csv
│   │   └── corridor_tri.csv
│   ├── models/
│   │   ├── resolution_time_model.json
│   │   ├── label_encoders.pkl
│   │   ├── feature_metadata.json
│   │   └── historical_lookups.json
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   ├── map_builder.py
│   │   └── mappls_client.py
│   └── pages_content/
│       ├── __init__.py
│       ├── page_kpis.py
│       ├── page_map.py
│       ├── page_tri.py
│       ├── page_analytics.py
│       ├── page_shap.py
│       ├── page_simulator.py
│       └── page_recommendations.py
└── docs/
    ├── MAPMYINDIA_INTEGRATION.md
    └── DEPLOYMENT_GUIDE.md
```

### Important: do NOT upload the raw ASTraM dataset to a public repo without checking competition rules

If `Astram_event_data_anonymized...csv` is meant to stay private per competition terms, either:
- Keep your repository **private**, or
- Add a `.gitignore` entry for the raw CSV and only commit the processed/derived files in `app/data/` (the app doesn't need the raw original CSV to run — it only reads `processed_events.csv` and `corridor_tri.csv`)

Example `.gitignore`:
```
__pycache__/
*.pyc
.DS_Store
data/astram_event_data.csv
```

(This only applies to the raw original file used by the notebook — `app/data/processed_events.csv` is the derived, already-processed file the dashboard needs and should stay in the repo.)

## 4. Verifying the upload

Go to your repository page on GitHub.com and confirm:
- [ ] `app/app.py` is visible and you can click into it to see the code
- [ ] `app/requirements.txt` is present
- [ ] `app/data/processed_events.csv` and `app/data/corridor_tri.csv` are present
- [ ] `app/models/*.json` and `*.pkl` files are present
- [ ] The notebook `.ipynb` renders with its cells visible when you click it (GitHub renders notebooks automatically)

If any model/data file shows as missing or 0 bytes, it likely hit GitHub's individual file size warnings (100MB hard limit, 50MB soft warning) — none of TRAFICOP's files are anywhere near that size, so this should not happen, but double-check `app/models/resolution_time_model.json` (the largest model artifact at under 1MB) uploaded correctly since binary files occasionally fail silently in slow connections.
