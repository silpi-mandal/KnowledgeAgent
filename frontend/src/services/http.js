const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api'

// sessionStorage: the login ends when the tab closes, and the token is not
// shared with other tabs. The token itself also expires on the server.
const TOKEN_KEY = 'documind-token'

let unauthorizedHandler = null

export class ApiError extends Error {
  constructor(message, { status = 0, cause } = {}) {
    super(message, { cause })
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken() {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Storage blocked: the user stays signed in until the page reloads.
  }
}

export function clearToken() {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // nothing to clear
  }
}

// Called when a request made with a token comes back 401 (expired/revoked).
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

function errorMessage(body, status) {
  // The Node backend wraps AI-service errors as { message, error: { detail } }.
  const detail = body?.error?.detail ?? body?.detail

  if (typeof detail === 'string' && detail) return detail
  if (typeof body?.message === 'string' && body.message) return body.message

  return `Request failed with status ${status}`
}

/**
 * Fetch JSON from the Node backend, attaching the bearer token when there is
 * one. Resolves with the parsed body; rejects with ApiError.
 */
export async function apiFetch(path, { method = 'GET', json, formData } = {}) {
  const headers = {}
  const token = getToken()

  if (token) headers.Authorization = `Bearer ${token}`

  let body

  if (formData) {
    body = formData
  } else if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  }

  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body,
    })
  } catch (error) {
    throw new ApiError('Network error: the server could not be reached.', {
      cause: error,
    })
  }

  let data

  if (response.ok && response.status === 204) return null

  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    if (response.status === 401 && token && unauthorizedHandler) {
      unauthorizedHandler()
    }

    throw new ApiError(errorMessage(data, response.status), {
      status: response.status,
    })
  }

  if (data === null) {
    throw new ApiError('The server returned an invalid response.', {
      status: response.status,
    })
  }

  return data
}
