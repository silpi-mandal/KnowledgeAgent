"""Pure functions behind the enterprise MCP tools (easy to unit test).

Data is synthetic. ``send_notification`` is a MOCK: it never sends real
email, it only appends a record to an outbox file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from documind_mcp.enterprise_data import EMPLOYEES, TICKETS

MAX_RESULTS = 20
MAX_SUBJECT = 150
MAX_MESSAGE = 2000


def lookup_ticket(ticket_id: str) -> dict:
    wanted = ticket_id.strip().upper()

    for ticket in TICKETS:
        if ticket["ticket_id"] == wanted:
            return dict(ticket)

    return {"error": "Ticket not found.", "ticket_id": ticket_id}


def search_tickets(
    status: str | None = None,
    assignee: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
) -> list[dict]:
    limit = max(1, min(limit, MAX_RESULTS))
    results = []

    for ticket in TICKETS:
        if status and ticket["status"] != status.strip().lower():
            continue
        if assignee and assignee.strip().lower() not in ticket["assignee"].lower():
            continue
        if keyword:
            text = f"{ticket['title']} {ticket['description']}".lower()
            if keyword.strip().lower() not in text:
                continue
        results.append(dict(ticket))

    return results[:limit]


def find_employee(
    query: str,
    department: str | None = None,
) -> list[dict]:
    needle = query.strip().lower()
    results = []

    for employee in EMPLOYEES:
        if department and employee["department"].lower() != department.strip().lower():
            continue

        haystack = f"{employee['name']} {employee['title']} {employee['email']}".lower()
        if needle and needle not in haystack:
            continue

        results.append(dict(employee))

    return results[:MAX_RESULTS]


def send_notification(
    recipient_email: str,
    subject: str,
    message: str,
    outbox_path: Path,
) -> dict:
    recipient = recipient_email.strip().lower()
    subject = subject.strip()
    message = message.strip()

    if not any(e["email"] == recipient for e in EMPLOYEES):
        return {"error": "Recipient is not in the employee directory."}
    if not subject or not message:
        return {"error": "Subject and message are required."}
    if len(subject) > MAX_SUBJECT or len(message) > MAX_MESSAGE:
        return {"error": "Subject or message is too long."}

    record = {
        "notification_id": str(uuid4()),
        "to": recipient,
        "subject": subject,
        "message": message,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }

    outbox_path.parent.mkdir(parents=True, exist_ok=True)
    with outbox_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    return {
        "status": "queued (mock - no real email sent)",
        "notification_id": record["notification_id"],
        "to": recipient,
    }
