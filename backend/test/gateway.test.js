// Gateway tests: run the real Express app against a stub "AI service".
// Run with `npm test` (Node's built-in test runner, no extra dependencies).
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");

let stub; // { server, requests, handler, url }
let gateway; // { server, url }

function startStub() {
    const state = { requests: [], handler: null };

    state.server = http.createServer((req, res) => {
        const chunks = [];

        req.on("data", (chunk) => chunks.push(chunk));
        req.on("end", () => {
            const record = {
                method: req.method,
                url: req.url,
                headers: req.headers,
                body: Buffer.concat(chunks).toString("utf8"),
            };

            state.requests.push(record);
            state.handler(record, res);
        });
    });

    return new Promise((resolve) =>
        state.server.listen(0, "127.0.0.1", () => {
            state.url = `http://127.0.0.1:${state.server.address().port}`;
            resolve(state);
        })
    );
}

function reply(res, status, body) {
    if (body === undefined) {
        res.writeHead(status).end();
        return;
    }

    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(body));
}

test.before(async () => {
    stub = await startStub();
    process.env.AI_SERVICE_URL = stub.url;
    process.env.AI_TIMEOUT_MS = "400";

    const app = require("../src/app");

    gateway = { server: http.createServer(app) };
    await new Promise((resolve) => gateway.server.listen(0, "127.0.0.1", resolve));
    gateway.url = `http://127.0.0.1:${gateway.server.address().port}`;
});

test.after(async () => {
    gateway.server.close();
    stub.server.close();
});

test.beforeEach(() => {
    stub.requests.length = 0;
    stub.handler = (req, res) => reply(res, 200, { ok: true });
});

const call = (path, options = {}) => fetch(`${gateway.url}${path}`, options);
const json = (body) => ({
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
});

test("health check answers without touching the AI service", async () => {
    const response = await call("/health");

    assert.equal(response.status, 200);
    assert.equal((await response.json()).server, "KnowledgeAgent");
    assert.equal(stub.requests.length, 0);
});

test("login forwards the credentials and returns the token", async () => {
    stub.handler = (req, res) => reply(res, 200, { access_token: "tok", token_type: "bearer", expires_in: 3600 });

    const response = await call("/api/auth/login", { method: "POST", ...json({ username: "a", password: "b" }) });

    assert.equal(response.status, 200);
    assert.equal((await response.json()).access_token, "tok");
    assert.deepEqual(JSON.parse(stub.requests[0].body), { username: "a", password: "b" });
    assert.equal(stub.requests[0].url, "/auth/login");
});

test("the Authorization header is forwarded; without one nothing is sent", async () => {
    await call("/api/workspaces", { headers: { Authorization: "Bearer abc" } });
    assert.equal(stub.requests[0].headers.authorization, "Bearer abc");

    await call("/api/workspaces");
    assert.equal(stub.requests[1].headers.authorization, undefined);
});

test("AI service errors keep their status code and detail", async () => {
    for (const [status, detail] of [[401, "Not authenticated."], [403, "Admin access required."], [404, "Workspace not found."], [429, "Too many failed sign-in attempts. Try again later."]]) {
        stub.handler = (req, res) => reply(res, status, { detail });

        const response = await call("/api/workspaces");
        const body = await response.json();

        assert.equal(response.status, status);
        assert.equal(body.error.detail, detail);
    }
});

test("503 when the AI service is unreachable", async () => {
    const saved = process.env.AI_SERVICE_URL;

    process.env.AI_SERVICE_URL = "http://127.0.0.1:1";
    const response = await call("/api/workspaces");
    process.env.AI_SERVICE_URL = saved;

    assert.equal(response.status, 503);
    assert.equal((await response.json()).message, "AI service is unavailable");
});

test("504 when the AI service is slower than AI_TIMEOUT_MS", async () => {
    stub.handler = (req, res) => setTimeout(() => reply(res, 200, { late: true }), 1500);

    const response = await call("/api/ai/chat", { method: "POST", ...json({ messages: [] }) });

    assert.equal(response.status, 504);
});

test("chat body and token are forwarded", async () => {
    const payload = { messages: [{ role: "user", content: "hi" }], document_ids: [], workspace_id: "hr" };

    await call("/api/ai/chat", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer t" }, body: JSON.stringify(payload) });

    assert.equal(stub.requests[0].url, "/agent/chat");
    assert.deepEqual(JSON.parse(stub.requests[0].body), payload);
    assert.equal(stub.requests[0].headers.authorization, "Bearer t");
});

test("204 from the AI service is passed through as 204", async () => {
    stub.handler = (req, res) => reply(res, 204);

    for (const [method, path, body] of [
        ["DELETE", "/api/users/alice"],
        ["DELETE", "/api/workspaces/hr"],
        ["PUT", "/api/users/alice/password", { password: "long-enough-1" }],
    ]) {
        const response = await call(path, { method, ...(body ? json(body) : {}) });

        assert.equal(response.status, 204, `${method} ${path}`);
    }
});

test("admin routes map to the right AI service paths", async () => {
    await call("/api/users");
    await call("/api/users", { method: "POST", ...json({ username: "bob", password: "long-enough-1" }) });
    await call("/api/users/bob/workspaces", { method: "PUT", ...json({ workspaces: ["it"] }) });
    await call("/api/workspaces", { method: "POST", ...json({ name: "Finance" }) });
    await call("/api/feedback/summary");

    assert.deepEqual(
        stub.requests.map((r) => `${r.method} ${r.url}`),
        ["GET /users", "POST /users", "PUT /users/bob/workspaces", "POST /workspaces", "GET /feedback/summary"]
    );
});

test("feedback list forwards its query string", async () => {
    await call("/api/feedback?rating=down&limit=5");

    assert.equal(stub.requests[0].url, "/feedback?rating=down&limit=5");
});

test("a crafted path segment cannot reach another AI service route", async () => {
    await call("/api/users/..%2Fauth%2Fme/password", { method: "PUT", ...json({ password: "long-enough-1" }) });
    await call("/api/workspaces/..%2Fusers", { method: "DELETE" });

    for (const request of stub.requests) {
        assert.ok(!request.url.startsWith("/auth/") && request.url !== "/users", `escaped to ${request.url}`);
        assert.match(request.url, /%2F/i);
    }
});

test("upload: rejects unsupported file types before calling the AI service", async () => {
    const form = new FormData();

    form.append("file", new Blob(["x"], { type: "text/plain" }), "notes.txt");
    const response = await call("/api/documents/upload", { method: "POST", body: form });

    assert.equal(response.status, 400);
    assert.equal(stub.requests.length, 0);
});

test("upload: forwards a PDF with its workspace and the token", async () => {
    stub.handler = (req, res) => reply(res, 200, { document_id: "d1", document_name: "p.pdf", workspace_id: "hr" });

    const form = new FormData();

    form.append("workspace_id", "hr");
    form.append("file", new Blob(["%PDF-1.4"], { type: "application/pdf" }), "p.pdf");

    const response = await call("/api/documents/upload", { method: "POST", headers: { Authorization: "Bearer t" }, body: form });
    const sent = stub.requests[0];

    assert.equal(response.status, 201);
    assert.equal(sent.url, "/documents/upload");
    assert.equal(sent.headers.authorization, "Bearer t");
    assert.match(sent.headers["content-type"], /^multipart\/form-data/);
    assert.match(sent.body, /name="workspace_id"[\s\S]*hr/);
    assert.match(sent.body, /filename="p\.pdf"/);
});

test("upload: a non-admin 403 from the AI service reaches the browser", async () => {
    stub.handler = (req, res) => reply(res, 403, { detail: "Admin access required." });

    const form = new FormData();

    form.append("file", new Blob(["%PDF-1.4"], { type: "application/pdf" }), "p.pdf");
    const response = await call("/api/documents/upload", { method: "POST", body: form });

    assert.equal(response.status, 403);
    assert.equal((await response.json()).error.detail, "Admin access required.");
});
