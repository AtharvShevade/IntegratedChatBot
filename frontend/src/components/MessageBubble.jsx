import React, { useState, useMemo, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import VarianceChartModal from './VarianceChartModal.jsx'

// ── Download helper ───────────────────────────────────────────────────────────
function triggerBlobDownload(url, label) {
  const filename = (() => {
    try {
      return new URL(url, window.location.origin).searchParams.get('filename') || label
    } catch {
      return label
    }
  })()
  fetch(url)
    .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.blob() })
    .then((blob) => {
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    })
    .catch((err) => console.error('[Download] failed:', err))
}

// ── Failed status codes (mirrors backend _FAILED_STATUSES) ───────────────────
const FAILED_STATUS_CODES = new Set([3, 5, 8, 10, 13])

// ── Detect error category from a list of error_details items ─────────────────
function detectErrorCategory(details) {
  if (!Array.isArray(details) || details.length === 0) return 'none'
  const first = details[0]
  const tag = first?._error_category ?? ''
  if (tag) return tag
  if (first?.rule_name !== undefined && first?.formula_type !== undefined) return 'formula_error'
  if (first?.error_class !== undefined && first?.concept !== undefined)    return 'dimensional'
  if (first?.table_info !== undefined)                                     return 'xbrl_schema_other'
  return 'unknown'
}

// ── Section label helpers ─────────────────────────────────────────────────────
const _CAT_META = {
  formula_error:       { icon: '⚙',  label: 'Formula Error',       color: '#9b59b6' },
  quality_check_error: { icon: '🔍', label: 'Quality Check',        color: '#e67e22' },
  specification_error: { icon: '📋', label: 'Specification Error',  color: '#c0392b' },
  xbrl_schema_other:   { icon: '⚠', label: 'Schema Error',         color: '#c0392b' },
  dimensional:         { icon: '📐', label: 'Dimensional Error',    color: '#2980b9' },
  unknown:             { icon: '⚠', label: 'Validation Error',     color: '#c0392b' },
}

function _catMeta(tag) {
  return _CAT_META[tag] ?? _CAT_META['unknown']
}

// ── Inline CSS ────────────────────────────────────────────────────────────────
const _ERROR_PANEL_STYLES = `
/* ── Error panel wrapper ─────────────────────────────────────────────────── */

`

// Inject styles once
if (typeof document !== 'undefined' && !document.getElementById('error-panel-styles')) {
  const s = document.createElement('style')
  s.id = 'error-panel-styles'
  s.textContent = _ERROR_PANEL_STYLES
  document.head.appendChild(s)
}

// ── DownloadButton ────────────────────────────────────────────────────────────
function DownloadButton({ downloadUrl, downloadLabel, className = 'download-btn' }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  if (!downloadUrl) return null
  return (
    <button
      className={className}
      onClick={() => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)}
    >
      ⬇ {downloadLabel || 'Download'}
    </button>
  )
}

// ── Summary category metadata ─────────────────────────────────────────────────
const _SUMMARY_CAT_META = {
  formula_error: { label: 'Formula Errors',      btnLabel: 'Explain Formula Errors',      cls: 'formula',   icon: '⚙' },
  xbrl_schema:   { label: 'XBRL Schema Errors',  btnLabel: 'Explain XBRL Schema Errors',  cls: 'xbrl',      icon: '⚠' },
  dimensional:   { label: 'Dimension Errors',    btnLabel: 'Explain Dimension Errors',    cls: 'dimension', icon: '📐' },
}
const _CAT_ORDER = ['formula_error', 'xbrl_schema', 'dimensional']

// ── ErrorSummaryPanelReadOnly ─────────────────────────────────────────────────
// Shown for non-4000-series failed reports.
// Displays error counts and download button only — no explain buttons.
function ErrorSummaryPanelReadOnly({ counts, downloadUrl, downloadLabel }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

  const activeCategories = _CAT_ORDER.filter(
    (cat) => counts && counts[cat] && counts[cat] > 0
  )

  return (
    <div className="error-summary-panel">
      <div className="error-summary-heading">⚠ Error Summary</div>
      <div className="error-summary-body">
        {activeCategories.length > 0 && (
          <div className="error-summary-counts">
            {activeCategories.map((cat) => {
              const meta = _SUMMARY_CAT_META[cat]
              return (
                <div key={cat} className={`error-count-chip ${meta.cls}`}>
                  <span>{meta.icon}</span>
                  <span>{meta.label}:</span>
                  <span className="error-count-num">{counts[cat]}</span>
                </div>
              )
            })}
          </div>
        )}
        <div className="error-summary-actions">
          {downloadUrl && (
            <button
              className="error-summary-dl-btn"
              onClick={() => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)}
            >
              ⬇ {downloadLabel || 'Download Error File'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── ErrorSummaryPanel ─────────────────────────────────────────────────────────
// Shown for 4000-series failed reports — counts + explain buttons.
function ErrorSummaryPanel({  counts, downloadUrl, downloadLabel, onExplainCategory, formId, reportName }) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const [loadingCat, setLoadingCat] = useState(null)

  const errorFilePath = counts?.error_file_path ?? ''
  const activeCategories = _CAT_ORDER.filter(
    (cat) => counts && counts[cat] && counts[cat] > 0
  )

  const handleExplain = async (cat) => {
    if (loadingCat) return
    setLoadingCat(cat)
    try {
      await onExplainCategory?.(cat, errorFilePath, formId, reportName)
    } finally {
      setLoadingCat(null)
    }
  }

  return (
    <div className="error-summary-panel">
      <div className="error-summary-heading">⚠ Error Summary</div>
      <div className="error-summary-body">
        {activeCategories.length > 0 && (
          <div className="error-summary-counts">
            {activeCategories.map((cat) => {
              const meta = _SUMMARY_CAT_META[cat]
              return (
                <div key={cat} className={`error-count-chip ${meta.cls}`}>
                  <span>{meta.icon}</span>
                  <span>{meta.label}:</span>
                  <span className="error-count-num">{counts[cat]}</span>
                </div>
              )
            })}
          </div>
        )}
        <div className="error-summary-actions">
          {activeCategories.map((cat) => {
            const meta = _SUMMARY_CAT_META[cat]
            const isLoading = loadingCat === cat
            return (
              <button
                key={cat}
                className={`explain-cat-btn ${meta.cls}`}
                onClick={() => handleExplain(cat)}
                disabled={!!loadingCat}
              >
                {isLoading
                  ? <><span className="btn-spinner" /> Generating…</>
                  : <>{meta.icon} {meta.btnLabel}</>
                }
              </button>
            )
          })}
          {downloadUrl && (
            <button
              className="error-summary-dl-btn"
              onClick={() => triggerBlobDownload(`${API_BASE}${downloadUrl}`, downloadLabel)}
            >
              ⬇ {downloadLabel || 'Download Error File'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── PlainTextErrorPanel ───────────────────────────────────────────────────────
function PlainTextErrorPanel({ details, errorMessages, downloadUrl, downloadLabel }) {
  const groups = useMemo(() => {
    const map = new Map()
    const push_item = (item) => {
      const cat     = item._error_category || 'unknown'
      const section = item.section || item.rule_name || ''
      const key     = `${cat}||${section}`
      if (!map.has(key)) {
        map.set(key, { cat, meta: _catMeta(cat), sectionName: section, items: [] })
      }
      const group = map.get(key)
      if (group.items.length < 5) group.items.push(item)
    }
    if (Array.isArray(details) && details.length > 0) {
      for (const err of details) {
        if (err?.rule_name !== undefined) {
          push_item({
            _error_category: err._error_category || 'formula_error',
            section:         err.rule_name,
            explanation:     err.explanation || err.business_rule || `Validation rule '${err.rule_name}' failed.`,
            raw_message:     err.business_rule || '',
          })
          continue
        }
        push_item({
          _error_category: err._error_category || 'unknown',
          section:         err.section || '',
          explanation:     err.explanation || err.message || '',
          raw_message:     err.message || err.col_0 || '',
        })
      }
    }
    if (map.size === 0 && Array.isArray(errorMessages) && errorMessages.length > 0) {
      const group = { cat: 'unknown', meta: _catMeta('unknown'), sectionName: '', items: [] }
      for (const msg of errorMessages.slice(0, 2)) {
        group.items.push({ explanation: msg, raw_message: '' })
      }
      map.set('fallback', group)
    }
    return [...map.values()]
  }, [details, errorMessages])

  if (groups.length === 0) return null

  return (
    <div className="error-panel-wrapper">
      {groups.map((group, gi) => {
        const color = group.meta.color
        return (
          <div key={gi} className="error-section-group">
            <div
              className="error-section-header"
              style={{ '--section-color': color, background: color }}
            >
              <span className="section-icon">{group.meta.icon}</span>
              <span className="section-name">
                {group.meta.label}
                {group.sectionName ? ` — ${group.sectionName}` : ''}
              </span>
            </div>
            {group.items.map((item, ii) => (
              <div
                key={ii}
                className="error-explanation-box"
                style={{ '--section-color': color, borderLeftColor: color }}
              >
                {item.explanation && (
                  <p className="error-explanation-text">{item.explanation}</p>
                )}
                {item.raw_message && item.raw_message !== item.explanation && (
                  <p className="error-explanation-raw" title={item.raw_message}>
                    {item.raw_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        )
      })}
      {downloadUrl && (
        <div className="error-details-actions">
          <DownloadButton
            downloadUrl={downloadUrl}
            downloadLabel={downloadLabel}
            className="error-details-dl-btn"
          />
        </div>
      )}
    </div>
  )
}

// ── DimensionalErrorPanel ─────────────────────────────────────────────────────
function DimensionalErrorPanel({ details, downloadUrl, downloadLabel }) {
  if (!details || details.length === 0) return null
  const color = _catMeta('dimensional').color
  return (
    <div className="error-panel-wrapper">
      <div className="error-section-group">
        <div
          className="error-section-header"
          style={{ '--section-color': color, background: color }}
        >
          <span className="section-icon">📐</span>
          <span className="section-name">Dimensional Validation Errors</span>
          <span className="error-section-count">{details.length}</span>
        </div>
        <ol className="dimensional-error-list">
          {details.map((err, i) => (
            <li key={i} className="dimensional-error-item">
              <div className="dimensional-error-explanation">
                {err.explanation || `Dimensional error detected for concept '${err.concept || 'unknown'}'.`}
              </div>
              {(err.concept || err.value || err.context) && (
                <div className="dimensional-error-meta">
                  {err.concept && <span className="dim-meta-chip">concept: {err.concept}</span>}
                  {err.value   && <span className="dim-meta-chip">value: {err.value}</span>}
                  {err.context && (
                    <span className="dim-meta-chip dim-meta-context" title={err.context}>
                      context: {err.context.length > 40 ? err.context.slice(0, 40) + '…' : err.context}
                    </span>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
        {downloadUrl && (
          <div className="error-details-actions">
            <DownloadButton downloadUrl={downloadUrl} downloadLabel={downloadLabel} className="error-details-dl-btn" />
          </div>
        )}
      </div>
    </div>
  )
}

// ── ErrorDetailsTablePanel ────────────────────────────────────────────────────
function ErrorDetailsTablePanel({ details, downloadUrl, downloadLabel, errorMessages }) {
  const tableRows = useMemo(() => details.map((err, i) => {
    const ti = err?.table_info ?? {}
    const db_table_name = (
      ti.db_table_name || err.db_tablename || err['db_tablename'] || err.table || ''
    ).toString().trim()
    const row_label = (
      ti.row_label || err.row_label || err['row_label(s)'] || err['row_label(s) '] || ''
    ).toString().trim()
    const context = (ti.context || err.context || '').toString().trim()
    const cell_code = (ti.cell_code || err.cellCode || err.cell || '').toString().trim()
    const validation_error = (
      ti.validation_error || err.message || err.col_0 || err.title || ''
    ).toString().trim()
    const explanation = (err.explanation || '').toString().trim()
    return { idx: i, db_table_name, row_label, context, cell_code, validation_error, explanation }
  }), [details])

  const filteredRows = tableRows.filter(
    (r) => r.db_table_name || r.row_label || r.context || r.cell_code || r.validation_error
  )
  const hasBacktrackedData = filteredRows.some(
    (r) => r.db_table_name || r.row_label || r.cell_code || r.validation_error
  )

  if (!hasBacktrackedData) {
    return (
      <PlainTextErrorPanel
        details={details}
        errorMessages={errorMessages}
        downloadUrl={downloadUrl}
        downloadLabel={downloadLabel}
      />
    )
  }

  return (
    <div className="error-details-panel">
      <div className="error-table-info-section">
        <div className="error-table-info-heading">📋 Validation Details</div>
        <div className="error-table-info-scroll">
          <table className="error-table-info-tbl">
            <thead>
              <tr>
                <th>DB Table Name</th>
                <th>Row Label</th>
                <th>Cell Code</th>
                <th>Error</th>
                <th>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((r) => (
                <tr key={r.idx}>
                  <td title={r.db_table_name}>{r.db_table_name || '—'}</td>
                  <td title={r.row_label}>{r.row_label || '—'}</td>
                  <td>{r.cell_code || '—'}</td>
                  <td className="vd-error-cell" title={r.explanation || r.validation_error}>
                    {r.validation_error || '—'}
                  </td>
                  <td className="vd-explanation-cell">
                    {r.explanation
                      ? (
                          <ul>
                            {r.explanation
                              .split(/(?<=[.!?])\s+/)
                              .filter(Boolean)
                              .map((point, i) => <li key={i}>{point}</li>)
                            }
                          </ul>
                        )
                      : '—'
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="error-details-actions">
        <DownloadButton downloadUrl={downloadUrl} downloadLabel={downloadLabel} className="error-details-dl-btn" />
      </div>
    </div>
  )
}

// ── ErrorDetailsPanel (router) ────────────────────────────────────────────────
function ErrorDetailsPanel({ details, errorMessages, downloadUrl, downloadLabel }) {
  if ((!details || details.length === 0) && (!errorMessages || errorMessages.length === 0)) {
    return <DownloadButton downloadUrl={downloadUrl} downloadLabel={downloadLabel} />
  }
  const category = detectErrorCategory(details)
  if (category === 'xbrl_schema_4000') {
    return (
      <ErrorDetailsTablePanel
        details={details}
        errorMessages={errorMessages}
        downloadUrl={downloadUrl}
        downloadLabel={downloadLabel}
      />
    )
  }
  if (category === 'dimensional') {
    return (
      <DimensionalErrorPanel
        details={details}
        downloadUrl={downloadUrl}
        downloadLabel={downloadLabel}
      />
    )
  }
  return (
    <PlainTextErrorPanel
      details={details}
      errorMessages={errorMessages}
      downloadUrl={downloadUrl}
      downloadLabel={downloadLabel}
    />
  )
}

// ── BubbleText ────────────────────────────────────────────────────────────────
function BubbleText({ text, errorDetails }) {
  const FAILURE_HEADING = 'Failure Reason(s):'
  const PENDING_MARKER  = 'Generating error explanations\u2026'
  const idx = (text ?? '').indexOf(FAILURE_HEADING)

  if ((text ?? '').includes(PENDING_MARKER) && (!errorDetails || errorDetails.length === 0)) {
    const beforePending = (text ?? '').replace(PENDING_MARKER, '').trimEnd()
    return (
      <>
        {beforePending.split('\n').map((line, i, arr) => (
          <span key={`b${i}`}>{line}{i < arr.length - 1 && <br />}</span>
        ))}
        <br />
        <span className="explanation-pending">⏳ Generating error explanations…</span>
      </>
    )
  }

  if (idx === -1) {
    return (text ?? '').split('\n').map((line, i, arr) => (
      <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
    ))
  }

  const before       = (text ?? '').slice(0, idx).replace(/\n+$/, '')
  const failureBlock = (text ?? '').slice(idx)

  const structuredItems = (() => {
    if (!Array.isArray(errorDetails) || errorDetails.length === 0) return []
    const items = []
    const seen  = new Set()
    for (const err of errorDetails) {
      if (err?.rule_name !== undefined) {
        const msg = (err.explanation || `Rule '${err.rule_name}' failed.`).trim()
        if (msg && !seen.has(msg)) {
          seen.add(msg)
          items.push({ cellCode: '', message: msg, label: msg })
        }
        if (items.length >= 5) break
        continue
      }
      const ti       = err?.table_info ?? {}
      const cellCode = (ti.cell_code || err.cellCode || err.cell || '').trim()
      const rawMsg   = (
        err.explanation || ti.validation_error || err.message || err.col_0 || err.title || ''
      ).trim()
      if (!rawMsg) continue
      const label = cellCode ? `${cellCode} → ${rawMsg}` : rawMsg
      if (!seen.has(label)) {
        seen.add(label)
        items.push({ cellCode, message: rawMsg, label })
      }
      if (items.length >= 5) break
    }
    return items
  })()

  const failureLines = failureBlock.split('\n')
  const bulletEnd    = failureLines.reduce((last, line, i) => (line.startsWith('•') ? i : last), 0)
  const rawBulletItems = structuredItems.length > 0 ? [] : (
    failureLines
      .slice(1, bulletEnd + 1)
      .map((l) => l.replace(/^•\s*/, '').trim())
      .filter(Boolean)
  )
  const afterLines = failureLines.slice(bulletEnd + 1).filter((l) => l.trim())

  return (
    <>
      {before.split('\n').map((line, i, arr) => (
        <span key={`b${i}`}>{line}{i < arr.length - 1 && <br />}</span>
      ))}
      {before && <br />}
      <div className="failure-reason-box">
        <div className="failure-reason-heading">⚠ Failure Reason(s)</div>
      </div>
      {afterLines.map((line, i) => (
        <span key={`a${i}`}><br />{line}</span>
      ))}
    </>
  )
}

// ── MessageBubble (main export) ───────────────────────────────────────────────
export default function MessageBubble({
  role, text, data, options, resultType, sqlData, dbQaData,
  varianceData, labelA, labelB, llmSummary, instancesData,
  downloadUrl, downloadLabel, statusNote,
  errorDetails,
  errorMessages,
  onFollowUp, onSuggestion, onGuidedAction, onCompare, onFeedback,
  onExplainCategory,
}) {
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const isUser    = role === 'user'
  const isError   = role === 'error'
  const isWelcome = role === 'welcome'

  if (isWelcome)              return <WelcomeCard onSuggestion={onSuggestion} onGuidedAction={onGuidedAction} />
  if (role === 'action_menu') return <ActionMenu onGuidedAction={onGuidedAction} />
  if (role === 'sql_welcome') return <SqlWelcomeCard />
  if (role === 'feedback_prompt')   return <FeedbackPrompt onFeedback={onFeedback} />
  if (role === 'feedback_positive') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="bubble assistant-bubble">Great! Glad I could help. 😊</div>
      </div>
    )
  }
  if (role === 'feedback_negative') return <SupportContact />

  if (!isUser && resultType === 'guided_menu') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <GuidedMenuCard text={text} options={options} onSelect={onSuggestion} />
      </div>
    )
  }

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

  if (!isUser && resultType === 'db_result' && sqlData) {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <SqlResultBlock data={sqlData} />
      </div>
    )
  }

  if (!isUser && resultType === 'db_qa_result') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <DbQaResultBlock data={dbQaData} fallbackText={text} />
      </div>
    )
  }

  if (!isUser && resultType === 'date_selection' && options?.length > 0) {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <InstanceDropdown
          headerText={text}
          options={options}
          instancesData={instancesData}
          onSelect={onSuggestion}
        />
      </div>
    )
  }

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
  const displayText = chips.length > 0
    ? (text ?? '').split('\n').filter((l) => !/^\s*\d+\.\s/.test(l)).join('\n').replace(/\n{3,}/g, '\n\n').trim()
    : (text ?? '')

  // ── Resolve errorDetails ───────────────────────────────────────────────────
  const resolvedErrorDetails = (
    (Array.isArray(errorDetails) && errorDetails.length > 0 ? errorDetails : null) ||
    (Array.isArray(data?.error_details) && data.error_details.length > 0 ? data.error_details : null) ||
    (Array.isArray(data?.errorDetails) && data.errorDetails.length > 0 ? data.errorDetails : null) ||
    []
  )

  // ── Resolve errorMessages ──────────────────────────────────────────────────
  const resolvedErrorMessages = (
    (Array.isArray(errorMessages) && errorMessages.length > 0 ? errorMessages : null) ||
    (Array.isArray(data?.error_messages) && data.error_messages.length > 0 ? data.error_messages : null) ||
    []
  )

  // ── Resolve error_category_counts ─────────────────────────────────────────
const errorCategoryCounts = data?.error_category_counts ?? null

// ── 4000-series gate ───────────────────────────────────────────────────────
const is4000Series = data?.is_4000_series ?? false

// ── Determine current status code ─────────────────────────────────────────
const statusCode = data?.status_code ?? null
const isFailed   = statusCode != null && FAILED_STATUS_CODES.has(Number(statusCode))

// TEMP DEBUG — move it here, AFTER all three are declared
console.log('[MessageBubble] data=', data)
console.log('[MessageBubble] is4000Series=', is4000Series)
console.log('[MessageBubble] errorCategoryCounts=', errorCategoryCounts)
console.log('[MessageBubble] isFailed=', isFailed, 'statusCode=', statusCode)

  // ── Decide which error panel to show ──────────────────────────────────────
  // Priority:
  //   1. If error_details already populated (user clicked Explain) → show detail panel
  //   2. Else if Failed + error_category_counts + is_4000_series → show summary panel with explain buttons
  //   3. Else if Failed + error_category_counts (non-4000) → show counts only, no explain buttons
  //   4. Else if error_messages → plain text fallback
  //   5. Else → just download button
  const errorPanel = (() => {
    if (resolvedErrorDetails.length > 0) {
      return (
        <ErrorDetailsPanel
          details={resolvedErrorDetails}
          errorMessages={resolvedErrorMessages}
          downloadUrl={downloadUrl}
          downloadLabel={downloadLabel}
        />
      )
    }
    if (isFailed && errorCategoryCounts) {
      if (is4000Series) {
        return (
          <ErrorSummaryPanel
            counts={errorCategoryCounts}
            downloadUrl={downloadUrl}
            downloadLabel={downloadLabel}
            onExplainCategory={onExplainCategory}
            formId={data?.form_id}
            reportName={data?.report_name}
          />
        )
      } else {
        return (
          <ErrorSummaryPanelReadOnly
            counts={errorCategoryCounts}
            downloadUrl={downloadUrl}
            downloadLabel={downloadLabel}
          />
        )
      }
    }
    if (resolvedErrorMessages.length > 0) {
      return (
        <PlainTextErrorPanel
          details={[]}
          errorMessages={resolvedErrorMessages}
          downloadUrl={downloadUrl}
          downloadLabel={downloadLabel}
        />
      )
    }
    if (downloadUrl) {
      return <DownloadButton downloadUrl={downloadUrl} downloadLabel={downloadLabel} />
    }
    return null
  })()

  // Ask-previous-dates card
  if (!isUser && resultType === 'ask_previous') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="assistant-msg-block">
          <div className="bubble assistant-bubble">
            <BubbleText text={displayText} errorDetails={resolvedErrorDetails} />
          </div>
          {errorPanel}
          <div className="bubble assistant-bubble" style={{ marginTop: 6, fontStyle: 'italic', fontSize: '0.88em' }}>
            Would you also like to check status for another reporting date?
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
        <div className={`bubble ${isUser ? 'user-bubble' : isError ? 'error-bubble' : 'assistant-bubble'}`}>
          <BubbleText text={displayText} errorDetails={resolvedErrorDetails} />
        </div>

        {/* Disambiguation / date-selection chips */}
        {!isUser && chips.length > 0 && (
          chips.length >= 5 ? (
            <ReportSearchDropdown options={chips} onSelect={onSuggestion} />
          ) : (
            <div className="welcome-suggestions option-chips">
              {chips.map((opt) => (
                <button key={opt} className="suggestion-chip" onClick={() => onSuggestion?.(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          )
        )}

        {/* Error panel or download button */}
        {!isUser && resultType !== 'ask_previous' && errorPanel}
      </div>

      {isUser && <div className="avatar user-avatar">You</div>}
    </div>
  )
}

// ── Status metadata helper ────────────────────────────────────────────────────
function getStatusMeta(code) {
  const n = parseInt(code, 10)
  if (n === 11)                       return { label: 'Success',     color: '#00C853' }
  if (n === 9)                        return { label: 'Approved',    color: '#006400' }
  if ([3, 5, 8, 10, 13].includes(n)) return { label: 'Failed',      color: '#FF4D4F' }
  if ([4, 6].includes(n))             return { label: 'In Progress', color: '#FF9800' }
  if (n === 0)                        return { label: 'Not Started', color: '#FFD600' }
  return { label: 'Unknown', color: '#9E9E9E' }
}

// ── Instance Dropdown ─────────────────────────────────────────────────────────
function InstanceDropdown({ headerText, options, instancesData, onSelect }) {
  const [selected, setSelected] = useState(options[0] ?? '')
  const statusMap = useMemo(() => {
    if (!instancesData?.length) return {}
    return Object.fromEntries(
      instancesData.map((item) => [item.label, getStatusMeta(item.status)])
    )
  }, [instancesData])
  const hasStatus = instancesData?.length > 0
  return (
    <div className="assistant-msg-block">
      <div className="bubble assistant-bubble">{headerText}</div>
      <div className="instance-listbox-card">
        <div className="instance-listbox">
          {options.map((opt) => {
            const meta = hasStatus ? statusMap[opt] : null
            return (
              <div
                key={opt}
                className={`instance-listbox-item${selected === opt ? ' selected' : ''}`}
                onClick={() => setSelected(opt)}
              >
                {meta && (
                  <span className="status-dot" style={{ background: meta.color }} title={meta.label} />
                )}
                <span className="instance-listbox-label">{opt}</span>
              </div>
            )
          })}
        </div>
        <button className="instance-dropdown-btn" onClick={() => onSelect?.(selected)}>
          Select ›
        </button>
      </div>
    </div>
  )
}

// ── Welcome Card ──────────────────────────────────────────────────────────────
const SUGGESTION_GROUPS = [
  { label: '📋 Check report status',          action: 'Check report status' },
  { label: '⚙️ Generate a report instance',   action: 'Generate instance for a report' },
  { label: '🗓️ Schedule a report',            action: 'Schedule a report' },
  { label: '📊 Perform comparative analysis', action: 'Perform comparative analysis' },
  { label: '🗄️ Retrieve data from database', action: 'Retrieve data from database' },
]

function WelcomeCard({ onSuggestion, onGuidedAction }) {
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble welcome-bubble">
        <p className="welcome-greeting">👋 Hi! I'm your Report Assistant.</p>
        <p className="welcome-subtext">I can help you with:</p>
        <ul className="welcome-list">
          <li>Checking the <strong>status</strong> of a report</li>
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
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Feedback Prompt ───────────────────────────────────────────────────────────
function FeedbackPrompt({ onFeedback }) {
  const [answered, setAnswered] = useState(false)
  const handleClick = (response) => {
    if (answered) return
    setAnswered(true)
    onFeedback?.(response)
  }
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="assistant-msg-block">
        <div className="bubble assistant-bubble">Was this helpful?</div>
        {!answered && (
          <div className="feedback-actions">
            <button className="feedback-btn feedback-yes" onClick={() => handleClick('yes')}>👍 Yes</button>
            <button className="feedback-btn feedback-no"  onClick={() => handleClick('no')}>👎 No</button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Support Contact ───────────────────────────────────────────────────────────
function SupportContact() {
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble support-contact-bubble">
        <p className="support-sorry">I'm sorry the experience wasn't helpful.</p>
        <p className="support-desc">If you're facing an issue, have a query, or want to report a problem, please contact our support team:</p>
        <div className="support-emails">
          <a href="mailto:support@company.com" className="support-email-link">📧 support@company.com</a>
          <a href="mailto:chatbot-support@company.com" className="support-email-link">📧 chatbot-support@company.com</a>
        </div>
      </div>
    </div>
  )
}

// ── Action Menu ───────────────────────────────────────────────────────────────
function ActionMenu({ onGuidedAction }) {
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble action-menu-bubble">
        <p className="action-menu-prompt">What would you like to do next?</p>
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
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Report Search Dropdown ────────────────────────────────────────────────────
function ReportSearchDropdown({ options, onSelect }) {
  const [query,    setQuery]    = useState('')
  const [isOpen,   setIsOpen]   = useState(false)
  const [selected, setSelected] = useState(null)
  const containerRef = useRef(null)
  const filtered = query.trim()
    ? options.filter((o) => o.toLowerCase().includes(query.toLowerCase()))
    : options
  useEffect(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])
  const handleChoose = (opt) => {
    setSelected(opt); setIsOpen(false); setQuery(''); onSelect?.(opt)
  }
  return (
    <div className="rsd-wrapper" ref={containerRef}>
      <div
        className={`rsd-control${isOpen ? ' rsd-open' : ''}`}
        onClick={() => setIsOpen((o) => !o)}
      >
        {selected
          ? <span className="rsd-value">{selected}</span>
          : <span className="rsd-placeholder">Select Report Name</span>
        }
        <span className="rsd-arrow">{isOpen ? '▲' : '▼'}</span>
      </div>
      {isOpen && (
        <div className="rsd-menu">
          <div className="rsd-search-wrap">
            <input
              autoFocus
              className="rsd-search"
              placeholder="Type to filter…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <ul className="rsd-list">
            {filtered.length === 0
              ? <li className="rsd-no-results">No matches</li>
              : filtered.map((opt) => (
                  <li key={opt} className="rsd-item" onClick={() => handleChoose(opt)}>{opt}</li>
                ))
            }
          </ul>
        </div>
      )}
    </div>
  )
}

// ── SQL Result Block ──────────────────────────────────────────────────────────
function SqlResultBlock({ data }) {
  const {
    sql, is_valid, validation_reason, db_error,
    matched_tables = [], matched_columns = [],
    columns = [], rows = [],
    accuracy_hint = null,
    needs_more_info = false,
    more_info_hint = null,
  } = data
  return (
    <div className="sql-result-block">
      {matched_tables.length > 0 && (
        <div>
          <div className="sql-result-label">Schema Match</div>
          <div className="sql-result-chips">
            {matched_tables.map((t) => <span key={t} className="sql-chip-table">{t}</span>)}
            {matched_columns.slice(0, 6).map((c) => <span key={c} className="sql-chip-col">{c}</span>)}
            {matched_columns.length > 6 && <span className="sql-chip-col">+{matched_columns.length - 6} more</span>}
          </div>
        </div>
      )}
      {sql && (
        <div>
          <div className="sql-result-label">Generated SQL</div>
          <pre className="sql-result-sql-box">{sql}</pre>
        </div>
      )}
      {!is_valid && <div className="sql-invalid-msg">⚠ {validation_reason || 'SQL validation failed.'}</div>}
      {db_error  && <div className="sql-db-error">⚠ DB error: {db_error}</div>}
      {is_valid && !db_error && columns.length > 0 && (
        <div>
          <div className="sql-result-label">Query Results</div>
          <div className="sql-table-wrapper">
            <table className="sql-data-table">
              <thead>
                <tr>{columns.map((col) => <th key={col}>{col}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci}>{cell === null ? <span className="sql-null-val">NULL</span> : String(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sql-row-count">{rows.length} row{rows.length !== 1 ? 's' : ''} returned</div>
        </div>
      )}
      {is_valid && !db_error && columns.length === 0 && (
        <div className="sql-db-error" style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none' }}>
          No rows returned.
        </div>
      )}
      {accuracy_hint && (
        <div className="sql-accuracy-hint">💡 {accuracy_hint}</div>
      )}
      {needs_more_info && more_info_hint && (
        <div className="sql-more-info-hint"><strong>Need more detail:</strong><br />{more_info_hint}</div>
      )}
    </div>
  )
}

// ── DB QA Result Block ────────────────────────────────────────────────────────
function DbQaResultBlock({ data, fallbackText }) {
  if (!data || (data.records?.length === 0 && !data.summary)) {
    return <div className="bubble assistant-bubble">{fallbackText || 'No data found.'}</div>
  }
  const {
    label, summary,
    cols = [], headers = [], records = [],
    is_count,
    tableNames = [], rowLabels = [], contexts = [], cellCodes = [],
  } = data
  if (records.length === 0) return <div className="bubble assistant-bubble">{summary || fallbackText}</div>
  const hasStructuredMeta = tableNames.length || rowLabels.length || contexts.length || cellCodes.length
  if (hasStructuredMeta) {
    return (
      <div className="dbqa-block structured-dbqa">
        {label && (
          <div className="dbqa-header-row">
            <span className="dbqa-label">{label}</span>
            <span className="dbqa-record-count">{records.length} records</span>
          </div>
        )}
        <div className="dbqa-table-wrapper">
          <table className="dbqa-table">
            <thead>
              <tr><th>DB TableName</th><th>Row Label(s)</th><th>Context</th><th>Cell Code</th></tr>
            </thead>
            <tbody>
              {records.map((_, i) => (
                <tr key={i}>
                  <td>{tableNames[i] ?? '—'}</td>
                  <td>{rowLabels[i] ?? '—'}</td>
                  <td>{contexts[i] ?? '—'}</td>
                  <td>{cellCodes[i] ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {summary && <div className="dbqa-summary">{summary}</div>}
      </div>
    )
  }
  if (is_count) {
    const rec = records[0]
    return (
      <div className="dbqa-block">
        <div className="dbqa-count-row">
          {cols.map((c, i) => (
            <div key={c} className="dbqa-count-card">
              <div className="dbqa-count-val">{rec[c] ?? '—'}</div>
              <div className="dbqa-count-label">{headers[i]}</div>
            </div>
          ))}
        </div>
        {summary && <div className="dbqa-summary">{summary}</div>}
      </div>
    )
  }
  if (records.length === 1) {
    const rec = records[0]
    return (
      <div className="dbqa-block">
        <div className="dbqa-kv-list">
          {cols.map((c, i) => (
            <div key={c} className="dbqa-kv-row">
              <span className="dbqa-kv-key">{headers[i]}</span>
              <span className="dbqa-kv-val">{rec[c] ?? '—'}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="dbqa-block">
      {label && (
        <div className="dbqa-header-row">
          <span className="dbqa-label">{label}</span>
          <span className="dbqa-record-count">{records.length} records</span>
        </div>
      )}
      <div className="dbqa-table-wrapper">
        <table className="dbqa-table">
          <thead>
            <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {records.map((rec, ri) => (
              <tr key={ri}>
                {cols.map((c) => <td key={c}>{rec[c] ?? '—'}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {summary && <div className="dbqa-summary">{summary}</div>}
    </div>
  )
}

// ── Instance Selection Block ──────────────────────────────────────────────────
function InstanceSelectionBlock({ instances, headerText, onCompare }) {
  const NONE = ''
  const [sel1, setSel1] = useState(NONE)
  const [sel2, setSel2] = useState(NONE)
  const [error, setError] = useState('')
  const labelFor = (inst) =>
    inst.label || `${inst.reporting_date || '—'} | Generated: ${inst.run_at || '—'}`
  const handleCompare = () => {
    if (!sel1 || !sel2)  { setError('Please select an instance in both dropdowns.'); return }
    if (sel1 === sel2)   { setError('Please select two different instances.'); return }
    setError('')
    onCompare?.(parseInt(sel1, 10) - 1, parseInt(sel2, 10) - 1)
  }
  return (
    <div className="inst-sel-block">
      <div className="inst-sel-header">{headerText}</div>
      <div className="inst-sel-dropdowns">
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">Instance 1</label>
          <select className="inst-sel-select" value={sel1} onChange={(e) => { setSel1(e.target.value); setError('') }}>
            <option value="">— Select instance —</option>
            {instances.map((inst, idx) => <option key={idx} value={String(idx + 1)}>{labelFor(inst)}</option>)}
          </select>
        </div>
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">Instance 2</label>
          <select className="inst-sel-select" value={sel2} onChange={(e) => { setSel2(e.target.value); setError('') }}>
            <option value="">— Select instance —</option>
            {instances.map((inst, idx) => (
              <option key={idx} value={String(idx + 1)} disabled={String(idx + 1) === sel1}>{labelFor(inst)}</option>
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
const SEV_CFG = {
  critical: { label: 'C', title: 'Critical', cls: 'vt-sev-critical' },
  high:     { label: 'H', title: 'High',     cls: 'vt-sev-high'     },
  medium:   { label: 'M', title: 'Medium',   cls: 'vt-sev-medium'   },
  low:      { label: 'L', title: 'Low',      cls: 'vt-sev-low'      },
}

function fmtFinancial(v) {
  if (v === null || v === undefined) return '—'
  if (v === 0) return '0'
  const abs = Math.abs(v)
  if (abs >= 1e12)  return `${(v / 1e12).toFixed(2)}T`
  if (abs >= 1e9)   return `${(v / 1e9).toFixed(2)}B`
  if (abs >= 1e6)   return `${(v / 1e6).toFixed(2)}M`
  if (abs >= 1e3)   return `${(v / 1e3).toFixed(2)}K`
  if (abs >= 1)     return v.toFixed(2)
  if (abs >= 0.001) return v.toFixed(4)
  const places = Math.min(10, Math.max(4, Math.ceil(-Math.log10(abs)) + 3))
  return v.toFixed(places)
}
function fmtRaw(v) {
  if (v === null || v === undefined) return '—'
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 6 })
}
function fmtPctFin(v) {
  if (v === null || v === undefined) return 'N/A'
  const abs = Math.abs(v)
  if (abs > 100_000) return `${v > 0 ? '+' : ''}Extreme ${v > 0 ? '↑' : '↓'}`
  if (abs > 10_000)  return `${v > 0 ? '+' : ''}Very High`
  if (abs > 1_000)   return `${v > 0 ? '+' : ''}>1,000%`
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}

function VarianceTableBlock({ rows, labelA, labelB, llmSummary, headerText }) {
  const [showChart, setShowChart] = useState(false)
  const [sortBy,    setSortBy]    = useState(null)
  const [sortDir,   setSortDir]   = useState('desc')
  const lines    = (headerText || '').split('\n')
  const title    = lines[0] || ''
  const subtitle = lines[1] || ''
  const SEV_ORDER = { critical: 4, high: 3, medium: 2, low: 1 }
  const sortedRows = useMemo(() => {
    if (!sortBy) return rows
    const dir = sortDir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      if (sortBy === 'concept')  return dir * (a.concept ?? '').localeCompare(b.concept ?? '')
      if (sortBy === 'val_a')    return dir * ((a.val_a ?? 0) - (b.val_a ?? 0))
      if (sortBy === 'val_b')    return dir * ((a.val_b ?? 0) - (b.val_b ?? 0))
      if (sortBy === 'diff')     return dir * ((a.diff ?? 0) - (b.diff ?? 0))
      if (sortBy === 'pct')      return dir * (Math.abs(a.pct_change ?? 0) - Math.abs(b.pct_change ?? 0))
      if (sortBy === 'severity') return dir * ((SEV_ORDER[a.severity] ?? 0) - (SEV_ORDER[b.severity] ?? 0))
      return 0
    })
  }, [rows, sortBy, sortDir])
  const handleSort = (col) => {
    if (sortBy === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setSortDir('desc') }
  }
  const sortIcon = (col) => {
    if (sortBy !== col) return <span className="vt-sort-icon">⇅</span>
    return <span className="vt-sort-icon">{sortDir === 'asc' ? '↑' : '↓'}</span>
  }
  return (
    <div className="variance-block">
      {title    && <div className="variance-title">{title}</div>}
      {subtitle && <div className="variance-subtitle">{subtitle}</div>}
      <div className="variance-table-wrapper">
        <table className="variance-table">
          <thead>
            <tr>
              <th className="vt-concept-col vt-sortable" onClick={() => handleSort('concept')}>Concept {sortIcon('concept')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('val_a')}>{labelA} {sortIcon('val_a')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('val_b')}>{labelB} {sortIcon('val_b')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('diff')}>Diff {sortIcon('diff')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('pct')}>% Chg {sortIcon('pct')}</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, rowIdx) => {
              const isPos   = (row.diff ?? 0) > 0
              const isNeg   = (row.diff ?? 0) < 0
              const diffCls = isPos ? 'vt-pos' : isNeg ? 'vt-neg' : ''
              const rowCls  = [
                row.significant  ? 'vt-row-sig' : '',
                row.sign_change  ? 'vt-row-sign-change' : '',
                rowIdx % 2 === 0 ? '' : 'vt-row-alt',
              ].filter(Boolean).join(' ')
              const anomalyText  = row.anomaly_flags?.length ? `Anomalies: ${row.anomaly_flags.join(', ')}` : ''
              const conceptTitle = [
                row.concept,
                row.context_key && row.context_key !== 'BASE' ? `Context: ${row.context_key}` : '',
                row.unit ? `Unit: ${row.unit}` : '',
                anomalyText,
              ].filter(Boolean).join('\n')
              const unitLabel = row.unit ? ` ${row.unit}` : ''
              const tipA = `Raw: ${fmtRaw(row.val_a)}${unitLabel}`
              const tipB = `Raw: ${fmtRaw(row.val_b)}${unitLabel}`
              const tipD = `Raw diff: ${fmtRaw(row.diff)}${unitLabel}`
              let signNote = null
              if (row.sign_change) {
                const notation = (row.val_a ?? 0) > 0 ? '−→+' : '+→−'
                signNote = <span className="vt-sign-note" title={`Direction reversed: ${notation}`}>{notation}</span>
              }
              const sev      = SEV_CFG[row.severity]
              const sevBadge = sev
                ? <span className={`vt-severity-badge ${sev.cls}`} title={`Severity: ${sev.title}`}>{sev.label}</span>
                : null
              return (
                <tr key={rowIdx} className={rowCls}>
                  <td className="vt-concept">
                    {row.significant && <span className="vt-sig-badge" title="High variance">⚠</span>}
                    <span className="vt-concept-text" title={conceptTitle}>{row.concept ?? ''}</span>
                    {signNote}
                  </td>
                  <td className="vt-num" title={tipA}>{fmtFinancial(row.val_a)}</td>
                  <td className="vt-num" title={tipB}>{fmtFinancial(row.val_b)}</td>
                  <td className={`vt-num ${diffCls}`} title={tipD}>{fmtFinancial(row.diff)}</td>
                  <td className={`vt-num ${diffCls}`}>{fmtPctFin(row.pct_change)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {llmSummary && (
        <div className="variance-summary">
          <div className="variance-summary-header">
            <div className="variance-summary-label">AI Analysis</div>
            <button className="vc-visualize-btn" onClick={() => setShowChart(true)} title="Open chart visualisation">📊 Visualize</button>
          </div>
          <div className="variance-summary-text">
            <ReactMarkdown>
              {llmSummary.replace(/^AI\s+Summary:\s*/i, '').split('\n').map((l) => l.replace(/^•\s*/, '- ')).join('\n')}
            </ReactMarkdown>
          </div>
        </div>
      )}
      {showChart && (
        <VarianceChartModal rows={rows} labelA={labelA} labelB={labelB} onClose={() => setShowChart(false)} />
      )}
    </div>
  )
}

// ── Guided Action Menu Card ───────────────────────────────────────────────────
const GUIDED_ACTION_META = {
  'Check report status':            { icon: '📋', desc: 'Look up the latest status of any report' },
  'Generate instance for a report': { icon: '⚙️', desc: 'Trigger a new report instance for a period' },
  'Schedule a report':              { icon: '🗓️', desc: 'Schedule a report to run at a future date/time' },
  'Perform comparative analysis':   { icon: '📊', desc: 'Compare two XBRL instances period-over-period' },
  'Retrieve data from database':    { icon: '🗄️', desc: 'Query the Oracle database in plain English' },
}

function GuidedMenuCard({ text, options, onSelect }) {
  return (
    <div className="guided-menu-card">
      <p className="guided-menu-prompt">{text}</p>
      <div className="guided-menu-options">
        {(options || []).map((opt) => {
          const meta = GUIDED_ACTION_META[opt] || { icon: '•', desc: '' }
          return (
            <button key={opt} className="guided-action-btn" onClick={() => onSelect?.(opt)}>
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