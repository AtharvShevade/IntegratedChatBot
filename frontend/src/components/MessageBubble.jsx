import { useState } from 'react'

// Programmatic fetch → blob → <a click> download.
// Works for both same-origin and proxied URLs; browser cannot override the filename.
function triggerBlobDownload(url, label) {
  const filename = (() => {
    try { return new URL(url, window.location.origin).searchParams.get('filename') || label } catch { return label }
  })()
  fetch(url)
    .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.blob() })
    .then((blob) => {
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href     = blobUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    })
    .catch((err) => console.error('[Download] failed:', err))
}

export default function MessageBubble({ role, text, data, options, resultType, sqlData, varianceData, labelA, labelB, llmSummary, instancesData, downloadUrl, downloadLabel, statusNote, onFollowUp, onSuggestion, onGuidedAction, onCompare }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const isUser    = role === 'user'
  const isError   = role === 'error'
  const isWelcome = role === 'welcome'

  if (isWelcome) {
    return <WelcomeCard onSuggestion={onSuggestion} onGuidedAction={onGuidedAction} />
  }

  if (role === 'sql_welcome') {
    return <SqlWelcomeCard />
  }

  // Guided action menu — large clickable cards
  if (!isUser && resultType === 'guided_menu') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <GuidedMenuCard text={text} options={options} onSelect={onSuggestion} />
      </div>
    )
  }

  // Guided input prompt — regular bubble + optional quick-pick chips
  if (!isUser && resultType === 'guided_input') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="assistant-msg-block">
          <div className="bubble assistant-bubble guided-prompt-bubble">
            <span className="guided-prompt-label">🧭 Guided</span>
            {(text ?? '').split('\n').map((line, i, arr) => (
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
            ))}
          </div>
          {options?.length > 0 && (
            <div className="welcome-suggestions option-chips">
              {options.map((opt) => (
                <button key={opt} className="suggestion-chip" onClick={() => onSuggestion?.(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // SQL result — full-width block, no bubble wrapper
  if (!isUser && resultType === 'sql_result' && sqlData) {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <SqlResultBlock data={sqlData} />
      </div>
    )
  }

  // Instance selection — interactive dropdown picker
  if (!isUser && resultType === 'instance_selection' && instancesData?.length > 0) {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <InstanceSelectionBlock
          instances={instancesData}
          headerText={text}
          onCompare={onCompare}
        />
      </div>
    )
  }

  // Variance table — rich table + LLM summary
  if (!isUser && resultType === 'variance_table' && varianceData?.length > 0) {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <VarianceTableBlock
          rows={varianceData}
          labelA={labelA}
          labelB={labelB}
          llmSummary={llmSummary}
          headerText={text}
        />
      </div>
    )
  }

  const chips = options?.length > 0 ? options : []

  // When chips are shown alongside text, strip the redundant numbered list
  // lines ("1. Name", "2. Name", ...) so options aren't shown twice.
  const displayText = chips.length > 0
    ? (text ?? '')
        .split('\n')
        .filter((l) => !/^\s*\d+\.\s/.test(l))
        .join('\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
    : (text ?? '')

  // Ask-previous-dates card — shows latest status then Yes/No chips
  if (!isUser && resultType === 'ask_previous') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="assistant-msg-block">
          <div className="bubble assistant-bubble">
            {displayText.split('\n').map((line, i, arr) => (
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
            ))}
          </div>
          {downloadUrl && (
            <button
              className="download-btn"
              onClick={() => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)}
            >
              ⬇ {downloadLabel || 'Download'}
            </button>
          )}
          <div className="bubble assistant-bubble" style={{ marginTop: 6, fontStyle: 'italic', fontSize: '0.88em' }}>
            Would you also like to check status for previous reporting dates?
          </div>
          <div className="welcome-suggestions option-chips sched-confirm-actions">
            {chips.map((opt) => (
              <button
                key={opt}
                className={`suggestion-chip${opt === 'Yes' ? ' chip-confirm' : ' chip-cancel'}`}
                onClick={() => onSuggestion?.(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Schedule confirmation card
  if (!isUser && resultType === 'sched_confirm') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="assistant-msg-block">
          <div className="bubble assistant-bubble sched-confirm-bubble">
            {displayText.split('\n').map((line, i, arr) => (
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
            ))}
          </div>
          <div className="welcome-suggestions option-chips sched-confirm-actions">
            {chips.map((opt) => (
              <button
                key={opt}
                className={`suggestion-chip${opt === 'Schedule' ? ' chip-confirm' : ' chip-cancel'}`}
                onClick={() => onSuggestion?.(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`bubble-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className={`avatar ${isError ? 'error-avatar' : 'assistant-avatar'}`}>
          {isError ? '!' : 'AI'}
        </div>
      )}

      <div className="assistant-msg-block">
        <div
          className={`bubble ${
            isUser ? 'user-bubble' : isError ? 'error-bubble' : 'assistant-bubble'
          }`}
        >
          {displayText.split('\n').map((line, i, arr) => (
            <span key={i}>
              {line}
              {i < arr.length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Disambiguation / date-selection chips */}
        {!isUser && chips.length > 0 && (
          <div className="welcome-suggestions option-chips">
            {chips.map((opt) => (
              <button
                key={opt}
                className="suggestion-chip"
                onClick={() => onSuggestion?.(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* Download button — rendered for final/ask_previous when a file is available */}
        {!isUser && downloadUrl && resultType !== 'ask_previous' && (
          <button
            className="download-btn"
            onClick={() => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)}
          >
            ⬇ {downloadLabel || 'Download'}
          </button>
        )}
      </div>

      {isUser && <div className="avatar user-avatar">You</div>}
    </div>
  )
}

// ── Welcome card ─────────────────────────────────────────────────────────────
const SUGGESTION_GROUPS = [
  {
    label:  '📋 Check report status',
    action: 'Check report status',
    chips:  [
      
    ],
  },
  {
    label:  '⚙️ Generate a report instance',
    action: 'Generate instance for a report',
    chips:  [
      
    ],
  },
  {
    label:  '🗓️ Schedule a report',
    action: 'Schedule a report',
    chips:  [],
  },
  {
    label:  '📊 Perform comparative analysis',
    action: 'Perform comparative analysis',
    chips:  [],
  },
  {
    label:  '🗄️ Retrieve data from database',
    action: 'Retrieve data from database',
    chips:  [],
  },
]

function WelcomeCard({ onSuggestion, onGuidedAction }) {
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble welcome-bubble">
        <p className="welcome-greeting">
          👋 Hi! I'm your Report Assistant.
        </p>
        <p className="welcome-subtext">I can help you with:</p>
        <ul className="welcome-list">
          <li>Checking the <strong>status</strong> of a report by name</li>
          <li><strong>Generating</strong> a new report instance for a date</li>
          <li><strong>Scheduling</strong> reports for a future date and time</li>
          <li>Performing <strong>comparative analysis</strong> on XBRL instances</li>
          <li>Retrieving data from the <strong>database</strong></li>
        </ul>
        <p className="welcome-subtext">Click a category to use guided mode, or type freely:</p>
        <div className="welcome-suggestion-groups">
          {SUGGESTION_GROUPS.map((group) => (
            <div key={group.label} className="welcome-suggestion-group">
              <button
                className="welcome-group-label-btn"
                onClick={() => onGuidedAction?.(group.action)}
                title={`Start guided flow: ${group.action}`}
              >
                {group.label}
                <span className="welcome-group-arrow">›</span>
              </button>
              {group.chips.length > 0 && (
                <div className="welcome-suggestions">
                  {group.chips.map((s) => (
                    <button
                      key={s}
                      className="suggestion-chip"
                      onClick={() => onSuggestion?.(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Clarify card ──────────────────────────────────────────────────────────────
// ── Shared label map ──────────────────────────────────────────────────────────
const ACTION_LABEL = {
  get_report_status: 'Report Status',
  get_report_error:  'Error Details',
}

// ── Results Panel ─────────────────────────────────────────────────────────────
function ResultsPanel({ results }) {
  const entries = Object.entries(results)
  if (entries.length === 0) return null
  return (
    <div className="results-panel">
      <div className="results-panel-label">Execution details</div>
      {entries.map(([action, output]) => (
        <ActionResult key={action} action={action} output={output} />
      ))}
    </div>
  )
}

// ── Status group → CSS class ──────────────────────────────────────────────────
const STATUS_CLASS = {
  success: 'status-success',
  warning: 'status-warning',
  failed:  'status-failed',
  pending: 'status-unknown',
  unknown: 'status-unknown',
}
const STATUS_ICON = {
  success: '✓',
  warning: '⚠',
  failed:  '✗',
  pending: '○',
  unknown: '?',
}

function ActionResult({ action, output }) {
  if (output?.error) {
    return (
      <div className="action-result action-result--error">
        <span className="ar-label">{ACTION_LABEL[action] ?? action}</span>
        <span className="ar-error">{output.error}</span>
      </div>
    )
  }

  // ── get_report_status ──────────────────────────────────────────────────────
  if (action === 'get_report_status' && output?.found) {
    const group      = output.status_group ?? 'unknown'
    const badgeClass = STATUS_CLASS[group]  ?? 'status-unknown'
    const badgeIcon  = STATUS_ICON[group]   ?? '?'
    return (
      <div className="action-result">
        <div className="ar-status-row">
          <span className={`status-badge ${badgeClass}`}>
            {badgeIcon} {output.status_label}
          </span>
          {output.form_id && <span className="ar-count">Form {output.form_id}</span>}
          {output.reporting_date && <span className="ar-count">Period: {output.reporting_date}</span>}
        </div>
        {output.start_time && (
          <div className="ar-meta-row">
            <span className="ar-meta-key">Started</span>
            <span className="ar-meta-val">{output.start_time}</span>
          </div>
        )}
        {output.end_time && (
          <div className="ar-meta-row">
            <span className="ar-meta-key">Completed</span>
            <span className="ar-meta-val">{output.end_time}</span>
          </div>
        )}
      </div>
    )
  }

  // ── get_report_error ───────────────────────────────────────────────────────
  if (action === 'get_report_error' && output?.found) {
    return (
      <div className="action-result">
        <span className="ar-label">{ACTION_LABEL[action]}</span>
        {(output.errors ?? []).map((e, i) => (
          <div key={i} className="ar-meta-row">
            <span className="ar-meta-key">{e.type}</span>
            <span className="ar-meta-val ar-error-path">{e.detail}</span>
          </div>
        ))}
      </div>
    )
  }

  // ── generic fallback ───────────────────────────────────────────────────────
  return null
}

// ── SQL Welcome Card ──────────────────────────────────────────────────────────
function SqlWelcomeCard() {
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble welcome-bubble sql-welcome-bubble">
        <p className="welcome-greeting">🗄️ SQL Data Query Mode</p>
        <p className="welcome-subtext">Ask me anything about the Oracle database in plain English.</p>
        <ul className="welcome-list">
          <li>I'll convert your question to SQL automatically</li>
          <li>Results are fetched live from Oracle DB</li>
          <li>Voice input is supported — press the mic</li>
        </ul>
        <p className="welcome-subtext">Try asking:</p>
        <div className="welcome-suggestions" style={{ marginTop: 6 }}>
          {[
            'Show NPA accounts with balance above 10 crore',
            'How many loans were disbursed last month?',
            'List all transactions for Q3 2024',
          ].map((s) => (
            <div key={s} className="suggestion-chip" style={{ cursor: 'default' }}>
              {s}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── SQL Result Block ──────────────────────────────────────────────────────────
function SqlResultBlock({ data }) {
  const {
    sql, is_valid, validation_reason, db_error,
    matched_tables = [], matched_columns = [],
    columns = [], rows = [],
  } = data

  return (
    <div className="sql-result-block">
      {/* Matched schema chips */}
      {matched_tables.length > 0 && (
        <div>
          <div className="sql-result-label">Schema Match</div>
          <div className="sql-result-chips">
            {matched_tables.map((t) => (
              <span key={t} className="sql-chip-table">{t}</span>
            ))}
            {matched_columns.slice(0, 6).map((c) => (
              <span key={c} className="sql-chip-col">{c}</span>
            ))}
            {matched_columns.length > 6 && (
              <span className="sql-chip-col">+{matched_columns.length - 6} more</span>
            )}
          </div>
        </div>
      )}

      {/* Generated SQL */}
      {sql && (
        <div>
          <div className="sql-result-label">Generated SQL</div>
          <pre className="sql-result-sql-box">{sql}</pre>
        </div>
      )}

      {/* Validation error */}
      {!is_valid && (
        <div className="sql-invalid-msg">
          ⚠ {validation_reason || 'SQL validation failed.'}
        </div>
      )}

      {/* DB error */}
      {db_error && (
        <div className="sql-db-error">⚠ DB error: {db_error}</div>
      )}

      {/* Results table */}
      {is_valid && !db_error && columns.length > 0 && (
        <div>
          <div className="sql-result-label">Query Results</div>
          <div className="sql-table-wrapper">
            <table className="sql-data-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci}>
                        {cell === null
                          ? <span className="sql-null-val">NULL</span>
                          : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sql-row-count">{rows.length} row{rows.length !== 1 ? 's' : ''} returned</div>
        </div>
      )}

      {/* Valid SQL but no rows */}
      {is_valid && !db_error && columns.length === 0 && (
        <div className="sql-db-error" style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none' }}>
          No rows returned.
        </div>
      )}
    </div>
  )
}

// ── Instance Selection Block ──────────────────────────────────────────────────
function InstanceSelectionBlock({ instances, headerText, onCompare }) {
  const NONE = ''
  const [sel1, setSel1] = useState(NONE)
  const [sel2, setSel2] = useState(NONE)
  const [error, setError] = useState('')

  // Build label for each instance — prefer the parsed label, fall back gracefully
  const labelFor = (inst) =>
    inst.label ||
    `${inst.reporting_date || '—'} | Generated: ${inst.run_at || '—'}`

  const handleCompare = () => {
    if (!sel1 || !sel2) {
      setError('Please select an instance in both dropdowns.')
      return
    }
    if (sel1 === sel2) {
      setError('Please select two different instances.')
      return
    }
    setError('')
    // Convert 1-based UI strings to 0-based indices for the /compare-execute endpoint
    onCompare?.(parseInt(sel1, 10) - 1, parseInt(sel2, 10) - 1)
  }

  return (
    <div className="inst-sel-block">
      <div className="inst-sel-header">{headerText}</div>

      <div className="inst-sel-dropdowns">
        {/* ── Dropdown 1 ── */}
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">Instance 1</label>
          <select
            className="inst-sel-select"
            value={sel1}
            onChange={(e) => { setSel1(e.target.value); setError('') }}
          >
            <option value="">— Select instance —</option>
            {instances.map((inst, idx) => (
              <option key={idx} value={String(idx + 1)}>
                {labelFor(inst)}
              </option>
            ))}
          </select>
        </div>

        {/* ── Dropdown 2 ── */}
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">Instance 2</label>
          <select
            className="inst-sel-select"
            value={sel2}
            onChange={(e) => { setSel2(e.target.value); setError('') }}
          >
            <option value="">— Select instance —</option>
            {instances.map((inst, idx) => (
              <option key={idx} value={String(idx + 1)} disabled={String(idx + 1) === sel1}>
                {labelFor(inst)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="inst-sel-error">{error}</div>}

      <button
        className="inst-sel-btn"
        disabled={!sel1 || !sel2 || sel1 === sel2}
        onClick={handleCompare}
      >
        Compare Instances
      </button>
    </div>
  )
}

// ── Variance Table Block ──────────────────────────────────────────────────────
function VarianceTableBlock({ rows, labelA, labelB, llmSummary, headerText }) {
  // Extract the first two lines from plain-text response as title/subtitle
  const lines = (headerText || '').split('\n')
  const title    = lines[0] || ''
  const subtitle = lines[1] || ''

  const fmtVal = (v) => {
    if (v === null || v === undefined) return '—'
    const abs = Math.abs(v)
    if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`
    if (abs >= 1_000) return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })
    return Number(v).toPrecision ? String(parseFloat(v.toFixed(4))) : String(v)
  }

  const fmtPct = (v) => {
    if (v === null || v === undefined) return 'N/A'
    return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
  }

  return (
    <div className="variance-block">
      {title    && <div className="variance-title">{title}</div>}
      {subtitle && <div className="variance-subtitle">{subtitle}</div>}

      <div className="variance-table-wrapper">
        <table className="variance-table">
          <thead>
            <tr>
              <th className="vt-concept-col">Concept</th>
              <th className="vt-num-col">{labelA}</th>
              <th className="vt-num-col">{labelB}</th>
              <th className="vt-num-col">Diff</th>
              <th className="vt-num-col">% Chg</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isPos = row.diff > 0
              const isNeg = row.diff < 0
              const diffCls = isPos ? 'vt-pos' : isNeg ? 'vt-neg' : ''
              return (
                <tr key={row.concept} className={row.significant ? 'vt-row-sig' : ''}>
                  <td className="vt-concept">
                    {row.significant && <span className="vt-sig-badge">⚠</span>}
                    {row.concept}
                  </td>
                  <td className="vt-num">{fmtVal(row.val_a)}</td>
                  <td className="vt-num">{fmtVal(row.val_b)}</td>
                  <td className={`vt-num ${diffCls}`}>{fmtVal(row.diff)}</td>
                  <td className={`vt-num ${diffCls}`}>{fmtPct(row.pct_change)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {llmSummary && (
        <div className="variance-summary">
          <div className="variance-summary-label">AI Analysis</div>
          <div className="variance-summary-text">
            {(() => {
              const bullets = llmSummary
                .split('\n')
                .map((l) => l.trim())
                .filter((l) => l.startsWith('* ') || l.startsWith('- ') || l.startsWith('• '))
                .map((l) => l.replace(/^[*\-•]\s+/, ''))
              if (bullets.length > 0) {
                return (
                  <ul className="variance-summary-bullets">
                    {bullets.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                )
              }
              // Fallback: plain text (e.g. model ignored bullet format)
              return llmSummary.split('\n').map((line, i) => (
                <span key={i}>{line}{i < llmSummary.split('\n').length - 1 && <br />}</span>
              ))
            })()}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Guided Action Menu Card ───────────────────────────────────────────────────
const GUIDED_ACTION_META = {
  'Check report status':           { icon: '📋', desc: 'Look up the latest status of any report' },
  'Generate instance for a report':{ icon: '⚙️',  desc: 'Trigger a new report instance for a period' },
  'Schedule a report':             { icon: '🗓️', desc: 'Schedule a report to run at a future date/time' },
  'Perform comparative analysis':  { icon: '📊', desc: 'Compare two XBRL instances period-over-period' },
  'Retrieve data from database':   { icon: '🗄️', desc: 'Query the Oracle database in plain English' },
}

function GuidedMenuCard({ text, options, onSelect }) {
  return (
    <div className="guided-menu-card">
      <p className="guided-menu-prompt">{text}</p>
      <div className="guided-menu-options">
        {(options || []).map((opt) => {
          const meta = GUIDED_ACTION_META[opt] || { icon: '•', desc: '' }
          return (
            <button
              key={opt}
              className="guided-action-btn"
              onClick={() => onSelect?.(opt)}
            >
              <span className="guided-action-icon">{meta.icon}</span>
              <div className="guided-action-body">
                <span className="guided-action-label">{opt}</span>
                {meta.desc && <span className="guided-action-desc">{meta.desc}</span>}
              </div>
              <span className="guided-action-arrow">›</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
