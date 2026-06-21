import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, monthStartISO, todayISO, seriesCaption } from '../util.js'
import GroupedBarChart from './GroupedBarChart.jsx'
import ConsultModal from './ConsultModal.jsx'

const GRANS = [['day', '일별'], ['week', '주별'], ['month', '월별'], ['year', '연별']]

function buildCSV(txs) {
  const head = ['날짜', '구분', '품목', '등급', '단위', '수량', '단가', '금액', '시세대비%']
  const rows = [head]
  txs.forEach((t) => t.lines.forEach((l) => rows.push([
    t.occurred_on, t.tx_type === 'purchase' ? '매입' : '매출', l.item_name, l.grade || '', l.unit || '',
    l.quantity, l.unit_price, l.line_total, l.margin_pct ?? '',
  ])))
  return '﻿' + rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
}

export default function ReportScreen() {
  const [gran, setGran] = useState('month')
  const [series, setSeries] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  // 월간 요약(품목 TOP·상담 첨부용)은 별도 유지
  const [rep, setRep] = useState(null)
  const [consult, setConsult] = useState(false)
  const from = monthStartISO(), to = todayISO()

  useEffect(() => { api.report(from, to).then(setRep).catch(() => {}) }, [])

  useEffect(() => {
    let alive = true
    setLoading(true); setErr(null)
    api.series(gran)
      .then((d) => { if (alive) { setSeries(d); setLoading(false) } })
      .catch((e) => { if (alive) { setErr(String(e)); setLoading(false) } })
    return () => { alive = false }
  }, [gran])

  async function exportCSV() {
    const d = await api.listTx()
    const blob = new Blob([buildCSV(d.transactions)], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `꽃장부_거래내역_${to}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  const t = series?.totals
  const margin = t ? t.margin : null

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter"><span className="d-name">리포트</span></div>
        <div className="seg">
          {GRANS.map(([v, l]) => (
            <button key={v} className={'seg-btn' + (gran === v ? ' seg-btn--on' : '')} onClick={() => setGran(v)}>{l}</button>
          ))}
        </div>
      </header>

      <div className="body">
        {err && <div className="error">{err}</div>}

        <div className="dash-cards">
          <div className="dash-card">
            <div className="dash-l">매출</div>
            <div className="dash-v rep-sell">{loading ? '…' : won(t?.sale)}</div>
          </div>
          <div className="dash-card">
            <div className="dash-l">매입</div>
            <div className="dash-v rep-buy">{loading ? '…' : won(t?.purchase)}</div>
          </div>
          <div className="dash-card">
            <div className="dash-l">마진</div>
            <div className={'dash-v ' + (margin >= 0 ? 'rep-pos' : 'rep-neg')}>{loading ? '…' : won(margin)}</div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">매출 · 매입 추이</div>
          <div className="caption">{series ? seriesCaption(gran, series.date_from, series.date_to) : ' '}</div>
          {loading ? <div className="loading">불러오는 중…</div>
            : <GroupedBarChart points={series?.points} granularity={gran} />}
        </div>

        {rep?.top_items?.length > 0 && (
          <div className="card">
            <div className="card-title">이번 달 매입 품목 TOP</div>
            {rep.top_items.map((it, i) => (
              <div className="kv" key={it.item_name}><span className="kv-k">{i + 1}. {it.item_name}</span><span className="grow" /><span className="kv-v">{won(it.amount)}원</span></div>
            ))}
          </div>
        )}

        <button className="cta" onClick={exportCSV}>거래내역 CSV 내보내기</button>
        <div className="empty-note">CSV를 카카오톡·메일로 세무사에게 그대로 전달하면 됩니다. (세무 연동은 추후 단계)</div>

        <button className="consult-btn" onClick={() => setConsult(true)}>세무 전문가 연결 · 빠른 절세 상담</button>
      </div>

      {consult && (
        <ConsultModal monthPurchase={rep?.purchase_total ?? 0} monthCount={rep?.purchase_count ?? 0} onClose={() => setConsult(false)} />
      )}
    </div>
  )
}
