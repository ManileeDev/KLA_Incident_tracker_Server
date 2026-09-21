import hashlib

import pyodbc
from fastapi import APIRouter, HTTPException

from ..database import get_database_connection
from ..schemas import SignInRequest, SignUpRequest
from ..serializers import user_from_row

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/users")
def list_users():
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, display_name FROM dbo.users "
                "WHERE is_active = 1 ORDER BY display_name"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to retrieve users") from exc
    return {"success": True, "data": [user_from_row(row) for row in rows]}


@router.post("/signin")
def sign_in(request: SignInRequest):
    password_hash = hashlib.sha256(request.password.encode("utf-8")).hexdigest()
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, display_name FROM dbo.users "
                "WHERE username = ? AND password_hash = ? AND is_active = 1",
                request.username.strip(),
                password_hash,
            )
            row = cursor.fetchone()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to sign in") from exc
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"success": True, "data": user_from_row(row)}


@router.post("/signup", status_code=201)
def sign_up(request: SignUpRequest):
    password_hash = hashlib.sha256(request.password.encode("utf-8")).hexdigest()
    try:
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM dbo.users WHERE username = ?",
                request.username,
            )
            if cursor.fetchone() is not None:
                raise HTTPException(status_code=409, detail="Username already exists")

            cursor.execute(
                "INSERT INTO dbo.users (username, display_name, password_hash) "
                "OUTPUT INSERTED.id, INSERTED.username, INSERTED.display_name "
                "VALUES (?, ?, ?)",
                request.username,
                request.display_name,
                password_hash,
            )
            row = cursor.fetchone()
            conn.commit()
        finally:
            conn.close()
    except pyodbc.Error as exc:
        raise HTTPException(status_code=500, detail="Unable to create account") from exc

    return {"success": True, "data": user_from_row(row)}
