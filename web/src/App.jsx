import { useState } from 'react'
import BottomTabs from './components/BottomTabs.jsx'
import HomeScreen from './components/HomeScreen.jsx'
import LedgerScreen from './components/LedgerScreen.jsx'
import PriceListScreen from './components/PriceListScreen.jsx'
import ReportScreen from './components/ReportScreen.jsx'
import MoreScreen from './components/MoreScreen.jsx'
import DetailScreen from './components/DetailScreen.jsx'

export default function App() {
  const [tab, setTab] = useState('home')
  const [detail, setDetail] = useState(null)   // 시세 상세로 볼 품목명
  const [ledgerInput, setLedgerInput] = useState(false)

  const openDetail = (item) => setDetail(item)
  const openInput = () => { setTab('ledger'); setLedgerInput(true) }

  return (
    <div className="frame">
      {detail ? (
        <DetailScreen item={detail} onBack={() => setDetail(null)} />
      ) : (
        <>
          {tab === 'home' && <HomeScreen onOpenItem={openDetail} onAddTx={openInput} />}
          {tab === 'ledger' && <LedgerScreen openInput={ledgerInput} setOpenInput={setLedgerInput} />}
          {tab === 'price' && <PriceListScreen onOpenItem={openDetail} />}
          {tab === 'report' && <ReportScreen />}
          {tab === 'more' && <MoreScreen />}
          <BottomTabs active={tab} onChange={(t) => { setTab(t); setLedgerInput(false) }} />
        </>
      )}
    </div>
  )
}
