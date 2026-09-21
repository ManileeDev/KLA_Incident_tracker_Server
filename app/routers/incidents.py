from enum import Enum
from typing import Optional

import pyodbc
from fastapi import APIRouter, HTTPException, Query, status

from ..constants import ALLOWED_TRANSITIONS, INCIDENT_COLUMNS, IncidentStatus, Severity
from ..database import get_database_connection
from ..schemas import IncidentCreate, IncidentUpdate, StatusUpdate
from ..serializers import incident_from_row

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_incident(incident: IncidentCreate):
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.incidents (title, description, severity, status, reported_by)
                OUTPUT INSERTED.id, INSERTED.title, INSERTED.description,
                       INSERTED.severity, INSERTED.status, INSERTED.reported_by,
                       INSERTED.assigned_to, INSERTED.created_at,
                       INSERTED.updated_at, INSERTED.resolved_at
                VALUES (?, ?, ?, 'Open', ?)
                """,
                incident.title,
                incident.description,
                incident.severity.value,
                incident.reported_by,
            )
            row = cursor.fetchone()
            conn.commit()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to create incident") from exc

    return {"success": True, "data": incident_from_row(row)}


@router.get("")
def list_incidents(
    status_filter: Optional[IncidentStatus] = Query(None, alias="status"),
    severity: Optional[Severity] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|severity)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    sort_expression = {
        "created_at": "created_at",
        "severity": "CASE severity WHEN 'Critical' THEN 4 WHEN 'High' THEN 3 "
        "WHEN 'Medium' THEN 2 WHEN 'Low' THEN 1 END",
    }[sort_by]
    direction = "ASC" if order == "asc" else "DESC"
    filters = []
    parameters = []
    if status_filter is not None:
        filters.append("status = ?")
        parameters.append(status_filter.value)
    if severity is not None:
        filters.append("severity = ?")
        parameters.append(severity.value)
    if assigned_to is not None:
        filters.append("assigned_to = ?")
        parameters.append(assigned_to)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (page - 1) * page_size
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) FROM dbo.incidents {where_clause}",
                *parameters,
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                f"SELECT {INCIDENT_COLUMNS} FROM dbo.incidents {where_clause} "
                f"ORDER BY {sort_expression} {direction}, id DESC "
                "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                *parameters,
                offset,
                page_size,
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to list incidents") from exc

    return {
        "success": True,
        "data": [incident_from_row(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{incident_id}/audit")
def get_incident_audit(incident_id: int):
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM dbo.incidents WHERE id = ?", incident_id)
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Incident not found")
            cursor.execute(
                "SELECT id, incident_id, from_status, to_status, changed_by, changed_at "
                "FROM dbo.incident_audit_log WHERE incident_id = ? ORDER BY changed_at DESC, id DESC",
                incident_id,
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to retrieve incident audit") from exc

    return {
        "success": True,
        "data": [
            {
                "id": row[0],
                "incident_id": row[1],
                "from_status": row[2],
                "to_status": row[3],
                "changed_by": row[4].replace("system (description)", "system").replace("system (assignee)", "system"),
                "changed_at": row[5],
                "activity_type": (
                    "description_updated" if row[4] == "system (description)"
                    else "assignee_updated" if row[4] == "system (assignee)"
                    else "status_changed"
                ),
            }
            for row in rows
        ],
    }


@router.get("/{incident_id}")
def get_incident(incident_id: int):
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {INCIDENT_COLUMNS} FROM dbo.incidents WHERE id = ?",
                incident_id,
            )
            row = cursor.fetchone()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to retrieve incident") from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"success": True, "data": incident_from_row(row)}


@router.put("/{incident_id}")
def update_incident(incident_id: int, incident: IncidentUpdate):
    values = incident.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=400, detail="At least one field is required")

    assignments = []
    parameters = []
    for field in ("title", "description", "severity", "reported_by", "assigned_to"):
        if field in values:
            assignments.append(f"{field} = ?")
            value = values[field]
            parameters.append(value.value if isinstance(value, Enum) else value)
    assignments.append("updated_at = SYSUTCDATETIME()")
    parameters.append(incident_id)

    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            current_status = None
            if "description" in values or "assigned_to" in values:
                cursor.execute("SELECT status FROM dbo.incidents WHERE id = ?", incident_id)
                status_row = cursor.fetchone()
                if status_row is None:
                    raise HTTPException(status_code=404, detail="Incident not found")
                current_status = status_row[0]
            cursor.execute(
                f"UPDATE dbo.incidents SET {', '.join(assignments)} "
                f"OUTPUT INSERTED.{INCIDENT_COLUMNS.replace(', ', ', INSERTED.') } "
                "WHERE id = ?",
                *parameters,
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Incident not found")
            if current_status is not None:
                cursor.execute(
                    "INSERT INTO dbo.incident_audit_log "
                    "(incident_id, from_status, to_status, changed_by) VALUES (?, ?, ?, ?)",
                    incident_id,
                    current_status,
                    current_status,
                    "system (description)" if "description" in values else "system (assignee)",
                )
            conn.commit()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to update incident") from exc
    return {"success": True, "data": incident_from_row(row)}


@router.patch("/{incident_id}/status")
def transition_incident_status(incident_id: int, update: StatusUpdate):
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM dbo.incidents WHERE id = ?", incident_id)
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Incident not found")

            current_status = IncidentStatus(row[0])
            if update.status not in ALLOWED_TRANSITIONS[current_status]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid transition: {current_status.value} -> {update.status.value}",
                )

            cursor.execute(
                "UPDATE dbo.incidents SET status = ?, updated_at = SYSUTCDATETIME(), "
                "resolved_at = CASE WHEN ? = 'Resolved' THEN SYSUTCDATETIME() "
                "ELSE resolved_at END WHERE id = ?",
                update.status.value,
                update.status.value,
                incident_id,
            )
            cursor.execute(
                "INSERT INTO dbo.incident_audit_log "
                "(incident_id, from_status, to_status, changed_by) VALUES (?, ?, ?, ?)",
                incident_id,
                current_status.value,
                update.status.value,
                update.changed_by,
            )
            conn.commit()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to transition incident status") from exc

    return {"success": True, "message": f"Status updated to {update.status.value}"}


@router.delete("/{incident_id}")
def delete_incident(incident_id: int):
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dbo.incidents WHERE id = ?", incident_id)
            if cursor.rowcount == 0:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Incident not found")
            conn.commit()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to delete incident") from exc
    return {"success": True, "message": "Incident deleted"}
