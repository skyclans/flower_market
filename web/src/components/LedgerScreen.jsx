import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'
import { fmtDateKo, won, marginText, monthStartISO, todayISO } from '../util.js'
import TxInput from './TxInput.jsx'

export default function LedgerScreen({ openInput, setOpenInput }) {
  const [filter, setFilter] = useState('')   // '' | purchase | sale
  const [txs, setTxs] = useState(null)
  const [monthBuy, setMonthBuy] = useState(null)
  const [err, setErr] = useState(null)

  const load = useCallback(() => {
    api.listTx(filter || undefined).then((d) => setTxs(d.transactions)).catch((e) => setErr(String(e)))
    api.report(monthStartISO(), todayISO()).then((r) => setMonthBuy(r.purchase_total)).catch(() => {})
  }, [filter])
  useEffect(() => { load() }, [load])

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter" style={{ justifyContent: 'space-between' }}>
          <span className="d-name">거래 장부</span>
          <button className="hd-add" onClick={() => setOpenInput(true)}>+ 기록</button>
        </div>
        <div className="seg">
          {[['', '전체'], ['purchase', '매입'], ['sale', '매출']].map(([v, l]) => (
            <button key={v} className={'seg-btn' + (filter === v ? ' seg-btn--on' : '')} onClick={() => setFilter(v)}>{l}</button>
          ))}
        </div>
      </header>

      <div className="body">
        <div className="deduction">
          <div><div className="ded-l">이번 달 기록된 매입 (공제 대상)</div><div className="ded-v">{won(monthBuy)} 원</div></div>
          <div className="ded-tag">기록할수록 ↑</div>
        </div>

        {err && <div className="error">{err}</div>}
        {txs && txs.length === 0 && <div className="empty-note">기록이 없습니다. ‘+ 기록’으로 첫 거래를 남겨보세요.</div>}

        {txs?.map((t) => (
          <div className="card txfull" key={t.id}>
            <div className="row vcenter" style={{ justifyContent: 'space-between' }}>
              <span className="tx-date">{fmtDateKo(t.occurred_on)}</span>
              <span className={'tx-type ' + (t.tx_type === 'purchase' ? 'tx-buy' : 'tx-sell')}>{t.tx_type === 'purchase' ? '매입' : '매출'}</span>
            </div>
            {t.lines.map((l, i) => {
              const mt = marginText(l.margin_pct)
              return (
                <div className="lineitem" key={i}>
                  <div className="li-main">
                    <span className="li-name">{l.item_name}</span>
                    <span className="li-meta">{l.grade} · {l.quantity}{l.unit} × {won(l.unit_price)}</span>
                  </div>
                  <div className="li-right">
                    <span className="li-total">{won(l.line_total)}</span>
                    {mt && <span className={'li-margin ' + (mt.good ? 'lm-good' : 'lm-bad')}>{mt.pct}</span>}
                  </div>
                </div>
              )
            })}
            <div className="txfull-foot"><span>합계</span><b>{won(t.total_amount)} 원</b></div>
          </div>
        ))}
      </div>

      {openInput && <TxInput onClose={() => setOpenInput(false)} onSaved={() => { setOpenInput(false); load() }} />}
    </div>
  )
}
