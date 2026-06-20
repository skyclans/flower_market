const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const MARKET = '0000000001'

async function getJSON(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  home: (items) =>
    getJSON(`/home?market=${MARKET}&items=${encodeURIComponent(items.join(','))}`),
  trend: (item, period) =>
    getJSON(`/items/${encodeURIComponent(item)}/trend?market=${MARKET}&period=${period}`),
  items: () => getJSON(`/items?market=${MARKET}`),
  compare: async (item, price) => {
    const r = await fetch(BASE + '/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_name: item, my_price: price, market: MARKET }),
    })
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
    return r.json()
  },
}
