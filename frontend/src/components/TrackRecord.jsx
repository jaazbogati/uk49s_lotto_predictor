import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import LoadingSpinner from './LoadingSpinner'

export default function TrackRecord({ drawType }) {
  const { data, isLoading, error } = useQuery({
    queryKey:  ['track-record', drawType],
    queryFn:   () => axios.get(`/api/v1/track-record/${drawType}`)
                         .then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <LoadingSpinner message="Loading track record..." />
  if (error)     return null   // Fail silently — not critical

  return (
    <div className="bg-slate-800 rounded-2xl p-6 mt-8">
      <h2 className="text-white text-xl font-bold mb-2">
        📋 Live Prediction Track Record
      </h2>
      <p className="text-slate-400 text-sm mb-6">
        Real predictions scored against actual draw outcomes.
        Grows daily as predictions are logged and draws happen.
      </p>

      {data?.total_scored === 0 ? (
        <p className="text-slate-500 text-sm">
          {data?.message || "No scored predictions yet."}
        </p>
      ) : (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-700 rounded-xl p-4">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">
                Total Scored
              </p>
              <p className="text-white text-2xl font-bold">
                {data?.total_scored}
              </p>
            </div>
            <div className="bg-slate-700 rounded-xl p-4">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">
                Avg Hits
              </p>
              <p className="text-white text-2xl font-bold">
                {data?.avg_hits}
              </p>
            </div>
            <div className="bg-slate-700 rounded-xl p-4">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">
                Random Baseline
              </p>
              <p className="text-slate-400 text-2xl font-bold">
                {data?.random_baseline}
              </p>
            </div>
          </div>

          {/* Recent predictions table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 pr-4">Date</th>
                  <th className="text-left py-2 pr-4">Ticket</th>
                  <th className="text-left py-2 pr-4">Actual</th>
                  <th className="text-left py-2 pr-4">Hits</th>
                  <th className="text-left py-2">Booster</th>
                </tr>
              </thead>
              <tbody>
                {data?.recent_predictions?.map((row, i) => (
                  <tr key={i}
                    className="border-b border-slate-700/50
                               hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 pr-4 text-slate-400">
                      {new Date(row.date).toLocaleDateString('en-GB')}
                    </td>
                    <td className="py-3 pr-4 font-mono text-slate-300 text-xs">
                      {row.ticket?.join(', ')}
                    </td>
                    <td className="py-3 pr-4 font-mono text-slate-400 text-xs">
                      {row.actual?.join(', ') || '—'}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                        row.hits >= 3 ? 'bg-green-500/20 text-green-400' :
                        row.hits >= 1 ? 'bg-blue-500/20 text-blue-400' :
                        'bg-slate-600/50 text-slate-400'
                      }`}>
                        {row.hits ?? '—'}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400">
                      {row.booster_hit ? '✅' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Honest disclaimer */}
          <p className="text-slate-500 text-xs mt-4">
            Random baseline: {data?.random_baseline} expected hits per ticket by chance alone.
            A model performing at baseline is performing as Phase 3 statistical tests predicted.
          </p>
        </>
      )}
    </div>
  )
}