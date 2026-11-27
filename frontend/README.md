# Frontend (React + Vite + Tailwind)

Sign-in page, workspace selector, document list, chat with citations, confidence badges, thumbs up/down feedback and a tool-activity view.

## Run

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (needs the backend on :3000)
npm run lint
npm run build
```

`VITE_API_BASE_URL` (default `http://localhost:3000/api`) points at the Node backend; see `.env.example`.

## How it behaves

- **Login:** the bearer token is kept in `sessionStorage` (cleared when the tab closes). A 401 on a signed-in request sends the user back to the sign-in page with a "session expired" notice. Signing out discards all chat state.
- **Roles:** the Upload button and the **Admin** button are shown to admins only. Employees see only the workspaces assigned to them.
- **Admin panel:** workspaces (create, delete empty ones), users (create, grant workspace access, reset password, delete) and feedback (summary, filter, rated question and answer). The server enforces admin-only access; hiding the button is only a convenience.
- **Connection problems:** if the server cannot be reached on reload, you stay signed in and see a "Can't reach the server" screen with **Try again** and **Sign out**. Only a rejected token ends the session.
- **Answers:** each source shows document, page, a confidence badge and an expandable snippet. The badge says how closely a passage matches the question; it does **not** mean the answer is correct.
- **Errors:** messages for 4xx responses are shown to the user; server (5xx) details never are.
