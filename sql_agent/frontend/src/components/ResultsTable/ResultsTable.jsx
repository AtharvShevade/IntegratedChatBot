export default function ResultsTable({ columns, rows, dbError }) {
  if (dbError) {
    return (
      <div className="rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-900/20 px-4 py-3">
        <p className="text-sm font-semibold text-rose-700 dark:text-rose-400">Database Error</p>
        <p className="mt-1 text-sm text-rose-600 dark:text-rose-300">{dbError}</p>
      </div>
    )
  }

  if (!columns.length) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-6 text-center text-sm text-gray-400">
        Query was not executed or returned no schema.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm transition-colors duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 py-3">
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          Results
          <span className="ml-2 rounded-full bg-indigo-100 dark:bg-indigo-900/40 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
            {rows.length} row{rows.length !== 1 ? 's' : ''}
          </span>
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {rows.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-gray-400">(no rows returned)</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="px-4 py-3 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {rows.map((row, ri) => (
                <tr key={ri} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-4 py-3 whitespace-nowrap text-gray-700 dark:text-gray-300 max-w-xs truncate"
                      title={cell === null ? 'NULL' : String(cell)}
                    >
                      {cell === null ? (
                        <span className="italic text-gray-400 dark:text-gray-500">NULL</span>
                      ) : (
                        String(cell)
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
