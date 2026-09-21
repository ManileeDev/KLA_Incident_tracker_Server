import pyodbc
from fastapi import APIRouter

from ..config import get_database_url

router = APIRouter(tags=["diagnostics"])


@router.get("/test-db")
def test_database():
    try:
        conn = pyodbc.connect(get_database_url())
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT TOP 5 id, title, severity, status, reported_by "
                "FROM dbo.incidents ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        incidents = [
            {
                "id": row[0],
                "title": row[1],
                "severity": row[2],
                "status": row[3],
                "reported_by": row[4],
            }
            for row in rows
        ]
        return {
            "status": "success",
            "message": "Connected to database!",
            "count": len(incidents),
            "data": incidents,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
