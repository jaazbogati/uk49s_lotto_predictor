import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useStats, useNumbers, usePredictions } from '../hooks/useDrawData'
import LoadingSpinner from '../components/LoadingSpinner'
import NumberGrid from '../components/NumberGrid'
import TicketCard from '../components/TicketCard'
import StatBadge from '../components/StatBadge'
import TrackRecord from '../components/TrackRecord'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts'

export default function DrawPage() {
  const { pathname }    = useLocation()     // "lunchtime" or "teatime"
  const drawType        = pathname.includes('teatime') ? 'teatime' : 'lunchtime'
  const drawLabel       = drawType === 'lunchtime' ? 'Lunchtime' : 'Teatime'

  const { data: stats,   isLoading: statsLoading }   = useStats(drawType)
  const { data: numbers, isLoading: numbersLoading } = useNumbers(drawType)

  const [runPrediction, setRunPrediction] = useState(false)
  const [nTickets, setNTickets]           = useState(5)

  const {
    data:      predictions,
    isLoading: predLoading,
    refetch:   rerunPrediction
  } = usePredictions(drawType, runPrediction, nTickets)

  const handleGenerate = () => {
    if (runPrediction) {
      rerunPrediction()
    } else {
      setRunPrediction(true)
    }
  }

  // Colour bars by status
  const getBarColor = (status) => {
    if (status === '🔥 Hot')     return '#EF4444'
    if (status === '🧊 Cold')    return '#3B82F6'
    return '#64748B'
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">

      {/* Header */}
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

      {/* Stat badges */}
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

      {/* Number heatmap grid */}
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

      {/* Frequency bar chart */}
      <div className="bg-slate-800 rounded-2xl p-6 mb-8">
        <h2 className="text-white text-xl font-bold mb-6">
          Frequency Chart
        </h2>
        {statsLoading
          ? <LoadingSpinner />
          : stats?.frequency && (() => {
              // Pre-compute sorted data outside JSX — avoids Recharts Cell issues
              const sorted = [...stats.frequency]
                .sort((a, b) => a.number - b.number)
                .map(entry => ({
                  ...entry,
                  fill: getBarColor(entry.status)
                }))

              return (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={sorted}>
                    <XAxis
                      dataKey="number"
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                    />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background:   '#1e293b',
                        border:       '1px solid #334155',
                        borderRadius: '8px',
                        color:        '#f1f5f9'
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

      {/* Statistical reality check */}
      <div className="bg-amber-500/10 border border-amber-500/30
                      rounded-2xl p-6 mb-8">
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

      {/* Prediction engine */}
      <div className="bg-slate-800 rounded-2xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center
                        justify-between gap-4 mb-6">
          <div>
            <h2 className="text-white text-xl font-bold">
              🎯 Prediction Engine
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Monte Carlo → Genetic Algorithm → Scored suggestions
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={nTickets}
              onChange={e => setNTickets(Number(e.target.value))}
              className="bg-slate-700 text-white rounded-lg px-3 py-2
                         text-sm border border-slate-600"
            >
              {[3,5,7,10].map(n => (
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {predictions.suggestions.map((ticket, i) => (
              <TicketCard key={i} ticket={ticket} rank={i + 1} />
            ))}
          </div>
        )}

        {!runPrediction && !predLoading && (
          <div className="text-center py-10 text-slate-500">
            Click Generate to run the full prediction pipeline
          </div>
        )}
      </div>
      {/* Track Record Section */}
      <TrackRecord drawType={drawType} />
    </div>
  )
}