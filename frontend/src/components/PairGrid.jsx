/**
 * PairGrid — two modes:
 *
 * 1. PREDICTION mode (no actualNumbers / pairHits):
 *    Shows the 20 predicted pairs as a simple grid.
 *    Used in the Prediction Engine section before a draw.
 *
 * 2. SCORED mode (actualNumbers + pairHits provided):
 *    Shows actual draw numbers at the top.
 *    Renders all 20 pairs colour-coded:
 *      green  = both numbers appeared in the draw (hit)
 *      amber  = one number appeared (near miss)
 *      slate  = neither appeared (miss)
 *    One accordion row per draw — not per ticket.
 */

import { useState } from 'react'

// ── Pair chip — colour depends on hit status ───────────────────
function PairChip({ n1, n2, count, status }) {
  const styles = {
    hit:      'bg-green-500/20 border-green-500/50 text-green-300',
    near:     'bg-amber-500/15 border-amber-500/40 text-amber-300',
    miss:     'bg-slate-700/60 border-slate-600    text-slate-400',
    default:  'bg-blue-500/10  border-blue-500/30  text-blue-400',
  }
  const cls = styles[status] ?? styles.default

  return (
    <div className={`flex items-center gap-1 border rounded-full
                     px-3 py-1.5 text-sm font-bold select-none ${cls}`}>
      <span>{n1}</span>
      <span className="text-xs opacity-50 font-normal">+</span>
      <span>{n2}</span>
      {count != null && (
        <span className="text-xs font-normal opacity-50 ml-0.5">×{count}</span>
      )}
    </div>
  )
}

// ── Actual draw number pill ────────────────────────────────────
function DrawNumber({ n }) {
  return (
    <span className="inline-flex items-center justify-center
                     w-8 h-8 rounded-full bg-white/10 border border-white/20
                     text-white text-xs font-bold">
      {n}
    </span>
  )
}

// ── Scored pair grid (one accordion per draw) ──────────────────
export function ScoredPairAccordion({ drawDate, drawType, actualNumbers, pairHits, pairs }) {
  const [open, setOpen] = useState(false)

  // Build a set for O(1) lookup
  const actualSet = new Set(actualNumbers ?? [])

  // Determine status of each pair
  const annotated = (pairs ?? []).map(p => {
    const n1in = actualSet.has(p.n1)
    const n2in = actualSet.has(p.n2)
    const status = n1in && n2in ? 'hit' : (n1in || n2in ? 'near' : 'miss')
    return { ...p, status }
  })

  const hitCount  = pairHits?.hit_count      ?? annotated.filter(p => p.status === 'hit').length
  const nearCount = pairHits?.near_miss_count ?? annotated.filter(p => p.status === 'near').length
  const total     = annotated.length || pairHits?.predicted_pairs || 20
  const hitRate   = pairHits?.hit_rate ?? (total ? ((hitCount / total) * 100).toFixed(1) : '0.0')
  const baseline  = pairHits?.random_baseline ?? 0.2551

  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden mb-2">

      {/* Accordion header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3
                   bg-slate-700/40 hover:bg-slate-700/60 transition-colors text-left"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-slate-300 text-sm font-medium">
            {drawDate} {drawType}
          </span>
          {actualNumbers?.length > 0 && (
            <div className="flex items-center gap-1">
              {actualNumbers.map(n => <DrawNumber key={n} n={n} />)}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0 ml-3">
          {/* Hit summary badges */}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            hitCount > 0
              ? 'bg-green-500/20 text-green-400'
              : 'bg-slate-600/50 text-slate-400'
          }`}>
            {hitCount} hit{hitCount !== 1 ? 's' : ''}
          </span>
          {nearCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full font-medium
                             bg-amber-500/15 text-amber-400">
              {nearCount} close
            </span>
          )}
          <span className="text-slate-500 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-4 py-4 bg-slate-800/60">

          {/* Actual draw numbers — prominent at top */}
          {actualNumbers?.length > 0 && (
            <div className="mb-4 pb-4 border-b border-slate-700">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">
                Actual Draw Numbers
              </p>
              <div className="flex gap-2 flex-wrap">
                {actualNumbers.map(n => (
                  <span
                    key={n}
                    className="inline-flex items-center justify-center
                               w-10 h-10 rounded-full bg-white/10
                               border-2 border-white/30 text-white
                               text-sm font-bold"
                  >
                    {n}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Stats row */}
          <div className="flex gap-6 mb-4 text-xs">
            <span className="text-slate-400">
              Pairs hit:&nbsp;
              <strong className="text-white">{hitCount}/{total}</strong>
            </span>
            <span className="text-slate-400">
              Hit rate:&nbsp;
              <strong className={hitRate > baseline * 100 ? 'text-green-400' : 'text-white'}>
                {hitRate}%
              </strong>
              <span className="text-slate-500 ml-1">
                (baseline {(baseline * 100).toFixed(1)}%)
              </span>
            </span>
          </div>

          {/* Legend */}
          <div className="flex gap-4 mb-3 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-green-400 inline-block" />
              <span className="text-slate-400">Both numbers hit</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" />
              <span className="text-slate-400">One number hit</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 inline-block" />
              <span className="text-slate-400">Neither hit</span>
            </span>
          </div>

          {/* All pairs grid */}
          {annotated.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {annotated.map((p, i) => (
                <PairChip
                  key={i}
                  n1={p.n1}
                  n2={p.n2}
                  count={p.count}
                  status={p.status}
                />
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-xs">
              Pair detail not available for this draw.
            </p>
          )}

        </div>
      )}
    </div>
  )
}


// ── Default export — prediction mode (no scoring) ─────────────
// Used in DrawPage when showing pairs before a draw result.
export default function PairGrid({ pairs }) {
  if (!pairs?.length) return null

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3">
        {pairs.map((pair, i) => (
          <PairChip
            key={i}
            n1={pair.n1}
            n2={pair.n2}
            count={pair.count}
            status="default"
          />
        ))}
      </div>
      <p className="text-slate-500 text-xs">
        Co-occurrence count = times these numbers appeared together historically.
        Higher = appeared together more often. No predictive power confirmed by Phase 3.
      </p>
    </div>
  )
}