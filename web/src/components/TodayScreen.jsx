import { useEffect, useState } from 'react'
import { api } from '../api.js'
import PriceCard from './PriceCard.jsx'
import BottomTabs from './BottomTabs.jsx'
import Chip from './Chip.jsx'

const FAVS = ['장미', '거베라', '호접란', '국화']

function formatDate(iso) {
  if (!iso) return ''
  const dt = new Date(iso + 'T00:00:00')
  const wd = ['일', '월', '화', '수', '목', '금', '토'][dt.getDay()]
  return `${dt.getMonth() + 1}월 ${dt.getDate()}일 (${wd})`
}

export default function TodayScreen({ onOpen }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    api.home(FAVS).then(setData).catch((e) => setErr(String(e)))
  }, [])

  const asOf = data?.items?.[0]?.as_of

  return (
    <div className="screen">
      <header className="hd">
        <div className="row vcenter">
          <span className="brand">꽃장부</span>
          <span className="hd-date">{formatDate(asOf)}</span>
        </div>
        <div className="row vcenter">
          <span className="mkt">aT화훼(양재) <span className="caret">▾</span></span>
          <Chip label="최신 시세" bg="var(--blue-bg)" fg="var(--blue)" />
        </div>
      </header>

      <div className="body">
        <div className="sec-title">
          <span>내 품목</span>
          <span className="count">{data?.items?.length ?? ''}</span>
          <span className="grow" />
          <span className="muted-link">편집</span>
        </div>

        {err && <div className="error">백엔드 연결 실패: {err}<br />FastAPI(uvicorn)가 켜져 있는지 확인하세요.</div>}
        {!data && !err && <div className="loading">불러오는 중…</div>}

        {data?.items?.map((d) => (
          <PriceCard key={d.item_name} d={d} onOpen={onOpen} />
        ))}
      </div>

      <BottomTabs active="today" />
    </div>
  )
}
