const {
    getDocuments,
    uploadDocument: sendDocumentToAI,
} = require("../services/documentService");
const { respondWithError } = require("../services/aiClient");

function textField(value) {
    return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

async function getAllDocuments(req, res) {
    try {
        const documents = await getDocuments({
            workspaceId: textField(req.query.workspace_id),
            authorization: req.headers.authorization,
        });

        res.json(documents);
    } catch (error) {
        return respondWithError(res, error, "Document list request");
    }
}

async function uploadDocument(req, res) {
    try {
        if (!req.file) {
            return res.status(400).json({
                message: "File is required",
            });
        }

        const document = await sendDocumentToAI(req.file, {
            workspaceId: textField(req.body?.workspace_id),
            authorization: req.headers.authorization,
        });

        return res.status(201).json(document);
    } catch (error) {
        return respondWithError(res, error, "Document upload request");
    }
}

module.exports = {
    getAllDocuments,
    uploadDocument,
};
