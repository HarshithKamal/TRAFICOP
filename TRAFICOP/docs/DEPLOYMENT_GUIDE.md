# Deployment Guide

Three deployment options, in order of recommendation for this project. **Streamlit Cloud (I have choosen) is the easiest and fastest — use it unless you have a specific reason not to.**

---

## Option A — Streamlit Cloud (recommended, easiest)

### Account Creation

1. Go to **https://share.streamlit.io**.
2. Click **Sign up** / **Continue with GitHub** and authorize Streamlit Cloud to access your GitHub account.
3. No credit card required for the free tier.

### Deployment Steps

1. Once logged in, click **Create app** (or **New app**).
2. Choose **"Deploy a public app from GitHub"**.
3. Fill in:
   - **Repository:** select your `traficop` repo from the dropdown (it auto-lists repos you have access to)
   - **Branch:** `main`
   - **Main file path:** `app/app.py` — this is important, since `app.py` is inside the `app/` subfolder, not the repo root
4. Click **Advanced settings** (optional but recommended):
   - **Python version:** select 3.11 or 3.12 to match what was tested
5. Click **Deploy**.
6. Streamlit Cloud will now: clone your repo, install everything in `app/requirements.txt`, and launch the app. This takes 2-5 minutes the first time. You'll see a live build log.
7. Once done, you get a public URL like `https://your-app-name.streamlit.app` — this is what you submit / demo from.

### Secrets Management

The app runs without any secrets configured — it auto-falls-back to OpenStreetMap tiles and corridor-based diversion logic. Once your Mappls developer account is approved and you have credentials:

1. In your app's dashboard on share.streamlit.io, click the **⋮ (kebab menu)** next to your app → **Settings → Secrets**.
2. Paste in TOML format (use whichever credential type your Mappls console gave you — REST key is simplest):
   ```toml
   MAPPLS_REST_KEY = "your_rest_key_here"

   # OR, if you have OAuth-style credentials instead:
   MAPPLS_CLIENT_ID = "your_client_id_here"
   MAPPLS_CLIENT_SECRET = "your_client_secret_here"
   ```
3. Click **Save**. Streamlit Cloud restarts your app automatically with the new secrets injected.
4. Reload the app — the sidebar should now show **"🟢 Mappls live map: Connected"**. If it instead shows a yellow "configured but unreachable" warning, double check the key was copied correctly (no extra whitespace) and that your Mappls account's free credits haven't been exhausted.

In code, these are read automatically by `app/utils/mappls_client.py` via `st.secrets` — you never need to touch `app.py` or any page file to enable this.

### Verification

- Open the public URL and confirm all 7 sidebar pages load without a red error box.
- Specifically test the **Incident Simulator** page (click "Run TRAFICOP Analysis") and the **Bengaluru Command Map** page (confirm the map renders and markers are clickable) — these are the two most complex pages and the most likely to surface a missed dependency.
- If you see `ModuleNotFoundError`, double check `app/requirements.txt` includes that package.
- If you see `FileNotFoundError` for a model or data file, confirm the **Main file path** was set to `app/app.py` (not just `app.py`) so relative paths resolve correctly.

---

## Option B — Render

### Account Creation

1. Go to **https://render.com** and sign up (GitHub sign-in is fastest).
2. Free tier available; no credit card required for basic web services (free tier apps sleep after inactivity and take ~30-60s to wake up on the next request — worth knowing if you're demoing live and there's been a gap).

### Deployment Steps

1. From the Render dashboard, click **New +** → **Web Service**.
2. Connect your GitHub account if not already connected, then select your `traficop` repository.
3. Configure:
   - **Name:** `traficop` (or anything)
   - **Region:** choose the one closest to your judges/audience, or default
   - **Branch:** `main`
   - **Root Directory:** `app` (since `app.py` and `requirements.txt` live inside the `app/` folder)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Select the **Free** instance type.
5. Click **Create Web Service**.
6. Render will build and deploy — watch the live log. First deploy takes 3-7 minutes.
7. Once live, Render gives you a URL like `https://traficop.onrender.com`.

### Secrets Management

1. In your service's dashboard, go to **Environment** tab.
2. Click **Add Environment Variable** for any secret (e.g. `MAPMYINDIA_REST_KEY`).
3. These are injected as environment variables at runtime — accessible in code via `os.environ.get("MAPMYINDIA_REST_KEY")`, which is exactly what the code in `docs/MAPMYINDIA_INTEGRATION.md` already expects.

### Verification

- Same checklist as Streamlit Cloud above.
- Additionally: free-tier Render services **spin down after 15 minutes of inactivity**. If you're demoing live, open the app a few minutes before your slot so it's already "warm" — the first request after sleep can take 30-60 seconds and might look like a hang to judges.

---

## Option C — Hugging Face Spaces

### Account Creation

1. Go to **https://huggingface.co/join** and create a free account.
2. Verify your email.

### Deployment Steps

1. Click your profile icon → **New Space**.
2. Fill in:
   - **Space name:** `traficop`
   - **License:** choose one (MIT is a safe default for a hackathon project) or skip
   - **Select the Space SDK:** choose **Streamlit**
   - **Space hardware:** Free (CPU basic) is sufficient
   - **Visibility:** Public or Private
3. Click **Create Space**. This creates a new Git repository hosted on Hugging Face.
4. You now need to push your `app/` folder contents to this Space's repo root (Hugging Face Spaces expects `app.py` and `requirements.txt` at the repo root, unlike Streamlit Cloud which lets you point at a subfolder).

   **Easiest approach:** clone the new empty Space repo locally, then copy your `app/` folder's *contents* (not the folder itself) into it:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/traficop
   cd traficop
   # copy contents of your project's app/ folder here (app.py, requirements.txt, data/, models/, utils/, pages_content/)
   git add .
   git commit -m "Initial TRAFICOP deployment"
   git push
   ```
5. Hugging Face automatically detects `app.py` + `requirements.txt` and builds/launches the Streamlit app. Watch the **Logs** tab in your Space for build progress.
6. Once live, your Space is available at `https://huggingface.co/spaces/YOUR_USERNAME/traficop`.

### Secrets Management

1. In your Space, go to **Settings → Variables and secrets**.
2. Click **New secret**, add name (e.g. `MAPMYINDIA_REST_KEY`) and value.
3. Access in code the same way as Render: `os.environ.get("MAPMYINDIA_REST_KEY")`.

### Verification

- Same checklist as above (all 7 pages load, simulator and map both work).
- Hugging Face Spaces free CPU tier is generally reliable for always-on demos (no sleep-on-inactivity issue like Render's free tier), which can make it a good backup if you're worried about a Render cold-start during judging.

---

## Which one should you actually use?

For a 24-hour hackathon timeline: **Streamlit Cloud (Option A)**. It is purpose-built for exactly this kind of app, requires zero extra configuration files, and the GitHub-native deploy flow is the fastest path from "code on my laptop" to "URL I can show judges." Use Render or Hugging Face Spaces only if Streamlit Cloud is unavailable or you hit a platform-specific limitation.
