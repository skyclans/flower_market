import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, monthStartISO, todayISO } from '../util.js'
import ConsultModal from './ConsultModal.jsx'

function buildCSV(txs) {
  const head = ['날짜', '구분', '품목', '등급', '단위', '수량', '단가', '금액', '시세대비%']
  const rows = [head]
  txs.forEach((t) => t.lines.forEach((l) => rows.push([
    t.occurred_on, t.tx_type === 'purchase' ? '매입' : '매출', l.item_name, l.grade || '', l.unit || '',
    l.quantity, l.unit_price, l.line_total, l.margin_pct ?? '',
  ])))
  return '\uFEFF' + rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
}

export default function ReportScreen() {
  const [rep, setRep] = useState(null)
  const [err, setErr] = useState(null)
  const [consult, setConsult] = useState(false)
  const from = monthStartISO(), to = todayISO()
  useEffect(() => { api.report(from, to).then(setRep).catch((e) => setErr(String(e))) }, [])

  async function exportCSV() {
    const d = await api.listTx()
    const blob = new Blob([buildCSV(d.transactions)], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `꽃장부_거래내역_${to}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter"><span className="d-name">리포트</span></div>
        <div className="d-sub">{from} ~ {to} (이번 달)</div>
      </header>
      <div className="body">
        {err && <div className="error">{err}</div>}
        {!rep && !err && <div className="loading">불러오는 중…</div>}
        {rep && (
          <>
            <div className="card">
              <div className="rep-grid">
                <div className="rep-cell"><div className="rep-l">매입</div><div className="rep-v rep-buy">{won(rep.purchase_total)}</div><div className="rep-s">{rep.purchase_count}건</div></div>
                <div className="rep-cell"><div className="rep-l">매출</div><div className="rep-v rep-sell">{won(rep.sale_total)}</div><div className="rep-s">{rep.sale_count}건</div></div>
                <div className="rep-cell"><div className="rep-l">추정 마진</div><div className={'rep-v ' + (rep.est_margin >= 0 ? 'rep-pos' : 'rep-neg')}>{won(rep.est_margin)}</div><div className="rep-s">매출−매입</div></div>
              </div>
            </div>

            {rep.top_items?.length > 0 && (
              <div className="card">
                <div className="card-title">매입 품목 TOP</div>
                {rep.top_items.map((it, i) => (
                  <div className="kv" key={it.item_name}><span className="kv-k">{i + 1}. {it.item_name}</span><span className="grow" /><span className="kv-v">{won(it.amount)}원</span></div>
                ))}
              </div>
            )}

            <button className="cta" onClick={exportCSV}>거래내역 CSV 내보내기</button>
            <div className="empty-note">CSV를 카카오톡·메일로 세무사에게 그대로 전달하면 됩니다. (세무 연동은 추후 단계)</div>

            <button className="consult-btn" onClick={() => setConsult(true)}>세무 전문가 연결 · 빠른 절세 상담</button>
          </>
        )}
      </div>

      {consult && (
        <ConsultModal monthPurchase={rep?.purchase_total ?? 0} monthCount={rep?.purchase_count ?? 0} onClose={() => setConsult(false)} />
      )}
    </div>
  )
}
