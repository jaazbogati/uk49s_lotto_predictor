export default function StatBadge({ label, value, sub }) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-1">
      <span className="text-slate-400 text-xs uppercase tracking-wider">
        {label}
      </span>
      <span className="text-white text-2xl font-bold">{value}</span>
      {sub && <span className="text-slate-500 text-xs">{sub}</span>}
    </div>
  )
}