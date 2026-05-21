export default function StatusBadge({ isValid, reason }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
          isValid
            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
            : 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300'
        }`}
      >
        {isValid ? (
          <>
            <span>✓</span> VALID
          </>
        ) : (
          <>
            <span>✗</span> INVALID
          </>
        )}
      </span>
      {!isValid && reason && (
        <span className="text-xs text-rose-600 dark:text-rose-400">{reason}</span>
      )}
    </div>
  )
}
