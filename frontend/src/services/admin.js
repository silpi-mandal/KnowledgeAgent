import { apiFetch } from './http'

// Every call here is admin-only; the AI service enforces that, not the UI.

export const createWorkspace = (name, description = '') =>
  apiFetch('/workspaces', { method: 'POST', json: { name, description } })

export const deleteWorkspace = (workspaceId) =>
  apiFetch(`/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: 'DELETE',
  })

export async function listUsers() {
  const data = await apiFetch('/users')

  if (!Array.isArray(data)) throw new Error('Failed to load users')

  return data
}

export const createUser = ({ username, password, role, workspaces }) =>
  apiFetch('/users', {
    method: 'POST',
    json: { username, password, role, workspaces },
  })

export const setUserWorkspaces = (username, workspaces) =>
  apiFetch(`/users/${encodeURIComponent(username)}/workspaces`, {
    method: 'PUT',
    json: { workspaces },
  })

export const resetUserPassword = (username, password) =>
  apiFetch(`/users/${encodeURIComponent(username)}/password`, {
    method: 'PUT',
    json: { password },
  })

export const deleteUser = (username) =>
  apiFetch(`/users/${encodeURIComponent(username)}`, { method: 'DELETE' })

export async function getFeedback(rating) {
  const query = rating ? `?rating=${encodeURIComponent(rating)}&limit=100` : '?limit=100'
  const data = await apiFetch(`/feedback${query}`)

  if (!Array.isArray(data)) throw new Error('Failed to load feedback')

  return data
}

export const getFeedbackSummary = () => apiFetch('/feedback/summary')
