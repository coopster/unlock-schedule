# HMS Unlock Schedule

Creates a weekly HMS unlock schedule configuration based on a selected week in the "Door Access" PSCRC Google Calendar.

The church administrator can run this at any time to get the suggested HMS unlock schedule configuration based on the PSCRC Door Access google calendar.

Features:

- Reads Google Calendar events (including recurring events, expanded automatically).
- Builds **maximal unlock intervals** (minimizes number of rows).
- Renders a **table** with weekdays as columns and ✔/◐/blank to show open/partial/closed status.
- Provides both **CLI** and **HTML UI**.
- Runs as a **Docker container** on Synology DS720+ (or any x86_64 system).


## How it Works

1. Connects to a **Google Calendar** using a **service account** configured with read-only access to that calendar.
2. Pulls events in the **current Sunday → Saturday week** (recurring events expanded).
3. Splits multi-day events per day and merges overlapping times.
4. Collects **unique time boundaries** across the range.
5. Builds **maximal unlock slots** between those boundaries (minimizes rows) and marks each weekday:
   - ✔ = unlock during this interval on that day.
   - blank = keep locked.

### Google service account information:

    Google cloud project name: PSCRC-HMS
    Project ID: pscrc-hms
    Name: PSCRC Automation
    Service account ID: pscrc-automation
    email address: pscrc-automation@pscrc-hms.iam.gserviceaccount.com

### Calendar

    Google Account: pscrc.video@gmail.com
    Name: Building Access
    Calendar ID: c5rf35bev99fst7teu5fdvfs2i6ra6uq@import.calendar.google.com
    Visibility: Only to designated PSCRC staff and support (and this service account)

## Prerequisites

- Python 3.11+
- A Google **service account** JSON file with access to your calendar.
  - share the calendar with the service account’s email
  - generate an application key json file, and store in a secrets folder outside this repo and only visible to the account running this application.

## Building and Testing Locally

### 1. Setup

Clone the repo locally.

```bash
git clone https://github.com/your-repo/unlock-schedule.git
cd unlock-schedule
```

Set up the virtual environment with all required packages.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Locate the service account app key (secrets) file and point to it.

```bash
export GCAL_SERVICE_ACCOUNT_JSON=./dir-to-secrets/service-account.json
```


### 2. Run with the commnd line (CLI)

Usage
```shell
python -m unlock_schedule --help

usage: python -m unlock_schedule [-h] [--start-date START_DATE] [--pad-before PAD_BEFORE] [--pad-after PAD_AFTER] [--optimize] [--output OUTPUT]

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
  --output OUTPUT       Output CSV path (default: hms_unlock_schedule_template.csv).
```


### 3. Run the web app locally

Use `--reload` for dev testing.

```bash
uvicorn unlock_schedule.app.main:app --reload
```

Visit with your browser: [http://localhost:8000](http://localhost:8000)

---

## Deploying on Synology DS720+

The DS720+ runs **x86_64**, and we deploy using Docker.

Prepare the .env file to include `APP_VERSION=<VERSION>` where the version is something like 0.1.0.

### 1. Prepare files on Synology

1. Create a folder:  
   `/volume1/docker/unlock-schedule/`

2. Copy into it:
   - `docker-compose.yml`
   - `.env`

3. Create a `secrets/` subfolder and put your Google service-account JSON there:  
   `/volume1/docker/unlock-schedule/secrets/service-account.json`

4. Create a `images` subfolder where you will put your docker image file.

### 2. Build on Mac (Apple Silicon) for Synology (x86_64)

From your Mac (M1), build an `amd64` image and version it:

```bash
APP_VERSION=<VERSION> ./build.sh
```

This produces a docker image file in `dist/unlock-schedule_<VERSION>_linux/amd64.tar`

Copy the `amd64.tar` file to your staging NAS in the `images` folder, then load it with the Synology Container Manager. This creates the image in its local registry.

### 3. Run on Synology (Container Manager Project)

On Synology **Container Manager**:

- Go to **Projects** → **Add**.
- Point to `/volume1/docker/unlock-schedule/` where your `docker-compose` file exists, naming the image you just created.
- Build (which then runs).

This runs the preloaded image referenced in `docker-compose.yml`.

*Note: You don't need to use the web proxy for just local reference.*

### 4. Access the app

Visit:  
`http://<your-nas-ip>:8000/`

---

## Environment Variables

Defined in the `.env` file.

| Variable | Purpose | Default |
|----------|---------|---------|
| `CALENDAR_ID` | Calendar to read (set in `.env` for local / `env_file` for Docker) | *(required for this repo’s `.env` workflow)* |
| `GCAL_SERVICE_ACCOUNT_JSON` | Path to the service account JSON key file | `/secrets/service-account.json` |

## Version

- Docker builds bake in a version via `APP_VERSION=... ./build.sh` (or set `APP_VERSION` when running `docker compose build`).

---

## Security Notes

- The container runs as a **non-root user**.
- The filesystem is **read-only** except for `/tmp`.
- Secrets should be mounted read-only from `./secrets/` accessible only to this user.

---

## Gotchas & Notes

- **Service Account Access**: You must share the calendar with the service account email.

- **All-day events** are ignored.

- **Synology Firewall**: Ensure port 8000 is allowed if accessing outside LAN.

---

## Example Usage

1. Set `CALENDAR_ID=...` in `.env`.
2. Run the app and open [http://localhost:8000](http://localhost:8000) (or NAS IP).
3. See a Sun→Sat grid of time intervals when the door should be unlocked (blank = locked).


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

- Agent feature to update HMS with this schedule
- Manage schedule for periodically synchronizing HMS with this calendar
- Audit logging
- Authentication
