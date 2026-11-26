import { useState } from 'react'
import ConfidenceBadge from './ConfidenceBadge'
import { ChevronIcon, FileIcon } from './icons'

function SourceItem({ source }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <li className="text-xs text-slate-600 dark:text-slate-300">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-500">
          <FileIcon className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate">
          {source.document_name || 'Document'}
          {source.page != null ? ` · Page ${source.page}` : ''}
        </span>
        <ConfidenceBadge
          confidence={source.confidence}
          level={source.confidence_level}
        />
      </div>

      {source.snippet && (
        <button
          type="button"
          onClick={() => setExpanded((open) => !open)}
          aria-expanded={expanded}
          title={expanded ? 'Show less' : 'Show more'}
          className="mt-1 ml-8 block w-[calc(100%-2rem)] cursor-pointer rounded-md text-left text-[11px] leading-5 text-slate-500 italic hover:text-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-slate-400 dark:hover:text-slate-200 dark:focus-visible:outline-indigo-400"
        >
          <span className={expanded ? '' : 'line-clamp-2'}>
            “{source.snippet}”
          </span>
        </button>
      )}
    </li>
  )
}

function SourceList({ sources }) {
  const [isOpen, setIsOpen] = useState(true)

  return (
    <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 transition hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-slate-300 dark:hover:text-slate-50 dark:focus-visible:outline-indigo-400"
      >
        Sources ({sources.length})
        <ChevronIcon
          className={`ml-auto h-4 w-4 text-slate-400 transition-transform dark:text-slate-500 ${
            isOpen ? '' : '-rotate-90'
          }`}
        />
      </button>

      {isOpen && (
        <ul className="space-y-3 border-t border-slate-200 px-3 py-2.5 dark:border-slate-700">
          {sources.map((source, index) => (
            <SourceItem
              key={`${source.document_id ?? 'source'}-${source.page ?? 0}-${index}`}
              source={source}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

export default SourceList
