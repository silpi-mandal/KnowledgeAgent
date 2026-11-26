const { callAI } = require("./aiClient");

async function chatWithAI(payload, authorization) {
    return callAI({
        method: "post",
        url: "/agent/chat",
        data: payload,
        authorization,
    });
}

module.exports = {
    chatWithAI,
};
