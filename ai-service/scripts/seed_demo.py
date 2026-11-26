"""Set up the KnowledgeAgent demo: workspaces, two employees and sample documents.

Needs the AI service running with login enabled (see README) and uses only the
standard library. Run from the ai-service folder:

    python scripts/seed_demo.py

It is safe to run again: existing workspaces and users are reused and documents
that are already uploaded are skipped. A user's password is only set when the
user is created; if you re-run it, existing users keep their old password.
"""

import argparse
import json
import mimetypes
import os
import secrets
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEMO_DATA = Path(__file__).resolve().parents[2] / "docs" / "demo-data"

WORKSPACES = [
    {"name": "HR", "id": "hr", "description": "Leave and payroll policies"},
    {"name": "IT", "id": "it", "description": "VPN, devices and security"},
]
USERS = [
    {"username": "alice", "workspace": "hr"},
    {"username": "bob", "workspace": "it"},
]
DOCUMENTS = [
    {"file": "hr-leave-policy.pdf", "workspace": "hr"},
    {"file": "it-vpn-and-devices.pdf", "workspace": "it"},
]


class SeedError(Exception):
    pass


def call(base, method, path, token=None, body=None, raw=None, content_type=None, ok=()):
    """Send one request. Returns (status, parsed JSON). Statuses in `ok` are not errors."""
    headers = {}
    data = raw

    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type

    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode()
    except urllib.error.URLError as error:
        raise SeedError(f"Cannot reach the AI service at {base}: {error.reason}") from None

    try:
        payload = json.loads(text) if text else None
    except ValueError:
        payload = text

    if status >= 400 and status not in ok:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise SeedError(f"{method} {path} failed ({status}): {detail}")

    return status, payload


def multipart(fields, file_field, file_path):
    boundary = uuid.uuid4().hex
    parts = []

    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\nContent-Type: {mime}\r\n\r\n'
        ).encode()
    )
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())

    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="AI service URL")
    parser.add_argument("--admin-user", default=os.environ.get("ADMIN_USERNAME", "admin"))
    parser.add_argument(
        "--admin-password",
        default=os.environ.get("ADMIN_PASSWORD"),
        help="or set ADMIN_PASSWORD",
    )
    args = parser.parse_args()
    base = args.api.rstrip("/")

    if not args.admin_password:
        raise SeedError("Give the admin password with --admin-password or ADMIN_PASSWORD.")

    _, login = call(
        base, "POST", "/auth/login",
        body={"username": args.admin_user, "password": args.admin_password},
    )
    token = login["access_token"]
    print(f"Signed in as {args.admin_user}")

    for workspace in WORKSPACES:
        status, _ = call(
            base, "POST", "/workspaces", token,
            body={"name": workspace["name"], "description": workspace["description"]},
            ok=(409,),
        )
        print(f"Workspace {workspace['id']}: {'already exists' if status == 409 else 'created'}")

    shared_password = os.environ.get("DEMO_USER_PASSWORD")
    created = {}

    for user in USERS:
        password = shared_password or secrets.token_urlsafe(12)
        status, _ = call(
            base, "POST", "/users", token,
            body={
                "username": user["username"],
                "password": password,
                "role": "employee",
                "workspaces": [user["workspace"]],
            },
            ok=(409,),
        )
        if status == 409:
            call(
                base, "PUT", f"/users/{user['username']}/workspaces", token,
                body={"workspaces": [user["workspace"]]},
            )
            print(f"User {user['username']}: already exists (password unchanged)")
        else:
            created[user["username"]] = password
            print(f"User {user['username']}: created (employee, workspace {user['workspace']})")

    for item in DOCUMENTS:
        path = DEMO_DATA / item["file"]
        if not path.exists():
            raise SeedError(f"Demo file not found: {path}")

        _, existing = call(base, "GET", f"/workspaces/{item['workspace']}/documents", token)
        if any(doc["document_name"] == item["file"] for doc in existing):
            print(f"Document {item['file']}: already uploaded")
            continue

        body, content_type = multipart({"workspace_id": item["workspace"]}, "file", path)
        print(f"Uploading {item['file']} (this indexes it, which can take a moment)...")
        call(base, "POST", "/documents/upload", token, raw=body, content_type=content_type)
        print(f"Document {item['file']}: uploaded to {item['workspace']}")

    print("\nDemo is ready.")
    if created:
        print("New employee passwords (shown once, save them now):")
        for username, password in created.items():
            print(f"  {username}: {password}")


if __name__ == "__main__":
    try:
        main()
    except SeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
