import { useState } from 'react'
import { api } from '../api.js'
import { won, catStyle } from '../util.js'
import Chip from './Chip.jsx'

export default function PriceCard({ d, onOpen }) {
  const [price, setPrice] = useState('')
  const [cmp, setCmp] = useState(null)
  const [busy, setBusy] = useState(false)
  const cs = catStyle(d.category)
  const wowUp = d.wow_pct != null && d.wow_pct > 0
  const wowDown = d.wow_pct != null && d.wow_pct < 0

  async function doCompare(e) {
    e.stopPropagation()
    if (!price) return
    setBusy(true)
    try {
      const r = await api.compare(d.item_name, Number(price))
      const t = r.by_auction_type.online || r.by_auction_type.main
      const ref = r.by_auction_type.online ? '온라인' : '본경매'
      setCmp({ pct: t.my_price_vs_avg_pct, ref, refPrice: t.wavg_price })
    } catch (err) {
      setCmp({ error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card pcard" onClick={() => onOpen?.(d.item_name)}>
      <div className="row">
        <div className="row gap8 vcenter">
          <span className="pcard-name">{d.item_name}</span>
          <Chip label={d.category} bg={cs.bg} fg={cs.fg} />
        </div>
        {d.wow_pct != null && (
          <span className={'wow ' + (wowUp ? 'wow--up' : 'wow--down')}>
            {wowUp ? '▲' : '▼'} 지난주 {Math.abs(d.wow_pct)}%
          </span>
        )}
      </div>

      <div className="prices">
        <div className="pcol">
          <div className="plabel plabel--main"><span className="dot" /> 본경매</div>
          <div className="pval">{won(d.main_price)}<span className="unit"> 원/{d.unit}</span></div>
        </div>
        <div className="pdiv" />
        <div className="pcol">
          <div className="plabel">온라인</div>
          <div className="pval pval--sub">{won(d.online_price)}<span className="unit"> 원/{d.unit}</span></div>
        </div>
      </div>

      {cmp && !cmp.error ? (
        <div className={'cmp ' + (cmp.pct > 0 ? 'cmp--over' : 'cmp--under')} onClick={(e) => e.stopPropagation()}>
          <div>
            <div className="cmp-l">내 매입가</div>
            <div className="cmp-v">{won(Number(price))} 원</div>
            <div className="cmp-b">{cmp.ref} {won(cmp.refPrice)}원 대비</div>
          </div>
          <div className="cmp-r">
            <div className="cmp-pct">{cmp.pct > 0 ? '+' : ''}{cmp.pct}%</div>
            <div className="cmp-note">{cmp.pct > 0 ? '비쌈' : '저렴'}</div>
          </div>
        </div>
      ) : (
        <div className="myin" onClick={(e) => e.stopPropagation()}>
          <input
            className="myin-input"
            inputMode="numeric"
            placeholder="내 매입가 입력"
            value={price}
            onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ''))}
            onKeyDown={(e) => e.key === 'Enter' && doCompare(e)}
          />
          <button className="myin-btn" onClick={doCompare} disabled={busy}>
            {busy ? '...' : '비교하기 ›'}
          </button>
        </div>
      )}
    </div>
  )
}
