import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import LoadingSpinner from './LoadingSpinner'

// ── API helpers ────────────────────────────────────────────────
const fetchTrackRecord  = (drawType) =>
  axios.get(`/api/v1/track-record/${drawType}`).then(r => r.data)

const fetchAllLogged    = (drawType, status) =>
  axios.get(`/api/v1/logged-predictions/${drawType}`, {
    params: status !== 'all' ? { status } : {}
  }).then(r => r.data)

const deleteprediction  = (id) =>
  axios.delete(`/api/v1/logged-predictions/${id}`).then(r => r.data)

const scorePending      = () =>
  axios.post('/api/v1/score-pending').then(r => r.data)

// ── Small reusable metric card ─────────────────────────────────
function MetricCard({ label, value, highlight }) {
  return (
    <div className="bg-slate-700 rounded-xl p-4">
      <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? 'text-green-400' : 'text-white'}`}>
        {value ?? '—'}
      </p>
    </div>
  )
}

// ── Hits badge ─────────────────────────────────────────────────
function HitsBadge({ hits }) {
  if (hits == null) return <span className="text-slate-500 text-xs">—</span>
  const cls =
    hits >= 3 ? 'bg-green-500/20 text-green-400' :
    hits >= 1 ? 'bg-blue-500/20  text-blue-400'  :
                'bg-slate-600/50 text-slate-400'
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cls}`}>
      {hits}
    </span>
  )
}

// ── Status badge ───────────────────────────────────────────────
function StatusBadge({ status }) {
  const styles = {
    scored:  'bg-green-500/15  text-green-400',
    pending: 'bg-amber-500/15  text-amber-400',
    missed:  'bg-red-500/15    text-red-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? 'text-slate-400'}`}>
      {status}
    </span>
  )
}

// ── Pair hits cell ─────────────────────────────────────────────
function PairCell({ pairHits }) {
  const [open, setOpen] = useState(false)
  if (!pairHits || pairHits.hit_count == null)
    return <span className="text-slate-500 text-xs">—</span>

  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-slate-300 hover:text-white transition-colors"
      >
        {pairHits.hit_count}/{pairHits.predicted_pairs ?? 20}
        <span className="text-slate-500 ml-1">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="mt-1 bg-slate-700 rounded-lg p-2 text-xs space-y-1 min-w-[180px]">
          <p className="text-slate-400">
            Hit rate: <span className="text-white">{pairHits.hit_rate}%</span>
            <span className="text-slate-500 ml-2">
              (baseline {((pairHits.random_baseline ?? 0.26) * 100).toFixed(0)}%)
            </span>
          </p>
          {pairHits.hit_pairs?.length > 0 && (
            <p className="text-green-400">
              ✅ {pairHits.hit_pairs.join(', ')}
            </p>
          )}
          {pairHits.near_misses?.length > 0 && (
            <p className="text-slate-400">
              Almost: {pairHits.near_misses.slice(0, 3).join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main TrackRecord component ─────────────────────────────────
export default function TrackRecord({ drawType }) {
  const queryClient = useQueryClient()

  // View controls
  const [activeTab,    setActiveTab]    = useState('scored')   // 'scored' | 'all'
  const [statusFilter, setStatusFilter] = useState('all')      // 'all' | 'pending' | 'scored' | 'missed'
  const [showPairCol,  setShowPairCol]  = useState(true)
  const [confirmId,    setConfirmId]    = useState(null)        // id pending delete confirm

  // ── Scored track record ──────────────────────────────────────
  const {
    data:      scored,
    isLoading: scoredLoading,
    refetch:   refetchScored
  } = useQuery({
    queryKey:  ['track-record', drawType],
    queryFn:   () => fetchTrackRecord(drawType),
    staleTime: 0,                    // always fresh — no stale cache
    refetchOnWindowFocus: true,
  })

  // ── All logged (pending + scored + missed) ───────────────────
  const {
    data:      allLogged,
    isLoading: allLoading,
    refetch:   refetchAll
  } = useQuery({
    queryKey:  ['logged-predictions', drawType, statusFilter],
    queryFn:   () => fetchAllLogged(drawType, statusFilter),
    staleTime: 0,
    enabled:   activeTab === 'all',
    refetchOnWindowFocus: true,
  })

  // ── Delete mutation ──────────────────────────────────────────
  const { mutate: doDelete, isPending: deleting } = useMutation({
    mutationFn: deleteprediction,
    onSuccess: () => {
      setConfirmId(null)
      // Invalidate both caches immediately
      queryClient.invalidateQueries({ queryKey: ['track-record', drawType] })
      queryClient.invalidateQueries({ queryKey: ['logged-predictions', drawType] })
    }
  })

  // ── Score pending mutation ───────────────────────────────────
  const { mutate: doScore, isPending: scoring, isSuccess: scoreSuccess } = useMutation({
    mutationFn: scorePending,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['track-record', drawType] })
      queryClient.invalidateQueries({ queryKey: ['logged-predictions', drawType] })
    }
  })

  const refetchAll_ = () => { refetchScored(); refetchAll() }

  // ── Render ───────────────────────────────────────────────────
  return (
    <div className="bg-slate-800 rounded-2xl p-6 mt-8">

      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="text-white text-xl font-bold">📋 Prediction Track Record</h2>
          <p className="text-slate-400 text-sm mt-1">
            Manage all logged predictions for {drawType === 'lunchtime' ? 'Lunchtime' : 'Teatime'} draws
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Refresh */}
          <button
            onClick={refetchAll_}
            className="px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-slate-700 border border-slate-600
                       text-slate-300 hover:text-white transition-colors"
          >
            🔄 Refresh
          </button>

          {/* Score pending */}
          <button
            onClick={() => doScore()}
            disabled={scoring}
            className="px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-blue-600/20 border border-blue-500/40
                       text-blue-400 hover:text-blue-300 transition-colors
                       disabled:opacity-50"
          >
            {scoring ? '⏳ Scoring...' : '⚡ Score Pending'}
          </button>

          {/* Pair column toggle */}
          <button
            onClick={() => setShowPairCol(p => !p)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showPairCol
                ? 'bg-slate-600 border-slate-500 text-white'
                : 'bg-slate-700 border-slate-600 text-slate-400 hover:text-white'
            }`}
          >
            🔗 {showPairCol ? 'Hide' : 'Show'} Pairs
          </button>
        </div>
      </div>

      {scoreSuccess && (
        <div className="mb-4 bg-green-500/10 border border-green-500/30 rounded-xl px-4 py-2">
          <p className="text-green-400 text-xs">
            ✅ Scoring complete — pending predictions updated.
          </p>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 bg-slate-700/50 rounded-xl p-1 w-fit">
        {[
          { key: 'scored', label: '✅ Scored' },
          { key: 'all',    label: '📂 All Logged' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-slate-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── SCORED TAB ─────────────────────────────────────── */}
      {activeTab === 'scored' && (
        <>
          {scoredLoading ? (
            <LoadingSpinner message="Loading scored predictions..." />
          ) : !scored || scored.total_scored === 0 ? (
            <div className="text-center py-10">
              <p className="text-slate-400 text-sm">{scored?.message || 'No scored predictions yet.'}</p>
              <p className="text-slate-500 text-xs mt-1">
                Generate predictions, save them, then click ⚡ Score Pending after the draw.
              </p>
            </div>
          ) : (
            <>
              {/* Summary metrics */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <MetricCard label="Total Scored"    value={scored.total_scored} />
                <MetricCard label="Avg Hits"        value={scored.avg_hits} />
                <MetricCard label="Random Baseline" value={scored.random_baseline} />
              </div>

              {/* Scored table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
                      <th className="text-left py-2 pr-3">Date</th>
                      <th className="text-left py-2 pr-3">Ticket</th>
                      <th className="text-left py-2 pr-3">Actual</th>
                      <th className="text-left py-2 pr-3">Hits</th>
                      {showPairCol && <th className="text-left py-2 pr-3">Pairs</th>}
                      <th className="text-left py-2">Booster</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scored.recent_predictions?.map((row, i) => (
                      <tr key={i}
                        className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-3 pr-3 text-slate-400 text-xs whitespace-nowrap">
                          {new Date(row.date + 'T00:00:00').toLocaleDateString('en-GB')}
                        </td>
                        <td className="py-3 pr-3 font-mono text-slate-300 text-xs">
                          {row.ticket?.join(', ')}
                        </td>
                        <td className="py-3 pr-3 font-mono text-slate-400 text-xs">
                          {row.actual?.join(', ') || '—'}
                        </td>
                        <td className="py-3 pr-3">
                          <HitsBadge hits={row.hits} />
                        </td>
                        {showPairCol && (
                          <td className="py-3 pr-3">
                            <PairCell pairHits={row.pair_hits} />
                          </td>
                        )}
                        <td className="py-3 text-slate-400 text-xs">
                          {row.booster_hit ? '✅' : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="text-slate-500 text-xs mt-4">
                Random baseline: {scored.random_baseline} expected hits per ticket by chance.
              </p>
            </>
          )}
        </>
      )}

      {/* ── ALL LOGGED TAB ─────────────────────────────────── */}
      {activeTab === 'all' && (
        <>
          {/* Status filter pills */}
          <div className="flex flex-wrap gap-2 mb-5">
            <span className="text-slate-400 text-xs self-center mr-1">Filter:</span>
            {['all', 'pending', 'scored', 'missed'].map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all border ${
                  statusFilter === s
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-slate-700 border-slate-600 text-slate-400 hover:text-white'
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          {allLoading ? (
            <LoadingSpinner message="Loading logged predictions..." />
          ) : !allLogged?.predictions?.length ? (
            <div className="text-center py-10">
              <p className="text-slate-400 text-sm">No predictions found for this filter.</p>
            </div>
          ) : (
            <>
              {/* Count summary */}
              <div className="flex gap-4 mb-4">
                <span className="text-slate-400 text-xs">
                  Total: <strong className="text-white">{allLogged.total}</strong>
                </span>
                <span className="text-amber-400 text-xs">
                  Pending: <strong>{allLogged.pending_count}</strong>
                </span>
                <span className="text-green-400 text-xs">
                  Scored: <strong>{allLogged.scored_count}</strong>
                </span>
                {allLogged.missed_count > 0 && (
                  <span className="text-red-400 text-xs">
                    Missed: <strong>{allLogged.missed_count}</strong>
                  </span>
                )}
              </div>

              {/* All logged table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
                      <th className="text-left py-2 pr-3">Date</th>
                      <th className="text-left py-2 pr-3">Status</th>
                      <th className="text-left py-2 pr-3">Ticket</th>
                      <th className="text-left py-2 pr-3">Score</th>
                      <th className="text-left py-2 pr-3">Hits</th>
                      {showPairCol && <th className="text-left py-2 pr-3">Pairs</th>}
                      <th className="text-left py-2 pr-3">Actual</th>
                      <th className="text-left py-2">Delete</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allLogged.predictions.map((row) => (
                      <tr key={row.id}
                        className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-3 pr-3 text-slate-400 text-xs whitespace-nowrap">
                          {new Date(row.draw_date + 'T00:00:00').toLocaleDateString('en-GB')}
                        </td>
                        <td className="py-3 pr-3">
                          <StatusBadge status={row.status} />
                        </td>
                        <td className="py-3 pr-3 font-mono text-slate-300 text-xs">
                          {row.ticket?.join(', ')}
                        </td>
                        <td className="py-3 pr-3 text-slate-400 text-xs">
                          {row.overall_score?.toFixed(2) ?? '—'}
                        </td>
                        <td className="py-3 pr-3">
                          <HitsBadge hits={row.hits} />
                        </td>
                        {showPairCol && (
                          <td className="py-3 pr-3">
                            <PairCell pairHits={row.pair_hits} />
                          </td>
                        )}
                        <td className="py-3 pr-3 font-mono text-slate-400 text-xs">
                          {row.actual_numbers?.join(', ') || '—'}
                        </td>
                        <td className="py-3">
                          {confirmId === row.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => doDelete(row.id)}
                                disabled={deleting}
                                className="text-xs px-2 py-0.5 rounded bg-red-600/30
                                           text-red-400 hover:bg-red-600/50 transition-colors"
                              >
                                {deleting ? '...' : 'Confirm'}
                              </button>
                              <button
                                onClick={() => setConfirmId(null)}
                                className="text-xs px-2 py-0.5 rounded bg-slate-600
                                           text-slate-300 hover:text-white transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmId(row.id)}
                              className="text-slate-500 hover:text-red-400 text-xs
                                         transition-colors px-1"
                              title="Delete this prediction"
                            >
                              🗑
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}