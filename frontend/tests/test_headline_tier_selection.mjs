// frontend/tests/test_headline_tier_selection.mjs
//
// Standalone regression test for the dynamic regulatory-importance tier
// fallback logic in frontend/src/components/MessageBubble.jsx
// (TIER_ORDER / selectHeadlineTiers).
//
// There is no jest/vitest configured in this repo (confirmed: no test
// runner in package.json, no *.config for one). Rather than adding a new
// test framework as an unrelated dependency change, this extracts the
// REAL `TIER_ORDER`/`selectHeadlineTiers` source text directly out of
// MessageBubble.jsx (so it can never silently drift from what's actually
// shipped) and evaluates it in an isolated Node context, asserting the
// exact fallback behaviour requested:
//
//   Critical > High > Medium > Low, each tier's window is itself plus the
//   next tier down, anchored at the highest tier with at least one changed
//   concept -- never hardcoded to Critical+High, and never empty merely
//   because the top tier(s) are absent.
//
// Run: node frontend/tests/test_headline_tier_selection.mjs

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const srcPath = path.join(__dirname, '..', 'src', 'components', 'MessageBubble.jsx')
const src = readFileSync(srcPath, 'utf8')

function extractBetween(markerStart, markerEnd) {
  const startIdx = src.indexOf(markerStart)
  if (startIdx === -1) throw new Error(`marker not found: ${markerStart}`)
  const endIdx = src.indexOf(markerEnd, startIdx)
  if (endIdx === -1) throw new Error(`end marker not found: ${markerEnd}`)
  return src.slice(startIdx, endIdx)
}

// Pull the two real declarations out of the live source, verbatim.
const tierOrderSrc = extractBetween(
  "const TIER_ORDER = ['Critical', 'High', 'Medium', 'Low']",
  '\n',
)
const selectFnSrc = extractBetween(
  'function selectHeadlineTiers(sourceRows) {',
  '\nfunction ',
)

// eslint-disable-next-line no-new-func
const { TIER_ORDER, selectHeadlineTiers } = new Function(
  `${tierOrderSrc}\n${selectFnSrc}\nreturn { TIER_ORDER, selectHeadlineTiers }`,
)()

let passed = 0
let failed = 0

function assertEqual(actual, expected, label) {
  const a = JSON.stringify(actual)
  const e = JSON.stringify(expected)
  if (a === e) {
    passed++
  } else {
    failed++
    console.error(`FAIL: ${label}\n  expected: ${e}\n  actual:   ${a}`)
  }
}

function rowsFor(counts) {
  // counts: { Critical: n, High: n, Medium: n, Low: n }
  const rows = []
  for (const [tier, n] of Object.entries(counts)) {
    for (let i = 0; i < n; i++) {
      rows.push({ importance_matched: true, importance_tier: tier, concept: `${tier}_${i}` })
    }
  }
  return rows
}

// ── 1. Critical + High + Medium + Low available -> default shows Critical + High ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 3, High: 7, Medium: 20, Low: 50 })),
  ['Critical', 'High'],
  '1. all four tiers present -> Critical + High',
)

// ── 2. Critical absent, High + Medium + Low available -> High + Medium ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 0, High: 5, Medium: 20, Low: 50 })),
  ['High', 'Medium'],
  '2. no Critical -> High + Medium',
)

// ── 3. Critical + High absent, Medium + Low available -> Medium + Low ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 0, High: 0, Medium: 8, Low: 40 })),
  ['Medium', 'Low'],
  '3. no Critical/High -> Medium + Low',
)

// ── 4. Only Low available -> default shows Low concepts (no tier below it) ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 0, High: 0, Medium: 0, Low: 7 })),
  ['Low'],
  '4. only Low -> just Low, no crash reaching past the end of TIER_ORDER',
)

// ── 5. No eligible concepts at all -> empty window (caller falls back to the existing empty/no-analysis state) ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 0, High: 0, Medium: 0, Low: 0 })),
  [],
  '5. nothing classified -> empty window',
)
assertEqual(
  selectHeadlineTiers([]),
  [],
  '5b. no rows at all -> empty window',
)

// ── 9 (partial, pure-function slice). Unclassified rows (importance_matched=false) never count toward any tier ──
assertEqual(
  selectHeadlineTiers([
    { importance_matched: false, importance_tier: 'Critical' },
    { importance_matched: false, importance_tier: 'High' },
    { importance_matched: true, importance_tier: 'Low', concept: 'x' },
  ]),
  ['Low'],
  '9. unmatched rows never satisfy a tier, even naming one',
)

// ── 11. Exactly 7 Decreased concepts, no Critical/High, nothing else classified -> those 7 are the window, via Low ──
assertEqual(
  selectHeadlineTiers(rowsFor({ Critical: 0, High: 0, Medium: 0, Low: 7 })).length > 0,
  true,
  '11. 7 Low-tier concepts and nothing higher -> a non-empty window is selected',
)

// ── TIER_ORDER itself must match the backend's canonical order exactly ──
assertEqual(TIER_ORDER, ['Critical', 'High', 'Medium', 'Low'], 'TIER_ORDER matches backend xbrl_importance.TIER_ORDER')

console.log(`\n${passed} passed, ${failed} failed`)
if (failed > 0) process.exit(1)
