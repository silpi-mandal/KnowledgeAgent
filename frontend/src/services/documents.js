import { apiFetch } from './http'

export async function getDocuments(workspaceId) {
  const query = workspaceId
    ? `?workspace_id=${encodeURIComponent(workspaceId)}`
    : ''

  const data = await apiFetch(`/documents${query}`)

  if (!Array.isArray(data)) {
    throw new Error('Failed to load documents')
  }

  return data
}

// Admin only on the server; the UI hides the button for everyone else.
export function uploadDocument(file, workspaceId) {
  const formData = new FormData()

  if (workspaceId) formData.append('workspace_id', workspaceId)
  formData.append('file', file)

  return apiFetch('/documents/upload', { method: 'POST', formData })
}
