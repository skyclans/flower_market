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

/* ===== 공제 모델 (생화=부가세 면세 도메인) =====
   생화는 부가세 면세 → 사업자 유형과 무관하게 공통 가치는 '종합소득세 필요경비'다.
   매입을 기록할수록 필요경비로 인정되는 금액이 늘어난다(절세액 단정은 하지 않는다). */
export const BIZ_TYPES = [
  { value: 'tax_free', label: '면세' },
  { value: 'general', label: '일반' },
  { value: 'simplified', label: '간이' },
]
const BIZ_KEY = 'biz_type'
const BIZ_DEFAULT = 'tax_free'

export function getBizType() {
  try {
    const v = localStorage.getItem(BIZ_KEY)
    return BIZ_TYPES.some((b) => b.value === v) ? v : BIZ_DEFAULT
  } catch { return BIZ_DEFAULT }
}
export function setBizTypeLS(v) {
  try { localStorage.setItem(BIZ_KEY, v) } catch { /* SSR/사생활모드 무시 */ }
}

const DEDUCTION_NOTES = {
  general: '포장재 등 과세매입은 매입세액공제 가능(생화는 면세라 부가세 공제 대상 아님)',
  simplified: '과세매입 0.5% 공제',
  tax_free: '부가세 공제 없음, 매입이 필요경비로 인정',
}

/* 기록 매입액(base)이 곧 종합소득세 필요경비 인정액.
   금액(절세액)은 세율·소득구간에 따라 달라지므로 단정하지 않는다. */
export function deductionView(bizType, recordedPurchase, unrecordedEst) {
  const type = BIZ_TYPES.some((b) => b.value === bizType) ? bizType : BIZ_DEFAULT
  const base = Math.max(0, Math.round(recordedPurchase || 0))
  const missed = Math.max(0, Math.round(unrecordedEst || 0))
  return {
    bizType: type,
    base,
    recordedPurchase: base,
    unrecordedEst: missed,
    benefitLabel: '종합소득세 필요경비 인정액',
    benefit: base,
    note: DEDUCTION_NOTES[type] || DEDUCTION_NOTES[BIZ_DEFAULT],
  }
}
