# Backend (Node.js / Express)

The only API the browser talks to. It is a thin gateway: it validates uploads, forwards the user's `Authorization` header to the FastAPI AI service, and returns the AI service's answers. **All permission decisions (login, roles, workspace access) are made by the AI service**, so there is one place to get them right.

## Run

```bash
cd backend
npm install
copy .env.example .env     # Windows   (cp on macOS/Linux)
npm run dev                # http://localhost:3000
```

## Routes

| Method & path | Forwards to (AI service) | Notes |
| --- | --- | --- |
| `GET /health` | - | Health check |
| `POST /api/auth/login` | `POST /auth/login` | Returns a bearer token |
| `GET /api/auth/me` | `GET /auth/me` | Current user and role |
| `GET /api/workspaces` | `GET /workspaces` | Only workspaces the user may access |
| `GET /api/documents?workspace_id=` | `GET /documents` | Filtered by access |
| `POST /api/documents/upload` | `POST /documents/upload` | multipart `file` + `workspace_id`; PDF/CSV/XLSX/XLS, max 10 MB; admin only |
| `POST /api/ai/chat` | `POST /agent/chat` | `{messages, document_ids, workspace_id}` |
| `POST /api/feedback` | `POST /feedback` | `{answer_id, rating, comment}` |

Errors from the AI service keep their status code (401, 403, 404, 400...). If the AI service is down you get 503; if it takes longer than 30 s you get 504.

## Not implemented here

Creating users or workspaces and reading feedback are admin tasks done directly on the AI service (`http://localhost:8000/docs`) or with `ai-service/scripts/seed_demo.py`. There is no database in this backend.
