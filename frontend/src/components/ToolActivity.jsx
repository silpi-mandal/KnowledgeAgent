import { useState } from 'react'
import { ChevronIcon, WrenchIcon } from './icons'

const MAX_ARGS_LENGTH = 200

function formatArguments(args) {
  if (!args || Object.keys(args).length === 0) return null

  let text

  try {
    text = JSON.stringify(args)
  } catch {
    return null
  }

  return text.length > MAX_ARGS_LENGTH
    ? `${text.slice(0, MAX_ARGS_LENGTH)}...`
    : text
}

// Shows which tools the agent called to produce the answer.
function ToolActivity({ traces }) {
  const [isOpen, setIsOpen] = useState(false)
  const failed = traces.filter((trace) => trace.ok === false).length

  return (
    <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 transition hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-slate-300 dark:hover:text-slate-50 dark:focus-visible:outline-indigo-400"
      >
        <WrenchIcon className="h-3.5 w-3.5" />
        Tool activity ({traces.length})
        {failed > 0 && (
          <span className="text-red-600 dark:text-red-400">
            · {failed} failed
          </span>
        )}
        <ChevronIcon
          className={`ml-auto h-4 w-4 text-slate-400 transition-transform dark:text-slate-500 ${
            isOpen ? '' : '-rotate-90'
          }`}
        />
      </button>

      {isOpen && (
        <ol className="space-y-2.5 border-t border-slate-200 px-3 py-2.5 dark:border-slate-700">
          {traces.map((trace, index) => {
            const args = formatArguments(trace.arguments)
            const ok = trace.ok !== false

            return (
              <li
                key={`${trace.tool}-${index}`}
                className="text-xs text-slate-600 dark:text-slate-300"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-medium text-slate-800 dark:text-slate-100">
                    {trace.tool}
                  </span>
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                      ok
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
                        : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300'
                    }`}
                  >
                    {ok ? 'ok' : 'failed'}
                  </span>
                </div>

                {args && (
                  <code className="mt-1 block rounded-md bg-white px-2 py-1 font-mono text-[11px] break-all text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                    {args}
                  </code>
                )}

                {trace.result_summary && (
                  <p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">
                    {trace.result_summary}
                  </p>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

export default ToolActivity
