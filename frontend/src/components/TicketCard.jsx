import NumberBall from './NumberBall'

export default function TicketCard({ ticket, rank }) {
  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700
                    hover:border-blue-500/50 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <span className="text-slate-400 text-sm">Ticket #{rank}</span>
        <span className="text-blue-400 text-sm font-mono">
          Score: {ticket.overall_score}
        </span>
      </div>

      {/* Number balls */}
      <div className="flex gap-2 flex-wrap mb-4">
        {ticket.ticket.map(n => (
          <NumberBall key={n} number={n} size="lg" />
        ))}
      </div>

      {/* Balance indicators */}
      <div className="flex gap-4 text-xs text-slate-400">
        <span>⚖️ {ticket.odd_even}</span>
        <span>📊 {ticket.high_low}</span>
      </div>
    </div>
  )
}