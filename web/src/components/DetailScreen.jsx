import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, catStyle, captionFor } from '../util.js'
import Chip from './Chip.jsx'
import SegmentedControl from './SegmentedControl.jsx'
import BarChart from './BarChart.jsx'

const PERIODS = [
  { value: 'daily', label: '일간' },
  { value: 'weekly', label: '주간' },
  { value: 'monthly', label: '월간' },
  { value: 'yearly', label: '연간' },
]

const INFO = [
  ['등급', '특 · 상 · 보 · 등외'],
  ['거래 단위', '속 / 분'],
  ['경매 구분', '본경매(월·수·금) · 온라인(화·목·토)'],
  ['데이터 출처', 'aT 화훼공판장'],
]

export default function DetailScreen({ item, onBack }) {
  const [summary, setSummary] = useState(null)
  const [period, setPeriod] = useState('yearly')
  const [trend, setTrend] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.home([item]).then((d) => setSummary(d.items?.[0] || null)).catch((e) => setErr(String(e)))
  }, [item])

  useEffect(() => {
    setTrend(null)
    api.trend(item, period).then(setTrend).catch((e) => setErr(String(e)))
  }, [item, period])

  const cs = catStyle(summary?.category)

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter gap10">
          <button className="back" onClick={onBack}>‹</button>
          <span className="d-name">{item}</span>
          {summary && <Chip label={summary.category} bg={cs.bg} fg={cs.fg} />}
          <span className="grow" />
          <span className="star">★</span>
        </div>
        <div className="d-sub">aT화훼(양재){summary?.as_of ? ` · ${summary.as_of} 기준` : ''}</div>
        {summary && (
          <div className="prices d-prices">
            <div className="pcol">
              <div className="plabel plabel--main"><span className="dot" /> 본경매</div>
              <div className="pval">{won(summary.main_price)}<span className="unit"> 원/{summary.unit}</span></div>
            </div>
            <div className="pdiv" />
            <div className="pcol">
              <div className="plabel">온라인</div>
              <div className="pval pval--sub">{won(summary.online_price)}<span className="unit"> 원/{summary.unit}</span></div>
            </div>
          </div>
        )}
      </header>

      <div className="body">
        {err && <div className="error">데이터 연결 실패: {err}</div>}

        <div className="card">
          <div className="card-title">시세 현황</div>
          <SegmentedControl value={period} onChange={setPeriod} options={PERIODS} />
          <div className="caption">{captionFor(period)}</div>
          {trend ? <BarChart points={trend.points} period={period} /> : <div className="chart-empty">불러오는 중…</div>}
          {trend?.stats && (
            <div className="statrow">
              <Stat label="평균" val={won(trend.stats.avg)} />
              <Stat label="최고" val={won(trend.stats.max)} />
              <Stat label="최저" val={won(trend.stats.min)} />
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">거래량</div>
          <div className="caption">{captionFor(period).split('·')[0].trim()} · 합계 {won(sumVol(trend))} {summary?.unit || ''}</div>
          {trend ? (
            <BarChart points={trend.points.map((p) => ({ key: p.key, price: p.volume }))} period={period}
              accent="var(--green)" light="var(--bar-lt)" />
          ) : <div className="chart-empty">불러오는 중…</div>}
        </div>

        <div className="card">
          <div className="row vcenter">
            <div className="card-title">산지</div>
            <span className="grow" />
            <Chip label="OpenAPI 연동 예정" bg="var(--seg)" fg="var(--sub)" />
          </div>
          <div className="caption">공공데이터포털(15141808) 연동 시 산지·포장 정보가 표시됩니다.</div>
        </div>

        <div className="card">
          <div className="card-title">상세 정보</div>
          {INFO.map(([k, v]) => (
            <div className="kv" key={k}><span className="kv-k">{k}</span><span className="grow" /><span className="kv-v">{v}</span></div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, val }) {
  return (<div className="stat"><div className="stat-l">{label}</div><div className="stat-v">{val}</div></div>)
}
function sumVol(trend) {
  if (!trend?.points) return null
  return trend.points.reduce((a, p) => a + (p.volume || 0), 0)
}
