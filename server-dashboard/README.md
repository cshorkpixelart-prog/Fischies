# Fisch Control Hub (Python)

This dashboard now runs on Python/Flask and includes:
- Dark-mode-only modern UI
- Login interface + sessions
- Owner/user management (create users, reset passwords, delete users)
- Rod data overview with per-rod tuning edits
- Rod lifecycle controls (add rod, deactivate/restore rod)
- Catch learning merge endpoint for macro clients
- Feedback inbox with mail-style list + preview + read/archive workflow
- Team chat with multiple channels
- Activity feed and feedback export
- AHK-compatible client endpoints for rod tuning + feedback

## Owner Login

- Username: `Makoral.Dev`
- Password: `TeamTea2421`

The owner account is enforced on startup.

## Run

1. Install Python 3.10+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python app.py
```

4. Open:
- Dashboard: `http://127.0.0.1:3030`
- Health check: `http://127.0.0.1:3030/api/health`

## Data Files

Stored in `server-dashboard/data/`:
- `rods.json`
- `feedback.json`
- `users.json`
- `chat.json`
- `activity.json`

## API Compatibility For AHK

- `GET /api/client/rod-tuning?name=<rod name>`
  - Returns the same key-value text format used by `RodData.ahk`.
  - Inactive rods are not returned.

- `POST /api/client/catch-learning`
  - Accepts `application/x-www-form-urlencoded` samples from the macro.
  - Merges per-rod catching tuning based on success/failure outcomes and returns key-value status.

- `POST /api/client/feedback`
  - Accepts `application/x-www-form-urlencoded` payload:
    - `type`
    - `description`
    - `rodName`
    - `clientTitle`
    - `clientVersion`
  - Returns text format (`status=ok`, `id=<...>`), compatible with current macro logic.

## Auto Deploy (GitHub -> Railway)

Workflow file:
- `.github/workflows/deploy-railway.yml`

Required GitHub Action secrets:
- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT`
- `RAILWAY_ENVIRONMENT`
- `RAILWAY_SERVICE`

Optional local helper script:
- `scripts/publish-and-deploy.ps1`
