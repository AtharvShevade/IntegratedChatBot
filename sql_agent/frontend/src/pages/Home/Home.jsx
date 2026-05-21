import { useState } from 'react'
import QueryInput from '../../components/QueryInput/QueryInput'
import VoiceRecorder from '../../components/VoiceRecorder/VoiceRecorder'
import SqlDisplay from '../../components/SqlDisplay/SqlDisplay'
import ResultsTable from '../../components/ResultsTable/ResultsTable'
import { useQuery } from '../../hooks/useQuery'

export default function Home({ darkMode, toggleDark }) {
  const [mode, setMode] = useState('text')
  const { status, result, error, submitText, submitVoice, reset } = useQuery()

  const loading = status === 'loading'

  const handleVoiceDone = (blob, filename) => {
    submitVoice(blob, filename)
  }

  const tabs = [
    { id: 'text', label: '⌨️  Text' },
    { id: 'voice', label: '🎤  Voice' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 font-sans transition-colors duration-200">
      {/* ── Top Nav ── */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm transition-colors duration-200">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚡</span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white">SQL Query Generator</h1>
              <p className="text-xs text-gray-400 dark:text-gray-400">Natural language → Oracle SQL</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Dark / Light toggle */}
            <button
              onClick={toggleDark}
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              className="flex items-center gap-2 rounded-full border border-gray-200 dark:border-gray-600
                         bg-gray-100 dark:bg-gray-700 px-3 py-1.5 text-sm font-medium
                         text-gray-600 dark:text-gray-300 transition hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              {darkMode ? '☀️ Light' : '🌙 Dark'}
            </button>

            <span className="rounded-full bg-indigo-50 dark:bg-indigo-900/40 px-3 py-1 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
              Oracle DB
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        {/* ── Input Card ── */}
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm transition-colors duration-200">
          {/* Tabs */}
          <div className="flex border-b border-gray-100 dark:border-gray-700">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => { setMode(tab.id); reset() }}
                className={`px-6 py-3 text-sm font-medium transition ${
                  mode === tab.id
                    ? 'border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-5">
            {mode === 'text' ? (
              <QueryInput onSubmit={(q) => submitText(q)} loading={loading} />
            ) : (
              <VoiceRecorder onRecordingDone={handleVoiceDone} loading={loading} />
            )}
          </div>
        </section>

        {/* ── Loading ── */}
        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-xl border border-indigo-100 dark:border-indigo-900 bg-indigo-50 dark:bg-indigo-900/20 py-8">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
              Retrieving schema → Generating SQL → Executing query…
            </span>
          </div>
        )}

        {/* ── Error ── */}
        {status === 'error' && error && (
          <div className="rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-900/20 px-5 py-4">
            <p className="font-semibold text-rose-700 dark:text-rose-400">Error</p>
            <p className="mt-1 text-sm text-rose-600 dark:text-rose-300">{error}</p>
          </div>
        )}

        {/* ── Results ── */}
        {result && status === 'success' && (
          <>
            {/* More info nudge — shown instead of results */}
            {result.needs_more_info ? (
              <div className="rounded-xl border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-5 py-4">
                <p className="font-semibold text-amber-700 dark:text-amber-400">More information needed</p>
                <p className="mt-1 text-sm text-amber-600 dark:text-amber-300">{result.more_info_hint}</p>
              </div>
            ) : (
            <>
            {/* Accuracy hint — soft informational banner */}
            {result.accuracy_hint && (
              <div className="rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 px-5 py-3 flex gap-3 items-start">
                <span className="mt-0.5 text-blue-500 dark:text-blue-400 text-base">ℹ️</span>
                <p className="text-sm text-blue-700 dark:text-blue-300">{result.accuracy_hint}</p>
              </div>
            )}

            {/* Voice transcript */}
            {'transcript' in result && (
              <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-5 py-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  Transcribed (English)
                </span>
                <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">{result.transcript}</p>
              </div>
            )}

            {/* Schema Match */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm transition-colors duration-200">
              <div className="border-b border-gray-100 dark:border-gray-700 px-4 py-3">
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">📊 Schema Match</span>
              </div>
              <div className="grid gap-4 p-4 sm:grid-cols-2">
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    Matched Tables
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.matched_tables.length ? (
                      result.matched_tables.map((t) => (
                        <span
                          key={t}
                          className="rounded-md bg-indigo-50 dark:bg-indigo-900/40 px-2.5 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300"
                        >
                          {t}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400">None</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    Matched Columns
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.matched_columns.length ? (
                      result.matched_columns.map((c) => (
                        <span
                          key={c}
                          className="rounded-md bg-gray-100 dark:bg-gray-700 px-2.5 py-1 text-xs font-mono text-gray-600 dark:text-gray-300"
                        >
                          {c}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400">None</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* SQL */}
            <SqlDisplay
              sql={result.sql}
              isValid={result.is_valid}
              validationReason={result.validation_reason}
            />

            {/* DB Results */}
            {result.is_valid && (
              <ResultsTable
                columns={result.columns}
                rows={result.rows}
                dbError={result.db_error}
              />
            )}
          </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
