export default function SegmentedControl({ value, onChange, options }) {
  return (
    <div className="seg">
      {options.map((o) => (
        <button
          key={o.value}
          className={'seg-btn' + (o.value === value ? ' seg-btn--on' : '')}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
