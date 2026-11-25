"""Synthetic company data for the enterprise MCP tools (no real people)."""

EMPLOYEES = [
    {"name": "Asha Verma", "email": "asha.verma@example.com", "title": "HR Manager", "department": "HR", "manager": "Rohan Mehta"},
    {"name": "Rohan Mehta", "email": "rohan.mehta@example.com", "title": "Head of People", "department": "HR", "manager": None},
    {"name": "Priya Nair", "email": "priya.nair@example.com", "title": "IT Support Lead", "department": "IT", "manager": "Karan Shah"},
    {"name": "Karan Shah", "email": "karan.shah@example.com", "title": "IT Director", "department": "IT", "manager": None},
    {"name": "Meera Iyer", "email": "meera.iyer@example.com", "title": "Security Engineer", "department": "IT", "manager": "Karan Shah"},
    {"name": "Dev Patel", "email": "dev.patel@example.com", "title": "Finance Analyst", "department": "Finance", "manager": "Sana Khan"},
    {"name": "Sana Khan", "email": "sana.khan@example.com", "title": "Finance Controller", "department": "Finance", "manager": None},
]

TICKETS = [
    {"ticket_id": "IT-1001", "title": "VPN not connecting from home", "status": "open", "priority": "high", "assignee": "Priya Nair", "department": "IT", "description": "User cannot connect to the company VPN after the latest update."},
    {"ticket_id": "IT-1002", "title": "Request new laptop", "status": "in_progress", "priority": "medium", "assignee": "Priya Nair", "department": "IT", "description": "New joiner needs a laptop and standard software bundle."},
    {"ticket_id": "IT-1003", "title": "Suspicious login alert", "status": "resolved", "priority": "high", "assignee": "Meera Iyer", "department": "IT", "description": "Alert reviewed; password reset and MFA re-enrolled."},
    {"ticket_id": "HR-2001", "title": "Update bank details for payroll", "status": "open", "priority": "medium", "assignee": "Asha Verma", "department": "HR", "description": "Employee asks to change salary account details."},
    {"ticket_id": "HR-2002", "title": "Parental leave question", "status": "closed", "priority": "low", "assignee": "Asha Verma", "department": "HR", "description": "Clarified leave entitlement per the leave policy document."},
    {"ticket_id": "FIN-3001", "title": "Expense reimbursement delayed", "status": "in_progress", "priority": "medium", "assignee": "Dev Patel", "department": "Finance", "description": "Travel claim submitted three weeks ago is still pending."},
]
