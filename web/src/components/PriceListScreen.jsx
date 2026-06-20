import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, catStyle } from '../util.js'
import PriceCard from './PriceCard.jsx'
import Chip from './Chip.jsx'

const FAVS = ['장미', '거베라', '호접란', '국화', '프리지아', '리시안사스', '백합', '작약', '수국', '카네이션', '튤립', '칼라', '해바라기', '스톡크', '라넌큘러스']

export default function PriceListScreen({ onOpenItem }) {
  const [data, setData] = useState(null)
  const [all, setAll] = useState(null)
  const [qy, setQy] = useState('')
  useEffect(() => {
    api.home(FAVS).then(setData).catch(() => {})
    api.items().then((d) => setAll(d.items)).catch(() => {})
  }, [])
  const filtered = (all || []).filter((i) => !qy || i.item_name.includes(qy)).slice(0, 40)

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter"><span className="d-name">시세</span></div>
        <div className="search"><input className="search-in" placeholder="품목 검색 (예: 장미, 호접란)" value={qy} onChange={(e) => setQy(e.target.value)} /></div>
      </header>
      <div className="body">
        <div className="sec-title"><span>관심 품목</span></div>
        {data?.items?.map((d) => <PriceCard key={d.item_name} d={d} onOpen={onOpenItem} />)}

        <div className="sec-title" style={{ marginTop: 6 }}><span>전체 품목</span><span className="grow" /><span className="muted-link">{all?.length ?? ''}개</span></div>
        <div className="card" style={{ padding: 0, gap: 0 }}>
          {filtered.map((i) => {
            const cs = catStyle(i.category)
            return (
              <button className="itemrow" key={i.item_name} onClick={() => onOpenItem(i.item_name)}>
                <div className="row vcenter gap8"><span className="ir-name">{i.item_name}</span><Chip label={i.category} bg={cs.bg} fg={cs.fg} /></div>
                <span className="grow" />
                <span className="ir-vol">연 {won(i.total_volume)}</span>
                <span className="ir-caret">›</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
