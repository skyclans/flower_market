import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, marginText, todayISO } from '../util.js'

const GRADES = ['특', '상', '보', '등외']
const UNITS = ['속', '분', '단', '본']

function emptyLine() { return { item_name: '', grade: '특', unit: '속', quantity: 1, unit_price: '', _margin: null, _av: null } }

export default function TxInput({ onClose, onSaved }) {
  const [type, setType] = useState('purchase')
  const [date, setDate] = useState(todayISO())
  const [pay, setPay] = useState('card')
  const [lines, setLines] = useState([emptyLine()])
  const [allItems, setAllItems] = useState([])
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => { api.items().then((d) => setAllItems(d.items.map((i) => i.item_name))).catch(() => {}) }, [])

  function update(i, patch) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)))
  }

  // 실시간 마진: 매입 + 품목 + 단가 → /quote
  async function refreshMargin(i) {
    const l = lines[i]
    if (type !== 'purchase' || !l.item_name || !l.unit_price) { update(i, { _margin: null, _av: null }); return }
    try {
      const q = await api.quote(l.item_name, Number(l.unit_price))
      update(i, { _margin: q.margin_pct, _av: q.auction_avg, unit: l.unit })
    } catch { /* ignore */ }
  }

  const total = lines.reduce((a, l) => a + (Number(l.unit_price) || 0) * (Number(l.quantity) || 0), 0)
  const valid = lines.some((l) => l.item_name && l.unit_price)

  async function save() {
    setSaving(true); setErr(null)
    try {
      await api.createTx({
        tx_type: type, occurred_on: date, payment_method: pay,
        lines: lines.filter((l) => l.item_name && l.unit_price).map((l) => ({
          item_name: l.item_name, grade: l.grade, unit: l.unit,
          quantity: Number(l.quantity) || 1, unit_price: Number(l.unit_price) || 0,
        })),
      })
      onSaved?.()
    } catch (e) { setErr(String(e)); setSaving(false) }
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <span className="modal-title">거래 기록</span>
          <button className="modal-x" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="seg seg--lg">
            <button className={'seg-btn' + (type === 'purchase' ? ' seg-btn--on' : '')} onClick={() => setType('purchase')}>매입</button>
            <button className={'seg-btn' + (type === 'sale' ? ' seg-btn--on' : '')} onClick={() => setType('sale')}>매출</button>
          </div>

          <div className="field-row">
            <label className="fl">날짜<input className="fi" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
            <label className="fl">결제
              <select className="fi" value={pay} onChange={(e) => setPay(e.target.value)}>
                <option value="card">카드</option><option value="cash">현금</option><option value="transfer">계좌이체</option>
              </select>
            </label>
          </div>

          {lines.map((l, i) => {
            const mt = marginText(l._margin)
            return (
              <div className="linecard" key={i}>
                <div className="line-top">
                  <input className="fi fi--item" list="item-list" placeholder="품목 (예: 장미)" value={l.item_name}
                    onChange={(e) => update(i, { item_name: e.target.value })} onBlur={() => refreshMargin(i)} />
                  {lines.length > 1 && <button className="line-del" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}>✕</button>}
                </div>
                <div className="line-grid">
                  <select className="fi fi--sm" value={l.grade} onChange={(e) => update(i, { grade: e.target.value })}>
                    {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <select className="fi fi--sm" value={l.unit} onChange={(e) => update(i, { unit: e.target.value })}>
                    {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                  <input className="fi fi--sm" inputMode="numeric" placeholder="수량" value={l.quantity}
                    onChange={(e) => update(i, { quantity: e.target.value.replace(/[^0-9]/g, '') })} />
                  <input className="fi fi--sm" inputMode="numeric" placeholder="단가" value={l.unit_price}
                    onChange={(e) => update(i, { unit_price: e.target.value.replace(/[^0-9]/g, '') })} onBlur={() => refreshMargin(i)} />
                </div>
                {mt && (
                  <div className={'line-margin ' + (mt.good ? 'lm-good' : 'lm-bad')}>
                    시세 {won(l._av)}원 대비 <b>{mt.pct}</b> {mt.good ? '저렴하게 매입 👍' : '비싸게 매입'}
                  </div>
                )}
              </div>
            )
          })}
          <datalist id="item-list">{allItems.map((n) => <option key={n} value={n} />)}</datalist>

          <button className="addline" onClick={() => setLines((ls) => [...ls, emptyLine()])}>+ 품목 추가</button>

          {err && <div className="error">저장 실패: {err}</div>}
        </div>

        <div className="modal-foot">
          <div className="foot-total"><span>합계</span><b>{won(total)} 원</b></div>
          <button className="save-btn" disabled={!valid || saving} onClick={save}>{saving ? '저장 중…' : '저장'}</button>
        </div>
      </div>
    </div>
  )
}
