import ConfidenceBadge from './ConfidenceBadge'
import FeedbackButtons from './FeedbackButtons'
import SourceList from './SourceList'
import ToolActivity from './ToolActivity'
import { AlertIcon } from './icons'

function ChatMessage({ message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-sm leading-6 whitespace-pre-wrap text-white">
          {message.content}
        </div>
      </div>
    )
  }

  const hasConfidence =
    !message.error && message.confidence != null && message.confidenceLevel
  const hasFeedback = !message.error && message.answerId

  return (
    <div className="flex gap-3">
      <img
        src="/documind-logo.svg"
        alt=""
        aria-hidden="true"
        className="mt-1 h-8 w-8 shrink-0 rounded-lg"
        width="32"
        height="32"
      />

      <div className="min-w-0 max-w-[85%] flex-1">
        <div
          className={`rounded-2xl rounded-tl-md px-4 py-3 text-sm leading-6 whitespace-pre-wrap ${
            message.error
              ? 'border border-red-200 bg-red-50 text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-300'
              : 'border border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200'
          }`}
        >
          {message.error && (
            <AlertIcon className="mr-1.5 inline h-4 w-4 align-[-2px]" />
          )}
          {message.content}
        </div>

        {(hasConfidence || hasFeedback) && (
          <div className="mt-1.5 flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
            {hasConfidence ? (
              <ConfidenceBadge
                confidence={message.confidence}
                level={message.confidenceLevel}
                prefix="Best source match: "
              />
            ) : (
              <span />
            )}

            {hasFeedback && <FeedbackButtons answerId={message.answerId} />}
          </div>
        )}

        {hasConfidence && message.confidenceLevel === 'low' && (
          <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-400">
            Weak match with your documents. Check the sources before relying on
            this answer.
          </p>
        )}

        {!message.error && message.sources?.length > 0 && (
          <SourceList sources={message.sources} />
        )}

        {!message.error && message.traces?.length > 0 && (
          <ToolActivity traces={message.traces} />
        )}
      </div>
    </div>
  )
}

export default ChatMessage
