import { apiFetch } from './http'

export const GENERIC_ERROR_MESSAGE =
  'Unable to get a response. Please try again.'

export async function sendChatMessage({
  messages,
  documentIds = [],
  workspaceId = null,
}) {
  const data = await apiFetch('/ai/chat', {
    method: 'POST',
    json: {
      messages,
      document_ids: documentIds,
      workspace_id: workspaceId,
    },
  })

  if (typeof data.answer !== 'string' || !data.answer.trim()) {
    throw new Error('The server returned an empty response.')
  }

  return {
    answer: data.answer,
    sources: Array.isArray(data.sources) ? data.sources : [],
    traces: Array.isArray(data.traces) ? data.traces : [],
    answerId: data.answer_id ?? null,
    confidence: data.answer_confidence ?? null,
    confidenceLevel: data.answer_confidence_level ?? null,
  }
}
