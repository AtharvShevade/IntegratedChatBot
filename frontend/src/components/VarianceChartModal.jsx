import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  ReferenceLine,
} from 'recharts'

// ── Colour constants ──────────────────────────────────────────────────────────
const COLOR_A       = '#0B5CAD'   // current  (accent blue)
const COLOR_B       = '#38BDF8'   // previous (sky blue)
const COLOR_HIGH    = '#F87171'   // high-variance highlight
const COLOR_SIGN    = '#FB923C'   // sign-reversal highlight (orange)
const COLOR_POS     = '#4ADE80'   // positive % change
const COLOR_NEG     = '#F87171'   // negative % change

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
function fmtPct(v) {
  if (v === null || v === undefined) return 'N/A'
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : ''
  if (abs > 100_000) return `${sign}Extreme ${v > 0 ? '↑' : '↓'}`
  if (abs > 10_000)  return `${sign}Very High`
  if (abs > 1_000)   return `${sign}>1,000%`
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
}

// ── Custom tooltip ────────────────────────────────────────────────────────────
function VarTooltip({ active, payload, label, labelA, labelB }) {
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
        <div className="vc-tooltip-pct" style={{ color: pct >= 0 ? COLOR_POS : COLOR_NEG }}>
          {pct >= 0 ? '▲' : '▼'} {fmtPct(pct)} change
        </div>
      )}
      {row.sign_change && (
        <div className="vc-tooltip-sign">⇕ Direction reversed</div>
      )}
      {row.significant && (
        <div className="vc-tooltip-high">⚠ High variance</div>
      )}
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

// ── Main Modal ────────────────────────────────────────────────────────────────
export default function VarianceChartModal({ rows, labelA, labelB, onClose }) {
  const [chartType,   setChartType]   = useState('bar')
  const [showSig,     setShowSig]     = useState(false)
  const [useLogScale, setUseLogScale] = useState(true)

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
  const allVals = rows.flatMap((r) => [Math.abs(r.val_a ?? 0), Math.abs(r.val_b ?? 0)])
    .filter((v) => v > 0)
  const autoLog = allVals.length > 1 &&
    (Math.max(...allVals) / Math.min(...allVals)) > 100

  // Prepare chart data — always use raw numeric values; formatting is in the tooltip
  const sourceRows = showSig ? rows.filter((r) => r.significant) : rows
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

  const sigCount      = rows.filter((r) => r.significant).length
  const signChgCount  = rows.filter((r) => r.sign_change).length
  const effectiveLog  = useLogScale || autoLog

  // Bar fill per entry — sign-reversal rows get a distinct orange colour
  const barFillA = (entry) =>
    entry.sign_change ? COLOR_SIGN : entry.significant ? COLOR_HIGH : COLOR_A
  const barFillB = (entry) =>
    entry.sign_change ? '#FCD34D' : entry.significant ? '#FBBF24' : COLOR_B

  const aKey = effectiveLog && chartType !== 'pct' ? `${labelA}_log` : labelA
  const bKey = effectiveLog && chartType !== 'pct' ? `${labelB}_log` : labelB

  // % change tooltip formatter
  const pctTickFmt = (v) => {
    const abs = Math.abs(v)
    if (abs > 10_000) return `${v > 0 ? '+' : ''}Ext`
    if (abs > 1_000)  return `${v > 0 ? '+' : ''}${(v/1000).toFixed(1)}K%`
    return `${v >= 0 ? '+' : ''}${v.toFixed(0)}%`
  }

  const sharedChartProps = {
    data: chartData,
    margin: { top: 10, right: 20, bottom: 60, left: 20 },
  }

  const sharedXAxis = (
    <XAxis
      dataKey="name"
      tick={{ fontSize: 11, fill: '#6B7280' }}
      angle={-35}
      textAnchor="end"
      interval={0}
    />
  )

  const sharedYAxis = (
    <YAxis
      tickFormatter={effectiveLog ? fmtLogAxis : fmtAxis}
      tick={{ fontSize: 11, fill: '#6B7280' }}
      width={70}
    />
  )

  const sharedGrid    = <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,120,160,0.15)" />
  const sharedLegend  = <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
  const sharedTooltip = (
    <Tooltip
      content={<VarTooltip labelA={labelA} labelB={labelB} />}
      cursor={{ fill: 'rgba(11,92,173,0.07)' }}
    />
  )

  return (
    /* backdrop */
    <div className="vc-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose?.() }}>
      <div className="vc-modal" role="dialog" aria-modal="true" aria-label="Variance Chart">

        {/* ── Header ── */}
        <div className="vc-header">
          <div className="vc-title">
            <span className="vc-title-icon">📊</span>
            Variance Visualisation
            <span className="vc-title-labels">
              <span className="vc-label-a">{labelA}</span>
              <span className="vc-vs">vs</span>
              <span className="vc-label-b">{labelB}</span>
            </span>
          </div>
          <div className="vc-header-controls">
            {sigCount > 0 && (
              <button
                className={`vc-filter-btn${showSig ? ' active' : ''}`}
                onClick={() => setShowSig((s) => !s)}
                title="Show only high-variance rows"
              >
                ⚠ High variance ({sigCount})
              </button>
            )}
            <button
              className={`vc-filter-btn${effectiveLog ? ' active' : ''}`}
              onClick={() => setUseLogScale((s) => !s)}
              title="Toggle logarithmic scale for better readability across large value ranges"
            >
              {effectiveLog ? '〜 Log scale' : '— Linear'}
            </button>
            <div className="vc-toggle-group">
              <button
                className={`vc-toggle-btn${chartType === 'bar' ? ' active' : ''}`}
                onClick={() => setChartType('bar')}
              >
                ▦ Bar
              </button>
              <button
                className={`vc-toggle-btn${chartType === 'line' ? ' active' : ''}`}
                onClick={() => setChartType('line')}
              >
                〰 Line
              </button>
              <button
                className={`vc-toggle-btn${chartType === 'pct' ? ' active' : ''}`}
                onClick={() => setChartType('pct')}
                title="Show % change per concept"
              >
                % Chg
              </button>
            </div>
            <button className="vc-close-btn" onClick={onClose} aria-label="Close chart">✕</button>
          </div>
        </div>

        {/* ── Stats strip ── */}
        <div className="vc-stats-strip">
          <div className="vc-stat">
            <span className="vc-stat-val">{rows.length}</span>
            <span className="vc-stat-label">Concepts</span>
          </div>
          <div className="vc-stat">
            <span className="vc-stat-val" style={{ color: '#F87171' }}>{sigCount}</span>
            <span className="vc-stat-label">High Variance</span>
          </div>
          {signChgCount > 0 && (
            <div className="vc-stat">
              <span className="vc-stat-val" style={{ color: COLOR_SIGN }}>{signChgCount}</span>
              <span className="vc-stat-label">Sign Reversed</span>
            </div>
          )}
          <div className="vc-stat">
            <span className="vc-stat-val" style={{ color: COLOR_POS }}>
              {rows.filter((r) => (r.pct_change ?? 0) > 0).length}
            </span>
            <span className="vc-stat-label">Increased</span>
          </div>
          <div className="vc-stat">
            <span className="vc-stat-val" style={{ color: COLOR_NEG }}>
              {rows.filter((r) => (r.pct_change ?? 0) < 0).length}
            </span>
            <span className="vc-stat-label">Decreased</span>
          </div>
        </div>

        {/* ── Chart area ── */}
        <div className="vc-chart-area">
          {chartData.length === 0 ? (
            <div className="vc-empty">No rows to display.</div>
          ) : chartType === 'pct' ? (
            /* ── % Change chart ── */
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 60, left: 20 }}>
                {sharedGrid}
                {sharedXAxis}
                <YAxis tickFormatter={pctTickFmt} tick={{ fontSize: 11, fill: '#6B7280' }} width={70} />
                {sharedTooltip}
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                <ReferenceLine y={0} stroke="rgba(100,120,160,0.3)" />
                <Bar dataKey="pct_display" name="% Change" radius={[4, 4, 0, 0]} maxBarSize={32} animationDuration={600}>
                  {chartData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.sign_change ? COLOR_SIGN
                           : entry.significant ? COLOR_HIGH
                           : (entry.pct_display ?? 0) >= 0 ? COLOR_POS : COLOR_NEG}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={340}>
              {chartType === 'bar' ? (
                <BarChart {...sharedChartProps}>
                  {sharedGrid}
                  {sharedXAxis}
                  {sharedYAxis}
                  {sharedTooltip}
                  {sharedLegend}
                  <ReferenceLine y={0} stroke="rgba(100,120,160,0.3)" />
                  <Bar dataKey={aKey} name={labelA} radius={[4, 4, 0, 0]} maxBarSize={32} animationDuration={600}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={barFillA(entry)} opacity={entry.significant ? 1 : 0.85} />
                    ))}
                  </Bar>
                  <Bar dataKey={bKey} name={labelB} radius={[4, 4, 0, 0]} maxBarSize={32} animationDuration={600}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={barFillB(entry)} opacity={entry.significant ? 1 : 0.75} />
                    ))}
                  </Bar>
                </BarChart>
              ) : (
                <LineChart {...sharedChartProps}>
                  {sharedGrid}
                  {sharedXAxis}
                  {sharedYAxis}
                  {sharedTooltip}
                  {sharedLegend}
                  <ReferenceLine y={0} stroke="rgba(100,120,160,0.3)" />
                  <Line
                    type="monotone"
                    dataKey={aKey}
                    name={labelA}
                    stroke={COLOR_A}
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: COLOR_A, strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                    animationDuration={600}
                  />
                  <Line
                    type="monotone"
                    dataKey={bKey}
                    name={labelB}
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

        {/* ── Legend note for high-variance and sign-change ── */}
        <div className="vc-legend-notes">
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
        </div>
      </div>
    </div>
  )
}
