# HMS Unlock Schedule

Creates a weekly HMS unlock schedule configuration based on a selected week in the "Door Access" PSCRC Google Calendar.

The church administrator can run this at any time to get the suggested HMS unlock schedule configuration based on a google calendar.

Features:

- Reads Google Calendar events (including recurring events, expanded automatically).
- Builds **maximal unlock intervals** (minimizes number of rows).
- Renders a **table** with weekdays as columns and ✔/◐/blank to show open/partial/closed status.
- Provides both **CLI** and **HTML UI**.
- Runs as a **Docker container** on Synology DS720+ (or any x86_64 system).

---

## How it Works

1. Connects to a **Google Calendar** using a **service account** configured with read-only access to that calendar.
2. Pulls events in the **current Sunday → Saturday week** (recurring events expanded).
3. Splits multi-day events per day and merges overlapping times.
4. Collects **unique time boundaries** across the range.
5. Builds **maximal unlock slots** between those boundaries (minimizes rows) and marks each weekday:
   - ✔ = unlock during this interval on that day.
   - blank = keep locked.

---

### 1. Prerequisites

- Python 3.11+
- A Google **service account** JSON file with access to your calendar.
  - share the calendar with the service account’s email.

### 2. Setup

```bash
git clone https://github.com/your-repo/unlock-scheduler.git
cd unlock-scheduler

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the app

```bash
export GCAL_SERVICE_ACCOUNT_JSON=./dir-to-secrets/service-account.json

uvicorn unlock_schedule.app.main:app --reload
```

Visit: [http://localhost:8000](http://localhost:8000)

---

## Deploying on Synology DS720+

The DS720+ runs **x86_64**, so the provided Dockerfile works.

### 1. Prepare files on Synology

1. Create a folder:  
   `/volume1/docker/unlock-scheduler/`

2. Copy into it:
   - `main.py`
   - `requirements.txt`
   - `Dockerfile`
   - `docker-compose.yml`
   - `README.md`

3. Create a `secrets/` subfolder and put your Google service-account JSON there:  
   `/volume1/docker/unlock-scheduler/secrets/service-account.json`

### 2. Build and Run (Option A: Docker Compose)

On Synology **Container Manager**:

- Go to **Projects** → **Add**.
- Point to `/volume1/docker/unlock-scheduler/`.
- Deploy.

This builds and runs the container as defined in `docker-compose.yml`.

### 3. Build and Run (Option B: CLI)

SSH into the Synology and run:

```bash
cd /volume1/docker/unlock-scheduler
docker compose up -d --build
```

### 4. Access the app

Visit:  
`http://<your-nas-ip>:8000/`

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CALENDAR_ID` | Calendar to read (set in `.env` for local / `env_file` for Docker) | *(required for this repo’s `.env` workflow)* |
| `GCAL_SERVICE_ACCOUNT_JSON` | Path inside container to the service account JSON | `/secrets/service-account.json` |

---

## Security Notes

- The container runs as a **non-root user**.
- The filesystem is **read-only** except for `/tmp`.
- Secrets are mounted read-only from `./secrets/`.

---

## Gotchas & Notes

- **Service Account Access**:  
  - For **Google Workspace**: Admin must enable domain-wide delegation, or you must share the calendar with the service account email.  
  - For **personal Gmail**: Share the calendar directly with the service account.

- **All-day events** are treated as **00:00–24:00** unlocks.

- **Mixed (◐) slots**: Occur if, for example, one Monday has an event and another Monday doesn’t. See the **exceptions list** under the schedule table for exact dates.

- **Synology Firewall**: Ensure port 8000 is allowed if accessing outside LAN.

- **Timezone**: Always set `DEFAULT_TIMEZONE` (e.g., `Pacific/Honolulu` for Oahu). Otherwise events may be misaligned.

- **Healthcheck**: Container has a built-in `/` healthcheck. Synology may restart it automatically if health fails.

---

## Example Usage

1. Set `CALENDAR_ID=...` in `.env`.
2. Run the app and open [http://localhost:8000](http://localhost:8000) (or NAS IP).
3. See a Sun→Sat grid of time intervals when the door should be unlocked (blank = locked).


## Running Locally (testing)

1. Create a virtual env
```shell
virtualenv .venv --python=python3
source .venv/activate
```
2. Install required packages into the virtual env
```shell
pip install -r requirements.txt
```
3. Set env variable to the google calendar app key file
```shell
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## Web UI

Auto reload for dev testing only.
```shell
uvicorn unlock_schedule.app.main:app --reload
```

Defaults to starting today; you can also pass `?start_date=YYYY-MM-DD`.

## CLI 

Usage
```shell
python -m unlock_schedule --help

usage: python -m unlock_schedule [-h] [--start-date START_DATE] [--pad-before PAD_BEFORE] [--pad-after PAD_AFTER]
                                 [--optimize] [--output OUTPUT]

Generate HMS unlock schedule CSV from Google Calendar.

options:
  -h, --help            show this help message and exit
  --start-date START_DATE
                        Start date for 7-day window in YYYY-MM-DD (local time). If omitted, uses today.
  --pad-before PAD_BEFORE
                        Minutes to unlock early (default: 0).
  --pad-after PAD_AFTER
                        Minutes to relock late (default: 0).
  --optimize            Use optimized interval decomposition to minimize number of HMS intervals.
  --output OUTPUT       Output CSV path (default: hms_unlock_schedule_template_next_week.csv).
```

Example writes to stdout a summary of the settings and writes a csv into the out folder.
```shell
python -m unlock_schedule
```

If you need a different 7-day window, pass `--start-date YYYY-MM-DD` (window starts at local midnight for that date).

## Tests
```shell
python -m unittest discover -s tests -q

▼ TestWindow
  ✔ test_next_sunday_midnight
  ✔ test_week_window_from_date_is_seven_days
▼ TestIntervals
  ✔ test_merge_intervals_touching
  ✔ test_split_interval_by_day
▼ TestServiceOptions
  ✔ test_generate_options_from_config
▼ TestTemplateVerify
  ✔ test_template_rows_round_trip_verify
▼ TestUnlockSchedules
  ✔ test_busy_week_5_intervals
  ✔ test_optimize_opportunity
```

---

## Futures

- Add UI controls to download schedule in CSV or JSON
