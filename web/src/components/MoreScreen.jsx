const ITEMS = [
  ['영수증 OCR 인식', '사진 1장으로 자동 분개', '예정'],
  ['데이터 내보내기', 'CSV · 세무사 전달', null],
  ['관심 품목 알림', '시세 임계치 도달 시 알림', '예정'],
  ['설정', '시장 · 결제수단 기본값', null],
  ['도움말', '사용 가이드', null],
]
export default function MoreScreen() {
  return (
    <div className="screen">
      <header className="hd"><div className="row vcenter"><span className="d-name">더보기</span></div></header>
      <div className="body">
        <div className="card" style={{ padding: 0, gap: 0 }}>
          {ITEMS.map(([t, s, tag]) => (
            <div className="itemrow" key={t}>
              <div><div className="ir-name">{t}</div><div className="ir-sub">{s}</div></div>
              <span className="grow" />
              {tag ? <span className="soon">{tag}</span> : <span className="ir-caret">›</span>}
            </div>
          ))}
        </div>
        <div className="empty-note">꽃장부 · 데이터 출처: aT 화훼공판장 · 공공데이터포털</div>
      </div>
    </div>
  )
}
