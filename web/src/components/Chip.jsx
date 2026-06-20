export default function Chip({ label, bg = 'var(--green-bg)', fg = 'var(--green)' }) {
  return <span className="chip" style={{ background: bg, color: fg }}>{label}</span>
}
