const TABS = [
  { key: 'home', label: '홈' },
  { key: 'ledger', label: '거래' },
  { key: 'price', label: '시세' },
  { key: 'report', label: '리포트' },
  { key: 'more', label: '더보기' },
]
function Icon({ kind, on }) {
  const c = on ? 'var(--green)' : 'var(--sub)'
  switch (kind) {
    case 'home': return (<svg width="22" height="22" viewBox="0 0 22 22"><path d="M3 11L11 4l8 7M5 9.5V19h12V9.5" fill="none" stroke={c} strokeWidth="1.7" strokeLinejoin="round"/></svg>)
    case 'ledger': return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="4" y="3" width="14" height="16" rx="2.5" fill="none" stroke={c} strokeWidth="1.7"/><path d="M7.5 7.5h7M7.5 11h7M7.5 14.5h4" stroke={c} strokeWidth="1.6" strokeLinecap="round"/></svg>)
    case 'price': return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="3" y="12" width="4" height="8" rx="1.5" fill={c}/><rect x="9" y="7" width="4" height="13" rx="1.5" fill={c}/><rect x="15" y="3" width="4" height="17" rx="1.5" fill={c}/></svg>)
    case 'report': return (<svg width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="8" fill="none" stroke={c} strokeWidth="1.7"/><path d="M11 11V4M11 11l5 3" stroke={c} strokeWidth="1.7" strokeLinecap="round"/></svg>)
    default: return (<svg width="22" height="22" viewBox="0 0 22 22"><circle cx="5" cy="11" r="1.8" fill={c}/><circle cx="11" cy="11" r="1.8" fill={c}/><circle cx="17" cy="11" r="1.8" fill={c}/></svg>)
  }
}
export default function BottomTabs({ active, onChange }) {
  return (
    <nav className="tabs">
      {TABS.map((t) => (
        <button className={'tab' + (t.key === active ? ' tab--on' : '')} key={t.key} onClick={() => onChange(t.key)}>
          <Icon kind={t.key} on={t.key === active} />
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  )
}
