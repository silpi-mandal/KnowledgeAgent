const { chatWithAI } = require("../services/aiService");
const { respondWithError } = require("../services/aiClient");

async function chat(req, res) {
    try {
        const result = await chatWithAI(req.body, req.headers.authorization);

        res.json(result);
    } catch (error) {
        return respondWithError(res, error, "AI chat request");
    }
}

module.exports = {
    chat,
};
