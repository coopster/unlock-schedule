python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Credentials (one option):
export GCAL_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
# Optional: Workspace domain delegation
# export GCAL_DELEGATE=you@yourdomain.com

# Optional defaults:
export DEFAULT_TIMEZONE=America/New_York
export CALENDAR_ID=primary

uvicorn unlock_schedule.app.main:app --reload --port 8000
