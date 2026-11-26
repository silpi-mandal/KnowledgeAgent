import { useState } from 'react'
import { submitFeedback } from '../services/feedback'
import { ThumbDownIcon, ThumbUpIcon } from './icons'

const buttonBase =
  'rounded-md p-1.5 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:outline-indigo-400'

// Thumbs up/down for one answer. A rating can be changed; the server keeps
// only the latest one. A thumbs-down offers an optional comment.
function FeedbackButtons({ answerId }) {
  const [rating, setRating] = useState(null)
  const [comment, setComment] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | saved | error

  async function save(nextRating, nextComment = '') {
    setStatus('saving')

    try {
      await submitFeedback(answerId, nextRating, nextComment)
      setRating(nextRating)
      setStatus('saved')
    } catch (error) {
      console.error('Feedback failed:', error)
      setStatus('error')
    }
  }

  const saving = status === 'saving'

  return (
    <div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => save('up')}
          disabled={saving}
          aria-label="Good answer"
          aria-pressed={rating === 'up'}
          title="Good answer"
          className={`${buttonBase} ${
            rating === 'up'
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300'
          }`}
        >
          <ThumbUpIcon className="h-4 w-4" filled={rating === 'up'} />
        </button>

        <button
          type="button"
          onClick={() => save('down', rating === 'down' ? comment : '')}
          disabled={saving}
          aria-label="Bad answer"
          aria-pressed={rating === 'down'}
          title="Bad answer"
          className={`${buttonBase} ${
            rating === 'down'
              ? 'text-red-600 dark:text-red-400'
              : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300'
          }`}
        >
          <ThumbDownIcon className="h-4 w-4" filled={rating === 'down'} />
        </button>

        <span
          role="status"
          aria-live="polite"
          className={`ml-1 text-[11px] ${
            status === 'error'
              ? 'text-red-600 dark:text-red-400'
              : 'text-slate-400 dark:text-slate-500'
          }`}
        >
          {status === 'saving' && 'Saving...'}
          {status === 'saved' && 'Thanks for the feedback'}
          {status === 'error' && 'Could not save. Try again.'}
        </span>
      </div>

      {rating === 'down' && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            save('down', comment.trim())
          }}
          className="mt-1.5 flex items-center gap-2"
        >
          <label htmlFor={`feedback-comment-${answerId}`} className="sr-only">
            What was wrong with this answer? (optional)
          </label>
          <input
            id={`feedback-comment-${answerId}`}
            type="text"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            maxLength={1000}
            placeholder="What was wrong? (optional)"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:outline-none dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-indigo-500/30"
          />
          <button
            type="submit"
            disabled={saving}
            className="shrink-0 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:focus-visible:outline-indigo-400"
          >
            Send
          </button>
        </form>
      )}
    </div>
  )
}

export default FeedbackButtons
