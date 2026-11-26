# KnowledgeAgent - Architecture

## Request flow

```
React (5173) --/api/* + Bearer token--> Node/Express (3000) --same token--> FastAPI (8000)
                                                                              |
                          login, roles, workspaces <--------------------------+
                          FAISS retrieval + LLM    <--------------------------+
                          MCP server (stdio)       <--------------------------+
```

**Why three services.** Node is the single entry point for the browser and keeps web concerns (upload limits, CORS, error mapping) in one place. FastAPI owns everything AI-related and every security decision. Node deliberately does not decide who may see what; it forwards the `Authorization` header and passes the AI service's status codes through. The result is one place for access control instead of two that can disagree.

## How a question is answered

1. The browser sends `{messages, document_ids, workspace_id}` to `POST /api/ai/chat` with the bearer token.
2. The AI service identifies the user, checks the workspace or documents against that user's access (404 if not allowed) and resolves the list of document ids.
3. The agent loop gives the LLM the tools its role may use and runs the tool calls it asks for. A tool call on a document outside the selected set is refused, and the document list is filtered to the selected set.
4. Document search runs through the MCP server: the query is embedded, FAISS returns the closest chunks, and each hit keeps document, page, text and distance.
5. The answer is returned with citations (best match first, one per page), a confidence derived from the FAISS distance, tool traces, and an `answer_id` for feedback.

## Storage (all local files under `ai-service/storage/`)

| Path | Content |
| --- | --- |
| `vector_stores/<document_id>/` | FAISS index and `metadata.json` (name, type, workspace) |
| `workspaces.json`, `users.json` | Workspaces; users with scrypt password hashes and workspace access |
| `answers/`, `feedback/` | One JSON file per answer and per rating |
| `outbox.jsonl` | Mock notifications |

There is no database. Users, answers and ratings are written atomically (temp file, then rename); `workspaces.json` is a plain write. That is enough for a single-process demo but not for several instances or heavy concurrent use.

## Access control model

- Two roles. Admins reach every workspace; employees reach the workspaces listed on their user record.
- Role and workspace access are read from the user store on every request, never trusted from the token.
- Resources the caller may not access return 404, the same as missing ones, so names and ids cannot be probed.
- Tools: `send_notification_tool` is admin-only (removed from the model's tool list and blocked at execution). Ticket and directory tools are not scoped by workspace (see README, known limits).

## Confidence

FAISS returns a squared L2 distance. For unit-length embeddings this equals `2 - 2*cosine`, so `1 - distance/2` is the cosine similarity between question and passage. It measures retrieval match, not answer correctness. Thresholds: high >= 0.60, medium >= 0.40.

## Deployment

Not deployed. Everything runs locally. A free-tier deployment would need a persistent disk for `storage/` (or a move to a real database and object storage), HTTPS, rate limiting and a proper secret store; none of that exists yet.
