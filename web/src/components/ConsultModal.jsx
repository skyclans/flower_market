import { useState } from 'react'
import { api } from '../api.js'
import { won, BIZ_TYPES, getBizType } from '../util.js'

const CHANNELS = [['phone', '전화'], ['kakao', '카톡']]

export default function ConsultModal({ monthPurchase = 0, monthCount = 0, bizType, onClose }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [biz, setBiz] = useState(bizType || getBizType())
  const [channel, setChannel] = useState('phone')
  const [memo, setMemo] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState(null)

  const valid = name.trim() && phone.trim()

  async function submit() {
    setSaving(true); setErr(null)
    try {
      await api.consult({
        name: name.trim(), phone: phone.trim(), biz_type: biz, channel,
        memo: memo.trim() || null, month_purchase: monthPurchase, month_count: monthCount,
      })
      setDone(true)
    } catch (e) { setErr(String(e)); setSaving(false) }
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <span className="modal-title">{done ? '신청 완료' : '세무 전문가 연결'}</span>
          <button className="modal-x" onClick={onClose}>✕</button>
        </div>

        {done ? (
          <div className="modal-body">
            <div className="consult-done">
              <div className="cd-check">✓</div>
              <div className="cd-title">상담 신청이 접수됐어요</div>
              <div className="cd-sub">담당 세무 전문가가 {channel === 'phone' ? '전화' : '카카오톡'}으로 곧 연락드립니다.</div>
              <div className="cd-summary">
                <div className="cd-row"><span>이번 달 매입</span><b>{won(monthPurchase)} 원</b></div>
                <div className="cd-row"><span>거래 건수</span><b>{monthCount}건</b></div>
              </div>
            </div>
            <button className="cta" onClick={onClose}>확인</button>
          </div>
        ) : (
          <>
            <div className="modal-body">
              <div className="consult-intro">생화는 부가세 면세라 매입을 잘 기록하면 종합소득세 필요경비로 인정됩니다. 내 장부에 맞는 절세 포인트를 무료로 확인해 보세요.</div>

              <label className="fl">이름<input className="fi" placeholder="홍길동" value={name} onChange={(e) => setName(e.target.value)} /></label>
              <label className="fl">휴대폰<input className="fi" inputMode="tel" placeholder="010-0000-0000" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>

              <div className="fl">사업자 유형
                <div className="seg seg--lg">
                  {BIZ_TYPES.map((b) => (
                    <button key={b.value} className={'seg-btn' + (biz === b.value ? ' seg-btn--on' : '')} onClick={() => setBiz(b.value)}>{b.label}</button>
                  ))}
                </div>
              </div>

              <div className="fl">상담 방법
                <div className="seg seg--lg">
                  {CHANNELS.map(([v, l]) => (
                    <button key={v} className={'seg-btn' + (channel === v ? ' seg-btn--on' : '')} onClick={() => setChannel(v)}>{l}</button>
                  ))}
                </div>
              </div>

              <label className="fl">메모 (선택)<textarea className="fi consult-memo" rows={3} placeholder="궁금한 점을 적어주세요" value={memo} onChange={(e) => setMemo(e.target.value)} /></label>

              <div className="consult-attach">
                <div className="ca-title">이번 달 장부 요약 (자동 첨부)</div>
                <div className="cd-row"><span>매입액</span><b>{won(monthPurchase)} 원</b></div>
                <div className="cd-row"><span>거래 건수</span><b>{monthCount}건</b></div>
              </div>

              {err && <div className="error">신청 실패: {err}</div>}
              <div className="empty-note">* 세무사 확인 필요 · 제출 시 위 요약이 함께 전달됩니다.</div>
            </div>

            <div className="modal-foot">
              <button className="save-btn" style={{ marginLeft: 0, flex: 1 }} disabled={!valid || saving} onClick={submit}>
                {saving ? '신청 중…' : '상담 신청'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
