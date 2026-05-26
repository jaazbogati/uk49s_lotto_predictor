import { Link } from 'react-router-dom'
import { useLatest } from '../hooks/useDrawData'
import LoadingSpinner from '../components/LoadingSpinner'
import StatBadge from '../components/StatBadge'
import NumberBall from '../components/NumberBall'

export default function Home() {
  const { data, isLoading, error } = useLatest(10)

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">

      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">
          UK49s Statistical Analytics
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          A full data science pipeline — scraping, frequency analysis,
          Bayesian modelling, Monte Carlo simulation, and a Genetic Algorithm.
          Built to analyse patterns, and to prove they don't beat randomness.
        </p>

        <div className="flex gap-4 justify-center mt-8">
          <Link to="/lunchtime"
            className="bg-blue-600 hover:bg-blue-700 text-white
                       px-6 py-3 rounded-xl font-medium transition-colors">
            Lunchtime Analysis
          </Link>
          <Link to="/teatime"
            className="bg-slate-700 hover:bg-slate-600 text-white
                       px-6 py-3 rounded-xl font-medium transition-colors">
            Teatime Analysis
          </Link>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <StatBadge label="Total Draws"     value="4,471+"  sub="since 2020" />
        <StatBadge label="Draw Types"      value="2"       sub="Lunchtime + Teatime" />
        <StatBadge label="Possible Combos" value="13.9M"   sub="1 in 13,983,816" />
        <StatBadge label="Randomness"      value="✅ Proven" sub="p > 0.05" />
      </div>

      {/* Recent results */}
      <div className="bg-slate-800 rounded-2xl p-6">
        <h2 className="text-white text-xl font-bold mb-6">
          Recent Draws
        </h2>

        {isLoading && <LoadingSpinner message="Loading recent draws..." />}
        {error    && <p className="text-red-400">Failed to load draws.</p>}

        {data && (
          <div className="flex flex-col gap-4">
            {data.results.map((draw, i) => (
              <div key={i}
                className="flex flex-col sm:flex-row sm:items-center
                           justify-between gap-3 py-3 border-b border-slate-700
                           last:border-0">

                <div className="flex flex-col gap-1">
                  <span className="text-slate-400 text-sm">
                    {new Date(draw.date).toLocaleDateString('en-GB', {
                      weekday: 'short', day: 'numeric',
                      month: 'short', year: 'numeric'
                    })}
                  </span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full w-fit ${
                    draw.draw_type === 'Lunchtime'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-orange-500/20 text-orange-400'
                  }`}>
                    {draw.draw_type}
                  </span>
                </div>

                <div className="flex gap-2 items-center flex-wrap">
                  {draw.numbers.map(n => (
                    <NumberBall key={n} number={n} size="sm" />
                  ))}
                  <span className="text-slate-500 text-xs mx-1">+</span>
                  <NumberBall number={draw.booster} size="sm"
                    status="➖ Neutral" />
                  <span className="text-slate-500 text-xs ml-1">(B)</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}