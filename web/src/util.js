export const won = (n) => (n == null ? '—' : Math.round(n).toLocaleString('ko-KR'))

export function catStyle(cat) {
  switch (cat) {
    case '난': return { bg: 'var(--purple-bg)', fg: 'var(--purple)' }
    case '관엽': return { bg: 'var(--leaf-bg)', fg: 'var(--leaf)' }
    default: return { bg: 'var(--pink-bg)', fg: 'var(--pink)' } // 절화
  }
}

export function bucketLabel(key, period) {
  if (period === 'monthly' || period === 'yearly') return String(parseInt(key.slice(5, 7), 10))
  const [, m, d] = key.split('-')
  return `${parseInt(m, 10)}/${parseInt(d, 10)}`
}

export function captionFor(period) {
  switch (period) {
    case 'weekly': return '최근 12주 · 본경매 주평균 (원)'
    case 'daily': return '최근 30일 · 거래일 평균 (원)'
    default: return '최근 12개월 · 본경매 월평균 (원)'
  }
}

export function fmtDateKo(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  const wd = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${wd})`
}
export function marginText(m) {
  if (m == null) return null
  return { pct: (m > 0 ? '+' : '') + m + '%', good: m <= 0 }
}
export const todayISO = () => new Date().toISOString().slice(0, 10)
export const monthStartISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01` }
