import { useState } from 'react'
import TodayScreen from './components/TodayScreen.jsx'
import DetailScreen from './components/DetailScreen.jsx'

export default function App() {
  const [screen, setScreen] = useState({ name: 'home' })
  return (
    <div className="frame">
      {screen.name === 'home' ? (
        <TodayScreen onOpen={(item) => setScreen({ name: 'detail', item })} />
      ) : (
        <DetailScreen item={screen.item} onBack={() => setScreen({ name: 'home' })} />
      )}
    </div>
  )
}
