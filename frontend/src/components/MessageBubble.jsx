import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useT, LANGUAGES, OPTION_LABELS } from '../i18n.js'
import VarianceChartModal from './VarianceChartModal.jsx'
import { fetchCompareSummary, stopRequest } from '../services/api.js'

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
    .catch(() => {
      // Ignore download failures in the UI; they are handled elsewhere.
    })
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
  const t = useT()
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
// Built per-render so the labels follow the selected language. This CANNOT be
// a module-level constant: t() would run at import time, before any React
// context exists. The category KEY (formula_error / xbrl_schema / dimensional)
// is the backend value and never changes.
const summaryCatMeta = (t) => ({
  formula_error: { label: t('errors.category.formulaErrors'),   btnLabel: t('errors.explainFormula'),   cls: 'formula',   icon: '⚙' },
  xbrl_schema:   { label: t('errors.category.schemaErrors'),    btnLabel: t('errors.explainSchema'),    cls: 'xbrl',      icon: '⚠' },
  dimensional:   { label: t('errors.category.dimensionErrors'), btnLabel: t('errors.explainDimension'), cls: 'dimension', icon: '📐' },
})
const _CAT_ORDER = ['formula_error', 'xbrl_schema', 'dimensional']

// ── ErrorSummaryPanel ─────────────────────────────────────────────────────────
// Counts are always shown for every active category. An "Explain" button is
// only rendered for categories in explainableCategories — 4000-series
// reports pass every category (unchanged); non-4000-series reports pass
// only the categories with a working non-backtracking explain flow behind
// them (currently just formula_error — see backend/tools/formula_error_generic.py).
// Categories left out of the list still show their count, just without a button.
function ErrorSummaryPanel({  counts, downloadUrl, downloadLabel, onExplainCategory, formId, reportName, explainableCategories = _CAT_ORDER }) {
  const t = useT()
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const [loadingCat, setLoadingCat] = useState(null)

  const errorFilePath = counts?.error_file_path ?? ''
  const activeCategories = _CAT_ORDER.filter(
    (cat) => counts && counts[cat] && counts[cat] > 0
  )
  const explainableActiveCategories = activeCategories.filter(
    (cat) => explainableCategories.includes(cat)
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
      <div className="error-summary-heading">⚠ {t('errors.summaryHeading')}</div>
      <div className="error-summary-body">
        {activeCategories.length > 0 && (
          <div className="error-summary-counts">
            {activeCategories.map((cat) => {
              const meta = summaryCatMeta(t)[cat]
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
          {explainableActiveCategories.map((cat) => {
            const meta = summaryCatMeta(t)[cat]
            const isLoading = loadingCat === cat
            return (
              <button
                key={cat}
                className={`explain-cat-btn ${meta.cls}`}
                onClick={() => handleExplain(cat)}
                disabled={!!loadingCat}
              >
                {isLoading
                  ? <><span className="btn-spinner" /> {t('common.generating')}</>
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
              ⬇ {downloadLabel || t('errors.downloadReport')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── ExplainNextErrorsButton ───────────────────────────────────────────────────
// Rendered under a batch's result once the backend reports more unexplained
// errors remain (data.has_more). Re-requests the SAME category+file at
// nextOffset — the backend never re-explains errors already covered by an
// earlier batch, so clicking this can never repeat a previously-shown error.
function ExplainNextErrorsButton({ category, errorFilePath, formId, reportName, nextOffset, onExplainCategory }) {
  const t = useT()
  const [loading, setLoading] = useState(false)
  const meta = summaryCatMeta(t)[category] || { icon: '⚙', label: category }

  const handleClick = async () => {
    if (loading) return
    setLoading(true)
    try {
      await onExplainCategory?.(category, errorFilePath, formId, reportName, nextOffset)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="explain-next-errors-wrap">
      <button
        className={`explain-cat-btn ${meta.cls || ''}`}
        onClick={handleClick}
        disabled={loading}
      >
        {loading ? <><span className="btn-spinner" /> {t('common.generating')}</> : <>{meta.icon} {t('errors.explainNext')}</>}
      </button>
    </div>
  )
}

// ── Formula error explanation: structured card rendering ─────────────────────
// The backend explanation is one markdown string with a known, consistent
// shape (title / paragraph / bullet stats / bullet locations / fix) built by
// report_lookup.py's _render_*_explanation* functions. Parsing it into
// typed blocks lets each part get real layout (a stats grid, key-value
// location rows, a distinct fix callout) that plain ReactMarkdown text
// can't produce — without requiring any backend/API change, since this
// parses the exact same string the API already returns.
function _parseFormulaBulletItem(line) {
  const body = line.replace(/^- /, '')
  const boldMatch = body.match(/^\*\*(.+?):\*\*\s*(.+)$/)
  if (boldMatch) return { label: boldMatch[1], value: boldMatch[2] }
  const plainMatch = body.match(/^([A-Za-z ]+):\s*(.+)$/)
  if (plainMatch) return { label: plainMatch[1], value: plainMatch[2].replace(/`/g, '') }
  return { label: '', value: body }
}

function _parseFormulaExplanationBlocks(text) {
  if (!text) return []
  const blocks = text.trim().split(/\n{2,}/).map((b) => b.trim()).filter(Boolean)
  const parsed = []
  for (const block of blocks) {
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean)
    if (lines.length === 0) continue

    const titleMatch = lines[0].match(/^❌\s*\*\*(.+?)\*\*\s*$/)
    if (titleMatch && lines.length === 1) {
      parsed.push({ type: 'title', text: titleMatch[1] })
      continue
    }

    if (lines.every((l) => l.startsWith('- '))) {
      parsed.push({ type: 'stats', items: lines.map(_parseFormulaBulletItem) })
      continue
    }

    const headerOnlyMatch = lines[0].match(/^\*\*(.+?):\*\*$/)
    if (headerOnlyMatch && lines.length > 1 && lines.slice(1).every((l) => l.startsWith('- '))) {
      parsed.push({ type: 'location', heading: headerOnlyMatch[1], items: lines.slice(1).map(_parseFormulaBulletItem) })
      continue
    }

    const inlineFixMatch = block.match(/^\*\*How to fix:\*\*\s*([\s\S]+)$/i)
    if (inlineFixMatch) {
      parsed.push({ type: 'fix', text: inlineFixMatch[1].trim() })
      continue
    }

    if (lines.length === 1 && /round/i.test(lines[0])) {
      parsed.push({ type: 'note', text: lines[0] })
      continue
    }

    parsed.push({ type: 'paragraph', text: block })
  }
  return parsed
}

// Split `text` on the backend-supplied `terms` (concept/detail labels) and
// `ops` (the relation being asserted), returning an array of plain strings and
// {text, cls} objects to style.
//
// Concept labels here contain digits, commas, dots and parentheses — "5. Other
// Non-food Credit, if any, please specify" — so a sentence built from two of
// them reads as one undifferentiated run. Styling the labels makes the relation
// between them ("must be less than") fall out as the connective.
function _splitEmphasis(text, terms, ops) {
  const marks = [
    ...(terms || []).map(t => ({ t, cls: 'error-card-term' })),
    ...(ops   || []).map(t => ({ t, cls: 'error-card-op'   })),
  ].filter(m => m.t && m.t.length > 1)
  if (marks.length === 0) return [text]

  // Longest first: a regex alternation takes the FIRST branch that matches, so
  // "equal to" listed ahead of "greater than or equal to" would stop the longer
  // phrase ever matching whole. (The backend sorts too; not relying on it.)
  marks.sort((a, b) => b.t.length - a.t.length)

  // These are data, not patterns — every metacharacter must be escaped or a
  // label like "III. Non-Food Credit ( 1 to 5)" throws on an unbalanced group.
  const pattern = marks
    .map(m => m.t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')

  const classOf = new Map(marks.map(m => [m.t.toLowerCase(), m.cls]))
  // A capturing group makes split() keep the delimiters it matched.
  return text.split(new RegExp(`(${pattern})`, 'g'))
    .filter(piece => piece !== '')
    .map(piece => {
      const cls = classOf.get(piece.toLowerCase())
      return cls ? { text: piece, cls } : piece
    })
}

// Prose with the labels and relation words styled. Falls back to a plain string
// when the section carries no hints, so v1 sections render exactly as before.
function RichText({ text, terms, ops }) {
  const parts = useMemo(
    () => _splitEmphasis(text || '', terms, ops), [text, terms, ops],
  )
  return (
    <>
      {parts.map((p, i) =>
        typeof p === 'string' ? p : <span key={i} className={p.cls}>{p.text}</span>,
      )}
    </>
  )
}

// Per-row verdict glyph for a `matrix` section. Kept as a lookup rather than a
// chain of ternaries so an unknown status renders as blank space instead of
// throwing — a future status value degrades, it does not break the card.
const _MATRIX_STATUS = {
  ok:      { glyph: '✓', className: 'error-card-row-ok' },
  bad:     { glyph: '✗', className: 'error-card-row-bad' },
  unknown: { glyph: '?', className: 'error-card-row-unknown' },
  neutral: { glyph: '',  className: '' },
}

// The expected-vs-actual table — the heart of the unified error card. Both
// formula and dimension errors send this exact shape; only the column HEADERS
// differ ("Detail / Expected / You provided" vs "Item / Expected / You
// reported"), which is why they travel with the data.
function ErrorCardMatrix({ section }) {
  const t = useT()
  const cols = section.columns || {}
  const rows = section.rows || []
  if (rows.length === 0) return null
  return (
    <div className="formula-error-section">
      {section.heading && (
        <div className="formula-error-section-heading">{section.heading}</div>
      )}
      {/* Wide tables scroll inside their own box; the chat bubble never
          scrolls horizontally. */}
      <div className="error-card-matrix-scroll">
        <table className="error-card-matrix">
          <thead>
            {/* Headers carry the same column classes as their cells so the
                alignment rules apply to both — a right-aligned column of
                numbers under a left-aligned header is harder to read, not
                easier. */}
            <tr>
              <th className="error-card-matrix-status" aria-label={t('common.status')} />
              <th className="error-card-matrix-label">{cols.label || t('errors.columns.item')}</th>
              <th className="error-card-matrix-expected">{cols.expected || t('errors.columns.expected')}</th>
              <th className="error-card-matrix-actual">{cols.actual || t('errors.columns.actual')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const status = _MATRIX_STATUS[r.status] || _MATRIX_STATUS.neutral
              return (
                <tr
                  key={i}
                  className={[
                    status.className,
                    // The result row of a formula is the consequence of the
                    // rows above it, not a peer — it gets a rule above and
                    // bolder text.
                    r.emphasis ? 'error-card-row-emphasis' : '',
                  ].filter(Boolean).join(' ')}
                >
                  <td className="error-card-matrix-status">{status.glyph}</td>
                  <td className="error-card-matrix-label">{r.label}</td>
                  {/* An empty cell leaves the reader asking "which column is
                      that number in?" — every row gets a mark in every column
                      so the columns stay readable as vertical stripes. */}
                  <td className="error-card-matrix-expected">
                    {r.expected
                      ? <span className="error-card-matrix-num">{r.expected}</span>
                      : <span className="error-card-matrix-empty">—</span>}
                  </td>
                  <td className="error-card-matrix-actual">
                    {/* The value is wrapped so it can be told not to break;
                        an amount split mid-digit ("₹125,619,592,00 / 0") is
                        unreadable and looks like a different number. */}
                    <span className="error-card-matrix-num">{r.actual}</span>
                    {r.note && <em className="error-card-matrix-note">{r.note}</em>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Renders the backend's structured sections directly. Every heading is a real
// element, so no markdown emphasis markers are ever shown to the user — the
// backend sends none, and none are reconstructed here.
//
// Serves BOTH formula and dimension errors, and both schema generations:
//   v1 (ERROR_CARD_V2=0) — headline / rule / values / points / note
//   v2 (the unified card) — headline / locator / rule / matrix / fix / details
// The v1 cases are left untouched so flipping the backend flag needs no
// frontend change; v2's `details` drawer nests v1 sections and renders them
// through this same component.
// v2-only section kinds. Their presence marks the container as a unified error
// card, so card-level styling (vertical rhythm, spacing) can target it without
// touching the legacy layout — which shares this component AND this container.
const _CARD_KINDS = ['locator', 'matrix', 'fix', 'details']

export function FormulaErrorSections({ sections }) {
  if (!Array.isArray(sections) || sections.length === 0) return null
  // The `details` drawer re-enters this component with v1 sections nested
  // inside it, so those correctly do NOT get the class — the drawer keeps its
  // own tighter spacing rather than inheriting the card's.
  const isCard = sections.some(s => _CARD_KINDS.includes(s.kind))
  return (
    <div className={isCard ? 'formula-error-body error-card-body' : 'formula-error-body'}>
      {sections.map((s, i) => {
        switch (s.kind) {
          case 'headline':
            return (
              <h4 key={i} className="formula-error-title">
                ❌ <RichText text={s.text} terms={s.terms} ops={s.ops} />
              </h4>
            )

          // ── v2 kinds ──────────────────────────────────────────────────────
          case 'locator':
            return (
              <div key={i} className="formula-error-section error-card-locator">
                <div className="formula-error-section-heading">{s.heading}</div>
                <div className="formula-error-kv-grid">
                  {(s.items || []).map((it, j) => (
                    <div key={j} className="formula-error-kv-row">
                      {it.label && (
                        <span className="formula-error-kv-label">{it.label}:</span>
                      )}
                      <span className="formula-error-kv-value">
                        {it.mono ? <code>{it.value}</code> : it.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )
          case 'matrix':
            return <ErrorCardMatrix key={i} section={s} />
          case 'fix':
            return (
              <div key={i} className="formula-error-section formula-error-fix">
                <div className="formula-error-section-heading">{s.heading}</div>
                <ul className="formula-error-points">
                  {(s.steps || []).map((step, j) => (
                    <li key={j}>
                      <RichText text={step} terms={s.terms} ops={s.ops} />
                    </li>
                  ))}
                </ul>
              </div>
            )
          case 'details':
            // Native <details> — collapsed by default, no state to manage, and
            // keyboard/screen-reader accessible for free.
            return (
              <details key={i} className="error-card-details">
                <summary className="error-card-details-summary">{s.heading}</summary>
                <div className="error-card-details-body">
                  <FormulaErrorSections sections={s.sections} />
                </div>
              </details>
            )

          // ── shared / v1 kinds ─────────────────────────────────────────────
          // `rule` is used by BOTH generations; `values`, `points` and `note`
          // are v1's, and are still reached in v2 from inside the `details`
          // drawer above.
          case 'rule':
            return (
              // error-card-rule is a spacing hook only. It is applied
              // unconditionally, but the CSS targets it as a DIRECT child of
              // .error-card-body — so a rule section nested in the details
              // drawer (or a legacy v1 body) is unaffected.
              <div key={i} className="formula-error-section error-card-rule">
                <div className="formula-error-section-heading">{s.heading}</div>
                {s.mono
                  ? <code className="formula-error-mono-block">{s.text}</code>
                  : (
                    <p className="formula-error-rule-text">
                      <RichText text={s.text} terms={s.terms} ops={s.ops} />
                    </p>
                  )}
              </div>
            )
          case 'values':
            return (
              <div key={i} className="formula-error-section">
                <div className="formula-error-section-heading">{s.heading}</div>
                <div className="formula-error-kv-grid">
                  {(s.items || []).map((it, j) => (
                    <div key={j} className="formula-error-kv-row">
                      {/* The ":" separator lives in the DOM, not in CSS. Layout
                          alone was separating label from value, so any styling
                          miss rendered "Branch codeTyped" with no gap at all. */}
                      {it.label && (
                        <span className="formula-error-kv-label">{it.label}:</span>
                      )}
                      <span className="formula-error-kv-value">
                        {it.value}
                        {it.note && <em className="formula-error-kv-note"> ({it.note})</em>}
                        {it.context && (
                          <code className="formula-error-kv-context" title={it.context}>{it.context}</code>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )
          case 'points':
            return (
              <div
                key={i}
                className={
                  /fix/i.test(s.heading || '')
                    ? 'formula-error-section formula-error-fix'
                    : 'formula-error-section'
                }
              >
                <div className="formula-error-section-heading">{s.heading}</div>
                <ul className="formula-error-points">
                  {(s.bullets || []).map((b, j) => (
                    <li key={j}>
                      <RichText text={b} terms={s.terms} ops={s.ops} />
                    </li>
                  ))}
                </ul>
              </div>
            )
          case 'note':
            return <p key={i} className="formula-error-note">{s.text}</p>
          default:
            return null
        }
      })}
    </div>
  )
}

function FormulaErrorContent({ explanation }) {
  const t = useT()
  const blocks = useMemo(() => _parseFormulaExplanationBlocks(explanation), [explanation])
  if (blocks.length === 0) return null
  return (
    <div className="formula-error-body">
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'title':
            return <h4 key={i} className="formula-error-title">❌ {b.text}</h4>
          case 'paragraph':
            return <p key={i} className="formula-error-explanation">{b.text}</p>
          case 'note':
            return <p key={i} className="formula-error-note">{b.text}</p>
          case 'stats':
            return (
              <div key={i} className="formula-error-stats-grid">
                {b.items.map((it, j) => (
                  <div key={j} className="formula-error-stat">
                    <span className="formula-error-stat-label">{it.label}</span>
                    <span className="formula-error-stat-value">{it.value}</span>
                  </div>
                ))}
              </div>
            )
          case 'location':
            return (
              <div key={i} className="formula-error-location">
                <div className="formula-error-location-heading">{b.heading}</div>
                <div className="formula-error-kv-grid">
                  {b.items.map((it, j) => (
                    <div key={j} className="formula-error-kv-row">
                      <span className="formula-error-kv-label">{it.label}</span>
                      <code className="formula-error-kv-value">{it.value}</code>
                    </div>
                  ))}
                </div>
              </div>
            )
          case 'fix':
            return (
              <div key={i} className="formula-error-fix">
                <div className="formula-error-fix-heading">{t('errors.howToFix')}</div>
                <p className="formula-error-fix-text">{b.text}</p>
              </div>
            )
          default:
            return null
        }
      })}
    </div>
  )
}

// ── PlainTextErrorPanel ───────────────────────────────────────────────────────
function PlainTextErrorPanel({ details, errorMessages, downloadUrl, downloadLabel }) {
  const t = useT()
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
          // The backend template already prepends "⚙ Formula Error — {rule_name}"
          // to err.explanation, but this panel renders its own section header
          // with the same icon/label/rule name above each item — strip the
          // duplicate leading line rather than show it twice.
          const rawExplanation = err.explanation || err.business_rule || t('errors.validationRuleFailed').replace('{0}', err.rule_name)
          push_item({
            _error_category: err._error_category || 'formula_error',
            section:         err.rule_name,
            explanation:     rawExplanation.replace(/^⚙\s*Formula Error\s*—[^\n]*\n+/, ''),
            // Structured sections built by backend/tools/formula_error.py.
            // Preferred over parsing `explanation` back out of a string; the
            // string remains the fallback for any producer that predates it.
            sections:        Array.isArray(err.explanation_sections) ? err.explanation_sections : null,
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
        const isFormula = group.cat === 'formula_error'
        return (
          <div key={gi} className={isFormula ? 'formula-error-card' : 'error-section-group'}>
            <div
              className={isFormula ? 'formula-error-card-header' : 'error-section-header'}
              style={isFormula ? undefined : { '--section-color': color, background: color }}
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
                className={isFormula ? 'formula-error-card-body' : 'error-explanation-box'}
                style={isFormula ? undefined : { '--section-color': color, borderLeftColor: color }}
              >
                {item.explanation && (
                  isFormula
                    ? (item.sections
                        ? <FormulaErrorSections sections={item.sections} />
                        : <FormulaErrorContent explanation={item.explanation} />)
                    : <p className="error-explanation-text">{item.explanation}</p>
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
// The explanation string is always "**Label:** content" blocks separated by
// blank lines (see backend/tools/dimension_taxonomy.py's _render_template) —
// parsed into real labeled sections here (icon + color-coded left border per
// label) rather than left to generic markdown rendering, so the structure
// and bolding are guaranteed regardless of markdown-renderer quirks.
// KEYED BY THE BACKEND'S ENGLISH LABEL. dimension_taxonomy.py emits these
// headings and _parseDimensionSections matches on them, so the keys are a
// parsing contract and must never be translated. _DIM_SECTION_I18N maps each
// to the label actually SHOWN, which is localized.
const _DIM_SECTION_META = {
  'Dimension Error':        { icon: '📐', cls: 'dim-sec-title' },
  'What is wrong':          { icon: '⚠️', cls: 'dim-sec-wrong' },
  'What should be checked': { icon: '🔍', cls: 'dim-sec-check' },
  'Reported value':         { icon: '🔢', cls: 'dim-sec-value' },
  'Context':                { icon: '📍', cls: 'dim-sec-context' },
}

const _DIM_SECTION_I18N = {
  'Dimension Error':        'errors.category.dimensionalError',
  'What is wrong':          'errors.whatIsWrong',
  'What should be checked': 'errors.whatShouldBeChecked',
  'Reported value':         'errors.reportedValue',
  'Context':                'errors.columns.context',
}

function _parseDimensionSections(text) {
  if (!text) return null
  const re = /\*\*([^*]+?):\*\*\s*([\s\S]*?)(?=\n\n\*\*[^*]+?:\*\*|$)/g
  const sections = []
  let m
  while ((m = re.exec(text)) !== null) {
    const label = m[1].trim()
    const content = m[2].trim()
    if (label && content) sections.push({ label, content })
  }
  return sections.length ? sections : null
}

// Renders `code` spans inline without pulling in a full markdown parser for
// this one case — content only ever contains plain text plus backtick spans.
function _renderInlineCode(text, keyPrefix) {
  return text.split('`').map((part, i) =>
    i % 2 === 1
      ? <code key={`${keyPrefix}-${i}`}>{part}</code>
      : <React.Fragment key={`${keyPrefix}-${i}`}>{part}</React.Fragment>
  )
}

function DimensionalErrorPanel({ details, downloadUrl, downloadLabel }) {
  const t = useT()
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
          <span className="section-name">{t('errors.dimensionalTitle')}</span>
          <span className="error-section-count">{details.length}</span>
        </div>
        <ol className="dimensional-error-list">
          {details.map((err, i) => {
            // Structured sections from backend/tools/dimension_error.py are
            // preferred; the legacy "**Label:**" parser remains the fallback
            // for any producer that predates them.
            const structured = Array.isArray(err.explanation_sections) ? err.explanation_sections : null
            const sections = structured ? null : _parseDimensionSections(err.explanation)
            return (
            <li key={i} className="dimensional-error-item">
              {structured ? (
                <FormulaErrorSections sections={structured} />
              ) : sections ? (
                <div className="dimensional-error-sections">
                  {sections.map((sec, si) => {
                    const meta = _DIM_SECTION_META[sec.label] || { icon: '•', cls: 'dim-sec-generic' }
                    return (
                      <div key={si} className={`dim-sec ${meta.cls}`}>
                        <span className="dim-sec-label">{meta.icon}{' '}
                          {_DIM_SECTION_I18N[sec.label]
                            ? t(_DIM_SECTION_I18N[sec.label])
                            : sec.label}:</span>{' '}
                        <span className="dim-sec-content">{_renderInlineCode(sec.content, `s${i}-${si}`)}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="dimensional-error-explanation error-explanation-markdown">
                  <ReactMarkdown>
                    {err.explanation || t('errors.dimensionalDetected').replace('{0}', err.concept || t('errors.unknownConcept'))}
                  </ReactMarkdown>
                </div>
              )}
              {/* The chips restate concept / value / context, which the
                  structured sections already show in their own rows. Keep
                  them only for the legacy string-parsed path. */}
              {!structured && (err.concept || err.value || err.context) && (
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
            )
          })}
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
  const t = useT()
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
                <th>{t('errors.columns.dbTableName')}</th>
                <th>{t('errors.columns.rowLabel')}</th>
                <th>{t('errors.columns.cellCode')}</th>
                <th>{t('errors.columns.error')}</th>
                <th>{t('errors.columns.explanation')}</th>
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
  const t = useT()
  // Matches the backend's English heading (agent/__init__.py:3230) to split
  // the message -- a parsing key, so it stays English. The heading shown to
  // the user is localized where failureBlock is rendered.
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
        const msg = (err.explanation || t('errors.ruleFailed').replace('{0}', err.rule_name)).trim()
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
  role, text, data, options, resultType, reportName, sqlData, dbQaData,
  varianceData, varianceAll, varianceMeta, labelA, labelB, llmSummary, summaryIsDraft, instancesData,
  downloadUrl, downloadLabel, statusNote,
  errorDetails,
  errorMessages,
  feedbackQuery, feedbackIntent,
  onFollowUp, onSuggestion, onGuidedAction, onCompare, onFeedback,
  onExplainCategory,
  batchCategory, batchErrorFilePath, batchFormId, batchReportName,
  allowedActions,
  noAutoSummary, onSummaryLoaded,
  lang, onLanguageChange,
}) {
  const t = useT()
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const isUser    = role === 'user'
  const isError   = role === 'error'
  const isWelcome = role === 'welcome'

  if (isWelcome)              return <WelcomeCard onSuggestion={onSuggestion} onGuidedAction={onGuidedAction} allowedActions={allowedActions} lang={lang} onLanguageChange={onLanguageChange} />
  if (role === 'action_menu') return <ActionMenu onGuidedAction={onGuidedAction} allowedActions={allowedActions} lang={lang} onLanguageChange={onLanguageChange} />
  if (role === 'sql_welcome') return <SqlWelcomeCard />
  if (role === 'feedback_prompt')   return (
    <FeedbackPrompt
      onFeedback={onFeedback}
      query={feedbackQuery}
      intent={feedbackIntent}
      resultType={resultType}
    />
  )
  if (role === 'feedback_positive') {
    return (
      <div className="bubble-row assistant">
        <div className="avatar assistant-avatar">AI</div>
        <div className="bubble assistant-bubble">{t('feedback.thanksPositive')}</div>
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
            <span className="guided-prompt-label">{t('guidedBadge')}</span>
            {(text ?? '').split('\n').map((line, i, arr) => (
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
            ))}
          </div>
          {options?.length > 0 && (
            <div className="welcome-suggestions option-chips">
              {options.map((opt) => (
                <button key={opt} className="suggestion-chip" onClick={() => onSuggestion?.(opt)}>
                  {t.option(opt)}
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
          allRows={varianceAll}
          meta={varianceMeta}
          labelA={labelA}
          labelB={labelB}
          llmSummary={llmSummary}
          summaryIsDraft={summaryIsDraft}
          headerText={text}
          reportName={reportName}
          noAutoSummary={noAutoSummary}
          onSummaryLoaded={onSummaryLoaded}
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
      // 4000-series reports can explain formula_error, xbrl_schema, and
      // dimensional. Non-4000-series returns use a separate non-backtracking
      // explain flow for formula errors (backend/tools/formula_error_generic.py)
      // and have no xbrl_schema explainer, but dimensional is form_id-keyed,
      // not 4000-series-specific (backend/tools/dimension_taxonomy.py via
      // report_lookup.py's dimensional branch), so it's enabled for every
      // return whose error file actually has dimension errors.
      return (
        <ErrorSummaryPanel
          counts={errorCategoryCounts}
          downloadUrl={downloadUrl}
          downloadLabel={downloadLabel}
          onExplainCategory={onExplainCategory}
          formId={data?.form_id}
          reportName={data?.report_name}
          explainableCategories={is4000Series ? ['formula_error', 'xbrl_schema', 'dimensional'] : ['formula_error', 'dimensional']}
        />
      )
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
            {t('checkAnotherDate')}
          </div>
          <div className="welcome-suggestions option-chips sched-confirm-actions">
            {chips.map((opt) => (
              <button
                key={opt}
                className={`suggestion-chip${opt === 'Yes' ? ' chip-confirm' : ' chip-cancel'}`}
                onClick={() => onSuggestion?.(opt)}
              >
                {t.option(opt)}
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
                {t.option(opt)}
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
          {/* A user bubble may be the echo of a clicked button, which holds the
              ENGLISH protocol token that was sent ("Generate instance for a
              report", "Schedule"). Show the label the user actually read; free
              text they typed is in neither table and passes through unchanged. */}
          <BubbleText
            text={isUser ? t.echo(displayText) : displayText}
            errorDetails={resolvedErrorDetails}
          />
        </div>

        {/* Disambiguation / date-selection chips */}
        {!isUser && chips.length > 0 && (
          chips.length >= 5 ? (
            <ReportSearchDropdown options={chips} onSelect={onSuggestion} />
          ) : (
            <div className="welcome-suggestions option-chips">
              {chips.map((opt) => (
                <button key={opt} className="suggestion-chip" onClick={() => onSuggestion?.(opt)}>
                  {t.option(opt)}
                </button>
              ))}
            </div>
          )
        )}

        {/* Error panel or download button */}
        {!isUser && resultType !== 'ask_previous' && errorPanel}

        {/* "Explain Next Errors" — shown only while more unexplained errors
            remain in this category+file (data.has_more from the backend's
            explain-category response); continues from data.next_offset so
            already-explained errors are never re-requested. */}
        {!isUser && resultType === 'final' && data?.has_more && batchCategory && (
          <ExplainNextErrorsButton
            category={batchCategory}
            errorFilePath={batchErrorFilePath}
            formId={batchFormId}
            reportName={batchReportName}
            nextOffset={data?.next_offset ?? 0}
            onExplainCategory={onExplainCategory}
          />
        )}
      </div>

      {isUser && <div className="avatar user-avatar">{t('common.you')}</div>}
    </div>
  )
}

// ── Status metadata helper ────────────────────────────────────────────────────
function getStatusMeta(code) {
  const n = parseInt(code, 10)
  // Labels mirror report_lookup._STATUS_LABELS, which is aligned with the
  // iDEAL application's own status dictionary. Colours are unchanged: bright
  // green = generated, awaiting approval; dark green = approved.
  if (n === 11)                       return { label: 'Approval Pending', color: '#00C853' }
  if (n === 9)                        return { label: 'Approved',    color: '#006400' }
  if ([3, 5, 8, 10, 13].includes(n)) return { label: 'Failed',      color: '#FF4D4F' }
  // 6 only — code 4 is not in the application's status dictionary and falls
  // through to Unknown, matching report_lookup._STATUS_LABELS.
  if (n === 6)                        return { label: 'In Process',  color: '#FF9800' }
  // "In Queue" mirrors report_lookup._STATUS_LABELS[0] and the wording the
  // iDEAL application page uses for the same row.
  if (n === 0)                        return { label: 'In Queue',    color: '#FFD600' }
  return { label: 'Unknown', color: '#9E9E9E' }
}

// Canonical legend, built from getStatusMeta itself so the swatches can never
// drift from the dots they explain. One representative code per distinct
// status; order runs healthy -> in-flight -> failed.
const STATUS_LEGEND = [11, 9, 4, 0, 3].map((code) => getStatusMeta(code))

// ── Instance Dropdown ─────────────────────────────────────────────────────────
function InstanceDropdown({ headerText, options, instancesData, onSelect }) {
  const t = useT()
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
          {t('common.select')} ›
        </button>
        {hasStatus && <StatusLegend />}
      </div>
    </div>
  )
}

// ── Status colour legend ──────────────────────────────────────────────────────
// Explains the coloured dots. Rendered from STATUS_LEGEND, which is itself
// derived from getStatusMeta, so a colour or wording change in one place
// updates both the dots and this legend.
function StatusLegend() {
  const t = useT()
  return (
    <div className="status-legend" role="note">
      <span className="status-legend-title">Status</span>
      {STATUS_LEGEND.map((meta) => (
        <span className="status-legend-item" key={meta.label}>
          <span className="status-dot" style={{ background: meta.color }} />
          {meta.label}
        </span>
      ))}
    </div>
  )
}

// ── Welcome Card ──────────────────────────────────────────────────────────────
// `action` is the ENGLISH PROTOCOL TOKEN: it is what gets sent to /guided,
// where guided.py:179-180 matches it with `msg in GUIDED_ACTIONS`, and what
// getAllowedActions() filters on. It is never translated. Only the label
// rendered beside the icon is localized, via t.action(group.action).
const SUGGESTION_GROUPS = [
  { icon: '📋', action: 'Check report status' },
  { icon: '⚙️', action: 'Generate instance for a report' },
  { icon: '🗓️', action: 'Schedule a report' },
  { icon: '📊', action: 'Perform comparative analysis' },
  { icon: '🗄️', action: 'Retrieve data from database' },
]

// Renders *starred* spans in a dictionary string as bold. The markers live
// inside the string so each language controls its own word order and which
// words carry the emphasis.
function renderRich(str) {
  return String(str).split('*').map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
  )
}

// The language dropdown, shown inside the chatbot menu section.
function LanguagePicker({ lang, onLanguageChange }) {
  const t = useT()
  if (!onLanguageChange) return null
  return (
    <div className="menu-lang-row">
      <label className="menu-lang-label" htmlFor="chat-lang-select">🌐 {t('chatLanguage')}</label>
      <select
        id="chat-lang-select"
        className="lang-select"
        value={lang}
        onChange={(e) => onLanguageChange(e.target.value)}
        title={t('chatLanguage')}
        aria-label={t('chatLanguage')}
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.label}</option>
        ))}
      </select>
    </div>
  )
}

// Filter SUGGESTION_GROUPS by the backend-resolved allowed-actions list
// (from guided.py's _allowed_actions, reused via App.jsx's prefetch). A null/
// undefined list means "not resolved yet" — show everything rather than hide
// buttons the user may actually be permitted to use; the backend still
// enforces the real permission on every action regardless.
function _visibleGroups(allowedActions) {
  if (!allowedActions) return SUGGESTION_GROUPS
  return SUGGESTION_GROUPS.filter((g) => allowedActions.includes(g.action))
}

function WelcomeCard({ onSuggestion, onGuidedAction, allowedActions, lang, onLanguageChange }) {
  const t = useT()
  const groups = _visibleGroups(allowedActions)
  const items = [
    'welcomeItemStatus', 'welcomeItemGenerate', 'welcomeItemSchedule',
    'welcomeItemCompare', 'welcomeItemDatabase', 'welcomeItemErrors',
  ]
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble welcome-bubble">
        <p className="welcome-greeting">{t('welcomeGreeting')}</p>
        <p className="welcome-subtext">{t('welcomeHelp')}</p>
        <ul className="welcome-list">
          {items.map((key) => <li key={key}>{renderRich(t(key))}</li>)}
        </ul>
        <LanguagePicker lang={lang} onLanguageChange={onLanguageChange} />
        <p className="welcome-subtext">{t('welcomeCta')}</p>
        <div className="welcome-suggestion-groups">
          {groups.map((group) => (
            <div key={group.action} className="welcome-suggestion-group">
              <button
                className="welcome-group-label-btn"
                onClick={() => onGuidedAction?.(group.action)}
                title={`${t('startGuidedFlow')}: ${t.action(group.action)}`}
              >
                {group.icon} {t.action(group.action)}
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
// How long the prompt stays on screen when the user doesn't answer. The
// depleting bar under the buttons is driven by the SAME value via the
// --feedback-timeout custom property, so the bar and the unmount can't drift.
const FEEDBACK_TIMEOUT_MS = 6500

function FeedbackPrompt({ onFeedback, query, intent, resultType }) {
  const t = useT()
  const [answered, setAnswered] = useState(false)
  // Self-hides once the timer elapses. The message deliberately STAYS in App's
  // message array — it is only hidden visually — so the array order
  // (result -> feedback_prompt -> action_menu) and App's
  // "last message is a feedback_prompt" de-duplication guards are untouched.
  const [expired, setExpired] = useState(false)

  useEffect(() => {
    if (answered) return              // answered: stop the timer, keep it shown
    const t = setTimeout(() => setExpired(true), FEEDBACK_TIMEOUT_MS)
    return () => clearTimeout(t)
  }, [answered])

  const handleClick = (response) => {
    if (answered) return
    setAnswered(true)                 // cancels the timer via the effect cleanup
    onFeedback?.(response, { query, intent, resultType })
  }

  if (expired) return null

  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div
        className={`assistant-msg-block${answered ? '' : ' feedback-timed'}`}
        style={answered ? undefined : { '--feedback-timeout': `${FEEDBACK_TIMEOUT_MS}ms` }}
      >
        <div className="bubble assistant-bubble">{t('wasThisHelpful')}</div>
        {!answered && (
          <>
            <div className="feedback-actions">
              <button className="feedback-btn feedback-yes" onClick={() => handleClick('yes')}>👍 Yes</button>
              <button className="feedback-btn feedback-no"  onClick={() => handleClick('no')}>👎 No</button>
            </div>
            {/* Timer indicator: a full-width bar that depletes to zero over
                FEEDBACK_TIMEOUT_MS, so the prompt visibly reads as temporary. */}
            <div className="feedback-timer" aria-hidden="true">
              <div className="feedback-timer-fill" />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Support Contact ───────────────────────────────────────────────────────────
function SupportContact() {
  const t = useT()
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble support-contact-bubble">
        <p className="support-sorry">{t('support.sorry')}</p>
        <p className="support-desc">{t('support.contact')}</p>
        <div className="support-emails">
          <a href="mailto:support@company.com" className="support-email-link">📧 support@company.com</a>
          <a href="mailto:chatbot-support@company.com" className="support-email-link">📧 chatbot-support@company.com</a>
        </div>
      </div>
    </div>
  )
}

// ── Action Menu ───────────────────────────────────────────────────────────────
function ActionMenu({ onGuidedAction, allowedActions, lang, onLanguageChange }) {
  const t = useT()
  const groups = _visibleGroups(allowedActions)
  return (
    <div className="bubble-row assistant">
      <div className="avatar assistant-avatar">AI</div>
      <div className="bubble assistant-bubble action-menu-bubble">
        <p className="action-menu-prompt">{t('actionMenuPrompt')}</p>
        <LanguagePicker lang={lang} onLanguageChange={onLanguageChange} />
        <div className="welcome-suggestion-groups">
          {groups.map((group) => (
            <div key={group.action} className="welcome-suggestion-group">
              <button
                className="welcome-group-label-btn"
                onClick={() => onGuidedAction?.(group.action)}
                title={`${t('startGuidedFlow')}: ${t.action(group.action)}`}
              >
                {group.icon} {t.action(group.action)}
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
// `placeholder` defaults to the report-name wording so every existing call
// site (report disambiguation) is unchanged; the instance picker passes its own.
function ReportSearchDropdown({ options, onSelect, placeholder }) {
  const t = useT()
  // Defaulted here rather than in the signature so the fallback follows the
  // selected language; the instance picker still passes its own wording.
  const ph = placeholder ?? t('selectReportName')
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
          : <span className="rsd-placeholder">{ph}</span>
        }
        <span className="rsd-arrow">{isOpen ? '▲' : '▼'}</span>
      </div>
      {isOpen && (
        <div className="rsd-menu">
          <div className="rsd-search-wrap">
            <input
              autoFocus
              className="rsd-search"
              placeholder={t('typeToFilter')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <ul className="rsd-list">
            {filtered.length === 0
              ? <li className="rsd-no-results">{t('sql.noMatches')}</li>
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
  const t = useT()
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
          <div className="sql-result-label">{t('sql.schemaMatch')}</div>
          <div className="sql-result-chips">
            {matched_tables.map((t) => <span key={t} className="sql-chip-table">{t}</span>)}
            {matched_columns.slice(0, 6).map((c) => <span key={c} className="sql-chip-col">{c}</span>)}
            {matched_columns.length > 6 && <span className="sql-chip-col">+{matched_columns.length - 6} more</span>}
          </div>
        </div>
      )}
      {sql && (
        <div>
          <div className="sql-result-label">{t('sql.generatedSql')}</div>
          <pre className="sql-result-sql-box">{sql}</pre>
        </div>
      )}
      {!is_valid && <div className="sql-invalid-msg">⚠ {validation_reason || t('errors.sqlValidationFailed')}</div>}
      {db_error  && <div className="sql-db-error">⚠ A database error occurred. Please try again.</div>}
      {is_valid && !db_error && columns.length > 0 && (
        <div>
          <div className="sql-result-label">{t('sql.queryResults')}</div>
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
          {t('sql.noRowsReturned')}
        </div>
      )}
      {accuracy_hint && (
        <div className="sql-accuracy-hint">💡 {accuracy_hint}</div>
      )}
      {needs_more_info && more_info_hint && (
        <div className="sql-more-info-hint"><strong>{t('sql.needMoreDetail')}</strong><br />{more_info_hint}</div>
      )}
    </div>
  )
}

function renderDbQaCell(col, value) {
  if ((col === 'Status' || col === 'status') && (value === 'Active' || value === 'Inactive')) {
    return (
      <span className={`dbqa-status-pill ${value === 'Active' ? 'is-active' : 'is-inactive'}`}>
        {value}
      </span>
    )
  }
  return value ?? '—'
}

// ── DB QA Result Block ────────────────────────────────────────────────────────
const DBQA_PAGE_SIZE = 10

function DbQaResultBlock({ data, fallbackText }) {
  const t = useT()
  // Hooks must run unconditionally on every render (Rules of Hooks) — this
  // has to sit above the early returns below, even though `page` is only
  // read/used by the table branches further down.
  const [page, setPage] = useState(0)

  if (!data || (data.records?.length === 0 && !data.summary)) {
    return <div className="bubble assistant-bubble">{fallbackText || t('noDataFound')}</div>
  }
  const {
    label, summary,
    cols = [], headers = [], records = [],
    is_count,
    tableNames = [], rowLabels = [], contexts = [], cellCodes = [],
  } = data
  if (records.length === 0) return <div className="bubble assistant-bubble">{summary || fallbackText}</div>
  const hasStructuredMeta = tableNames.length || rowLabels.length || contexts.length || cellCodes.length

  // Paginate any table over DBQA_PAGE_SIZE rows — click through pages
  // instead of scrolling the whole message vertically. Horizontal
  // scrolling (dbqa-table-wrapper's overflow-x) is unrelated and stays as
  // the mechanism for wide tables with many columns.
  const totalPages = Math.max(1, Math.ceil(records.length / DBQA_PAGE_SIZE))
  const clampedPage = Math.min(page, totalPages - 1)
  const pageStart = clampedPage * DBQA_PAGE_SIZE
  const pageEnd = Math.min(pageStart + DBQA_PAGE_SIZE, records.length)
  const showPagination = records.length > DBQA_PAGE_SIZE
  const paginationEl = showPagination && (
    <div className="dbqa-pagination">
      <button
        type="button"
        className="dbqa-page-btn"
        onClick={() => setPage((p) => Math.max(0, p - 1))}
        disabled={clampedPage === 0}
      >‹ {t('prev')}</button>
      <span className="dbqa-page-info">
        {pageStart + 1}–{pageEnd} / {records.length} {t('records')} · {clampedPage + 1} / {totalPages}
      </span>
      <button
        type="button"
        className="dbqa-page-btn"
        onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
        disabled={clampedPage >= totalPages - 1}
      >{t('next')} ›</button>
    </div>
  )

  if (hasStructuredMeta) {
    const pageIdxs = Array.from({ length: pageEnd - pageStart }, (_, i) => pageStart + i)
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
              <tr><th>{t('errors.columns.dbTableName')}</th><th>{t('errors.columns.rowLabels')}</th><th>{t('errors.columns.context')}</th><th>{t('errors.columns.cellCode')}</th></tr>
            </thead>
            <tbody>
              {pageIdxs.map((i) => (
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
        {paginationEl}
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
              <span className="dbqa-kv-val">{renderDbQaCell(c, rec[c])}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }
  const pageRecords = records.slice(pageStart, pageEnd)
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
            {pageRecords.map((rec, ri) => (
              <tr key={pageStart + ri}>
                {cols.map((c) => <td key={c}>{renderDbQaCell(c, rec[c])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {paginationEl}
      {summary && <div className="dbqa-summary">{summary}</div>}
    </div>
  )
}

// ── Instance Selection Block ──────────────────────────────────────────────────
function InstanceSelectionBlock({ instances, headerText, onCompare }) {
  const t = useT()
  const NONE = ''
  const [sel1, setSel1] = useState(NONE)
  const [sel2, setSel2] = useState(NONE)
  const [error, setError] = useState('')
  const labelFor = (inst) =>
    inst.label || `${inst.reporting_date || '—'} | Generated: ${inst.run_at || '—'}`
  const handleCompare = () => {
    if (!sel1 || !sel2)  { setError(t('variance.selectEachDropdown')); return }
    if (sel1 === sel2)   { setError(t('variance.chooseTwoInstances')); return }
    setError('')
    onCompare?.(parseInt(sel1, 10) - 1, parseInt(sel2, 10) - 1)
  }
  return (
    <div className="inst-sel-block">
      <div className="inst-sel-header">{headerText}</div>
      <div className="inst-sel-dropdowns">
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">{t('comparativeAnalysis.instance1')}</label>
          <select className="inst-sel-select" value={sel1} onChange={(e) => { setSel1(e.target.value); setError('') }}>
            <option value="">{t('variance.selectInstancePlaceholder')}</option>
            {instances.map((inst, idx) => <option key={idx} value={String(idx + 1)}>{labelFor(inst)}</option>)}
          </select>
        </div>
        <div className="inst-sel-dropdown-group">
          <label className="inst-sel-label">{t('comparativeAnalysis.instance2')}</label>
          <select className="inst-sel-select" value={sel2} onChange={(e) => { setSel2(e.target.value); setError('') }}>
            <option value="">{t('variance.selectInstancePlaceholder')}</option>
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
        {t('comparativeAnalysis.compareInstances')}
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
// Percentage change — always a percentage, never a multiplier.
//
// An earlier version rendered very large ratios as "203x" on the grounds that a
// five-digit percentage is hard to read. That is a judgement call the reader
// should not have forced on them: the column is headed "% Chg", so it shows a
// percentage at every magnitude. Compact suffixes keep it short without
// changing what it is.
//
//    < 1,000%      +324.71%      two decimals — the precise figure
//    < 1,000,000%  +387,976%     grouped integer
//    >= 1,000,000% +3.88M%       compact, still a percentage
//
// The exact unrounded value is always in the cell tooltip.
function fmtPctFin(v) {
  if (v === null || v === undefined) return 'N/A'
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B%`
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M%`
  if (abs >= 1e3) return `${sign}${Math.round(abs).toLocaleString()}%`
  return `${sign}${abs.toFixed(2)}%`
}

// The full, unrounded figure — always available on hover so the compact form
// above never hides the real number.
function pctExactLabel(v, t) {
  if (v === null || v === undefined) return t('variance.noPctZeroBaseline')
  return `${t('comparativeAnalysis.exactChange')}: ${v >= 0 ? '+' : ''}${v.toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}%`
}

// ── Direction of change ───────────────────────────────────────────────────────
// One helper so the table, the chart and the exported HTML all classify a row
// the same way. Direction is taken from `diff`, not from pct_change, because a
// zero baseline leaves pct_change null while the difference is still real.
//
//   increase → green  ↑        no change → neutral  →        decrease → red  ↓
function changeDir(diff) {
  const d = diff ?? 0
  if (d > 0) return { cls: 'vt-pos',     arrow: '↑', sign: '+' }
  if (d < 0) return { cls: 'vt-neg',     arrow: '↓', sign: ''  }
  return       { cls: 'vt-neutral', arrow: '→', sign: ''  }
}

// "+841" / "-3649" / "0" — signed, so direction reads without the colour too
// (colour alone is not accessible, and these tables get printed).
function fmtSignedFin(v) {
  const d = v ?? 0
  const body = fmtFinancial(Math.abs(d))
  if (d > 0) return `+${body}`
  if (d < 0) return `-${body}`
  return '0'
}

// ── Dimensional context → its own column ─────────────────────────────────────
// context_key is the backend's stable identity for a fact's dimensional
// combination: "BASE" for an aggregate, otherwise "axis=member" pairs joined
// by "|". The member is the part a reviewer reads; the axis name is long,
// repeated on every row, and adds nothing on screen — so it moves to the
// tooltip and the member becomes the cell.
//
//   "BASE"                                        → ""        (aggregate row)
//   "CurrencyMismatchDurationDimension=OneMonth"  → "OneMonth"
//   "axis1=val1|axis2=val2"                       → "val1 · val2"
function dimLabel(contextKey) {
  if (!contextKey || contextKey === 'BASE') return ''
  return contextKey
    .split('|')
    .map((part) => {
      const raw = part.includes('=') ? part.slice(part.indexOf('=') + 1) : part
      // XBRL member names conventionally end in "Member" — noise once the
      // value is already in a column headed "Dimension".
      return raw.endsWith('Member') ? raw.slice(0, -6) : raw
    })
    .join(' · ')
}

// The concept WITHOUT its embedded "[member]" suffix. compute_variance appends
// that suffix so the single-column text table can disambiguate dimensional
// rows; once the dimension has its own column the suffix is duplication.
// concept_base is supplied by the backend — the strip is only a fallback.
function conceptOnly(row) {
  const c = row.concept_base || row.concept || ''
  return c.includes(' [') ? c.slice(0, c.indexOf(' [')) : c
}

// ── Row count options ────────────────────────────────────────────────────────
// The table has always shown 30. That stays the default — but 30 of 1,284 with
// no way to see row 31 forced users into the chart modal just to read further.
const ROWCOUNT_OPTIONS = [10, 25, 50, 100, 'All']

// Human names for the active sort, so the coverage line can state the real
// ordering instead of always claiming "ranked by variance".
// Built per-render so the wording follows the selected language. The SORT
// KEY (concept / val_a / val_b / diff / pct / severity) never changes.
const sortLabels = (t) => ({
  concept: t('comparativeAnalysis.sortConcept'),
  val_a:   t('comparativeAnalysis.sortCurrent'),
  val_b:   t('comparativeAnalysis.sortPrevious'),
  diff:    t('comparativeAnalysis.sortDifference'),
  pct:     t('comparativeAnalysis.sortPctChange'),
  severity: t('comparativeAnalysis.sortSeverity'),
})

// [key, label, tooltip] — mirrors the chart modal's filter set exactly.
// Built per-render so the labels follow the selected language. The KEY
// ('all','sig','up','down','reversal','zero') is the filter value and never
// changes -- only the label and tooltip are localized.
const vtFilters = (t) => [
  ['all',      t('common.all'),                             t('comparativeAnalysis.filters.allDesc')],
  ['sig',      t('comparativeAnalysis.highVariance'),        t('comparativeAnalysis.filters.sigDesc')],
  ['up',       t('comparativeAnalysis.increased'),           t('comparativeAnalysis.filters.upDesc')],
  ['down',     t('comparativeAnalysis.decreased'),           t('comparativeAnalysis.filters.downDesc')],
  ['reversal', t('comparativeAnalysis.reversed'),            t('comparativeAnalysis.filters.reversalDesc')],
  ['zero',     t('comparativeAnalysis.filters.zero'),
               t('comparativeAnalysis.zeroBaselineNote')],
]


function VarianceTableBlock({ rows, allRows, meta, labelA, labelB, llmSummary, summaryIsDraft, headerText, reportName, noAutoSummary, onSummaryLoaded }) {
  const t = useT()
  const [showChart, setShowChart] = useState(false)
  const [sortBy,    setSortBy]    = useState(null)
  const [sortDir,   setSortDir]   = useState('desc')
  // Display controls. All three narrow what is DRAWN; none re-derives the
  // comparison, and the coverage line below always reports against the
  // backend's own totals.
  const [rowCount,   setRowCount]   = useState(ROWCOUNT_OPTIONS[0])  // 10|25|50|100|'All'
  const [filterMode, setFilterMode] = useState('all')  // all|sig|up|down|reversal|zero
  const [search,     setSearch]     = useState('')

  // ── The dataset the table actually works over ────────────────────────────
  // `rows` is the backend's top-30 slice; `allRows` is every comparable fact.
  // Sorting, filtering and searching must run over the COMPLETE set, or a
  // click on "% Chg" returns the largest percentage *within the 30 already
  // chosen by importance* — which is not the largest percentage, but reads
  // exactly like it. allRows was already passed in for the chart; this makes
  // the table use it too. Falls back to `rows` if it is ever absent.
  const sourceRows = allRows?.length ? allRows : rows

  // ── Chat table scope: Critical + High only ───────────────────────────────
  // The chat table answers "what must I look at?", so it lists only the
  // regulatory tiers that warrant attention. Everything else stays in the
  // dataset and is one click away in Visualize — this narrows the VIEW, never
  // the comparison.
  //
  // A concept the return's JSON did not classify carries importance_matched
  // false. It is deliberately excluded: unclassified is not a tier, and
  // showing it here would assert an importance the data does not support.
  const importanceAvailable = Boolean(
    meta?.importance_available ?? sourceRows.some((r) => r.importance_matched),
  )
  const headlineRows = useMemo(
    () => sourceRows.filter(
      (r) => r.importance_matched
        && (r.importance_tier === 'Critical' || r.importance_tier === 'High'),
    ),
    [sourceRows],
  )
  // With no importance data at all the table keeps its previous behaviour
  // rather than rendering empty — "no JSON" and "nothing critical" are
  // different facts and must not look the same.
  const tableScope = importanceAvailable ? headlineRows : sourceRows
  // What the AI Analysis describes. Capped so a very large Critical/High set
  // still fits a prompt; the backend applies its own SUMMARY_ROWS cap too.
  // The FULL eligible set is posted. Selection (top 20, max 3 variants per
  // concept) happens server-side in variance_explain, which needs every
  // eligible row to spread the cap across concepts — and every row of the
  // comparison to find parent totals for share-of-total. Slicing here would
  // pre-empt both.
  const summaryScope = useMemo(
    () => (importanceAvailable ? headlineRows : rows.slice(0, 40)),
    [importanceAvailable, headlineRows, rows],
  )
  const lines    = (headerText || '').split('\n')
  const title    = lines[0] || ''
  const subtitle = lines[1] || ''

  // The summary arrives on a SECOND request. /compare-execute gives the
  // summary only 8 seconds inline so the table is never held up, and on a
  // CPU-hosted Ollama that budget always expires (~140s is the real cost),
  // which is why this panel used to come back empty every time. Fetch it
  // here, once the table is already rendered, and fill the panel in when it
  // lands. Only when the inline attempt came back empty — a fast host that
  // beat the 8s budget has already supplied it.
  //
  // Three guards, each for a failure this caused in practice:
  //
  //   noAutoSummary — messages RESTORED from localStorage must never start
  //     LLM work. Chat history is persisted with llmSummary:"" (the inline
  //     call having failed), so without this every page load re-generated a
  //     summary for every past comparison in the history — which is what
  //     made explanations appear on their own after a backend restart.
  //   requestedRef — `rows` is a new array identity on every render, so a
  //     dependency on it alone re-fired the effect repeatedly. One attempt
  //     per mount, full stop.
  //   onSummaryLoaded — hands the text back to App so it is stored on the
  //     message. Without it the summary is lost on reload and fetched again
  //     from scratch, forever.
  const [asyncSummary, setAsyncSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)
  const summaryRequestedRef = useRef(false)
  // Kept in refs so the Stop button can reach the in-flight request: abort()
  // ends the client wait, and /stop cancels the LLM call server-side (the
  // endpoint registers the task under this id via _run_cancellable).
  const summaryAbortRef = useRef(null)
  const summaryRequestIdRef = useRef(null)
  // Set ONLY by the Stop button — never by effect cleanup.
  //
  // Two separate failures came from tying cancellation to cleanup:
  //   1. Success updates llmSummary through onSummaryLoaded, and llmSummary
  //      is a dependency here — so React ran the cleanup, which aborted the
  //      request that had just succeeded. The guard then skipped
  //      setSummaryLoading(false), leaving the spinner and Stop button on
  //      over a summary that had already arrived.
  //   2. StrictMode (main.jsx) double-invokes effects in development:
  //      mount → cleanup → mount. The cleanup cancelled the first request,
  //      the second mount saw summaryRequestedRef already set and started
  //      nothing, so the summary never appeared at all under `npm run dev`.
  //
  // Nothing needs cancelling on unmount: a setState on an unmounted
  // component is a no-op in React 18, and onSummaryLoaded updating App is
  // exactly what should still happen — the summary gets persisted rather
  // than thrown away because the user scrolled the message out of view.
  const summaryCancelledRef = useRef(false)
  useEffect(() => {
    // The narrative describes the SAME rows the table lists, so the analysis
    // and the figures beneath it can never disagree. With no importance data
    // that is the existing top slice, unchanged.
    // The inline response now always carries text — Python's deterministic
    // draft — so testing `llmSummary` alone would skip the polish request and
    // the LLM would never run. A draft still needs polishing; only a summary
    // that has already been through the model is final.
    const isDraft = typeof llmSummary === 'string' && llmSummary.includes('•') && summaryIsDraft
    if ((llmSummary && !isDraft) || noAutoSummary || !summaryScope?.length) return undefined
    if (summaryRequestedRef.current) return undefined
    summaryRequestedRef.current = true
    const controller = new AbortController()
    summaryAbortRef.current = controller
    const requestId = (crypto?.randomUUID?.() ?? String(Date.now()))
    summaryRequestIdRef.current = requestId
    setSummaryLoading(true)
    // Structural, not parsed. The header is now localized, so stripping the
    // English "Variance Analysis — " prefix would silently stop matching and
    // send a wrong report name to /compare-summary.
    const resolvedReportName = reportName || ''
    fetchCompareSummary(summaryScope, labelA, labelB, resolvedReportName,
      // t.lang is the active language from the shared LanguageContext -- no
      // second language state anywhere.
      { signal: controller.signal, requestId, lang: t.lang })
      .then((text) => {
        if (summaryCancelledRef.current) return
        // Loading is cleared in the SAME callback as the result, so the two
        // can never be separated by a re-render: success, empty and error
        // all land here (fetchCompareSummary resolves to '' rather than
        // throwing), so every path clears the spinner exactly once.
        setSummaryLoading(false)
        setAsyncSummary(text)
        // Persist even an empty result: it records that the attempt was
        // made, so a reload doesn't try again — and it releases the
        // deferred feedback prompt / action menu in App.
        onSummaryLoaded?.(text)
      })
    // No cleanup: see summaryCancelledRef above. Only Stop cancels.
    return undefined
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmSummary, noAutoSummary])

  const handleStopSummary = () => {
    summaryCancelledRef.current = true
    summaryAbortRef.current?.abort()
    if (summaryRequestIdRef.current) stopRequest(summaryRequestIdRef.current)
    setSummaryLoading(false)
    // Record the attempt so it is not restarted on the next render/reload,
    // and so the deferred follow-up menu is released.
    onSummaryLoaded?.('')
  }
  const summaryText = llmSummary || asyncSummary
  const SEV_ORDER = { critical: 4, high: 3, medium: 2, low: 1 }


  // ── Filter → search, over the complete set ───────────────────────────────
  // Same semantics as the chart modal's filters, deliberately: two views of
  // one comparison must not disagree about what "Increased" means.
  const filteredRows = useMemo(() => {
    let out = tableScope
    if (filterMode === 'sig')           out = out.filter((r) => r.significant)
    else if (filterMode === 'up')       out = out.filter((r) => (r.diff ?? 0) > 0)
    else if (filterMode === 'down')     out = out.filter((r) => (r.diff ?? 0) < 0)
    else if (filterMode === 'reversal') out = out.filter((r) => r.sign_change)
    else if (filterMode === 'zero') {
      out = out.filter((r) => r.pct_change === null || r.pct_change === undefined)
    }
    const q = search.trim().toLowerCase()
    // Matching the concept string alone already covers dimension members: the
    // backend appends them as a "[OneMonth]" suffix, which is exactly what the
    // Concept column displays.
    if (q) out = out.filter((r) => (r.concept ?? '').toLowerCase().includes(q))
    return out
  }, [tableScope, filterMode, search])

  // Sort the filtered set. With no explicit sort the backend's importance
  // ranking is preserved — that is what "ranked by variance" in the caption
  // refers to, and the caption follows this state so it never claims an
  // ordering the table is not in.
  const sortedRows = useMemo(() => {
    if (!sortBy) return filteredRows
    const dir = sortDir === 'asc' ? 1 : -1
    // Nulls sort last in BOTH directions rather than as 0: a zero-baseline row
    // has no percentage at all, and letting it read as 0% would put it above
    // genuine declines when sorting ascending.
    const nullLast = (a, b, key) => {
      const av = key(a), bv = key(b)
      const aN = av === null || av === undefined
      const bN = bv === null || bv === undefined
      if (aN && bN) return 0
      if (aN) return 1
      if (bN) return -1
      return dir * (av - bv)
    }
    return [...filteredRows].sort((a, b) => {
      if (sortBy === 'concept')   return dir * (a.concept ?? '').localeCompare(b.concept ?? '')
      if (sortBy === 'val_a')     return nullLast(a, b, (r) => r.val_a)
      if (sortBy === 'val_b')     return nullLast(a, b, (r) => r.val_b)
      if (sortBy === 'diff')      return dir * ((a.diff ?? 0) - (b.diff ?? 0))
      if (sortBy === 'pct')       return nullLast(a, b, (r) => (r.pct_change === null || r.pct_change === undefined ? null : Math.abs(r.pct_change)))
      if (sortBy === 'severity')  return dir * ((SEV_ORDER[a.severity] ?? 0) - (SEV_ORDER[b.severity] ?? 0))
      return 0
    })
  }, [filteredRows, sortBy, sortDir])

  // Cap last, so the rows shown are the true top N of the sorted set.
  const visibleRows = useMemo(
    () => (rowCount === 'All' ? sortedRows : sortedRows.slice(0, rowCount)),
    [sortedRows, rowCount],
  )
  const isFiltered = filterMode !== 'all' || Boolean(search.trim())

  // Counts for the filter chips — computed over the complete set once, so each
  // chip states how many facts it would show before it is clicked.
  const filterCounts = useMemo(() => {
    let sig = 0, up = 0, down = 0, rev = 0, zero = 0
    for (const r of sourceRows) {
      if (r.significant) sig++
      if (r.sign_change) rev++
      if (r.pct_change === null || r.pct_change === undefined) zero++
      const d = r.diff ?? 0
      if (d > 0) up++
      else if (d < 0) down++
    }
    return { all: sourceRows.length, sig, up, down, reversal: rev, zero }
  }, [sourceRows])

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
      {/* ── Display controls ─────────────────────────────────────────────
          Filter, search and row count, all over the complete dataset. The
          same filter set as the chart modal so the two views never disagree
          about what "Increased" means. */}
      <div className="vt-controls">
        <div className="vt-filter-group">
          {vtFilters(t).map(([key, label, hint]) => {
            const n = filterCounts[key]
            return (
              <button
                key={key}
                className={`vt-chip${filterMode === key ? ' active' : ''}`}
                onClick={() => setFilterMode(key)}
                title={hint}
                type="button"
              >
                {label}{n !== undefined ? ` (${n.toLocaleString()})` : ''}
              </button>
            )
          })}
        </div>
        <div className="vt-controls-right">
          <input
            className="vt-search"
            type="search"
            placeholder={t('comparativeAnalysis.searchConcept')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label={t('comparativeAnalysis.filterTooltip')}
            title={t('comparativeAnalysis.filterNoteTable')}
          />
          <div className="vt-rowcount-group">
            <label className="vt-rowcount-label" htmlFor="vt-rowcount">{t('common.rows')}</label>
            <select
              id="vt-rowcount"
              className="vt-select"
              value={String(rowCount)}
              // Values are strings in the DOM; 'All' stays a string while the
              // numbers convert back, because the slice keys off
              // `rowCount === 'All'` and Number('All') is NaN.
              onChange={(e) => {
                const v = e.target.value
                setRowCount(v === 'All' ? 'All' : Number(v))
              }}
              title={t('comparativeAnalysis.rowsNoteTable')}
            >
              {ROWCOUNT_OPTIONS.map((opt) => (
                <option key={String(opt)} value={String(opt)}>
                  {opt === 'All' ? t('comparativeAnalysis.allCount').replace('{0}', sortedRows.length.toLocaleString()) : opt}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <div className="variance-table-wrapper">
        <table className="variance-table">
          <thead>
            <tr>
              <th className="vt-concept-col vt-sortable" onClick={() => handleSort('concept')}>{t('comparativeAnalysis.columns.concept')} {sortIcon('concept')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('val_a')}>{labelA} {sortIcon('val_a')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('val_b')}>{labelB} {sortIcon('val_b')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('diff')}>{t('comparativeAnalysis.columns.diff')} {sortIcon('diff')}</th>
              <th className="vt-num-col vt-sortable" onClick={() => handleSort('pct')}>{t('comparativeAnalysis.columns.pctChange')} {sortIcon('pct')}</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIdx) => {
              const dir     = changeDir(row.diff)
              const diffCls = dir.cls
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
              const tipD = `${t('comparativeAnalysis.rawDiff')}: ${fmtRaw(row.diff)}${unitLabel}`
              let signNote = null
              if (row.sign_change) {
                const notation = (row.val_a ?? 0) > 0 ? '−→+' : '+→−'
                signNote = <span className="vt-sign-note" title={`${t('comparativeAnalysis.directionReversedLabel')}: ${notation}`}>{notation}</span>
              }
              const isZeroBase = row.pct_change === null || row.pct_change === undefined
              const sev      = SEV_CFG[row.severity]
              const sevBadge = sev
                ? <span className={`vt-severity-badge ${sev.cls}`} title={`Severity: ${sev.title}`}>{sev.label}</span>
                : null
              return (
                <tr key={rowIdx} className={rowCls}>
                  <td className="vt-concept">
                    {row.significant && <span className="vt-sig-badge" title={t('comparativeAnalysis.highVariance')}>⚠</span>}
                    {/* Concept keeps its embedded "[member]" suffix — that
                        suffix is what distinguishes dimensional rows from one
                        another in a single-column layout. */}
                    <span className="vt-concept-text" title={conceptTitle}>{row.concept ?? ''}</span>
                    {signNote}
                  </td>
                  <td className="vt-num" title={tipA}>{fmtFinancial(row.val_a)}</td>
                  <td className="vt-num" title={tipB}>{fmtFinancial(row.val_b)}</td>
                  {/* Difference and % change both read as direction-coloured
                      chips: green up, red down, grey flat. The arrow repeats
                      the meaning so the column still works in print and for
                      colour-blind readers, where hue alone would not. */}
                  <td className="vt-num" title={tipD}>
                    <span className={`vt-delta ${diffCls}`}>
                      <span className="vt-dir-arrow" aria-hidden="true">{dir.arrow}</span>
                      {fmtSignedFin(row.diff)}
                    </span>
                  </td>
                  {/* A null pct_change means the PREVIOUS value was 0, so the
                      percentage has no denominator — the fact was reported in
                      both periods and is fully comparable. Rendering it as
                      "N/A" made it look like missing data, which is a
                      different thing entirely (those rows never reach the
                      table — the backend intersects the two periods). "0 →"
                      states what actually happened. */}
                  <td className="vt-num">
                    {isZeroBase ? (
                      <span
                        className="vt-pct vt-pct-zerobase"
                        title={t('comparativeAnalysis.zeroBaseTooltip').replace('{0}', labelB)}
                      >
                        0 →
                      </span>
                    ) : (
                      <span className={`vt-pct ${diffCls}`} title={pctExactLabel(row.pct_change, t)}>
                        <span className="vt-dot" aria-hidden="true" />
                        {fmtPctFin(row.pct_change)}
                      </span>
                    )}
                  </td>
                </tr>
              )
            })}
            {visibleRows.length === 0 && (
              <tr>
                <td className="vt-empty" colSpan={5}>
                  {/* Three different reasons for an empty table, and they must
                      not read the same. "No Critical/High" is a finding about
                      the data; "no importance data" is a gap in it. */}
                  {importanceAvailable && headlineRows.length === 0 && !isFiltered ? (
                    <>
                      No Critical or High regulatory-importance concepts changed in this
                      comparison. {sourceRows.length.toLocaleString()} concept(s) were
                      compared — open <b>{t('comparativeAnalysis.visualize')}</b> {t('variance.toSeeEveryTier')}
                    </>
                  ) : (
                    <>{t('comparativeAnalysis.noFactsMatch')}</>
                  )}
                  {isFiltered && (
                    <button
                      className="vt-link-btn"
                      onClick={() => { setFilterMode('all'); setSearch('') }}
                      type="button"
                    >
                      {t('common.clearFilters')}
                    </button>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Only shown when the cap is actually hiding something. */}
      {rowCount !== 'All' && sortedRows.length > visibleRows.length && (
        <div className="vt-more">
          {t('comparativeAnalysis.moreRowsNotShown')
            .replace('{0}', (sortedRows.length - visibleRows.length).toLocaleString())}
          <button className="vt-link-btn" onClick={() => setRowCount('All')} type="button">
            {t('comparativeAnalysis.showAll').replace('{0}', sortedRows.length.toLocaleString())}
          </button>
        </div>
      )}
      {/* The chart is computed entirely from `rows` — data already on screen
          in the table above — and has no dependency on the AI summary. It
          used to live INSIDE the `llmSummary &&` block, so whenever the
          optional LLM call failed or timed out the Visualize button
          disappeared along with it, taking a working deterministic feature
          down with a decorative one. The header now renders on the table's
          own terms; only the summary TEXT waits on the LLM. */}
      <div className="variance-summary">
        <div className="variance-summary-header">
          <div className="variance-summary-label">
            {t('comparativeAnalysis.aiAnalysis')}
            {/* The summary arrives on a SECOND request that can take ~140s on a
                CPU-hosted Ollama. A static line of text gave no sign anything
                was still happening, so a stalled panel and a working one looked
                identical. The state is shown in the header AND in the body: the
                header so it is visible even when the body is scrolled past. */}
            {summaryLoading && (
              <span className="variance-summary-status">
                <span className="variance-summary-spinner" aria-hidden="true" />
                generating
              </span>
            )}
          </div>
          <div className="variance-summary-actions">
            {/* The summary runs for minutes on a CPU host, and until now there
                was no way out of it: the chat's own Stop button only governs
                the main /chat request, and this is a separate background
                call. Aborts the fetch AND cancels the LLM work server-side. */}
            {summaryLoading && (
              <button
                className="vc-stop-btn"
                onClick={handleStopSummary}
                title={t('comparativeAnalysis.stopAnalysis')}
              >
                ■ Stop
              </button>
            )}
            <button className="vc-visualize-btn" onClick={() => setShowChart(true)} title={t('comparativeAnalysis.openChart')}>📊 Visualize</button>
          </div>
        </div>
        {summaryText ? (
          <div className="variance-summary-text">
            <ReactMarkdown>
              {summaryText.replace(/^AI\s+Summary:\s*/i, '').split('\n').map((l) => l.replace(/^•\s*/, '- ')).join('\n')}
            </ReactMarkdown>
          </div>
        ) : summaryLoading ? (
          // role/aria-live so a screen reader announces the wait rather than
          // landing on a panel that appears empty.
          <div
            className="variance-summary-text variance-summary-loading"
            role="status"
            aria-live="polite"
          >
            {/* Skeleton lines rather than a lone spinner: they show the shape of
                what is coming, so the panel reads as filling in rather than as
                a placeholder that might never resolve. */}
            <span className="variance-summary-skeleton" aria-hidden="true">
              <i /><i /><i />
            </span>
            <span className="variance-summary-loading-text">
              Analysing the variance… this can take a minute or two.
              The table and chart above are ready now.
            </span>
          </div>
        ) : (
          <div className="variance-summary-text variance-summary-empty">
            AI analysis is unavailable for this comparison. The variance table and chart above are complete.
          </div>
        )}
      </div>
      {showChart && (
        <VarianceChartModal
          /* ALL comparable rows — never `rows`, which is the 30-row table slice. */
          rows={allRows?.length ? allRows : rows}
          meta={meta}
          labelA={labelA}
          labelB={labelB}
          /* The AI narrative leads the downloaded report. Passed down rather
             than regenerated so the file says exactly what the panel says. */
          summaryText={summaryText}
          onClose={() => setShowChart(false)}
        />
      )}
    </div>
  )
}

// ── Guided Action Menu Card ───────────────────────────────────────────────────
// Icons only. The label and description now come from the language
// dictionary, keyed by this same ENGLISH action token — which is also what
// onSelect sends back to /guided, untranslated.
const GUIDED_ACTION_ICONS = {
  'Check report status':            '📋',
  'Generate instance for a report': '⚙️',
  'Schedule a report':              '🗓️',
  'Perform comparative analysis':   '📊',
  'Retrieve data from database':    '🗄️',
}

function GuidedMenuCard({ text, options, onSelect }) {
  const t = useT()
  return (
    <div className="guided-menu-card">
      <p className="guided-menu-prompt">{text}</p>
      <div className="guided-menu-options">
        {(options || []).map((opt) => {
          // `opt` is the English action token the backend sent and expects
          // back verbatim — onSelect(opt) below passes it through unchanged.
          // Only what is DISPLAYED is looked up in the dictionary.
          const icon = GUIDED_ACTION_ICONS[opt] || '•'
          const desc = t.actionDesc(opt)
          return (
            <button key={opt} className="guided-action-btn" onClick={() => onSelect?.(opt)}>
              <span className="guided-action-icon">{icon}</span>
              <div className="guided-action-body">
                <span className="guided-action-label">{t.action(opt)}</span>
                {desc && desc !== opt && <span className="guided-action-desc">{desc}</span>}
              </div>
              <span className="guided-action-arrow">›</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}