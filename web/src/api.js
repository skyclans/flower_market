const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const MARKET = '0000000001'

async function getJSON(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}
async function postJSON(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}
const qs = (o) => {
  const p = Object.entries(o).filter(([, v]) => v != null && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
  return p.length ? '?' + p.join('&') : ''
}

export const api = {
  // 시세
  home: (items) => getJSON(`/home${qs({ market: MARKET, items: items.join(',') })}`),
  trend: (item, period) => getJSON(`/items/${encodeURIComponent(item)}/trend${qs({ market: MARKET, period })}`),
  items: () => getJSON(`/items${qs({ market: MARKET })}`),
  compare: (item, price) => postJSON('/compare', { item_name: item, my_price: price, market: MARKET }),
  // 장부
  quote: (item, unitPrice) => getJSON(`/quote${qs({ item, unit_price: unitPrice, market: MARKET })}`),
  listTx: (type) => getJSON(`/transactions${qs({ tx_type: type })}`),
  createTx: (body) => postJSON('/transactions', body),
  report: (from, to) => getJSON(`/reports/summary${qs({ date_from: from, date_to: to })}`),
  // 세무 상담
  consult: (payload) => postJSON('/consult', payload),
}
