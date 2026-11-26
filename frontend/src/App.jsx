import ChatWorkspace from './components/ChatWorkspace'
import LoginPage from './components/LoginPage'
import useAuth from './hooks/useAuth'

function App() {
  const { user, status, notice, login, logout } = useAuth()

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

  if (status !== 'authenticated') {
    return <LoginPage onLogin={login} notice={notice} />
  }

  // Mounted only while signed in, so signing out discards every piece of
  // chat and document state belonging to that user.
  return <ChatWorkspace user={user} onLogout={logout} />
}

export default App
