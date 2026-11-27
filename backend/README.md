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
| `GET /api/feedback`, `GET /api/feedback/summary` | same paths | Admin only; `rating` and `limit` query parameters are forwarded |
| `POST /api/workspaces`, `DELETE /api/workspaces/:id` | same paths | Admin only |
| `GET/POST /api/users`, `PUT /api/users/:name/workspaces`, `PUT /api/users/:name/password`, `DELETE /api/users/:name` | same paths | Admin only |

Errors from the AI service keep their status code (401, 403, 404, 429, 400...). A 204 (deletes, password reset) is passed through as 204. If the AI service is down you get 503; if it takes longer than `AI_TIMEOUT_MS` (default 60000) you get 504. Path segments from the browser are re-encoded before they are forwarded, so a crafted name cannot reach a different AI service route.

## Tests

```bash
npm test      # 14 tests, Node's built-in runner, no extra packages
```

They run the real Express app against a stub AI service and check header forwarding, status-code and 204 pass-through, 503/504 handling, upload validation, the admin routes and path-segment encoding.

There is no database in this backend.
