import { useCallback, useEffect, useState } from 'react'
import { getCurrentUser, login as loginRequest, logout as logoutRequest } from '../services/auth'
import { ApiError, getToken, setUnauthorizedHandler } from '../services/http'

const SESSION_EXPIRED_NOTICE = 'Your session expired. Please sign in again.'

// status: 'loading' (checking a saved token) | 'anonymous' | 'authenticated'
//         | 'unreachable' (signed in, but the server did not answer: retry)
function useAuth() {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() =>
    getToken() ? 'loading' : 'anonymous',
  )
  const [notice, setNotice] = useState(null)

  // Ask the server who the saved token belongs to. A 401 is handled by the
  // unauthorized handler below; a network or server failure must NOT sign the
  // user out (their token may be fine), so it ends in 'unreachable' instead.
  const checkSession = useCallback((isCancelled = () => false) => {
    return getCurrentUser()
      .then((currentUser) => {
        if (isCancelled()) return
        setUser(currentUser)
        setStatus('authenticated')
      })
      .catch((error) => {
        if (isCancelled()) return

        if (error instanceof ApiError && error.status === 401) return

        if (error instanceof ApiError && error.status > 0 && error.status < 500) {
          logoutRequest()
          setStatus('anonymous')
          return
        }

        setStatus('unreachable')
      })
  }, [])

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

    checkSession(() => cancelled)

    return () => {
      cancelled = true
      setUnauthorizedHandler(null)
    }
  }, [checkSession])

  const retry = useCallback(() => {
    setStatus('loading')
    checkSession()
  }, [checkSession])

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

  return { user, status, notice, login, logout, retry }
}

export default useAuth
