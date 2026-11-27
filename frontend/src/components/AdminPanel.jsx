import { useCallback, useEffect, useState } from 'react'
import * as admin from '../services/admin'
import { ApiError } from '../services/http'
import { AlertIcon, CloseIcon } from './icons'

const TABS = [
  ['workspaces', 'Workspaces'],
  ['users', 'Users'],
  ['feedback', 'Feedback'],
]

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus-visible:outline-2 focus-visible:outline-indigo-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:focus-visible:outline-indigo-400'
const primaryButton =
  'rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'
const subtleButton =
  'rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800'
const dangerButton =
  'rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-500/40 dark:text-red-300 dark:hover:bg-red-500/10'

// 4xx messages come from our own API and are safe to show; anything else is generic.
function errorText(error) {
  return error instanceof ApiError && error.status >= 400 && error.status < 500
    ? error.message
    : 'Something went wrong. Please try again.'
}

function Notice({ error, success }) {
  if (!error && !success) return null

  return (
    <p
      role={error ? 'alert' : 'status'}
      className={`flex items-start gap-2 rounded-md px-3 py-2 text-sm ${
        error
          ? 'bg-red-50 text-red-800 dark:bg-red-500/10 dark:text-red-300'
          : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300'
      }`}
    >
      {error && <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />}
      {error || success}
    </p>
  )
}

function WorkspaceChecks({ workspaces, value, onChange, name }) {
  if (workspaces.length === 0) {
    return <p className="text-xs text-slate-500">No workspaces yet.</p>
  }

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {workspaces.map((workspace) => {
        const id = `${name}-${workspace.workspace_id}`

        return (
          <label key={id} htmlFor={id} className="flex items-center gap-1.5 text-sm text-slate-700 dark:text-slate-200">
            <input
              id={id}
              type="checkbox"
              checked={value.includes(workspace.workspace_id)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...value, workspace.workspace_id]
                    : value.filter((item) => item !== workspace.workspace_id),
                )
              }
            />
            {workspace.name}
          </label>
        )
      })}
    </div>
  )
}

function WorkspacesTab({ workspaces, onChanged }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function run(action, message) {
    setBusy(true)
    setError('')
    setSuccess('')

    try {
      await action()
      setSuccess(message)
      await onChanged()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  function handleCreate(event) {
    event.preventDefault()

    const trimmed = name.trim()

    if (!trimmed) return

    run(() => admin.createWorkspace(trimmed), `Workspace "${trimmed}" created.`).then(() => setName(''))
  }

  function handleDelete(workspace) {
    if (!window.confirm(`Delete the empty workspace "${workspace.name}"?`)) return

    run(() => admin.deleteWorkspace(workspace.workspace_id), `Workspace "${workspace.name}" deleted.`)
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleCreate} className="flex items-end gap-2">
        <div className="flex-1">
          <label htmlFor="new-workspace" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
            New workspace
          </label>
          <input id="new-workspace" className={inputClass} value={name} maxLength={60} placeholder="e.g. Finance" onChange={(event) => setName(event.target.value)} />
        </div>
        <button type="submit" className={primaryButton} disabled={busy || !name.trim()}>
          Create
        </button>
      </form>

      <Notice error={error} success={success} />

      <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
        {workspaces.map((workspace) => {
          const isDefault = workspace.workspace_id === 'general'
          const hasDocuments = workspace.document_count > 0

          return (
            <li key={workspace.workspace_id} className="flex items-center gap-3 px-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{workspace.name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  id: {workspace.workspace_id} · {workspace.document_count} document{workspace.document_count === 1 ? '' : 's'}
                </p>
              </div>
              <button
                type="button"
                className={dangerButton}
                disabled={busy || isDefault || hasDocuments}
                title={isDefault ? 'The default workspace cannot be deleted' : hasDocuments ? 'Only empty workspaces can be deleted' : 'Delete workspace'}
                onClick={() => handleDelete(workspace)}
              >
                Delete
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function UserRow({ user, workspaces, isSelf, onChanged, onMessage }) {
  const [mode, setMode] = useState(null) // null | 'access' | 'password'
  const [access, setAccess] = useState(user.workspaces)
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function run(action, message) {
    setBusy(true)
    onMessage({ error: '', success: '' })

    try {
      await action()
      setMode(null)
      setPassword('')
      await onChanged()
      onMessage({ error: '', success: message })
    } catch (err) {
      onMessage({ error: errorText(err), success: '' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="space-y-2 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
            {user.username}
            {isSelf && <span className="ml-2 text-xs font-normal text-slate-500">(you)</span>}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {user.role} ·{' '}
            {user.role === 'admin' ? 'all workspaces' : user.workspaces.length ? user.workspaces.join(', ') : 'no workspaces'}
          </p>
        </div>

        {user.role !== 'admin' && (
          <button type="button" className={subtleButton} disabled={busy} onClick={() => { setAccess(user.workspaces); setMode(mode === 'access' ? null : 'access') }}>
            Access
          </button>
        )}
        <button type="button" className={subtleButton} disabled={busy} onClick={() => setMode(mode === 'password' ? null : 'password')}>
          Reset password
        </button>
        <button
          type="button"
          className={dangerButton}
          disabled={busy || isSelf}
          title={isSelf ? 'You cannot delete yourself' : 'Delete user'}
          onClick={() => {
            if (window.confirm(`Delete user "${user.username}"?`)) {
              run(() => admin.deleteUser(user.username), `User "${user.username}" deleted.`)
            }
          }}
        >
          Delete
        </button>
      </div>

      {mode === 'access' && (
        <div className="space-y-2 rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
          <WorkspaceChecks workspaces={workspaces} value={access} onChange={setAccess} name={`access-${user.username}`} />
          <button type="button" className={primaryButton} disabled={busy} onClick={() => run(() => admin.setUserWorkspaces(user.username, access), `Access updated for ${user.username}.`)}>
            Save access
          </button>
        </div>
      )}

      {mode === 'password' && (
        <form
          className="flex items-end gap-2 rounded-md bg-slate-50 p-3 dark:bg-slate-800/60"
          onSubmit={(event) => {
            event.preventDefault()
            run(() => admin.resetUserPassword(user.username, password), `Password reset for ${user.username}. Their open sessions were signed out.`)
          }}
        >
          <div className="flex-1">
            <label htmlFor={`pw-${user.username}`} className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
              New password (8+ characters)
            </label>
            <input id={`pw-${user.username}`} type="password" autoComplete="new-password" className={inputClass} value={password} minLength={8} onChange={(event) => setPassword(event.target.value)} />
          </div>
          <button type="submit" className={primaryButton} disabled={busy || password.length < 8}>
            Set password
          </button>
        </form>
      )}
    </li>
  )
}

function UsersTab({ workspaces, currentUser }) {
  const [users, setUsers] = useState(null)
  const [form, setForm] = useState({ username: '', password: '', role: 'employee', workspaces: [] })
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState({ error: '', success: '' })

  const load = useCallback(async () => {
    try {
      setUsers(await admin.listUsers())
    } catch (err) {
      setMessage({ error: errorText(err), success: '' })
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    admin
      .listUsers()
      .then((data) => {
        if (!cancelled) setUsers(data)
      })
      .catch((err) => {
        if (!cancelled) setMessage({ error: errorText(err), success: '' })
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setBusy(true)
    setMessage({ error: '', success: '' })

    try {
      await admin.createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        workspaces: form.role === 'admin' ? [] : form.workspaces,
      })
      setMessage({ error: '', success: `User "${form.username.trim()}" created.` })
      setForm({ username: '', password: '', role: 'employee', workspaces: [] })
      await load()
    } catch (err) {
      setMessage({ error: errorText(err), success: '' })
    } finally {
      setBusy(false)
    }
  }

  const canCreate = form.username.trim().length >= 3 && form.password.length >= 8

  return (
    <div className="space-y-4">
      <form onSubmit={handleCreate} className="space-y-3 rounded-md border border-slate-200 p-3 dark:border-slate-700">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">Add a user</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="new-username" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Username</label>
            <input id="new-username" className={inputClass} autoComplete="off" value={form.username} maxLength={32} onChange={(event) => setForm({ ...form, username: event.target.value })} />
          </div>
          <div>
            <label htmlFor="new-password" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Password (8+ characters)</label>
            <input id="new-password" type="password" autoComplete="new-password" className={inputClass} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          </div>
          <div>
            <label htmlFor="new-role" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Role</label>
            <select id="new-role" className={inputClass} value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
              <option value="employee">Employee</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>

        {form.role === 'employee' && (
          <div>
            <p className="mb-1 text-xs font-medium text-slate-600 dark:text-slate-300">Workspaces this employee can use</p>
            <WorkspaceChecks workspaces={workspaces} value={form.workspaces} onChange={(next) => setForm({ ...form, workspaces: next })} name="new-user" />
          </div>
        )}

        <button type="submit" className={primaryButton} disabled={busy || !canCreate}>
          Create user
        </button>
      </form>

      <Notice error={message.error} success={message.success} />

      {users === null ? (
        <p className="text-sm text-slate-500">Loading users...</p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
          {users.map((user) => (
            <UserRow key={user.username} user={user} workspaces={workspaces} isSelf={user.username === currentUser.username} onChanged={load} onMessage={setMessage} />
          ))}
        </ul>
      )}
    </div>
  )
}

function FeedbackTab() {
  const [rating, setRating] = useState('')
  const [summary, setSummary] = useState(null)
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    let cancelled = false

    Promise.all([admin.getFeedbackSummary(), admin.getFeedback(rating)])
      .then(([summaryData, entryData]) => {
        if (cancelled) return
        setSummary(summaryData)
        setEntries(entryData)
        setError('')
      })
      .catch((err) => {
        if (!cancelled) setError(errorText(err))
      })

    return () => {
      cancelled = true
    }
  }, [rating])

  const satisfaction = summary?.satisfaction == null ? '-' : `${Math.round(summary.satisfaction * 100)}%`

  return (
    <div className="space-y-4">
      <Notice error={error} />

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[['Ratings', summary.total], ['Thumbs up', summary.up], ['Thumbs down', summary.down], ['Satisfaction', satisfaction]].map(([label, value]) => (
            <div key={label} className="rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700">
              <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
              <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
            </div>
          ))}
        </div>
      )}

      {summary && Object.keys(summary.by_workspace).length > 0 && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          By workspace:{' '}
          {Object.entries(summary.by_workspace).map(([workspace, counts]) => `${workspace} (${counts.up} up, ${counts.down} down)`).join(' · ')}
        </p>
      )}

      <div className="flex items-center gap-2">
        <label htmlFor="feedback-filter" className="text-xs font-medium text-slate-600 dark:text-slate-300">Show</label>
        <select id="feedback-filter" className={`${inputClass} !w-auto`} value={rating} onChange={(event) => { setEntries(null); setRating(event.target.value) }}>
          <option value="">All ratings</option>
          <option value="down">Thumbs down</option>
          <option value="up">Thumbs up</option>
        </select>
      </div>

      {entries === null && !error && <p className="text-sm text-slate-500">Loading feedback...</p>}
      {entries && entries.length === 0 && <p className="text-sm text-slate-500">No feedback yet.</p>}

      {entries && entries.length > 0 && (
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
          {entries.map((entry) => {
            const key = `${entry.answer_id}-${entry.username}`
            const open = expanded === key

            return (
              <li key={key} className="space-y-1 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${entry.rating === 'up' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300' : 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300'}`}>
                    {entry.rating === 'up' ? 'Thumbs up' : 'Thumbs down'}
                  </span>
                  <span>{entry.username}</span>
                  <span>· {entry.workspace_id || 'no workspace'}</span>
                  <span>· {new Date(entry.updated_at).toLocaleString()}</span>
                </div>
                <p className="font-medium text-slate-900 dark:text-slate-100">{entry.question || '(question not stored)'}</p>
                {entry.comment && <p className="text-slate-700 dark:text-slate-300">Comment: {entry.comment}</p>}
                <button type="button" className="text-xs text-indigo-700 underline dark:text-indigo-300" onClick={() => setExpanded(open ? null : key)} aria-expanded={open}>
                  {open ? 'Hide answer' : 'Show answer'}
                </button>
                {open && <p className="whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-slate-700 dark:bg-slate-800/60 dark:text-slate-300">{entry.answer || '(answer not stored)'}</p>}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function AdminPanel({ user, workspaces, onClose, onWorkspacesChanged }) {
  const [tab, setTab] = useState('workspaces')

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', onKey)

    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div role="dialog" aria-modal="true" aria-label="Admin panel" className="fixed inset-0 z-50 flex items-stretch justify-center bg-slate-900/50 p-0 sm:p-6">
      <div className="flex w-full max-w-3xl flex-col overflow-hidden bg-white shadow-xl sm:rounded-xl dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">Admin</h2>

          <div role="tablist" aria-label="Admin sections" className="order-last flex w-full gap-1 overflow-x-auto sm:order-none sm:ml-2 sm:w-auto">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                id={`tab-${id}`}
                role="tab"
                type="button"
                aria-selected={tab === id}
                aria-controls="admin-tabpanel"
                onClick={() => setTab(id)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${tab === id ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}
              >
                {label}
              </button>
            ))}
          </div>

          <button type="button" onClick={onClose} aria-label="Close admin panel" className="ml-auto rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div id="admin-tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="flex-1 overflow-y-auto p-4">
          {tab === 'workspaces' && <WorkspacesTab workspaces={workspaces} onChanged={onWorkspacesChanged} />}
          {tab === 'users' && <UsersTab workspaces={workspaces} currentUser={user} />}
          {tab === 'feedback' && <FeedbackTab />}
        </div>
      </div>
    </div>
  )
}

export default AdminPanel
