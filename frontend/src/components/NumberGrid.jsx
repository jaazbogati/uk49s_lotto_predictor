import NumberBall from './NumberBall'

// Renders all 49 numbers in a 7x7 grid with heat colouring
export default function NumberGrid({ numbers }) {
  if (!numbers) return null

  // Build lookup: number → status
  const statusMap = {}
  numbers.forEach(n => { statusMap[n.number] = n.status })

  return (
    <div className="grid grid-cols-7 gap-2">
      {Array.from({ length: 49 }, (_, i) => i + 1).map(n => (
        <div key={n} className="flex items-center justify-center">
          <NumberBall
            number={n}
            status={statusMap[n] || "➖ Neutral"}
            size="md"
          />
        </div>
      ))}
    </div>
  )
}