import { useState } from 'react'

const MIN_LENGTH = 20

export default function QueryInput({ onSubmit, loading }) {
  const [value, setValue] = useState('')

  const trimmed = value.trim()
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_LENGTH

  const handleSubmit = (e) => {
    e.preventDefault()
    if (trimmed.length >= MIN_LENGTH) onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. Show total NPA for Q1 FY2024 across all banks"
          disabled={loading}
          className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-700 px-4 py-3 text-sm
                     text-gray-800 dark:text-gray-100
                     placeholder-gray-400 dark:placeholder-gray-500
                     shadow-sm outline-none transition
                     focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800
                     disabled:bg-gray-50 dark:disabled:bg-gray-800 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={loading || trimmed.length < MIN_LENGTH}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold
                     text-white shadow-sm transition hover:bg-indigo-700 active:scale-95
                     disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Running…
            </>
          ) : (
            <>Generate SQL →</>
          )}
        </button>
      </div>
      {tooShort && (
        <p className="text-xs text-amber-600 dark:text-amber-400 pl-1">
          Please enter more details — include the report or metric name and a time period (e.g. Q1 FY2024, March 2025).
        </p>
      )}
    </form>
  )
}
