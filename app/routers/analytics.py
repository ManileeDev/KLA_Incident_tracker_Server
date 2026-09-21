import pyodbc
from fastapi import APIRouter, HTTPException

from ..constants import ANALYTICS_SEVERITIES, ANALYTICS_STATUSES
from ..database import get_database_connection

router = APIRouter(prefix="/incidents", tags=["analytics"])


@router.get("/analytics")
def get_analytics_data():
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT status, COUNT(*) FROM dbo.incidents GROUP BY status")
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT severity, COUNT(*) FROM dbo.incidents GROUP BY severity")
            severity_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN status = 'Investigating' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) "
                "FROM dbo.incidents"
            )
            totals_row = cursor.fetchone()

            cursor.execute(
                "SELECT AVG(CAST(DATEDIFF(SECOND, created_at, resolved_at) AS FLOAT) / 3600) "
                "FROM dbo.incidents WHERE status IN ('Resolved', 'Closed') "
                "AND resolved_at IS NOT NULL"
            )
            avg_resolution_row = cursor.fetchone()

            cursor.execute(
                "SELECT severity, AVG(CAST(DATEDIFF(SECOND, created_at, resolved_at) AS FLOAT) / 3600) "
                "FROM dbo.incidents WHERE status IN ('Resolved', 'Closed') "
                "AND resolved_at IS NOT NULL GROUP BY severity"
            )
            resolution_rows = cursor.fetchall()

            cursor.execute(
                "SELECT CAST(created_at AS DATE), COUNT(*) FROM dbo.incidents "
                "WHERE created_at >= DATEADD(DAY, -14, CAST(GETDATE() AS DATE)) "
                "GROUP BY CAST(created_at AS DATE) ORDER BY CAST(created_at AS DATE) ASC"
            )
            daily_rows = cursor.fetchall()

            cursor.execute(
                "SELECT COALESCE(assigned_to, 'Unassigned'), COUNT(*) FROM dbo.incidents "
                "WHERE status IN ('Open', 'Investigating') GROUP BY assigned_to ORDER BY COUNT(*) DESC"
            )
            assignment_rows = cursor.fetchall()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to retrieve analytics") from exc

    totals = {
        "total_incidents": totals_row[0] or 0,
        "open_count": totals_row[1] or 0,
        "investigating_count": totals_row[2] or 0,
        "resolved_count": totals_row[3] or 0,
        "closed_count": totals_row[4] or 0,
    }
    avg_resolution = avg_resolution_row[0] or 0
    return {
        "success": True,
        "data": {
            **totals,
            "by_severity": {
                severity: severity_counts.get(severity, 0)
                for severity in ANALYTICS_SEVERITIES
            },
            "by_status": {
                incident_status: status_counts.get(incident_status, 0)
                for incident_status in ANALYTICS_STATUSES
            },
            "avg_resolution_time_hours": round(avg_resolution, 1),
            "avg_resolution_time_by_severity": {
                severity: round(
                    next((row[1] for row in resolution_rows if row[0] == severity), 0) or 0,
                    1,
                )
                for severity in ANALYTICS_SEVERITIES
            },
            "incidents_per_day_last_14_days": [
                {"date": str(row[0]), "count": row[1]} for row in daily_rows
            ],
            "open_by_assigned_to": {str(row[0]): row[1] for row in assignment_rows},
        },
    }
