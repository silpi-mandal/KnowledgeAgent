const axios = require("axios");

// Chat runs an agent loop (several LLM calls), so allow a minute by default.
// Override with AI_TIMEOUT_MS in backend/.env.
const DEFAULT_TIMEOUT_MS = 60000;

function defaultTimeout() {
    const configured = Number(process.env.AI_TIMEOUT_MS);

    return Number.isFinite(configured) && configured > 0
        ? configured
        : DEFAULT_TIMEOUT_MS;
}

/**
 * Calls the FastAPI AI service on behalf of the signed-in user.
 *
 * Only the Authorization header is forwarded, so the AI service stays the one
 * place that decides who the user is and what they may see.
 * Errors are normalised so every controller can answer the same way:
 *   - timeout            -> Error("AI service request timed out")
 *   - non-2xx response   -> Error with .status and .details from the AI service
 *   - anything else      -> Error("AI service is unavailable")
 */
async function callAI({
    method = "get",
    url,
    data,
    params,
    authorization,
    headers = {},
    timeout = defaultTimeout(),
}) {
    const requestHeaders = { ...headers };

    if (authorization) {
        requestHeaders.Authorization = authorization;
    }

    try {
        const response = await axios.request({
            baseURL: process.env.AI_SERVICE_URL,
            method,
            url,
            data,
            params,
            headers: requestHeaders,
            timeout,
        });

        return response.data;
    } catch (error) {
        if (error.code === "ECONNABORTED") {
            throw new Error("AI service request timed out");
        }

        if (error.response) {
            const serviceError = new Error("AI service returned an error");

            serviceError.status = error.response.status;
            serviceError.details = error.response.data;

            throw serviceError;
        }

        throw new Error("AI service is unavailable");
    }
}

function respondWithError(res, error, label) {
    console.error(`${label} failed:`, error.message);

    if (error.status) {
        return res.status(error.status).json({
            message: error.message,
            error: error.details,
        });
    }

    if (error.message === "AI service request timed out") {
        return res.status(504).json({ message: error.message });
    }

    return res.status(503).json({ message: error.message });
}

module.exports = {
    callAI,
    respondWithError,
};
