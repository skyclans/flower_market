import { bucketLabel } from '../util.js'

export default function BarChart({ points, period, accent = 'var(--green)', light = 'var(--bar-lt)' }) {
  if (!points || points.length === 0) return <div className="chart-empty">데이터 없음</div>
  const prices = points.map((p) => p.price)
  const max = Math.max(...prices)
  const min = Math.min(...prices)
  const span = max - min || max || 1
  const lo = min - span * 0.25
  const hi = max + span * 0.12
  return (
    <div className="bars">
      {points.map((p, i) => {
        const h = 14 + ((p.price - lo) / (hi - lo)) * 110
        const last = i === points.length - 1
        return (
          <div className="bar-col" key={p.key}>
            <div className="bar" style={{ height: `${h}px`, background: last ? accent : light }} />
            <span className="bar-lbl">{bucketLabel(p.key, period)}</span>
          </div>
        )
      })}
    </div>
  )
}
