const LEVEL_STYLES = {
  high: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300',
  medium:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300',
  low: 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300',
}

const LEVEL_LABELS = { high: 'High', medium: 'Medium', low: 'Low' }

export const CONFIDENCE_EXPLANATION =
  'How closely the retrieved passage matches your question. It does not prove the answer is correct.'

// The level is always written out, so meaning never depends on colour alone.
function ConfidenceBadge({ confidence, level, prefix }) {
  if (confidence == null || !LEVEL_STYLES[level]) return null

  return (
    <span
      title={CONFIDENCE_EXPLANATION}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${LEVEL_STYLES[level]}`}
    >
      {prefix}
      {LEVEL_LABELS[level]} · {Math.round(confidence * 100)}%
    </span>
  )
}

export default ConfidenceBadge
