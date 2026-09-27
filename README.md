# FitBuddy – AI Fitness Plan Generator

FastAPI + Jinja2 + SQLite + Google Gemini 2.5 Flash.

## 1. Create environment

Windows PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate
```

## 2. Configure Gemini

Copy `.env.example` to `.env` and put your Gemini API key in:
```text
GEMINI_API_KEY=your_real_key
```

Keep:
```text
DEMO_MODE=false
GEMINI_MODEL=gemini-2.5-flash
```

## 3. Run

```powershell
python -m uvicorn app.main:app --reload
```

Open:
- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/view-all-users

## 4. If you need to prove the UI works before adding the API key

Set in `.env`:
```text
DEMO_MODE=true
```
The site will run with a built-in sample plan. This is only for UI/demo testing, not real Gemini generation.

## 5. Demo flow

1. Open home page.
2. Enter Name: Anu
3. User ID: FB001
4. Age: 21
5. Weight: 60
6. Goal: muscle gain
7. Intensity: medium
8. Click Generate 7-Day Plan.
9. Show workout + nutrition tip.
10. Enter feedback: "Add more cardio and one extra rest day."
11. Click Update My Plan.
12. Open Admin Dashboard and show original/updated plans.
13. Open `/docs` to show FastAPI API documentation.

## Troubleshooting

- `ModuleNotFoundError`: activate `.venv` and run `pip install -r requirements.txt`.
- `Could not import module "main"`: run exactly `python -m uvicorn app.main:app --reload` from the FitBuddy project root.
- Port busy: `python -m uvicorn app.main:app --reload --port 8001`, then open http://127.0.0.1:8001.
- Gemini authentication/model error: check `.env`, API key, and `GEMINI_MODEL=gemini-2.5-flash`.
