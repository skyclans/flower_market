const TABS = [
  { key: 'today', label: '오늘' },
  { key: 'trend', label: '추세' },
  { key: 'items', label: '내 품목' },
  { key: 'settings', label: '설정' },
]
function Icon({ kind, on }) {
  const c = on ? 'var(--green)' : 'var(--sub)'
  if (kind === 'today')
    return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="2.5" y="4.5" width="17" height="15" rx="3.5" fill="none" stroke={c} strokeWidth="1.7"/><path d="M2.5 8.5h17" stroke={c} strokeWidth="3.5"/></svg>)
  if (kind === 'trend')
    return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="3" y="12" width="4" height="8" rx="1.5" fill={c}/><rect x="9" y="7" width="4" height="13" rx="1.5" fill={c}/><rect x="15" y="3" width="4" height="17" rx="1.5" fill={c}/></svg>)
  if (kind === 'items')
    return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="3" y="5" width="16" height="2.4" rx="1.2" fill={c}/><rect x="3" y="10.3" width="16" height="2.4" rx="1.2" fill={c}/><rect x="3" y="15.6" width="11" height="2.4" rx="1.2" fill={c}/></svg>)
  return (<svg width="22" height="22" viewBox="0 0 22 22"><rect x="3" y="7" width="16" height="2.4" rx="1.2" fill={c}/><rect x="3" y="13.6" width="16" height="2.4" rx="1.2" fill={c}/><circle cx="15" cy="8.2" r="3.5" fill="#fff" stroke={c} strokeWidth="1.7"/><circle cx="8" cy="14.8" r="3.5" fill="#fff" stroke={c} strokeWidth="1.7"/></svg>)
}
export default function BottomTabs({ active = 'today' }) {
  return (
    <nav className="tabs">
      {TABS.map((t) => (
        <div className={'tab' + (t.key === active ? ' tab--on' : '')} key={t.key}>
          <Icon kind={t.key} on={t.key === active} />
          <span>{t.label}</span>
        </div>
      ))}
    </nav>
  )
}
