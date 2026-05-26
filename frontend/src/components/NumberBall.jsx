// Renders a single lottery ball with colour based on status
export default function NumberBall({ number, status, size = "md" }) {
  const sizes = {
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
  }

  const colors = {
    "🔥 Hot":     "bg-red-500 text-white shadow-red-500/40",
    "🧊 Cold":    "bg-blue-500 text-white shadow-blue-500/40",
    "➖ Neutral": "bg-slate-600 text-white shadow-slate-500/40",
    default:      "bg-yellow-400 text-slate-900 shadow-yellow-400/40",
  }

  const color = colors[status] || colors.default

  return (
    <div className={`
      ${sizes[size]} ${color}
      rounded-full flex items-center justify-center
      font-bold shadow-lg
    `}>
      {number}
    </div>
  )
}