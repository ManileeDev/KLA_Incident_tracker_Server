def user_from_row(row):
    return {"id": row[0], "username": row[1], "display_name": row[2]}


def incident_from_row(row):
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "severity": row[3],
        "status": row[4],
        "reported_by": row[5],
        "assigned_to": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        "resolved_at": row[9],
    }
