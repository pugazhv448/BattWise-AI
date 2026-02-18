# BattWise AI – Procedure to run and finish

## 1. One-time setup

Open PowerShell and go to the project folder:

```powershell
cd c:\Users\admin\OneDrive\Documents\battwise\battwise-ai
```

Create the virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ensure `.env` exists in `battwise-ai` with your Gemini key (no quotes):

```
GEMINI_API_KEY=AIzaSyChLlk_dPxMava0gljmKBi-tK45_lA9LHw
```

## 2. Run the app (pick one)

### Option A – Single script (recommended)

From `battwise-ai`:

```powershell
.\run.ps1
```

This starts the backend, then opens the frontend in the same window. Open **http://localhost:8501** in your browser.

### Option B – Two terminals

**Terminal 1 – Backend:**

```powershell
cd c:\Users\admin\OneDrive\Documents\battwise\battwise-ai
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 – Frontend:**

```powershell
cd c:\Users\admin\OneDrive\Documents\battwise\battwise-ai
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py --server.port 8501
```

Then open **http://localhost:8501**.

## 3. Verify

- **Frontend:** http://localhost:8501 – SoC chart, stress, plan, chat.
- **API docs:** http://127.0.0.1:8000/docs – Try `/simulate`, `/status`, `/plan`, `/chat`.

If chat still says “offline” or shows an error, the message will now include the real Gemini error (e.g. invalid key or quota). Fix the key in `.env` and restart the backend.

## 4. Stop

- Close the terminal where Streamlit is running (frontend).
- Close the terminal or window where uvicorn is running (backend), or run:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```
