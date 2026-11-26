const FormData = require("form-data");

const { callAI } = require("./aiClient");

async function getDocuments({ workspaceId, authorization } = {}) {
    return callAI({
        method: "get",
        url: "/documents",
        params: workspaceId ? { workspace_id: workspaceId } : undefined,
        authorization,
    });
}

async function uploadDocument(file, { workspaceId, authorization } = {}) {
    const formData = new FormData();

    formData.append("file", file.buffer, {
        filename: file.originalname,
        contentType: file.mimetype,
    });

    if (workspaceId) {
        formData.append("workspace_id", workspaceId);
    }

    return callAI({
        method: "post",
        url: "/documents/upload",
        data: formData,
        headers: formData.getHeaders(),
        authorization,
    });
}

module.exports = {
    getDocuments,
    uploadDocument,
};
