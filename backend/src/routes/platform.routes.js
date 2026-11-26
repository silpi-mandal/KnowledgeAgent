const express = require("express");

const { callAI, respondWithError } = require("../services/aiClient");

/**
 * Thin pass-through routes for the AI service's auth, workspace and feedback
 * endpoints. The browser talks to this backend only; the Authorization header
 * is forwarded and the AI service does all permission checks.
 */
function forward({ method, url, withBody = false, label }) {
    return async (req, res) => {
        try {
            const data = await callAI({
                method,
                url,
                data: withBody ? req.body : undefined,
                authorization: req.headers.authorization,
            });

            res.json(data);
        } catch (error) {
            return respondWithError(res, error, label);
        }
    };
}

const router = express.Router();

router.post(
    "/auth/login",
    forward({ method: "post", url: "/auth/login", withBody: true, label: "Login request" })
);
router.get(
    "/auth/me",
    forward({ method: "get", url: "/auth/me", label: "Current user request" })
);
router.get(
    "/workspaces",
    forward({ method: "get", url: "/workspaces", label: "Workspace list request" })
);
router.post(
    "/feedback",
    forward({ method: "post", url: "/feedback", withBody: true, label: "Feedback request" })
);

module.exports = router;
