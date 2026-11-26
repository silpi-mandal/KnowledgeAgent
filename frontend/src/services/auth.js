import { apiFetch, clearToken, setToken } from './http'

export async function login(username, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    json: { username, password },
  })

  if (!data || typeof data.access_token !== 'string') {
    throw new Error('The server returned an invalid response.')
  }

  setToken(data.access_token)

  try {
    return await getCurrentUser()
  } catch (error) {
    clearToken()
    throw error
  }
}

export async function getCurrentUser() {
  const data = await apiFetch('/auth/me')

  return {
    username: data.username,
    role: data.role,
    workspaces: Array.isArray(data.workspaces) ? data.workspaces : [],
  }
}

export function logout() {
  clearToken()
}
