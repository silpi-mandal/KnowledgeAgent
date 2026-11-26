import { useState } from 'react'
import { AlertIcon } from './icons'

function LoginPage({ onLogin, notice }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()

    if (isSubmitting || !username.trim() || !password) return

    setIsSubmitting(true)
    setError(null)

    try {
      await onLogin(username.trim(), password)
    } catch (loginError) {
      console.error('Login failed:', loginError)
      // 401 carries "Invalid username or password."; other failures are
      // network/server problems and say so.
      setError(
        loginError.message || 'Unable to sign in. Please try again.',
      )
      setIsSubmitting(false)
    }
  }

  const message = error ?? notice

  return (
    <div className="flex min-h-dvh items-center justify-center bg-slate-50 px-4 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <img
            src="/documind-logo.svg"
            alt=""
            className="h-10 w-10"
            width="40"
            height="40"
          />
          <div>
            <h1 className="text-lg leading-tight font-semibold text-slate-900 dark:text-slate-50">
              KnowledgeAgent
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Sign in to your knowledge workspace
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label
              htmlFor="login-username"
              className="block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Username
            </label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              maxLength={64}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:outline-none dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-indigo-500/30"
            />
          </div>

          <div>
            <label
              htmlFor="login-password"
              className="block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              maxLength={128}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:outline-none dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 dark:focus:ring-indigo-500/30"
            />
          </div>

          {message && (
            <p
              role="alert"
              className={`flex items-start gap-1.5 text-sm ${
                error
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-amber-700 dark:text-amber-400'
              }`}
            >
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
              {message}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting || !username.trim() || !password}
            className="w-full rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:outline-indigo-400"
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
