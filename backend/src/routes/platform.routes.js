const express = require("express");

const { callAI, respondWithError } = require("../services/aiClient");

/**
 * Thin pass-through routes for the AI service's auth, workspace, user and
 * feedback endpoints. The browser talks to this backend only; the
 * Authorization header is forwarded and the AI service does ALL permission
 * checks (including "admin only"), so nothing is decided here.
 */
function forward({ method, url, withBody = false, label }) {
    return async (req, res) => {
        try {
            const data = await callAI({
                method,
                url: typeof url === "function" ? url(req) : url,
                data: withBody ? req.body : undefined,
                params: req.query,
                authorization: req.headers.authorization,
            });

            // The AI service answers 204 (no body) for deletes and password resets.
            if (data === "" || data === undefined || data === null) {
                return res.status(204).end();
            }

            res.json(data);
        } catch (error) {
            return respondWithError(res, error, label);
        }
    };
}

// Path segments come from the browser: re-encode them so one can never
// climb out of its own route (e.g. "..%2Fauth%2Fme").
const segment = (value) => encodeURIComponent(value);

const router = express.Router();

// --- auth ---
router.post("/auth/login", forward({ method: "post", url: "/auth/login", withBody: true, label: "Login request" }));
router.get("/auth/me", forward({ method: "get", url: "/auth/me", label: "Current user request" }));

// --- workspaces ---
router.get("/workspaces", forward({ method: "get", url: "/workspaces", label: "Workspace list request" }));
router.post("/workspaces", forward({ method: "post", url: "/workspaces", withBody: true, label: "Workspace create request" }));
router.delete(
    "/workspaces/:id",
    forward({ method: "delete", url: (req) => `/workspaces/${segment(req.params.id)}`, label: "Workspace delete request" })
);

// --- users (admin only, enforced by the AI service) ---
router.get("/users", forward({ method: "get", url: "/users", label: "User list request" }));
router.post("/users", forward({ method: "post", url: "/users", withBody: true, label: "User create request" }));
router.put(
    "/users/:name/workspaces",
    forward({ method: "put", url: (req) => `/users/${segment(req.params.name)}/workspaces`, withBody: true, label: "User workspaces request" })
);
router.put(
    "/users/:name/password",
    forward({ method: "put", url: (req) => `/users/${segment(req.params.name)}/password`, withBody: true, label: "Password reset request" })
);
router.delete(
    "/users/:name",
    forward({ method: "delete", url: (req) => `/users/${segment(req.params.name)}`, label: "User delete request" })
);

// --- feedback ---
router.post("/feedback", forward({ method: "post", url: "/feedback", withBody: true, label: "Feedback request" }));
router.get("/feedback/summary", forward({ method: "get", url: "/feedback/summary", label: "Feedback summary request" }));
router.get("/feedback", forward({ method: "get", url: "/feedback", label: "Feedback list request" }));

module.exports = router;
