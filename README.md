# Incident Tracker API

FastAPI backend for the Incident Tracker application. The API uses SQL Server through `pyodbc` and returns JSON envelopes with `success` and `data` fields for application routes.

## Setup

Create and activate a virtual environment from this directory:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in this directory. It is ignored by Git:

```env
DATABASE_URL=Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=incident_tracker;Trusted_Connection=yes;TrustServerCertificate=yes;
```

The configured SQL Server database must contain:

- `dbo.users`
- `dbo.incidents`
- `dbo.incident_audit_log`

The SQL scripts in `sql/` provide the user table and demo users. Apply the incident and audit table scripts required by your database setup before starting the API.

## Run

```powershell
uvicorn app.main:app --reload
```

API base URL: `http://localhost:8000`

OpenAPI documentation: `http://localhost:8000/docs`

## Module Layout

- `app/main.py`: FastAPI app, CORS, exception handlers, and router registration
- `app/config.py`: environment loading and allowed frontend origins
- `app/constants.py`: enums, status transitions, and shared SQL constants
- `app/database.py`: SQL Server connection helper
- `app/schemas.py`: Pydantic request models
- `app/serializers.py`: database row-to-response conversion
- `app/routers/auth.py`: user listing and sign-in
- `app/routers/incidents.py`: incident CRUD, status transitions, and audit history
- `app/routers/analytics.py`: incident analytics
- `app/routers/diagnostics.py`: database connectivity check

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/auth/users` | List active users |
| `POST` | `/auth/signin` | Sign in |
| `POST` | `/auth/signup` | Create an account |
| `GET` | `/incidents` | List incidents with filters and pagination |
| `POST` | `/incidents` | Create an incident |
| `GET` | `/incidents/{id}` | Get incident details |
| `PUT` | `/incidents/{id}` | Update incident fields |
| `PATCH` | `/incidents/{id}/status` | Transition incident status |
| `GET` | `/incidents/{id}/audit` | Get incident history |
| `DELETE` | `/incidents/{id}` | Delete an incident |
| `GET` | `/incidents/analytics` | Get analytics data |
| `GET` | `/test-db` | Test database connectivity |

## Validation

```powershell
.\venv\Scripts\python.exe -m compileall app
.\venv\Scripts\python.exe -c "from app.main import app; print([(route.path, sorted(route.methods or [])) for route in app.routes])"
```
