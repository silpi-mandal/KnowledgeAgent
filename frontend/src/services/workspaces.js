import { apiFetch } from './http'

// Only the workspaces the signed-in user may access are returned.
export async function getWorkspaces() {
  const data = await apiFetch('/workspaces')

  if (!Array.isArray(data)) {
    throw new Error('Failed to load workspaces')
  }

  return data
}
