import { useCallback, useEffect, useState } from 'react'
import { getCurrentUser, login as loginRequest, logout as logoutRequest } from '../services/auth'
import { getToken, setUnauthorizedHandler } from '../services/http'

const SESSION_EXPIRED_NOTICE = 'Your session expired. Please sign in again.'

// status: 'loading' (checking a saved token) | 'anonymous' | 'authenticated'
function useAuth() {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() =>
    getToken() ? 'loading' : 'anonymous',
  )
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    // Any request made with a token that the server rejects ends the session.
    setUnauthorizedHandler(() => {
      logoutRequest()
      setUser(null)
      setStatus('anonymous')
      setNotice(SESSION_EXPIRED_NOTICE)
    })

    if (!getToken()) return undefined

    let cancelled = false

    getCurrentUser()
      .then((currentUser) => {
        if (cancelled) return
        setUser(currentUser)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        logoutRequest()
        setStatus('anonymous')
      })

    return () => {
      cancelled = true
      setUnauthorizedHandler(null)
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const currentUser = await loginRequest(username, password)

    setUser(currentUser)
    setNotice(null)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(() => {
    logoutRequest()
    setUser(null)
    setNotice(null)
    setStatus('anonymous')
  }, [])

  return { user, status, notice, login, logout }
}

export default useAuth
