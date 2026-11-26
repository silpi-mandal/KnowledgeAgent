import { LayersIcon } from './icons'

function WorkspaceSelector({
  workspaces,
  selectedWorkspaceId,
  onSelect,
  disabled,
}) {
  return (
    <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
      <label
        htmlFor="workspace-select"
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400"
      >
        <LayersIcon className="h-3.5 w-3.5" />
        Workspace
      </label>

      <select
        id="workspace-select"
        value={selectedWorkspaceId ?? ''}
        onChange={(event) => onSelect(event.target.value)}
        disabled={disabled || workspaces.length === 0}
        className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-indigo-500/30"
      >
        {workspaces.map((workspace) => (
          <option key={workspace.workspace_id} value={workspace.workspace_id}>
            {workspace.name} ({workspace.document_count ?? 0})
          </option>
        ))}
      </select>
    </div>
  )
}

export default WorkspaceSelector
