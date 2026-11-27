import ChatWorkspace from './components/ChatWorkspace'
import LoginPage from './components/LoginPage'
import useAuth from './hooks/useAuth'

function App() {
  const { user, status, notice, login, logout, retry } = useAuth()

  if (status === 'loading') {
    return (
      <div
        role="status"
        className="flex min-h-dvh items-center justify-center bg-slate-50 text-sm text-slate-500 dark:bg-slate-950 dark:text-slate-400"
      >
        Loading...
      </div>
    )
  }

  if (status === 'unreachable') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-50 px-6 dark:bg-slate-950">
        <div role="alert" className="max-w-sm text-center">
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
            Can&apos;t reach the server
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            You are still signed in. Check that the backend is running, then try again.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              type="button"
              onClick={retry}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (status !== 'authenticated') {
    return <LoginPage onLogin={login} notice={notice} />
  }

  // Mounted only while signed in, so signing out discards every piece of
  // chat and document state belonging to that user.
  return <ChatWorkspace user={user} onLogout={logout} />
}

export default App
