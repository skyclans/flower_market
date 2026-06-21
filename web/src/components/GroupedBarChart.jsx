import { seriesLabel, won } from '../util.js'

/* 순수 SVG 그룹형 막대 차트 (매출=녹색 / 매입=파랑) */
export default function GroupedBarChart({ points, granularity }) {
  const pts = points || []
  const max = Math.max(0, ...pts.map((p) => Math.max(p.sale || 0, p.purchase || 0)))

  if (pts.length === 0 || max === 0) {
    return <div className="gchart-empty">아직 거래 기록이 없어요</div>
  }

  // viewBox 좌표계 (uniform 스케일 → 막대 rx·텍스트 왜곡 없음)
  const W = 320, H = 180
  const padL = 6, padR = 6, padT = 10, padB = 26
  const plotW = W - padL - padR
  const plotH = H - padT - padB
  const baseY = padT + plotH

  // 스케일: 최댓값을 "보기 좋은" 상한으로 올림 (눈금 깔끔하게)
  const niceMax = niceCeil(max)

  const n = pts.length
  const slot = plotW / n
  const groupGap = Math.min(slot * 0.28, 10)   // 그룹 사이 여백
  const innerGap = 2                            // 막대 둘 사이
  const barW = Math.max(2, (slot - groupGap - innerGap) / 2)
  const rx = Math.min(barW / 2, 3)

  // 그리드 라인 (0 / 50% / 100%)
  const grids = [0, 0.5, 1].map((f) => ({ f, y: baseY - f * plotH, v: niceMax * f }))

  // x축 라벨 솎기: 최대 ~6개만 표시
  const maxLabels = 6
  const step = Math.max(1, Math.ceil(n / maxLabels))

  const barH = (v) => ((v || 0) / niceMax) * plotH

  return (
    <div className="gchart">
      <div className="gchart-legend">
        <span><i className="gleg-dot gleg-sale" /> 매출</span>
        <span><i className="gleg-dot gleg-buy" /> 매입</span>
      </div>
      <svg className="gchart-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" role="img">
        {grids.map((g, i) => (
          <line key={i} x1={padL} x2={W - padR} y1={g.y} y2={g.y}
            stroke="var(--line)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        ))}
        {pts.map((p, i) => {
          const gx = padL + i * slot + groupGap / 2
          const saleH = barH(p.sale)
          const buyH = barH(p.purchase)
          const showLabel = i % step === 0 || i === n - 1
          return (
            <g key={p.bucket}>
              <rect x={gx} y={baseY - saleH} width={barW} height={Math.max(0, saleH)} rx={rx}
                fill="var(--green)">
                <title>{seriesLabel(p.bucket, granularity)} 매출 {won(p.sale)}원</title>
              </rect>
              <rect x={gx + barW + innerGap} y={baseY - buyH} width={barW} height={Math.max(0, buyH)} rx={rx}
                fill="var(--blue)">
                <title>{seriesLabel(p.bucket, granularity)} 매입 {won(p.purchase)}원</title>
              </rect>
              {showLabel && (
                <text x={gx + barW + innerGap / 2} y={H - 6} className="gchart-xlbl"
                  textAnchor="middle">{seriesLabel(p.bucket, granularity)}</text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// 최댓값을 깔끔한 상한으로 올림 (1·2·5 × 10^n)
function niceCeil(v) {
  if (v <= 0) return 1
  const exp = Math.floor(Math.log10(v))
  const base = Math.pow(10, exp)
  const f = v / base
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10
  return nice * base
}
