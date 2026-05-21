import { useVoiceRecorder } from '../../hooks/useVoiceRecorder'

export default function VoiceRecorder({ onRecordingDone, loading }) {
  const { state, audioBlob, mimeType, start, stop, reset, error } = useVoiceRecorder()

  const handleSubmit = () => {
    if (!audioBlob) return
    const ext = mimeType.split('/')[1]?.split(';')[0] ?? 'webm'
    onRecordingDone(audioBlob, `recording.${ext}`)
  }

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {state === 'idle' && (
          <button
            onClick={start}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-rose-600 px-5 py-3 text-sm font-semibold
                       text-white shadow-sm transition hover:bg-rose-700 active:scale-95
                       disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="h-3 w-3 rounded-full bg-white" />
            Start Recording
          </button>
        )}

        {state === 'recording' && (
          <button
            onClick={stop}
            className="flex items-center gap-2 rounded-lg bg-gray-700 dark:bg-gray-600 px-5 py-3 text-sm font-semibold
                       text-white shadow-sm transition hover:bg-gray-800 dark:hover:bg-gray-500 active:scale-95 animate-pulse"
          >
            <span className="h-3 w-3 rounded-full bg-rose-400" />
            Stop Recording
          </button>
        )}

        {state === 'done' && (
          <>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold
                         text-white shadow-sm transition hover:bg-indigo-700 active:scale-95
                         disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Processing…
                </>
              ) : (
                <>🚀 Generate SQL from Recording</>
              )}
            </button>

            <button
              onClick={reset}
              disabled={loading}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-3 text-sm
                         text-gray-600 dark:text-gray-300
                         transition hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              Re-record
            </button>
          </>
        )}
      </div>

      {/* Recording indicator */}
      {state === 'recording' && (
        <p className="flex items-center gap-2 text-sm text-rose-600 dark:text-rose-400">
          <span className="inline-block h-2 w-2 animate-ping rounded-full bg-rose-500" />
          Recording… speak your query. Click Stop when done or wait for silence.
        </p>
      )}

      {/* Audio preview */}
      {state === 'done' && audioBlob && (
        <div className="space-y-1">
          <p className="text-xs text-gray-500 dark:text-gray-400">Preview your recording:</p>
          <audio
            controls
            src={URL.createObjectURL(audioBlob)}
            className="h-8 w-full"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="rounded-md bg-rose-50 dark:bg-rose-900/20 px-3 py-2 text-sm text-rose-700 dark:text-rose-400">{error}</p>
      )}
    </div>
  )
}
