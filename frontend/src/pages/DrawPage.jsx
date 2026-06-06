import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useStats, useNumbers, usePredictions, useLogPredictions } from '../hooks/useDrawData'
import LoadingSpinner from '../components/LoadingSpinner'
import NumberGrid from '../components/NumberGrid'
import TicketCard from '../components/TicketCard'
import StatBadge from '../components/StatBadge'
import TrackRecord from '../components/TrackRecord'
import PairGrid, { ScoredPairAccordion } from '../components/PairGrid'  // ← added named import

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts'

// ── usePairRecord ──────────────────────────────────────────────
// Fetches scored predictions, groups by draw_date so we get
// one accordion per draw (not one per ticket).
function usePairRecord(drawType) {
  return useQuery({
    queryKey:  ['pair-record', drawType],
    queryFn:   async () => {
      // Use the new logged-predictions endpoint so we get predicted_pairs too
      const res  = await axios.get(`/api/v1/logged-predictions/${drawType}?status=scored`)
      const rows = res.data?.predictions ?? []

      // Group by draw_date — one entry per draw date
      const byDate = {}
      for (const row of rows) {
        const key = row.draw_date
        if (!byDate[key]) {
          byDate[key] = {
            draw_date:      row.draw_date,
            draw_type:      row.draw_type,
            actual_numbers: row.actual_numbers ?? [],
            pair_hits:      null,
            pairs:          null,   // full predicted pairs list for colour-coding
          }
        }
        // Take pair_hits from whichever ticket has it (first ticket in group)
        if (row.pair_hits && !byDate[key].pair_hits) {
          byDate[key].pair_hits = row.pair_hits
        }
        // Take predicted_pairs from the ticket that stored them (has_pairs=true)
        if (row.predicted_pairs && !byDate[key].pairs) {
          byDate[key].pairs = row.predicted_pairs
        }
      }

      return Object.values(byDate)
        .filter(d => d.pair_hits)
        .sort((a, b) => b.draw_date.localeCompare(a.draw_date))
    },
    staleTime: 0,
    enabled:   !!drawType,
  })
}

// ── MetricCard ─────────────────────────────────────────────────
function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-slate-700/50 rounded-xl p-4">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className="text-white text-2xl font-bold">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

// ── PairRecord sub-component ───────────────────────────────────
// One ScoredPairAccordion per draw date — actual numbers at top,
// all 20 pairs colour-coded green/amber/slate.
function PairRecord({ drawType, drawLabel }) {
  const { data, isLoading, isError } = usePairRecord(drawType)

  if (isLoading) return <LoadingSpinner message="Loading pair record..." />
  if (isError)   return (
    <p className="text-slate-500 text-sm py-4">
      Could not load pair record. Make sure scored predictions exist.
    </p>
  )
  if (!data?.length) return (
    <div className="bg-slate-700/30 rounded-xl p-6 text-center mt-4">
      <p className="text-slate-400 text-sm">
        No scored pair data yet for {drawLabel}.
      </p>
      <p className="text-slate-500 text-xs mt-1">
        Generate predictions, save them, then score after the draw.
      </p>
    </div>
  )

  // Summary aggregates across all scored draws
  const totalDraws  = data.length
  const avgHitCount = (
    data.reduce((s, d) => s + (d.pair_hits?.hit_count ?? 0), 0) / totalDraws
  ).toFixed(2)
  const avgHitRate  = (
    data.reduce((s, d) => s + (d.pair_hits?.hit_rate  ?? 0), 0) / totalDraws
  ).toFixed(1)
  const baseline    = data[0]?.pair_hits?.random_baseline ?? 0.2551

  return (
    <div className="mt-4 space-y-4">

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Draws Scored"    value={totalDraws} />
        <MetricCard label="Avg Pairs Hit"   value={avgHitCount} />
        <MetricCard label="Avg Hit Rate"    value={`${avgHitRate}%`} />
        <MetricCard
          label="Random Baseline"
          value={`${(baseline * 100).toFixed(1)}%`}
          sub="expected by chance"
        />
      </div>

      {/* One accordion per draw */}
      <div>
        <h3 className="text-slate-300 text-sm font-semibold uppercase tracking-wider mb-3">
          Per-Draw Pair Results
        </h3>
        {data.map((draw, i) => (
          <ScoredPairAccordion
            key={i}
            drawDate={draw.draw_date}
            drawType={draw.draw_type}
            actualNumbers={draw.actual_numbers}
            pairHits={draw.pair_hits}
            pairs={draw.pairs ?? []}
          />
        ))}
      </div>

    </div>
  )
}


// ── DrawPage (main) ────────────────────────────────────────────
export default function DrawPage() {
  const { pathname } = useLocation()
  const drawType     = pathname.includes('teatime') ? 'teatime' : 'lunchtime'
  const drawLabel    = drawType === 'lunchtime' ? 'Lunchtime' : 'Teatime'

  const prevDrawType = useRef(drawType)

  const { data: stats,   isLoading: statsLoading }   = useStats(drawType)
  const { data: numbers, isLoading: numbersLoading } = useNumbers(drawType)

  const [runPrediction,   setRunPrediction]   = useState(false)
  const [nTickets,        setNTickets]        = useState(5)
  const [showPairs,       setShowPairs]       = useState(false)
  const [showPairRecord,  setShowPairRecord]  = useState(false)

  const [logDate, setLogDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() + 1)
    return d.toISOString().split('T')[0]
  })

  const {
    data:      predictions,
    isLoading: predLoading,
    refetch:   rerunPrediction
  } = usePredictions(drawType, runPrediction, nTickets)

  const {
    mutate:    saveLog,
    isPending: saving,
    isSuccess: saved,
    data:      saveResult,
    reset:     resetSave
  } = useLogPredictions()

  useEffect(() => {
    if (prevDrawType.current !== drawType) {
      prevDrawType.current = drawType
      setRunPrediction(false)
      setNTickets(5)
      setShowPairs(false)
      setShowPairRecord(false)
      const d = new Date()
      d.setDate(d.getDate() + 1)
      setLogDate(d.toISOString().split('T')[0])
      resetSave()
    }
  }, [drawType, resetSave])

  const handleGenerate = () => {
    setShowPairs(false)
    if (saved) resetSave()
    if (runPrediction) {
      rerunPrediction()
    } else {
      setRunPrediction(true)
    }
  }

  const getBarColor = (status) => {
    if (status === '🔥 Hot')  return '#EF4444'
    if (status === '🧊 Cold') return '#3B82F6'
    return '#64748B'
  }

  const pairCount = predictions?.top_pairs?.length ?? 0

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">

      {/* ── Header ─────────────────────────────────────────── */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            drawType === 'lunchtime'
              ? 'bg-blue-500/20 text-blue-400'
              : 'bg-orange-500/20 text-orange-400'
          }`}>
            {drawLabel}
          </span>
        </div>
        <h1 className="text-3xl font-bold text-white">
          {drawLabel} Analysis
        </h1>
        <p className="text-slate-400 mt-2">
          Frequency analysis, statistical scoring, and AI-assisted ticket suggestions.
        </p>
      </div>

      {/* ── Stat badges ────────────────────────────────────── */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <StatBadge label="Total Draws"  value={stats.total_draws?.toLocaleString()} />
          <StatBadge label="Hot Numbers"  value={stats.hot_numbers?.length}
                     sub={stats.hot_numbers?.slice(0,3).join(', ')} />
          <StatBadge label="Cold Numbers" value={stats.cold_numbers?.length}
                     sub={stats.cold_numbers?.slice(0,3).join(', ')} />
          <StatBadge label="Date Range"
                     value={stats.date_range?.from?.slice(0,7)}
                     sub={`to ${stats.date_range?.to?.slice(0,7)}`} />
        </div>
      )}

      {/* ── Number heatmap ─────────────────────────────────── */}
      <div className="bg-slate-800 rounded-2xl p-6 mb-8">
        <h2 className="text-white text-xl font-bold mb-2">Number Heatmap</h2>
        <p className="text-slate-400 text-sm mb-6">
          🔴 Hot &nbsp; 🔵 Cold &nbsp; ⚫ Neutral — based on historical frequency + recency
        </p>
        {numbersLoading
          ? <LoadingSpinner message="Loading number scores..." />
          : <NumberGrid numbers={numbers?.numbers} />
        }
      </div>

      {/* ── Frequency bar chart ────────────────────────────── */}
      <div className="bg-slate-800 rounded-2xl p-6 mb-8">
        <h2 className="text-white text-xl font-bold mb-6">Frequency Chart</h2>
        {statsLoading
          ? <LoadingSpinner />
          : stats?.frequency && (() => {
              const sorted = [...stats.frequency]
                .sort((a, b) => a.number - b.number)
                .map(entry => ({ ...entry, fill: getBarColor(entry.status) }))

              return (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={sorted}>
                    <XAxis dataKey="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: '#1e293b', border: '1px solid #334155',
                        borderRadius: '8px', color: '#f1f5f9'
                      }}
                    />
                    <ReferenceLine
                      y={sorted[0]?.expected}
                      stroke="#f59e0b"
                      strokeDasharray="4 4"
                      label={{ value: 'Expected', fill: '#f59e0b', fontSize: 11 }}
                    />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]} fill="#64748B" />
                  </BarChart>
                </ResponsiveContainer>
              )
            })()
        }
      </div>

      {/* ── Statistical reality check ──────────────────────── */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6 mb-8">
        <h2 className="text-amber-400 font-bold text-lg mb-2">
          ⚠️ Statistical Reality Check
        </h2>
        <p className="text-slate-300 text-sm leading-relaxed">
          Chi-square tests confirm these draws are statistically random
          (p = 0.6689 Lunchtime / p = 0.1975 Teatime).
          Hot number analysis shows <strong>no predictive power</strong> (p = 0.772).
          Overdue scores show <strong>no predictive power</strong> (p = 0.541).
          Lunchtime and Teatime draws are <strong>independent</strong> (p = 0.308).
          All suggestions below are for entertainment only.
        </p>
      </div>

      {/* ── Prediction engine ──────────────────────────────── */}
      <div className="bg-slate-800 rounded-2xl p-6">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-white text-xl font-bold">🎯 Prediction Engine</h2>
            <p className="text-slate-400 text-sm mt-1">
              Monte Carlo → Genetic Algorithm → Scored suggestions
              <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${
                drawType === 'lunchtime'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-orange-500/20 text-orange-400'
              }`}>
                {drawLabel} draw
              </span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={nTickets}
              onChange={e => setNTickets(Number(e.target.value))}
              className="bg-slate-700 text-white rounded-lg px-3 py-2
                         text-sm border border-slate-600"
            >
              {[3, 5, 7, 10].map(n => (
                <option key={n} value={n}>{n} tickets</option>
              ))}
            </select>

            <button
              onClick={handleGenerate}
              disabled={predLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600
                         text-white px-6 py-2 rounded-xl font-medium
                         transition-colors text-sm"
            >
              {predLoading ? 'Running (~60s)...' : 'Generate'}
            </button>
          </div>
        </div>

        {predLoading && (
          <LoadingSpinner message="Running Monte Carlo + Genetic Algorithm..." />
        )}

        {predictions && !predLoading && (
          <>
            {/* Ticket suggestions */}
            <div className="mb-2">
              <h3 className="text-slate-300 text-sm font-semibold uppercase tracking-wider mb-4">
                🎟️ Ticket Suggestions — {drawLabel}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {predictions.suggestions.map((ticket, i) => (
                  <TicketCard key={i} ticket={ticket} rank={i + 1} />
                ))}
              </div>
            </div>

            {/* Pair analysis — toggle-controlled, hidden by default */}
            {pairCount > 0 && (
              <div className="mt-8 pt-6 border-t border-slate-700">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-slate-300 text-sm font-semibold uppercase tracking-wider">
                      🔗 Pair Analysis
                    </h3>
                    <p className="text-slate-500 text-xs mt-0.5">
                      {pairCount} co-occurring pairs from historical {drawLabel} draws
                    </p>
                  </div>
                  <button
                    onClick={() => setShowPairs(prev => !prev)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm
                                font-medium transition-all border ${
                      showPairs
                        ? 'bg-slate-600 border-slate-500 text-white'
                        : 'bg-slate-700 border-slate-600 text-slate-300 hover:text-white hover:border-slate-500'
                    }`}
                  >
                    <span>{showPairs ? '▲ Hide' : '▼ Show'} Pairs</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                      drawType === 'lunchtime'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-orange-500/20 text-orange-400'
                    }`}>
                      {pairCount}
                    </span>
                  </button>
                </div>

                {showPairs && (
                  <div className="bg-slate-700/40 rounded-xl p-4 border border-slate-700">
                    <p className="text-slate-500 text-xs mb-4 leading-relaxed">
                      Pairs that appear together most often in historical {drawLabel} draws.
                      <strong className="text-amber-400 ml-1">
                        Phase 3 confirms no predictive power — for reference only.
                      </strong>
                    </p>
                    <PairGrid pairs={predictions.top_pairs} />
                  </div>
                )}
              </div>
            )}

            {/* Save predictions */}
            <div className="mt-6 pt-6 border-t border-slate-700">
              {saved ? (
                <div className="bg-green-500/10 border border-green-500/30
                                rounded-xl p-4 flex items-center gap-3">
                  <span className="text-green-400 text-lg">✅</span>
                  <div>
                    <p className="text-green-400 font-medium text-sm">
                      {saveResult?.message}
                    </p>
                    <p className="text-slate-400 text-xs mt-1">
                      Visible in Track Record after the draw date passes and results are scored.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-700/50 rounded-xl p-4">
                  <h3 className="text-white font-medium mb-3">📝 Log These Predictions</h3>
                  <p className="text-slate-400 text-xs mb-4">
                    Save to track record. After the draw, run Score Pending to see how many numbers matched.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                    <div>
                      <label className="text-slate-400 text-xs block mb-1">
                        Draw date to predict for
                      </label>
                      <input
                        type="date"
                        value={logDate}
                        onChange={e => setLogDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                        className="bg-slate-600 text-white rounded-lg px-3 py-2
                                   text-sm border border-slate-500
                                   focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <button
                      onClick={() => saveLog({
                        draw_type:       drawLabel,
                        draw_date:       logDate,
                        suggestions:     predictions.suggestions,
                        ga_fitness:      predictions.ga_fitness,
                        predicted_pairs: predictions.top_pairs
                      })}
                      disabled={saving}
                      className="bg-blue-600 hover:bg-blue-700
                                 disabled:bg-slate-600 text-white px-5 py-2
                                 rounded-xl font-medium transition-colors text-sm"
                    >
                      {saving ? '💾 Saving...' : '💾 Save to Log'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {!runPrediction && !predLoading && (
          <div className="text-center py-10 text-slate-500">
            Click Generate to run the full prediction pipeline
          </div>
        )}
      </div>

      {/* ── Ticket Track Record ────────────────────────────── */}
      <TrackRecord drawType={drawType} />

      {/* ── Pair Prediction Record ─────────────────────────── */}
      <div className="bg-slate-800 rounded-2xl p-6 mt-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="text-white text-xl font-bold">🔗 Pair Prediction Record</h2>
            <p className="text-slate-400 text-sm mt-1">
              How often predicted pairs appeared together in scored {drawLabel} draws
            </p>
          </div>
          <button
            onClick={() => setShowPairRecord(prev => !prev)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm
                        font-medium transition-all border ${
              showPairRecord
                ? 'bg-slate-600 border-slate-500 text-white'
                : 'bg-slate-700 border-slate-600 text-slate-300 hover:text-white hover:border-slate-500'
            }`}
          >
            {showPairRecord ? '▲ Hide' : '▼ Show'} Record
          </button>
        </div>

        {showPairRecord && (
          <PairRecord drawType={drawType} drawLabel={drawLabel} />
        )}
      </div>

    </div>
  )
}