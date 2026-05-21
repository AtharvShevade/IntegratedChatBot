import { useState } from 'react'
import StatusBadge from '../StatusBadge/StatusBadge'

export default function SqlDisplay({ sql, isValid, validationReason }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm transition-colors duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">Generated SQL</span>
          <StatusBadge isValid={isValid} reason={validationReason} />
        </div>
        <button
          onClick={handleCopy}
          className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400
                     transition hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-200"
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
      </div>

      {/* SQL code block */}
      <pre className="overflow-x-auto p-4 font-mono text-sm leading-relaxed text-gray-800 dark:text-gray-200">
        <code>{sql || '— no SQL generated —'}</code>
      </pre>
    </div>
  )
}
