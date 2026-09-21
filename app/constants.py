from enum import Enum


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class IncidentStatus(str, Enum):
    OPEN = "Open"
    INVESTIGATING = "Investigating"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


ALLOWED_TRANSITIONS = {
    IncidentStatus.OPEN: {IncidentStatus.INVESTIGATING},
    IncidentStatus.INVESTIGATING: {IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: {IncidentStatus.CLOSED},
    IncidentStatus.CLOSED: set(),
}

INCIDENT_COLUMNS = (
    "id, title, description, severity, status, reported_by, assigned_to, "
    "created_at, updated_at, resolved_at"
)

ANALYTICS_STATUSES = ["Open", "Investigating", "Resolved", "Closed"]
ANALYTICS_SEVERITIES = ["Critical", "High", "Medium", "Low"]
