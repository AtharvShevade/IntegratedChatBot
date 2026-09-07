import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useT, makeT } from '../i18n.js'
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  ReferenceLine, LabelList,
} from 'recharts'

// ── Colour system ─────────────────────────────────────────────────────────────
// Two orthogonal axes, deliberately kept apart:
//
//   PERIOD IDENTITY  blue = current, purple = previous
//   DIRECTION        green = increase, red = decrease, grey = no change
//
// Previously the period bars were RECOLOURED coral/yellow whenever a row was
// significant, so on a mostly-significant dataset almost every bar lost its
// period identity and borrowed the direction palette's hues — the two
// meanings collided and neither read. Period fills are now constant; variance
// and reversals are signalled by the filters, the tooltip and a stroke, never
// by taking over the period colour.
const COLOR_A       = '#60A5FA'   // CURRENT period  — light blue
const COLOR_B       = '#A78BFA'   // PREVIOUS period — light violet
const COLOR_SIGN    = '#D97706'   // reversal accent (amber) — outline only
const COLOR_POS     = '#16A34A'   // increase — green
const COLOR_NEG     = '#DC2626'   // decrease — red
const COLOR_FLAT    = '#6B7280'   // no change — slate
const COLOR_HIGH    = '#DC2626'   // retained name; used only by % Chg bars

// ── Financial formatter (never scientific notation) ─────────────────────────
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

// Backward-compat wrapper used by VarTooltip (div/sfx still accepted but ignored)
function fmtVal(v) {
  return fmtFinancial(v)
}

// ── Raw value for tooltip ─────────────────────────────────────────────────────
function fmtRaw(v) {
  if (v === null || v === undefined) return '—'
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 6 })
}

// ── Analyst-friendly percentage ───────────────────────────────────────────────
function fmtPct(v, t) {
  if (v === null || v === undefined) return t('common.notAvailable')
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : ''
  if (abs > 100_000) return `${sign}${t('comparativeAnalysis.extreme')} ${v > 0 ? '↑' : '↓'}`
  if (abs > 10_000)  return `${sign}${t('comparativeAnalysis.veryHigh')}`
  if (abs > 1_000)   return `${sign}>1,000%`
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}

// ── Custom tooltip ────────────────────────────────────────────────────────────
function VarTooltip({ active, payload, label, labelA, labelB }) {
  const t = useT()
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload ?? {}
  const pct = row.pct_change

  return (
    <div className="vc-tooltip">
      <div className="vc-tooltip-title">{row.fullName || label}</div>
      {payload.map((p) => {
        const rawVal = row[p.dataKey.replace('_log', '')] ?? p.value
        return (
          <div key={p.dataKey} className="vc-tooltip-row">
            <span className="vc-tooltip-dot" style={{ background: p.color }} />
            <span className="vc-tooltip-key">{p.name}:</span>
            <span className="vc-tooltip-val">{fmtFinancial(rawVal)}</span>
          </div>
        )
      })}
      {row[labelA] !== undefined && (
        <div className="vc-tooltip-raw">Raw {labelA}: {fmtRaw(row[labelA])}</div>
      )}
      {row[labelB] !== undefined && (
        <div className="vc-tooltip-raw">Raw {labelB}: {fmtRaw(row[labelB])}</div>
      )}
      {row.unit && (
        <div className="vc-tooltip-raw">Unit: {row.unit}</div>
      )}
      {pct !== undefined && pct !== null && (
        <div
          className="vc-tooltip-pct"
          style={{ color: pct > 0 ? COLOR_POS : pct < 0 ? COLOR_NEG : COLOR_FLAT }}
        >
          <span className="vc-tip-dot" aria-hidden="true" />
          {fmtChange(pct, t)} {pct > 0 ? t('comparativeAnalysis.legendIncrease').toLowerCase() : pct < 0 ? t('comparativeAnalysis.legendDecrease').toLowerCase() : t('comparativeAnalysis.legendNoChange').toLowerCase()}
        </div>
      )}
      {(row.pct_change === null || row.pct_change === undefined) && (
        <div className="vc-tooltip-zero">
          {t('comparativeAnalysis.zeroPreviousNote')}
        </div>
      )}
      {row.sign_change && (
        <div className="vc-tooltip-sign">⇕ {t('comparativeAnalysis.directionReversed')}</div>
      )}
      {/* {row.significant && (
        <div className="vc-tooltip-high">⚠ {t('comparativeAnalysis.highVariance')}</div>
      )} */}
      {row.anomaly_flags?.length > 0 && (
        <div className="vc-tooltip-anomaly">
          {row.anomaly_flags.join(' · ')}
        </div>
      )}
    </div>
  )
}

// ── Y-axis tick formatter — derive scale from value, no per-row context ───────
function fmtAxis(v) {
  const abs = Math.abs(v)
  if (abs >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`
  if (abs >= 1_000_000)     return `${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)         return `${(v / 1_000).toFixed(0)}K`
  if (abs >= 0.001 || abs === 0) return String(v)
  // Very small: avoid scientific — show with enough decimal places
  const places = Math.min(8, Math.ceil(-Math.log10(abs)) + 2)
  return v.toFixed(places)
}

// ── Logarithmic-safe value ────────────────────────────────────────────────────
// Recharts log scale requires strictly positive values. We map raw values to
// a signed-log transform: sign(v) * log10(|v| + 1).
// This preserves zero, direction, and relative ordering while making very
// large and very small values visible on the same axis.
function signedLog(v) {
  if (v === null || v === undefined || v === 0) return 0
  return Math.sign(v) * Math.log10(Math.abs(v) + 1)
}

// ── Signed-log axis tick formatter ───────────────────────────────────────────
function fmtLogAxis(logV) {
  if (logV === 0) return '0'
  const sign = logV < 0 ? '-' : ''
  const raw  = Math.sign(logV) * (Math.pow(10, Math.abs(logV)) - 1)
  return sign + fmtAxis(Math.abs(raw))
}

// ── Truncate long concept names for X-axis ───────────────────────────────────
function shortLabel(str, max = 14) {
  if (!str) return ''
  // Strip embedded dimension label for the short X-axis label, keep it in tooltip
  const base = str.includes(' [') ? str.slice(0, str.indexOf(' [')) : str
  return base.length > max ? base.slice(0, max - 1) + '…' : base
}

// ── Standalone HTML export ────────────────────────────────────────────────────
// Builds a single self-contained file: no CDN, no build step, no dependency on
// the application. Every comparable row is embedded — not the 30 the chat table
// shows, and not just the page currently painted — and the chart is inline SVG
// so it renders identically offline. Colours mirror the on-screen palette.
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

// Change label for the export and chart tooltips — always a percentage,
// matching the in-app table exactly (see fmtPctFin in MessageBubble.jsx).
function fmtChange(v, t) {
  if (v === null || v === undefined) return t('common.notAvailable')
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B%`
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M%`
  if (abs >= 1e3) return `${sign}${Math.round(abs).toLocaleString()}%`
  return `${sign}${abs.toFixed(2)}%`
}

// Exported so the export can be verified without mounting the component —
// it is a pure function of (rows, meta, labels).
export function buildStandaloneHtml({ rows, meta, labelA, labelB, reportName, summaryText, lang = 'en' }) {
  // Not a component -- no hooks here. The caller passes the active
  // language and this stays a pure function of its arguments.
  const t = makeT(lang)
  const generated = new Date().toLocaleString()
  const total     = rows.length
  const inc       = rows.filter((r) => (r.diff ?? 0) > 0).length
  const dec       = rows.filter((r) => (r.diff ?? 0) < 0).length
  const flat      = total - inc - dec

  // Report order is Analysis → Critical graph → full table.
  //
  // The GRAPH is Critical-only: a reader opening this wants the supervisory
  // headline, and a 7,000-bar canvas buries it. The TABLE below stays the
  // complete set, so restricting the graph narrows what is drawn first without
  // removing anything from the export.
  const criticalRows = rows.filter(
    (r) => r.importance_matched && r.importance_tier === 'Critical',
  )
  const headlineRows = rows.filter(
    (r) => r.importance_matched
      && (r.importance_tier === 'Critical' || r.importance_tier === 'High'),
  )
  // No importance data (or no Critical rows) → the graph falls back to every
  // fact, which is exactly what this export drew before tiers existed.
  const graphRows = criticalRows.length ? criticalRows : rows
  const graphIsCritical = criticalRows.length > 0

  // The AI narrative arrives as plain text bullets ('• ...'). Rendered as a
  // list rather than injected as markup — it is model output and must never be
  // trusted as HTML.
  const analysisHtml = (() => {
    const raw = String(summaryText || '').replace(/^AI\s+Summary:\s*/i, '').trim()
    if (!raw) return ''
    const items = raw.split('\n')
      .map((l) => l.replace(/^[•\-*]\s*/, '').trim())
      .filter(Boolean)
      // ** ** is the only markup the prompt asks for; convert just that.
      .map((l) => escapeHtml(l).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'))
    if (!items.length) return ''
    return `<section class="ai">
<h2>${t('comparativeAnalysis.aiAnalysis')}</h2>
<p class="aisub">Generated from the ${headlineRows.length.toLocaleString()} Critical and High
regulatory-importance concept(s) in this comparison.</p>
<ul>${items.map((i) => `<li>${i}</li>`).join('')}</ul>
</section>`
  })()

  // Chart: horizontal paired bars, one group per row, drawn as inline SVG.
  // Height grows with the row count and the page simply scrolls — no
  // truncation, which is the whole point of the export.
  const ROW_H = 26, PAD_L = 300, PAD_R = 150, W = 1180
  const bodyH = Math.max(1, graphRows.length) * ROW_H
  // Scale over the rows actually drawn, so a Critical-only graph is not
  // squashed against a maximum that belongs to a bar it does not show.
  const scale = graphRows.reduce(
    (m, r) => Math.max(m, Math.abs(r.val_a ?? 0), Math.abs(r.val_b ?? 0)), 0,
  ) || 1
  // ── Bar width: signed-log, matching the on-screen chart ──────────────────
  // A LINEAR width (|v| / globalMax) made this export unreadable on real data.
  // These returns span orders of magnitude in one chart — a 5e13 row sets the
  // scale, so a 4e10 row computes to ~0.08% of the track and lands on the 3px
  // floor. Every smaller row then rendered as the SAME 3px stub, so bars that
  // differ by thousands of percent looked identical and the graph appeared to
  // show no variance at all.
  //
  // The in-app chart defaults to a signed-log scale for exactly this reason
  // (see signedLog / effectiveLog above). Using the same transform here makes
  // the two agree, and keeps small values visibly distinct instead of
  // collapsing them onto the minimum.
  const TRACK = W - PAD_L - PAD_R
  const logMax = Math.abs(signedLog(scale)) || 1
  // Floor of 3px: a value of 0 is data, and a zero-width bar would read as
  // "not reported" — the same confusion the in-app chart had.
  const barW = (v) => Math.max(3, (Math.abs(signedLog(v ?? 0)) / logMax) * TRACK)

  const bars = graphRows.map((r, i) => {
    const y = i * ROW_H
    const a = barW(r.val_a), b = barW(r.val_b)
    const pos = (r.diff ?? 0) > 0, neg = (r.diff ?? 0) < 0
    const dirCol = pos ? '#16A34A' : neg ? '#DC2626' : '#6B7280'
    const arrow  = pos ? '↑' : neg ? '↓' : '→'
    const pct = fmtChange(r.pct_change, t)
    return (
      `<g><title>${escapeHtml(r.concept)}` +
      `${r.context_key && r.context_key !== 'BASE' ? `\nContext: ${escapeHtml(r.context_key)}` : ''}` +
      `\n${escapeHtml(labelA)} (${t('comparativeAnalysis.tooltipCurrent')}): ${fmtRaw(r.val_a)}` +
      `\n${escapeHtml(labelB)} (${t('comparativeAnalysis.tooltipPrevious')}): ${fmtRaw(r.val_b)}` +
      `\n${t('comparativeAnalysis.tooltipDifference')}: ${(r.diff ?? 0) > 0 ? '+' : ''}${fmtRaw(r.diff)}` +
      `\n${t('comparativeAnalysis.tooltipChange')}: ${pct} ${arrow}` +
      `\n${t('comparativeAnalysis.tooltipDirection')}: ${pos ? t('comparativeAnalysis.increased') : neg ? t('comparativeAnalysis.decreased') : t('comparativeAnalysis.legendNoChange')}` +
      `${r.sign_change ? `\n${t('comparativeAnalysis.tooltipSignReversal')}` : ''}` +
      `${r.unit ? `\nUnit: ${escapeHtml(r.unit)}` : ''}</title>` +
      `<text x="${PAD_L - 10}" y="${y + 17}" text-anchor="end" class="lbl">${escapeHtml(
        (r.concept || '').length > 46 ? r.concept.slice(0, 45) + '…' : r.concept,
      )}</text>` +
      `<rect x="${PAD_L}" y="${y + 4}" width="${a.toFixed(1)}" height="8" fill="${COLOR_A}"/>` +
      `<rect x="${PAD_L}" y="${y + 14}" width="${b.toFixed(1)}" height="8" fill="${COLOR_B}"/>` +
      `<text x="${W - PAD_R + 8}" y="${y + 17}" class="dir" fill="${dirCol}">${arrow} ${pct}</text></g>`
    )
  }).join('')


  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Variance Analysis${reportName ? ` — ${escapeHtml(reportName)}` : ''}</title>
<style>
:root{--ink:#111827;--muted:#6B7280;--rule:#E5E7EB;--paper:#fff;--sunken:#F9FAFB;
--a:${COLOR_A};--b:${COLOR_B};--up:#16A34A;--down:#DC2626;--flat:#6B7280}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 18px}
.cmp{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:18px}
.key{display:inline-flex;align-items:center;gap:7px;font-weight:600}
.sw{width:14px;height:14px;border-radius:3px;display:inline-block}
.cov{background:var(--sunken);border:1px solid var(--rule);border-left:3px solid var(--a);
padding:12px 16px;margin:0 0 22px;border-radius:3px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 22px}
.stat{border:1px solid var(--rule);border-radius:4px;padding:10px 16px;min-width:104px;background:var(--sunken)}
.stat b{display:block;font-size:1.32rem;line-height:1.2;font-variant-numeric:tabular-nums}
.stat span{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
h2{font-size:1.05rem;margin:30px 0 12px;padding-bottom:7px;border-bottom:1px solid var(--rule)}
.chart{overflow-x:auto;border:1px solid var(--rule);border-radius:4px;padding:12px;background:var(--paper)}
svg{display:block}
.lbl{font-size:11px;fill:var(--ink)}
.dir{font-size:11px;font-weight:600}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:4px}
table{border-collapse:collapse;width:100%;min-width:900px;font-size:13px}
th,td{padding:8px 12px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}
th{background:var(--sunken);position:sticky;top:0;font-size:11px;text-transform:uppercase;
letter-spacing:.06em;color:var(--muted)}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.n.up{background:#F0FDF4}td.n.down{background:#FEF2F2}td.n.flat{background:#F9FAFB}
tr.up td.n.up:last-of-type,tr.down td.n.down:last-of-type{font-weight:700}
td.u{color:var(--muted);font-size:12px}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.sep{width:1px;height:15px;background:var(--rule);display:inline-block}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:6px;vertical-align:middle}
.dot.up{background:var(--up)}.dot.down{background:var(--down)}.dot.flat{background:var(--flat)}
.excl{display:block;margin-top:5px;color:var(--muted);font-size:12px}
/* AI Analysis block — leads the report, above the graph. */
.ai{margin:22px 0 6px;padding:16px 18px;border:1px solid var(--rule);
border-left:3px solid #0B5CAD;border-radius:8px;background:var(--sunken)}
.ai h2{margin:0 0 4px}
.ai ul{margin:10px 0 0;padding-left:20px}
.ai li{margin:0 0 7px;line-height:1.55}
.aisub{margin:0;color:var(--muted);font-size:12.5px}
tr.up td.n.up,tr.down td.n.down{font-weight:600}
.ctx{display:block;font-size:11px;color:var(--muted)}
.rev{color:#EA580C;margin-left:6px;font-weight:700}
footer{margin-top:34px;padding-top:14px;border-top:1px solid var(--rule);color:var(--muted);font-size:12px}
@media print{th{position:static}.chart,.tw{border:none}}
</style></head><body><div class="wrap">
<h1>Variance Analysis${reportName ? ` — ${escapeHtml(reportName)}` : ''}</h1>
<p class="sub">${escapeHtml(labelA)} &nbsp;vs&nbsp; ${escapeHtml(labelB)}</p>
<div class="cmp">
  <span class="key"><span class="sw" style="background:${COLOR_A}"></span>${escapeHtml(labelA)} — ${t('comparativeAnalysis.current')}</span>
  <span class="key"><span class="sw" style="background:${COLOR_B}"></span>${escapeHtml(labelB)} — ${t('comparativeAnalysis.previous')}</span>
  <span class="sep"></span>
  <span class="key up">↑ ${t('comparativeAnalysis.legendIncrease')}</span><span class="key flat">→ ${t('comparativeAnalysis.legendNoChange')}</span>
  <span class="key down">↓ ${t('comparativeAnalysis.legendDecrease')}</span>
</div>
<div class="cov"><b>${t('export.visualizationAll').replace('{0}', total.toLocaleString())}${
    meta?.concepts ? ` across ${Number(meta.concepts).toLocaleString()} concepts` : ''
  }.</b>${
    meta?.dimensional
      ? ` ${t('comparativeAnalysis.dimensionalContext').replace('{0}', Number(meta.dimensional).toLocaleString())}`
      : ''
  } ${graphIsCritical
      ? `The graph below shows the <b>${graphRows.length.toLocaleString()}</b> Critical
         regulatory-importance concept(s); the comparison itself covered every fact above.`
      : 'Every comparable fact is drawn below.'}${
    meta?.one_sided
      ? ` <span class="excl">${Number(meta.one_sided).toLocaleString()} fact(s) reported in only one period are excluded — they cannot be compared.</span>`
      : ''
  }</div>
<div class="stats">
  <div class="stat"><b>${total.toLocaleString()}</b><span>${t('comparativeAnalysis.factsCompared')}</span></div>
  ${meta?.concepts ? `<div class="stat"><b>${Number(meta.concepts).toLocaleString()}</b><span>${t('comparativeAnalysis.concepts')}</span></div>` : ''}
  <div class="stat"><b class="up">${inc.toLocaleString()}</b><span>${t('comparativeAnalysis.increased')}</span></div>
  <div class="stat"><b class="down">${dec.toLocaleString()}</b><span>${t('comparativeAnalysis.decreased')}</span></div>
  <div class="stat"><b class="flat">${flat.toLocaleString()}</b><span>${t('comparativeAnalysis.unchanged')}</span></div>
  ${meta?.sign_changes ? `<div class="stat"><b style="color:#EA580C">${Number(meta.sign_changes).toLocaleString()}</b><span>${t('comparativeAnalysis.reversed')}</span></div>` : ''}
</div>
${analysisHtml}
<h2>${graphIsCritical
    ? t('comparativeAnalysis.criticalConceptsOf').replace('{0}', graphRows.length.toLocaleString()).replace('{1}', total.toLocaleString())
    : t('comparativeAnalysis.currentVsPreviousAll').replace('{0}', total.toLocaleString())}</h2>
${graphIsCritical
    ? `<p class="aisub">Graph limited to Critical regulatory-importance concepts.
Bars use a signed-log scale so values orders of magnitude apart stay
distinguishable — hover any bar for the exact figures.</p>`
    : ''}
<div class="chart"><svg width="${W}" height="${bodyH + 20}" viewBox="0 0 ${W} ${bodyH + 20}"
role="img" aria-label="Paired bars comparing ${escapeHtml(labelA)} against ${escapeHtml(labelB)} for ${graphRows.length} ${graphIsCritical ? 'Critical' : 'comparable'} facts">
<g transform="translate(0,10)">${bars}</g></svg></div>
<footer>Generated ${escapeHtml(generated)} from iDEAL Xia. Values are exactly as compared —
raw XBRL figures, unmodified. Hover a bar for full precision.</footer>
</div></body></html>`
}

// ── Main Modal ────────────────────────────────────────────────────────────────
// Per-row height of the bar layouts, and how many extra rows to mount either
// side of the viewport so fast scrolling never shows a blank band.
const ROW_PX = 36
const ROW_OVERSCAN = 10
// Below this, mount everything — windowing has a cost and small charts do not
// need it.
const ROW_WINDOW_MIN = 120

// ── Top-N presentation cap ───────────────────────────────────────────────────
// A comparison routinely returns thousands of facts. Drawing all of them is
// honest but unreadable: scrolling a 1,200-bar canvas is not analysis, and the
// rows that matter are buried among rows that moved by a rounding error.
// So the chart opens on the ranked top slice and says so, with All still one
// click away. This is a VIEW cap only — `rows` (the complete dataset) still
// feeds the summary cards, the filter counts and the download.
const TOPN_OPTIONS = [10, 25, 50, 'All']
const DEFAULT_TOPN = 10
// Above this many rows the layout stays dense (one thin bar pair per 36px).
// At or below it, rows get room to breathe and carry printed values — see
// ROW_PX_LARGE.
const GROUPED_MAX = 25
const ROW_PX_LARGE = 58

// [key, label, tooltip] for the ranking selector. Ranking decides WHICH rows
// survive the Top-N cut, so it must be visible and switchable — otherwise
// "top 10" silently means "top 10 by a rule the user cannot see".
// Regulatory-importance tiers, read from the return's generated taxonomy JSON
// (<repo>/JSON/<form_id>.json) — never recomputed here. Selecting one narrows
// what is DRAWN; `rows` stays the complete comparison, so the summary cards,
// the direction counts and the download are unaffected.
//
// 'all' is not a tier: it clears the filter. A concept the JSON does not
// classify carries importance_matched:false and belongs to NO tier — it shows
// under All and nowhere else, because "we don't know" is not "Low".
const TIER_FILTERS = ['All', 'Critical', 'High', 'Medium', 'Low']

// Optional re-orderings. Neither is selected by default: with no chip active
// the chart keeps the order the backend already returned (composite priority —
// movement weighted by value size, with sign reversals and anomalies
// promoted). Clicking a chip applies that sort; clicking it again clears it
// and returns to the default order.
//
// There is deliberately no 'Importance' chip here. Regulatory importance is a
// FILTER now (the Importance dropdown, driven by the return's taxonomy JSON),
// not a sort — having it in both places meant two controls named the same
// thing doing different jobs.
// Built per-render so the labels follow the selected language. The KEY
// ('diff' / 'pct') is the ranking value and never changes.
const rankings = (t) => [
  ['diff', t('comparativeAnalysis.rankAbsoluteDiff'),
   t('comparativeAnalysis.rankAbsoluteDiffDesc')],
  ['pct', t('comparativeAnalysis.rankPctChange'),
   t('comparativeAnalysis.rankPctChangeDesc')],
]

export default function VarianceChartModal({ rows, meta, labelA, labelB, summaryText, onClose }) {
  const t = useT()
  const [chartType,   setChartType]   = useState('bar')
  const [showSig,     setShowSig]     = useState(false)
  const [useLogScale, setUseLogScale] = useState(true)
  // Direction / significance filter over the FULL dataset.
  const [filterMode,  setFilterMode]  = useState('all')   // all|sig|up|down|reversal
  const [search,      setSearch]      = useState('')
  // Presentation cap + what "top" means. Both affect the DRAWN slice only.
  const [topN,        setTopN]        = useState(DEFAULT_TOPN)  // 10|25|50|'All'
  // null = no re-ordering chosen; the backend's own ranking stands.
  const [rankBy,      setRankBy]      = useState(null)          // null|diff|pct
  const [tier,        setTier]        = useState('All')         // All|Critical|High|Medium|Low

  // Close on Escape key
  const handleKey = useCallback((e) => {
    if (e.key === 'Escape') onClose?.()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [handleKey])

  // Detect whether the data spans multiple orders of magnitude —
  // auto-enable log scale when max/min ratio > 100.
  // Reduced rather than spread into Math.max/min: `rows` is now the COMPLETE
  // dataset, and Math.max(...arr) passes every element as an argument, which
  // overflows the call stack on large arrays. A reduce has no such limit.
  const { minVal, maxVal, valCount } = useMemo(() => {
    let mn = Infinity, mx = 0, n = 0
    for (const r of rows) {
      for (const v of [Math.abs(r.val_a ?? 0), Math.abs(r.val_b ?? 0)]) {
        if (v > 0) { if (v < mn) mn = v; if (v > mx) mx = v; n++ }
      }
    }
    return { minVal: mn, maxVal: mx, valCount: n }
  }, [rows])
  const autoLog = valCount > 1 && minVal > 0 && (maxVal / minVal) > 100

  // Importance availability + per-tier counts come from the backend's meta,
  // which counts MATCHED rows only. Falling back to a scan of `rows` keeps the
  // control working if meta is ever absent.
  const importanceAvailable = Boolean(
    meta?.importance_available ?? rows.some((r) => r.importance_matched),
  )
  const tierCounts = useMemo(() => {
    if (meta?.importance_tiers) return meta.importance_tiers
    const t = {}
    for (const r of rows) {
      if (r.importance_matched && r.importance_tier) {
        t[r.importance_tier] = (t[r.importance_tier] ?? 0) + 1
      }
    }
    return t
  }, [rows, meta])

  // Counted once over the COMPLETE dataset (`rows` = variance_all), so the
  // summary cards never describe the filtered view. Direction is taken from
  // `diff`, matching the table, because a zero baseline leaves pct_change null
  // while the difference is still a real movement.
  const { sigCount, signChgCount, incCount, decCount, flatCount, zeroBaseCount } = useMemo(() => {
    let sig = 0, rev = 0, inc = 0, dec = 0, zero = 0
    for (const r of rows) {
      if (r.significant) sig++
      if (r.sign_change) rev++
      // pct_change is null exactly when the previous value was 0 — the
      // denominator does not exist. Those rows are still real comparisons.
      if (r.pct_change === null || r.pct_change === undefined) zero++
      const d = r.diff ?? 0
      if (d > 0) inc++
      else if (d < 0) dec++
    }
    return {
      sigCount: sig, signChgCount: rev, incCount: inc, decCount: dec,
      flatCount: rows.length - inc - dec, zeroBaseCount: zero,
    }
  }, [rows])
  // ── Scroll windowing ──────────────────────────────────────────────────────
  // The chart shows EVERY filtered row and is navigated by scrolling — no
  // pagination, no controls. But a horizontal bar chart grows ~36px per row, so
  // 7,000 facts is a 250,000px canvas and ~14,000 SVG bars: enough to hang or
  // crash the tab, which is indistinguishable from a broken screen.
  //
  // So the scroll CONTAINER keeps the full height (the scrollbar tells the
  // truth about how much data there is) while only the slice near the viewport
  // is actually mounted. Scrolling feels completely normal; nothing is dropped.
  const scrollRef  = useRef(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportH, setViewportH] = useState(560)
  const onChartScroll = useCallback((e) => {
    setScrollTop(e.currentTarget.scrollTop)
    setViewportH(e.currentTarget.clientHeight || 560)
  }, [])
  useEffect(() => {
    const el = scrollRef.current
    if (el) setViewportH(el.clientHeight || 560)
  }, [chartType])

  // ── Filter → search → page, all over the COMPLETE dataset ────────────────
  // `rows` is every comparable fact (variance_all), never the table's slice.
  const filteredRows = useMemo(() => {
    let out = rows
    if (filterMode === 'sig')      out = out.filter((r) => r.significant)
    else if (filterMode === 'up')  out = out.filter((r) => (r.diff ?? 0) > 0)
    else if (filterMode === 'down') out = out.filter((r) => (r.diff ?? 0) < 0)
    else if (filterMode === 'reversal') out = out.filter((r) => r.sign_change)
    else if (filterMode === 'zero') {
      out = out.filter((r) => r.pct_change === null || r.pct_change === undefined)
    }
    // Regulatory tier, straight from the row's JSON-derived fields. A row the
    // JSON did not classify (importance_matched false) matches NO tier — it is
    // reachable only under All, never bucketed as Low.
    if (tier !== 'All') {
      out = out.filter((r) => r.importance_matched && r.importance_tier === tier)
    }
    const q = search.trim().toLowerCase()
    if (q) out = out.filter((r) => (r.concept ?? '').toLowerCase().includes(q))
    return out
  }, [rows, filterMode, search, tier])

  // Legacy toggle kept working: it simply drives the same filter.
  const effectiveFiltered = showSig
    ? filteredRows.filter((r) => r.significant)
    : filteredRows

  // ── Rank, then cap ────────────────────────────────────────────────────────
  // Order matters: rank the FILTERED set, then take the top N of it. Doing it
  // the other way ("top 10 overall, then keep the decreases") would return
  // fewer than 10 rows and silently answer a different question — so
  // "top 10 decreases" composes correctly with the direction filters above.
  //
  // With no chip active the rows keep the order compute_variance already
  // returned (composite priority: log-weighted % movement, anomaly and
  // sign-reversal bonuses) — the backend stays the one place that definition
  // lives, and nothing is re-sorted here.
  const rankedRows = useMemo(() => {
    if (!rankBy) return effectiveFiltered
    const out = [...effectiveFiltered]
    if (rankBy === 'diff') {
      out.sort((a, b) => Math.abs(b.diff ?? 0) - Math.abs(a.diff ?? 0))
    } else if (rankBy === 'pct') {
      // Zero-baseline rows have no percentage at all (null). They sort last
      // rather than as 0, so a genuine 0% row is not pushed below them.
      const key = (r) => (r.pct_change === null || r.pct_change === undefined
        ? -Infinity : Math.abs(r.pct_change))
      out.sort((a, b) => key(b) - key(a))
    }
    return out
  }, [effectiveFiltered, rankBy])

  // The cap is a slice of the ranked list. 'All' keeps every filtered row and
  // the scroll windowing below handles the size, exactly as before.
  const cappedRows = useMemo(
    () => (topN === 'All' ? rankedRows : rankedRows.slice(0, topN)),
    [rankedRows, topN],
  )
  const hiddenByCap = rankedRows.length - cappedRows.length

  // Below GROUPED_MAX the two period bars get a taller row and printed value
  // labels, so A vs B is read directly off the chart instead of inferred from
  // two thin bars or recovered by hovering. Above it the dense layout stays.
  const grouped  = cappedRows.length > 0 && cappedRows.length <= GROUPED_MAX
  const rowPx    = grouped ? ROW_PX_LARGE : ROW_PX

  const visibleRows = cappedRows

  // Rows are only windowed for the row-per-bar layouts; below the threshold the
  // whole thing mounts at once, exactly as before.
  const totalRows   = visibleRows.length
  const windowed    = totalRows > ROW_WINDOW_MIN
  const startIdx    = windowed
    ? Math.max(0, Math.floor(scrollTop / rowPx) - ROW_OVERSCAN)
    : 0
  const endIdx      = windowed
    ? Math.min(totalRows, Math.ceil((scrollTop + viewportH) / rowPx) + ROW_OVERSCAN)
    : totalRows
  const windowRows  = windowed ? visibleRows.slice(startIdx, endIdx) : visibleRows
  const spacerH     = totalRows * rowPx
  const offsetY     = startIdx * rowPx

  // ── Download: ALWAYS the complete dataset ────────────────────────────────
  // Deliberately `rows`, not filteredRows or pageRows — the reason to export
  // is to get everything the screen could not show.
  const handleDownloadHtml = useCallback(() => {
    const html = buildStandaloneHtml({ rows, meta, labelA, labelB, reportName: '', summaryText, lang: t.lang })
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    const safe = (s) => String(s || '').replace(/[^A-Za-z0-9._-]+/g, '-').slice(0, 40)
    a.href = url
    a.download = `variance-${safe(labelA)}-vs-${safe(labelB)}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    // Revoked on the next tick — revoking synchronously can cancel the
    // download before the browser has read the blob.
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }, [rows, meta, labelA, labelB, summaryText])

  // Direction chips get the same colour + arrow the old legend row used to
  // carry on its own — the legend was removed as redundant once the chips
  // that select a direction also LOOK like that direction. 'all' / 'sig' /
  // 'zero' have no direction of their own, so they keep the neutral chip
  // style and no arrow.
  const FILTER_META = {
    up:       { arrow: '↑ ', color: COLOR_POS },
    down:     { arrow: '↓ ', color: COLOR_NEG },
    reversal: { arrow: '⇕ ', color: COLOR_SIGN },
  }

  // [key, label, tooltip] — every control states what it does. All of them
  // filter the DISPLAY only; the comparison dataset is never re-derived.
  const FILTERS = [
    ['all',      `${t('common.all')} (${rows.length.toLocaleString()})`,
                 t('comparativeAnalysis.filters.allDesc')],
    ['sig',      `${t('comparativeAnalysis.highVariance')} (${sigCount.toLocaleString()})`,
                 t('comparativeAnalysis.filters.sigDesc')],
    ['up',       `${t('comparativeAnalysis.increased')} (${incCount.toLocaleString()})`,
                 t('comparativeAnalysis.filters.upDesc')],
    ['down',     `${t('comparativeAnalysis.decreased')} (${decCount.toLocaleString()})`,
                 t('comparativeAnalysis.filters.downDesc')],
    ['reversal', `${t('comparativeAnalysis.reversed')} (${signChgCount.toLocaleString()})`,
                 t('comparativeAnalysis.filters.reversalDesc')],
    // "Previous was 0" rather than "From zero": the first reading of the label
    // should already be the explanation. Users asked what "From zero" meant.
    ['zero',     t('comparativeAnalysis.previousWas0Count')
                   .replace('{0}', zeroBaseCount.toLocaleString()),
                 t('comparativeAnalysis.zeroBaselineNote')],
  ]

  // Prepare chart data — always use raw numeric values; formatting is in the tooltip
  const sourceRows = windowRows
  const chartData = sourceRows.map((r) => ({
    name:        shortLabel(r.concept),
    fullName:    r.concept,
    // Raw values for accurate chart rendering
    [labelA]:              r.val_a ?? 0,
    [labelB]:              r.val_b ?? 0,
    // Signed-log-transformed values for the log-scale variant
    [`${labelA}_log`]:     signedLog(r.val_a ?? 0),
    [`${labelB}_log`]:     signedLog(r.val_b ?? 0),
    // % change for the pct view
    pct_display:           r.pct_change ?? 0,
    pct_change:            r.pct_change,
    significant:           r.significant,
    sign_change:           r.sign_change,
    unit:                  r.unit,
    anomaly_flags:         r.anomaly_flags,
    severity:              r.severity,
  }))

  const effectiveLog  = useLogScale || autoLog

  // Period fills are CONSTANT — a bar's colour states which period it is and
  // nothing else. Reversals keep a visual marker via an amber stroke, which
  // is findable without hijacking the fill (and the Reversed filter isolates
  // them outright).
  const barFillA = () => COLOR_A
  const barFillB = () => COLOR_B
  const barStroke = (entry) => (entry.sign_change ? COLOR_SIGN : 'none')
  // The % Chg chart's subject IS direction, so green/red is correct there —
  // that chart has no period identity to preserve.
  const pctFill  = (entry) => {
    const v = entry.pct_display ?? 0
    if (v > 0) return COLOR_POS
    if (v < 0) return COLOR_NEG
    return COLOR_FLAT
  }

  // The colour of a bar is decided PER ROW, on <Cell>. Recharts' <Legend> and
  // its tooltip dots read the SERIES-level `fill` instead — which these bars
  // never set — so both rendered black while the chart itself was salmon and
  // yellow, and the legend swatch told the reader nothing.
  //
  // Since there is no single series colour, use the one the reader actually
  // sees most of: the most frequent cell fill. That keeps the swatch honest
  // when a few rows differ, instead of picking row 0's colour and being wrong
  // for the majority.
  const dominantFill = (fillOf, fallback) => {
    const tally = new Map()
    for (const entry of chartData) {
      const colour = fillOf(entry)
      tally.set(colour, (tally.get(colour) ?? 0) + 1)
    }
    let best = fallback
    let bestCount = 0
    for (const [colour, count] of tally) {
      if (count > bestCount) { best = colour; bestCount = count }
    }
    return best
  }

  // Period fills are constant now, so the swatch is simply the period colour —
  // no need to infer a dominant one. Kept for the % Chg series, whose cells do
  // legitimately vary per row.
  const legendFillA   = COLOR_A
  const legendFillB   = COLOR_B
  const legendFillPct = dominantFill(pctFill,  COLOR_POS)

  const aKey = effectiveLog && chartType !== 'pct' ? `${labelA}_log` : labelA
  const bKey = effectiveLog && chartType !== 'pct' ? `${labelB}_log` : labelB

  // % change tooltip formatter
  const pctTickFmt = (v) => {
    const abs = Math.abs(v)
    if (abs > 10_000) return `${v > 0 ? '+' : ''}Ext`
    if (abs > 1_000)  return `${v > 0 ? '+' : ''}${(v/1000).toFixed(1)}K%`
    return `${v >= 0 ? '+' : ''}${v.toFixed(0)}%`
  }

  // ── Replace sharedXAxis, sharedYAxis, sharedChartProps, sharedLegend ─────────

const sharedChartProps = {
  data: chartData,
  layout: "vertical",
  margin: { top: 10, right: 30, bottom: 10, left: 10 },
}

const sharedXAxis = (
  <XAxis
    type="number"
    tickFormatter={effectiveLog ? fmtLogAxis : fmtAxis}
    tick={{ fontSize: 11, fill: '#6B7280' }}
    width={70}
  />
)

const sharedYAxis = (
  <YAxis
    type="category"
    dataKey="fullName"
    tick={{ fontSize: 11, fill: '#6B7280', textAnchor: 'end' }}
    width={250}
    tickLine={false}
    dx={-4}
  />
)


  const sharedGrid    = <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,120,160,0.15)" />
  const sharedLegend = (
  <Legend
    verticalAlign="top"
    align="center"
    wrapperStyle={{ fontSize: 12, paddingBottom: 10 }}
  />
)

  const sharedTooltip = (
    <Tooltip
      content={<VarTooltip labelA={labelA} labelB={labelB} />}
      cursor={{ fill: 'rgba(11,92,173,0.07)' }}
    />
  )

  // Height of the mounted slice. Previously this was the whole dataset, which
  // is what produced the enormous canvas.
  const chartHeight = Math.max(340, chartData.length * rowPx + 60)


  return (
    /* backdrop */
    <div className="vc-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose?.() }}>
      <div className="vc-modal" role="dialog" aria-modal="true" aria-label={t('comparativeAnalysis.chartTitle')}>

        {/* ── Header ── */}
        <div className="vc-header">
          <div className="vc-title">
            <span className="vc-title-icon">📊</span>
            {t('comparativeAnalysis.title')}
            <span className="vc-title-labels">
              <span className="vc-label-a">{labelA}</span>
              <span className="vc-vs">vs</span>
              <span className="vc-label-b">{labelB}</span>
            </span>
          </div>
          <div className="vc-header-controls">
            {/* {sigCount > 0 && (
              <button
                className={`vc-filter-btn${showSig ? ' active' : ''}`}
                onClick={() => setShowSig((s) => !s)}
                title="Show only high-variance rows"
              >
                ⚠ {t('comparativeAnalysis.highVariance')} ({sigCount})
              </button>
            )} */}
            {/* <button
              className={`vc-filter-btn${effectiveLog ? ' active' : ''}`}
              onClick={() => setUseLogScale((s) => !s)}
              title="Toggle logarithmic scale for better readability across large value ranges"
            >
              {effectiveLog ? '〜 Log scale' : '— Linear'}
            </button> */}
            {/* Left of the chart-type toggles and the close button. Exports the
                COMPLETE comparison — never the active filter, and never the
                portion currently scrolled into view. */}
            <button
              className="vc-download-btn-main"
              onClick={handleDownloadHtml}
              title={t('comparativeAnalysis.downloadTooltip').replace('{0}', rows.length.toLocaleString())}
            >
              ⭳ {t('common.download')}
            </button>
            <div className="vc-toggle-group">
              <button
                className={`vc-toggle-btn${chartType === 'bar' ? ' active' : ''}`}
                onClick={() => setChartType('bar')}
              >
                ▦ {t('comparativeAnalysis.chartBar')}
              </button>
              <button
                className={`vc-toggle-btn${chartType === 'line' ? ' active' : ''}`}
                onClick={() => setChartType('line')}
              >
                〰 {t('comparativeAnalysis.chartLine')}
              </button>
              <button
                className={`vc-toggle-btn${chartType === 'pct' ? ' active' : ''}`}
                onClick={() => setChartType('pct')}
                title={t('comparativeAnalysis.showPctChange')}
              >
                % Chg
              </button>
            </div>
            <button className="vc-close-btn" onClick={onClose} aria-label={t('comparativeAnalysis.closeChart')}>✕</button>
          </div>
        </div>

        {/* ── Summary cards — fixed, never scrollable ── */}
        {/* Every metric is labelled: a row of bare numbers (7,239  139  6,711)
            tells the reader nothing. Counts come from the backend's own
            comparison, which intersects the two periods, so a fact present in
            only one period contributes to none of them. */}
        <div className="vc-summary">
          <div
            className="vc-sum-card"
            title={[
              t('comparativeAnalysis.factsBoth')
                .replace('{0}', rows.length.toLocaleString())
                .replace('{1}', labelA).replace('{2}', labelB),
              meta?.one_sided
                ? t('comparativeAnalysis.oneSidedExcluded')
                    .replace('{0}', Number(meta.one_sided).toLocaleString())
                : '',
              meta?.dimensional
                ? t('comparativeAnalysis.dimensionalContext')
                    .replace('{0}', Number(meta.dimensional).toLocaleString())
                : '',
            ].filter(Boolean).join('\n')}
          >
            <span className="vc-sum-label">{t('comparativeAnalysis.comparableFacts')}</span>
            <span className="vc-sum-val">{rows.length.toLocaleString()}</span>
          </div>
          {meta?.concepts ? (
            <div className="vc-sum-card">
              <span className="vc-sum-label">{t('comparativeAnalysis.concepts')}</span>
              <span className="vc-sum-val">{Number(meta.concepts).toLocaleString()}</span>
            </div>
          ) : null}
          <div className="vc-sum-card">
            <span className="vc-sum-label">{t('comparativeAnalysis.increased')}</span>
            <span className="vc-sum-val" style={{ color: COLOR_POS }}>{incCount.toLocaleString()}</span>
          </div>
          <div className="vc-sum-card">
            <span className="vc-sum-label">{t('comparativeAnalysis.decreased')}</span>
            <span className="vc-sum-val" style={{ color: COLOR_NEG }}>{decCount.toLocaleString()}</span>
          </div>
          <div className="vc-sum-card">
            <span className="vc-sum-label">{t('comparativeAnalysis.noChange')}</span>
            <span className="vc-sum-val" style={{ color: COLOR_FLAT }}>{flatCount.toLocaleString()}</span>
          </div>
          {signChgCount > 0 ? (
            <div className="vc-sum-card">
              <span className="vc-sum-label">{t('comparativeAnalysis.reversed')}</span>
              <span className="vc-sum-val" style={{ color: COLOR_SIGN }}>{signChgCount.toLocaleString()}</span>
            </div>
          ) : null}

          {/* Period identity, pushed to the far right of the summary row and
              stacked vertically — which period is "current" vs "previous" is
              a single fact, not a filter, so it sits with the cards rather
              than in the filter bar below. */}
          <div className="vc-period-badge">
            <span className="vc-pl-item">
              <span className="vc-pl-swatch" style={{ background: COLOR_A }} />
              {labelA} <em>{t('comparativeAnalysis.current')}</em>
            </span>
            <span className="vc-pl-item">
              <span className="vc-pl-swatch" style={{ background: COLOR_B }} />
              {labelB} <em>{t('comparativeAnalysis.previous')}</em>
            </span>
          </div>
        </div>

        {/* One row: direction filters ... search ... Show + Ranked by.
            Search sits between the two control groups so it stays visually
            level with the filter chips it complements, rather than on a row
            of its own. */}
        <div className="vc-filterbar">
        {/* These change only what is DISPLAYED. The comparison result is
            untouched, and the counts above always describe the whole set. */}
        <div className="vc-fb-row">
        <div className="vc-controls">
          <div className="vc-filter-group">
            {FILTERS.map(([key, label, hint]) => {
              const meta = FILTER_META[key]
              const active = filterMode === key
              return (
                <button
                  key={key}
                  className={`vc-chip${active ? ' active' : ''}`}
                  onClick={() => setFilterMode(key)}
                  title={hint}
                  style={meta ? (active
                    ? { background: meta.color, borderColor: meta.color, color: '#fff' }
                    : { color: meta.color, borderColor: meta.color }
                  ) : undefined}
                >
                  {meta ? meta.arrow : ''}{label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Search — horizontally aligned with the direction filter chips and
            the ranking controls, all three in one row. */}
        <div className="vc-search-col">
          <input
            className="vc-search"
            type="search"
            placeholder={t('comparativeAnalysis.searchConceptName')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label={t('comparativeAnalysis.filterChartTooltip')}
            title={t('comparativeAnalysis.filterNoteChart')}
          />
        </div>

        {/* ── Top-N cap + ranking ──────────────────────────────────────────
            Two controls that together answer "top 10 of what, by what?".
            Both are presentation-only: the summary cards above, the filter
            counts and the Download button all still describe the complete
            comparison. */}
        <div className="vc-controls vc-controls-rank">
          <div className="vc-rank-group">
            <label className="vc-rank-label" htmlFor="vc-topn">{t('common.show')}</label>
            <select
              id="vc-topn"
              className="vc-select"
              value={String(topN)}
              // The option values are strings; 'All' stays a string while the
              // numeric caps are converted back, because the slice logic keys
              // off `topN === 'All'` and Number('All') is NaN.
              onChange={(e) => {
                const v = e.target.value
                setTopN(v === 'All' ? 'All' : Number(v))
              }}
              title={t('comparativeAnalysis.rowsNoteChart')}
            >
              {TOPN_OPTIONS.map((opt) => (
                <option key={String(opt)} value={String(opt)}>
                  {opt === 'All' ? t('common.all') : t('comparativeAnalysis.topN').replace('{0}', String(opt))}
                </option>
              ))}
            </select>
          </div>
          {/* Regulatory tier filter. Rendered only when the return actually
              has importance data — offering tiers that can never match would
              read as a broken control rather than an empty result. */}
          {importanceAvailable && (
            <div className="vc-rank-group">
              <label className="vc-rank-label" htmlFor="vc-tier">{t('comparativeAnalysis.importance')}</label>
              <select
                id="vc-tier"
                className="vc-select"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
                title={t('comparativeAnalysis.tierFilterTooltip')}
              >
                {TIER_FILTERS.map((t) => {
                  const n = t === 'All' ? rows.length : (tierCounts[t] ?? 0)
                  return (
                    <option key={t} value={t}>
                      {t}{n ? ` (${n.toLocaleString()})` : ''}
                    </option>
                  )
                })}
              </select>
            </div>
          )}
          <div className="vc-rank-group">
            <span className="vc-rank-label">{t('comparativeAnalysis.rankedBy')}</span>
            {rankings(t).map(([key, label, hint]) => {
              const active = rankBy === key
              return (
                <button
                  key={key}
                  type="button"
                  className={`vc-chip vc-chip-sm${active ? ' active' : ''}`}
                  // Toggle: clicking the active chip clears it, restoring the
                  // backend's default order. Without this there would be no
                  // way back once either sort was applied.
                  onClick={() => setRankBy(active ? null : key)}
                  aria-pressed={active}
                  title={active ? `${hint}\n\nClick again to restore the default order.` : hint}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
        </div>
        </div>

        {/* ── Coverage caption ─────────────────────────────────────────────
            Anything that caps what is drawn must say what it left out, or the
            chart reads as the whole result. Denominators come from the
            backend's own counts (variance_meta / the complete `rows`), never
            from the length of the drawn slice. */}
        <div className="vc-coverage">
          {hiddenByCap > 0 ? (
            <>
              {t('comparativeAnalysis.showingTopOf')
                .replace('{0}', cappedRows.length.toLocaleString())
                .replace('{1}', rankedRows.length.toLocaleString())}{' '}
              {filterMode === 'all' && !search.trim() && tier === 'All'
                ? t('comparativeAnalysis.comparableFacts')
                : t('comparativeAnalysis.matchingFacts')}
              {/* Names the ACTIVE ordering. With no chip selected the rows are
                  in the backend's own priority order, which is what this says
                  rather than naming a control the user never touched. */}
              {' · '}{t('comparativeAnalysis.rankedBySep')}{' '}
              <b>{(rankings(t).find(([k]) => k === rankBy)
                || [, t('comparativeAnalysis.defaultRanking')])[1]}</b>
              {tier !== 'All'
                ? <> · {t('comparativeAnalysis.tierSep')} <b>{tier}</b></> : null}
            </>
          ) : (
            <>
              {t('comparativeAnalysis.showingAll')
                .replace('{0}', cappedRows.length.toLocaleString())}{' '}
              {filterMode === 'all' && !search.trim() && tier === 'All'
                ? t('comparativeAnalysis.comparableFacts')
                : t('comparativeAnalysis.matchingFacts')}
              {tier !== 'All' ? <> {t('comparativeAnalysis.inTier')} <b>{tier}</b></> : null}
            </>
          )}
          {' · '}
          <span className="vc-cov-up">{t('comparativeAnalysis.countUp').replace('{0}', incCount.toLocaleString())}</span>
          {' · '}
          <span className="vc-cov-down">{t('comparativeAnalysis.countDown').replace('{0}', decCount.toLocaleString())}</span>
          {flatCount > 0 ? <> · {t('comparativeAnalysis.countUnchanged').replace('{0}', flatCount.toLocaleString())}</> : null}
          {/* The up/down counts describe the COMPLETE comparison, not the
              drawn slice — stated explicitly so the two numbers on this line
              are not read as parts of the same total. */}
          {hiddenByCap > 0 || filterMode !== 'all' || search.trim() ? (
            <span className="vc-cov-note">
              {' '}{t('comparativeAnalysis.directionCountsNote')
                .replace('{0}', rows.length.toLocaleString())}
            </span>
          ) : null}
          {' · '}
          <span className="vc-cov-note">{t('comparativeAnalysis.downloadNote')}</span>
        </div>

        {/* ── Chart area ── */}
        <div className="vc-chart-wrap">
        <div
          className="vc-chart-area"
          ref={scrollRef}
          onScroll={onChartScroll}
          // scrollbarGutter matches the modal's: the plot area's own scrollbar
          // comes and goes with the row count, and without a reserved gutter
          // the bars shift sideways every time a filter changes the count.
          style={{ overflowY: "auto", maxHeight: "65vh", scrollbarGutter: "stable" }}
        >
        {/* Spacer carries the FULL height so the scrollbar reflects every row;
            the inner layer is offset to the mounted slice's position. */}
        <div style={windowed ? { height: spacerH, position: 'relative' } : undefined}>
        <div style={windowed ? { position: 'absolute', top: offsetY, left: 0, right: 0 } : undefined}>
  {chartData.length === 0 ? (
    <div className="vc-empty">{t('comparativeAnalysis.noRows')}</div>
  ) : chartType === 'pct' ? (
    /* ── % Change chart ── */
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart
        data={chartData}
        layout="vertical"                          // ← flip
        margin={{ top: 10, right: 30, bottom: 10, left: 10 }}
      >
        {sharedGrid}
        <XAxis
          type="number"
          tickFormatter={pctTickFmt}
          tick={{ fontSize: 11, fill: '#6B7280' }}
          width={70}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: '#6B7280' }}
          width={220}
          tickLine={false}
        />
        {sharedTooltip}
        <Legend wrapperStyle={{ fontSize: 12, paddingBottom: 10 }} verticalAlign="top" />
        <ReferenceLine x={0} stroke="rgba(100,120,160,0.3)" />   {/* ← x not y */}
        {/* `fill` is for the LEGEND swatch and tooltip dot only — the <Cell>
            children below still decide each bar's actual colour. */}
        <Bar dataKey="pct_display" name="% Change" fill={legendFillPct} radius={[0, 4, 4, 0]} maxBarSize={22} animationDuration={600}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={pctFill(entry)} />
          ))}
          {grouped && (
            <LabelList dataKey="pct_display" position="right" formatter={pctTickFmt}
                       style={{ fontSize: 10, fill: '#475569' }} />
          )}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  ) : (
    <ResponsiveContainer width="100%" height={chartHeight}>
      {chartType === 'bar' ? (
        <BarChart {...sharedChartProps}>
          {sharedGrid}
          {sharedXAxis}
          {sharedYAxis}
          {sharedTooltip}
          <ReferenceLine x={0} stroke="rgba(100,120,160,0.3)" />   {/* ← x not y */}
          {/* `fill` is for the LEGEND swatch and tooltip dot only — the <Cell>
              children below still decide each bar's actual colour. Without it
              Recharts falls back to black for both. */}
          <Bar dataKey={aKey} name={`${labelA} — Current`} fill={legendFillA} radius={[0, 4, 4, 0]} maxBarSize={grouped ? 18 : 22} minPointSize={3} animationDuration={600}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={barFillA(entry)} stroke={barStroke(entry)} strokeWidth={entry.sign_change ? 1.5 : 0} />
            ))}
            {/* Printed values, small-N only. The bar is POSITIONED by aKey
                (signed-log when the scale is on) but the label must read the
                RAW figure, so LabelList takes its own dataKey. Without this
                the chart would print log values as if they were rupees. */}
            {grouped && (
              <LabelList dataKey={labelA} position="right" formatter={fmtAxis}
                         style={{ fontSize: 10, fill: '#475569' }} />
            )}
          </Bar>
          <Bar dataKey={bKey} name={`${labelB} — Previous`} fill={legendFillB} radius={[0, 4, 4, 0]} maxBarSize={grouped ? 18 : 22} minPointSize={3} animationDuration={600}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={barFillB(entry)} stroke={barStroke(entry)} strokeWidth={entry.sign_change ? 1.5 : 0} />
            ))}
            {grouped && (
              <LabelList dataKey={labelB} position="right" formatter={fmtAxis}
                         style={{ fontSize: 10, fill: '#475569' }} />
            )}
          </Bar>
        </BarChart>
      ) : (
        <LineChart {...sharedChartProps}>
          {sharedGrid}
          {sharedXAxis}
          {sharedYAxis}
          {sharedTooltip}
          <ReferenceLine x={0} stroke="rgba(100,120,160,0.3)" />   {/* ← x not y */}
          <Line
            type="monotone"
            dataKey={aKey}
            name={`${labelA} — Current`}
            stroke={COLOR_A}
            strokeWidth={2.5}
            dot={{ r: 4, fill: COLOR_A, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            animationDuration={600}
          />
          <Line
            type="monotone"
            dataKey={bKey}
            name={`${labelB} — Previous`}
            stroke={COLOR_B}
            strokeWidth={2.5}
            dot={{ r: 4, fill: COLOR_B, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            animationDuration={600}
          />
        </LineChart>
      )}
    </ResponsiveContainer>
  )}
        </div>
        </div>
</div>
        </div>
        {/* Its own row BELOW the chart. Floating it over the plot area covered
            the x-axis and the last rows of data. Always exports the COMPLETE
            comparison — never the active filter or the scrolled-to portion. */}
        {/* ── Legend note for high-variance and sign-change ── */}
        {/* <div className="vc-legend-notes">
          {sigCount > 0 && !showSig && (
            <div className="vc-legend-note">
              <span className="vc-legend-dot" style={{ background: COLOR_HIGH }} />
              Red bars: high-variance concepts (⚠)
            </div>
          )}
          {signChgCount > 0 && (
            <div className="vc-legend-note">
              <span className="vc-legend-dot" style={{ background: COLOR_SIGN }} />
              Orange bars: direction reversed (↕)
            </div>
          )}
          {effectiveLog && (
            <div className="vc-legend-note" style={{ color: '#94A3B8' }}>
              Y-axis uses signed-log scale — sign(v)·log₁₀(|v|+1)
            </div>
          )}
        </div> */}
      </div>
    </div>
  )
}
