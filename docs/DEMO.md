# KnowledgeAgent - Demo script (about 12 minutes)

Two walkthroughs on the same data: an **employee** (alice, HR only) and an **admin**. The demo documents are fictional ("Example Corp") and live in `docs/demo-data/`.

> **Before you present:** the document facts below are fixed, but the LLM's wording changes from run to run. Rehearse the whole script once with your own API key and adjust what you say to what you actually see.

## 1. Setup (once, about 10 minutes)

1. Follow **Quick start** in the [README](../README.md): start the AI service, backend and frontend.
2. Load the demo data: `cd ai-service && python scripts/seed_demo.py --admin-password <ADMIN_PASSWORD>`. **Write down the alice and bob passwords it prints**; they are shown once.
3. Open `http://localhost:5173`.

**Five minutes before:** all three services are running; sign in as alice and as the admin once; ask one question to warm the model up; keep `ai-service/storage/outbox.jsonl` open in an editor (it may not exist yet).

## 2. Employee walkthrough (sign in as `alice`)

| # | Do | What to see and say |
| --- | --- | --- |
| 1 | Sign in as alice. | The workspace selector lists only **HR**. No upload button. "Access is decided by the AI service, not the UI." |
| 2 | Ask: *How many days of annual leave do I get, and how many can I carry over?* | Expect **20 days**, **5 carried over**, expiring **31 March**. Point at the source line (`hr-leave-policy.pdf`, page 1), the confidence badge and the expandable snippet. "The badge shows how closely the passage matches the question, not whether the answer is right, so you check the page." |
| 3 | Click thumbs-up. | "Thanks for the feedback". Click thumbs-down on another answer to show the optional comment box. |
| 4 | Ask: *How do I set up the VPN?* | The HR workspace has no VPN content, so expect a refusal or a low-match warning, never the IT guide. "Alice cannot reach the IT workspace's documents." |
| 5 | Ask: *Who is assigned to ticket HR-2001 and what is their email?* | Open **Tool activity**: `lookup_ticket_tool`, then `find_employee_tool`. Expect **Asha Verma**, asha.verma@example.com. "These tools run on an MCP server." |
| 6 | Ask: *What is the status of ticket IT-1001?* | Alice only has the HR workspace, so the result is filtered on the server and the agent reports that the ticket was not found. "A ticket from another department looks exactly like one that does not exist." |
| 7 | Ask: *Send Asha a notification about HR-2001.* | The agent cannot send it: `send_notification` is not offered to employees. "Dangerous tools are removed from the model's tool list, and blocked again at execution." |
| 8 | Sign out. | Back to the sign-in page; chat state is cleared. |

## 3. Admin walkthrough (sign in with the admin account)

| # | Do | What to see and say |
| --- | --- | --- |
| 1 | Sign in as admin. | Selector shows **HR and IT**. The **Upload document** button is visible. |
| 2 | Switch to **IT**. Ask: *What are the password rules and how often are passwords reviewed?* | Expect **at least 12 characters**, reviewed every **180 days**, with an `it-vpn-and-devices.pdf` citation. |
| 3 | Ask: *Notify Priya Nair that ticket IT-1001 needs an update.* | Tool activity shows `find_employee_tool` and `send_notification_tool` (status "queued (mock - no real email sent)"). Show the new line in `outbox.jsonl`. "It is a mock, so nothing is emailed." |
| 4 | Click **Admin**, open the **Feedback** tab. | Totals and satisfaction from the ratings alice gave, filter by thumbs down, and use **Show answer** to see the rated question, comment and answer. "Admins review quality; employees cannot." |
| 5 | **Workspaces** tab: create `Finance`. Close the panel. | The workspace selector now includes Finance. Empty workspaces can be deleted; the default one and ones with documents cannot. |
| 6 | **Users** tab: add `carol` (employee, HR). Open a private window and sign in as carol. | Carol sees only HR. Use **Access** to grant her a second workspace. |
| 7 | Still on **Users**: **Reset password** for carol. In carol's window, ask any question. | Carol is signed out with a "session expired" notice, because a reset revokes her existing sessions. The old password no longer works. |

## 4. Optional extras (2 minutes)

- Wrong password on the sign-in page: "Invalid username or password."
- Session expiry: set `TOKEN_EXPIRE_MINUTES=1` in `ai-service/.env`, restart, sign in, wait, ask a question; you are returned to sign-in with a "session expired" notice.
- Stop the AI service and ask a question: the UI shows a generic error, not server details.

## 5. Questions you should be ready for

| Question | Honest answer |
| --- | --- |
| Why does the browser not call the AI service directly? | One entry point for web concerns, and the AI service stays the single place that decides access. Node only forwards the token. |
| Is the confidence score the accuracy of the answer? | No. It is the similarity between the question and the best retrieved passage. A confident match can still produce a wrong answer; that is why sources are shown. |
| How secure is it? | Hashed passwords, signed expiring tokens, per-request access checks, 404 for forbidden resources, a 15-minute lockout after 5 wrong passwords, and admin password resets that revoke old sessions. Missing: a per-IP rate limit, self-service or email password reset, revoking a single token, HTTPS. The lockout is in memory and can be used to lock a known username out for a while. |
| Can an employee see another team's tickets? | No. Ticket results are filtered on the server by matching the ticket's department to the employee's workspace ids. The employee directory is open to every signed-in user on purpose, and the data is synthetic. |
| Where is the data? | Local files under `ai-service/storage/`; no database. Answers are stored so feedback can be tied to them. |
| What did you build versus reuse? | The RAG pipeline, agent loop and MCP client came from the DocuMind AI reference project. Workspaces, enterprise MCP tools, login and roles, citations with confidence, feedback and the new UI were added on top. |

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| Login returns 503 | `AUTH_SECRET_KEY` in `ai-service/.env` is missing or shorter than 32 characters. |
| Cannot sign in as admin | `ADMIN_USERNAME` / `ADMIN_PASSWORD` must be set *before* the first login; the admin is only created while no users exist. Delete `ai-service/storage/users.json` to start over. |
| Upload or chat fails with an LLM or embedding error | Check `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, and `EMBEDDING_PROVIDER` (`local` needs `pip install -r requirements-local-embeddings.txt`). |
| Tool calls fail ("python not found" or MCP errors) | Start `uvicorn` from the activated virtual environment inside `ai-service/`; the MCP server is launched with that `python`. |
| Frontend shows network errors | Backend must be on port 3000 and `CORS_ORIGINS` must include `http://localhost:5173`. |
| 401 on everything right after changing `AUTH_SECRET_KEY` | Old tokens no longer verify; sign in again. |
| "Too many failed sign-in attempts" | The username is locked for 15 minutes after 5 wrong passwords. Wait, or restart the AI service (the lock is in memory). |
| "Can't reach the server" after a reload | The backend or AI service is down; start it and press **Try again** (you stay signed in). |

## 7. Screenshots for the README

Save these in `docs/screenshots/` and uncomment the image lines in the README: `01-login.png`, `02-answer-citations.png` (answer, confidence badge, expanded snippet), `03-tool-activity.png`, `04-feedback-thumbs-down.png`, `05-admin-panel-users.png`, `06-admin-panel-feedback.png`, `07-mobile-view.png`, `08-dark-mode.png`.
