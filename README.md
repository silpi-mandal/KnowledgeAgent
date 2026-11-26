# KnowledgeAgent

An MCP-powered enterprise knowledge assistant. Employees sign in, pick a **workspace** (HR, IT, ...), and ask questions in plain language. An AI agent answers from the workspace's documents, shows **where** each answer came from, and can call company tools (ticket lookup, employee directory) through the **Model Context Protocol (MCP)**. Admins control who can see which workspace.

Built on the DocuMind AI codebase as a reference, then extended with workspaces, MCP tools, login and roles, citations with confidence, feedback and a new UI.

## What it does

| Feature | Details |
| --- | --- |
| Document Q&A (RAG) | Upload PDF, CSV, XLSX or XLS. Text is chunked, embedded and stored in FAISS; the agent retrieves the closest passages and answers from them. |
| Workspaces | Documents are grouped (HR, IT, Policies...). A chat searches one workspace or one document. |
| MCP tools | The agent calls tools served by an MCP server: document search and info, `lookup_ticket`, `search_tickets`, `find_employee`, `send_notification` (mock). |
| Login and roles | `admin` and `employee`. Employees only see workspaces assigned to them. Notifications are admin-only. |
| Citations and confidence | Every answer lists document, page, an expandable snippet and a match score. |
| Feedback | Thumbs up/down with an optional comment; admins can read ratings and a summary. |
| Tool activity | Each answer can show which tools the agent called, their arguments and result. |

> **About the confidence score:** it is the cosine similarity between your question and the retrieved passage (0-1; high >= 0.60, medium >= 0.40). It tells you how closely a passage *matches the question*. It does **not** prove the answer is correct, so check the cited page. The cut-offs were chosen for normalized embeddings and should be re-checked if you change the embedding model.

<!-- Add your screenshots to docs/screenshots/ and uncomment:
![Sign in](docs/screenshots/01-login.png)
![Answer with citations and confidence](docs/screenshots/02-answer-citations.png)
![Tool activity](docs/screenshots/03-tool-activity.png)
-->

## Architecture

```
Browser (React + Vite)                    :5173
   |  /api/*  + Authorization: Bearer <token>
   v
Node.js / Express gateway                 :3000   validates uploads, forwards the token, maps errors
   |  same token
   v
FastAPI AI service                        :8000   login, roles, workspaces, RAG, agent, feedback
   |-- FAISS indexes + JSON files          (ai-service/storage/)
   |-- LLM via any OpenAI-compatible API   (Gemini free tier by default)
   '-- MCP server (stdio subprocess)       documents + enterprise tools
```

The browser never calls the AI service directly. The Node layer only forwards the `Authorization` header; **the AI service makes every permission decision** (who you are, which workspaces you may use, which tools the model may run), so there is one place to get access control right. More detail: [`docs/architecture.md`](docs/architecture.md).

## Quick start

Prerequisites: Python 3.11+, Node.js LTS, and a free [Gemini API key](https://aistudio.google.com) (or another OpenAI-compatible provider).

### 1. AI service (port 8000)

```bash
cd ai-service
python -m venv .venv
.venv\Scripts\activate            # Windows   (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
pip install -r requirements-local-embeddings.txt   # free offline embeddings (large download)
copy .env.example .env            # Windows   (cp on macOS/Linux)
```

Edit `ai-service/.env`:

- `LLM_API_KEY` - your key. `LLM_MODEL` / `LLM_BASE_URL` are pre-filled for Gemini.
- `EMBEDDING_PROVIDER=local` (free, offline) - or `openai` to use the remote endpoint.
- `AUTH_SECRET_KEY` - 32+ random characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `ADMIN_USERNAME` and `ADMIN_PASSWORD` (8+ characters) - the first admin is created from these on first login.

```bash
uvicorn app.main:app --reload     # http://localhost:8000  (API docs at /docs)
```

> Start it from the activated virtual environment inside `ai-service/`: the MCP server is launched as `python -m documind_mcp.server`, so `python` must be that environment's Python.

### 2. Backend (port 3000)

```bash
cd backend
npm install
copy .env.example .env
npm run dev
```

### 3. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev                       # open http://localhost:5173
```

### 4. Load the demo data (optional but recommended)

With the AI service running:

```bash
cd ai-service
python scripts/seed_demo.py --admin-password <your ADMIN_PASSWORD>
```

This creates the `hr` and `it` workspaces, two employees (`alice` -> HR, `bob` -> IT) with generated passwords (printed once), and uploads two synthetic documents from `docs/demo-data/`. It is safe to re-run. Then follow [`docs/DEMO.md`](docs/DEMO.md).

## Roles

| | Admin | Employee |
| --- | --- | --- |
| See and chat with workspaces | all | only assigned workspaces |
| Upload documents, create/delete workspaces | yes | no |
| Manage users and workspace access | yes | no |
| Read feedback and summary | yes | no |
| `send_notification` tool | yes | hidden from the model and blocked |

There is no admin screen for creating users or workspaces. Use `scripts/seed_demo.py` or the AI service's Swagger page (`http://localhost:8000/docs`, click **Authorize** and paste a token from `POST /auth/login`).

## API overview

The browser uses the Node routes listed in [`backend/README.md`](backend/README.md). The AI service exposes:

| Endpoint | Who | Purpose |
| --- | --- | --- |
| `GET /health` | public | Health check |
| `POST /auth/login`, `GET /auth/me` | all | Sign in, current user |
| `GET /workspaces`, `GET /workspaces/{id}/documents` | signed in | Only what you may access |
| `POST /workspaces`, `DELETE /workspaces/{id}` | admin | Create / delete (empty) workspace |
| `GET /documents?workspace_id=` | signed in | Document list |
| `POST /documents/upload` | admin | multipart `file` + `workspace_id` |
| `POST /agent/chat` | signed in | `{messages, document_ids, workspace_id}` -> answer, `sources[]`, `traces[]`, `answer_id`, `answer_confidence` |
| `GET /agent/tools` | signed in | Tools available to your role |
| `POST /feedback` | signed in | Rate an answer you received |
| `GET /feedback`, `GET /feedback/summary` | admin | Read ratings |
| `GET/POST /users`, `PUT /users/{name}/workspaces`, `DELETE /users/{name}` | admin | User management |

A workspace, document or answer you are not allowed to touch returns **404**, the same as one that does not exist.

## Testing

```bash
cd ai-service && pytest               # 147 tests: RAG, agent, MCP tools, auth, workspaces, feedback
cd frontend && npm run lint && npm run build
```

- The Python tests use fake embeddings and a mocked LLM, so they need no API key and no network. One group starts the real MCP server over stdio.
- The Node backend has no automated tests yet (`npm test` is a placeholder). It was checked by hand against the real AI service.
- Chat answers with a real LLM have to be checked manually; rehearse the demo once with your own key.

## Security notes and known limits

- Passwords are stored as salted scrypt hashes; tokens are signed, expire after `TOKEN_EXPIRE_MINUTES` (default 60), and role and access are re-checked on every request, so deleting a user takes effect immediately.
- The token lives in browser `sessionStorage` (gone when the tab closes). A script injected into the page could read it; the UI never renders server text as HTML.
- `AUTH_ENABLED=false` switches login off and makes everyone an admin. Local development only.
- **Not done:** login rate limiting (AI service and Node), password reset, early token revocation, HTTPS (use it if you ever deploy), an admin UI.
- **Tool scope:** the ticket and employee-directory tools are *not* scoped by workspace, so any signed-in employee can ask about any ticket or person. The data is synthetic; add scoping before using real data.
- `send_notification` is a **mock**: it validates the recipient and appends to `ai-service/storage/outbox.jsonl`. No email is sent.
- To support feedback, each question and answer is stored in `ai-service/storage/answers/` (readable via the API by admins only). Delete that folder if you do not want it kept.
- Uploaded content and answers are processed by the LLM provider you configure. Do not upload confidential files to a free-tier provider.
- Retrieved document text is untrusted input to the model; prompt injection inside a document is a general RAG risk this project does not fully defend against.

## Project structure

```
KnowledgeAgent/
├── frontend/            React + Vite + Tailwind UI
├── backend/             Node.js / Express gateway
├── ai-service/
│   ├── app/             FastAPI app: routes, services (RAG, agent, auth, feedback), models
│   ├── documind_mcp/    MCP server (document + enterprise tools, synthetic data)
│   ├── scripts/         seed_demo.py, manual MCP smoke scripts
│   └── tests/
├── docs/                architecture, demo script, demo documents
├── docker/              placeholder (no containers yet)
└── .github/workflows/   placeholder (no CI yet)
```

## License

MIT - see [LICENSE](LICENSE).
