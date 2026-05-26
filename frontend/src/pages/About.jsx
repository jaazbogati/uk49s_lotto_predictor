export default function About() {
  const phases = [
    { phase: 1, title: "Data Scraping",        tech: "Python, BeautifulSoup, PostgreSQL",
      desc: "Automated scraper collects every UK49s draw since 2020. POST-based pagination, retry logic, duplicate prevention via ON CONFLICT DO NOTHING." },
    { phase: 2, title: "Frequency Engine",     tech: "pandas, NumPy",
      desc: "Counts appearances per number, computes gaps between appearances, rolling 90-day windows, weighted composite scores." },
    { phase: 3, title: "Statistical Tests",    tech: "SciPy",
      desc: "Chi-square goodness-of-fit, hot number predictive power test, overdue score correlation, draw independence test. All four confirm randomness." },
    { phase: 4, title: "Bayesian + Monte Carlo", tech: "NumPy, SciPy",
      desc: "Beta-Binomial Bayesian updating with exponential recency decay. Monte Carlo simulation of 100k draws to map the probability landscape." },
    { phase: 5, title: "Genetic Algorithm",    tech: "Python",
      desc: "Evolves 50 candidate tickets over 100 generations using tournament selection, crossover, and mutation. Fitness function scores spread, balance, frequency, and entropy." },
    { phase: 6, title: "Prediction Engine",    tech: "Python",
      desc: "Orchestrates all engines into one pipeline. Returns ranked tickets with full transparency about statistical limitations." },
    { phase: 7, title: "FastAPI Backend",      tech: "FastAPI, SQLAlchemy",
      desc: "REST API with 7 endpoints. CORS configured, background task scraping, auto-generated OpenAPI docs." },
    { phase: 8, title: "Streamlit Dashboard",  tech: "Streamlit, Plotly",
      desc: "Internal analytics tool with frequency heatmaps, statistical test results, and interactive prediction runner." },
    { phase: 9, title: "React Frontend",       tech: "React, Vite, Tailwind, React Query",
      desc: "Public-facing UI. Talks exclusively to FastAPI. Number heatmaps, frequency charts, ticket generator." },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">

      <h1 className="text-3xl font-bold text-white mb-4">About This Project</h1>
      <p className="text-slate-400 text-lg mb-10 leading-relaxed">
        This project started with a question: can statistical analysis of lottery
        history improve predictions? The answer — proven with your own data — is no.
        But building the system that proves it is a complete data engineering exercise.
      </p>

      {/* The honest result */}
      <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 mb-10">
        <h2 className="text-red-400 font-bold text-lg mb-3">
          What the Statistics Proved
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          {[
            ["Chi-Square (Lunchtime)", "p = 0.6689 — ✅ Random"],
            ["Chi-Square (Teatime)",   "p = 0.1975 — ✅ Random"],
            ["Hot Number Power",       "p = 0.7720 — ❌ No effect"],
            ["Overdue Score Power",    "p = 0.5406 — ❌ No effect"],
            ["Draw Independence",      "p = 0.3080 — ✅ Independent"],
          ].map(([test, result]) => (
            <div key={test} className="flex justify-between gap-4
                                       bg-slate-800 rounded-lg px-4 py-2">
              <span className="text-slate-400">{test}</span>
              <span className="text-slate-200 font-mono text-xs">{result}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Build phases */}
      <h2 className="text-white text-2xl font-bold mb-6">How It Was Built</h2>
      <div className="flex flex-col gap-4">
        {phases.map(p => (
          <div key={p.phase}
            className="bg-slate-800 rounded-xl p-5 border-l-4 border-blue-500">
            <div className="flex items-center gap-3 mb-2">
              <span className="bg-blue-600 text-white text-xs font-bold
                               px-2 py-0.5 rounded-full">
                Phase {p.phase}
              </span>
              <span className="text-white font-semibold">{p.title}</span>
              <span className="text-slate-500 text-xs ml-auto">{p.tech}</span>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed">{p.desc}</p>
          </div>
        ))}
      </div>

      {/* Portfolio note */}
      <div className="bg-blue-500/10 border border-blue-500/30
                      rounded-2xl p-6 mt-10">
        <h2 className="text-blue-400 font-bold mb-2">Project Goals</h2>
        <p className="text-slate-300 text-sm leading-relaxed">
          This project demonstrates data engineering, ETL pipelines, statistical
          modelling, probabilistic simulation, evolutionary algorithms, REST API
          design, and full-stack development — while maintaining scientific honesty
          about what the data actually shows.
        </p>
      </div>
    </div>
  )
}