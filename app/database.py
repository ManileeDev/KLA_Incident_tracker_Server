import pyodbc
from fastapi import HTTPException

from .config import get_database_url


def get_database_connection():
    try:
        return pyodbc.connect(get_database_url())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
