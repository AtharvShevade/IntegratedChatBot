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
const COLOR_POS     = '#4ADE80'   // positive % change
const COLOR_NEG     = '#F87171'   // negative % change

// ── Custom tooltip ────────────────────────────────────────────────────────────
function VarTooltip({ active, payload, label, labelA, labelB }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload ?? {}
  const pct = row.pct_change

  return (
    <div className="vc-tooltip">
      <div className="vc-tooltip-title">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="vc-tooltip-row">
          <span className="vc-tooltip-dot" style={{ background: p.color }} />
          <span className="vc-tooltip-key">{p.name}:</span>
          <span className="vc-tooltip-val">{fmtVal(p.value)}</span>
        </div>
      ))}
      {pct !== undefined && pct !== null && (
        <div className="vc-tooltip-pct" style={{ color: pct >= 0 ? COLOR_POS : COLOR_NEG }}>
          {pct >= 0 ? '▲' : '▼'} {Math.abs(pct).toFixed(1)}% change
        </div>
      )}
      {row.significant && (
        <div className="vc-tooltip-high">⚠ High variance</div>
      )}
    </div>
  )
}

// ── Number formatter ──────────────────────────────────────────────────────────
function fmtVal(v) {
  if (v === null || v === undefined) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000)     return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })
  return parseFloat(v.toFixed(4)).toString()
}

// ── Y-axis tick formatter ────────────────────────────────────────────────────
function fmtAxis(v) {
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)     return `${(v / 1_000).toFixed(0)}K`
  return v
}

// ── Truncate long concept names for X-axis ───────────────────────────────────
function shortLabel(str, max = 14) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max - 1) + '…' : str
}

// ── Main Modal ────────────────────────────────────────────────────────────────
export default function VarianceChartModal({ rows, labelA, labelB, onClose }) {
  const [chartType, setChartType] = useState('bar')
  const [showSig, setShowSig]     = useState(false)   // filter to significant only

  // Close on Escape key
  const handleKey = useCallback((e) => {
    if (e.key === 'Escape') onClose?.()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [handleKey])

  // Prepare chart data — filter & map rows
  const sourceRows = showSig ? rows.filter((r) => r.significant) : rows
  const chartData = sourceRows.map((r) => ({
    name:        shortLabel(r.concept),
    fullName:    r.concept,
    [labelA]:    r.val_a ?? 0,
    [labelB]:    r.val_b ?? 0,
    pct_change:  r.pct_change,
    significant: r.significant,
  }))

  const sigCount = rows.filter((r) => r.significant).length

  // Determine bar fill per entry — highlight significant rows
  const barFillA = (entry) => entry.significant ? COLOR_HIGH : COLOR_A
  const barFillB = (entry) => entry.significant ? '#FBBF24' : COLOR_B

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
      tickFormatter={fmtAxis}
      tick={{ fontSize: 11, fill: '#6B7280' }}
      width={60}
    />
  )

  const sharedGrid   = <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,120,160,0.15)" />
  const sharedLegend = <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
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
                  <Bar dataKey={labelA} name={labelA} radius={[4, 4, 0, 0]} maxBarSize={32} animationDuration={600}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={barFillA(entry)} opacity={entry.significant ? 1 : 0.85} />
                    ))}
                  </Bar>
                  <Bar dataKey={labelB} name={labelB} radius={[4, 4, 0, 0]} maxBarSize={32} animationDuration={600}>
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
                    dataKey={labelA}
                    name={labelA}
                    stroke={COLOR_A}
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: COLOR_A, strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                    animationDuration={600}
                  />
                  <Line
                    type="monotone"
                    dataKey={labelB}
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

        {/* ── Legend note for high-variance ── */}
        {sigCount > 0 && !showSig && (
          <div className="vc-legend-note">
            <span className="vc-legend-dot" style={{ background: COLOR_HIGH }} />
            Red bars indicate high-variance concepts (⚠)
          </div>
        )}
      </div>
    </div>
  )
}
