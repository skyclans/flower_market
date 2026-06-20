import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fmtDateKo, won } from '../util.js'
import PriceCard from './PriceCard.jsx'
import Chip from './Chip.jsx'

const FAVS = ['장미', '거베라', '호접란', '국화', '프리지아', '리시안사스', '백합', '작약', '수국', '카네이션', '튤립', '칼라', '해바라기', '스톡크', '라넌큘러스']

export default function HomeScreen({ onOpenItem, onAddTx }) {
  const [data, setData] = useState(null)
  const [recent, setRecent] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    api.home(FAVS).then(setData).catch((e) => setErr(String(e)))
    api.listTx().then((d) => setRecent(d.transactions.slice(0, 3))).catch(() => {})
  }, [])
  const asOf = data?.items?.[0]?.as_of

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter" style={{ justifyContent: 'space-between' }}>
          <span className="brand">꽃장부</span>
          <span className="hd-date">{fmtDateKo(asOf)}</span>
        </div>
        <div className="row vcenter" style={{ justifyContent: 'space-between' }}>
          <span className="mkt">aT화훼(양재) <span className="caret">▾</span></span>
          <Chip label="최신 시세" bg="var(--blue-bg)" fg="var(--blue)" />
        </div>
      </header>

      <div className="body">
        <button className="cta" onClick={onAddTx}>+ 매입 기록하기</button>

        <div className="sec-title"><span>오늘 시세</span><span className="grow" /><span className="muted-link" onClick={onAddTx}>내 품목 ›</span></div>
        {err && <div className="error">백엔드 연결 실패: {err}</div>}
        {!data && !err && <div className="loading">불러오는 중…</div>}
        {data?.items?.map((d) => <PriceCard key={d.item_name} d={d} onOpen={onOpenItem} />)}

        <div className="sec-title" style={{ marginTop: 6 }}><span>최근 거래</span></div>
        {recent && recent.length === 0 && <div className="empty-note">아직 기록된 거래가 없어요. 위 버튼으로 첫 매입을 기록해 보세요.</div>}
        {recent?.map((t) => (
          <div className="card txrow" key={t.id}>
            <div className="row vcenter" style={{ justifyContent: 'space-between' }}>
              <span className="tx-date">{fmtDateKo(t.occurred_on)}</span>
              <span className={'tx-type ' + (t.tx_type === 'purchase' ? 'tx-buy' : 'tx-sell')}>{t.tx_type === 'purchase' ? '매입' : '매출'}</span>
            </div>
            <div className="tx-items">{t.lines.map((l) => l.item_name).join(', ')}</div>
            <div className="tx-total">{won(t.total_amount)} 원</div>
          </div>
        ))}
      </div>
    </div>
  )
}
