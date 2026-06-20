import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { won, monthStartISO, todayISO, BIZ_TYPES, getBizType, setBizTypeLS, deductionView } from '../util.js'
import ConsultModal from './ConsultModal.jsx'

export default function DeductionBanner() {
  const [biz, setBiz] = useState(getBizType())
  const [rep, setRep] = useState(null)
  const [consult, setConsult] = useState(false)

  useEffect(() => {
    api.report(monthStartISO(), todayISO()).then(setRep).catch(() => {})
  }, [])

  const recorded = rep?.purchase_total ?? 0
  const unrecorded = rep?.deduction?.unrecorded_est ?? 0
  const count = rep?.purchase_count ?? 0
  const v = deductionView(biz, recorded, unrecorded)
  const pick = (val) => { setBiz(val); setBizTypeLS(val) }

  return (
    <div className="ded2">
      <div className="ded2-seg">
        {BIZ_TYPES.map((b) => (
          <button key={b.value} className={'ded2-seg-btn' + (biz === b.value ? ' ded2-seg-btn--on' : '')} onClick={() => pick(b.value)}>{b.label}</button>
        ))}
      </div>

      <div className="ded2-grid">
        <div className="ded2-cell">
          <div className="ded2-l">공제·경비 대상 기록액</div>
          <div className="ded2-v">{won(v.recordedPurchase)} 원</div>
        </div>
        <div className="ded2-cell">
          <div className="ded2-l">{v.benefitLabel}</div>
          <div className="ded2-v ded2-pos">{won(v.benefit)} 원</div>
        </div>
        <div className="ded2-cell">
          <div className="ded2-l">미기록 시 놓치는 경비</div>
          <div className="ded2-v ded2-warn">{won(v.unrecordedEst)} 원</div>
        </div>
      </div>

      <div className="ded2-note">{v.note}</div>
      <div className="ded2-foot">* 세무사 확인 필요</div>

      <button className="consult-btn" onClick={() => setConsult(true)}>세무 전문가 연결 · 빠른 절세 상담</button>

      {consult && (
        <ConsultModal monthPurchase={recorded} monthCount={count} bizType={biz} onClose={() => setConsult(false)} />
      )}
    </div>
  )
}
