import { useState } from 'react'
import { Icon, ItemIcon, PICKER_GROUPS, iconFor } from './icons.jsx'

/**
 * Button that shows the current icon and opens a grid of the drawn pastel icons, with a section per holiday.
 * Everyday icons save as their emoji (so older data stays the same); holiday icons save as their id. Any other emoji can still be typed in.
 */
export default function IconPicker({ value, onChange, fallback = 'star' }) {
  const [open, setOpen] = useState(false)
  const [custom, setCustom] = useState(value && !iconFor(value) ? value : '')
  const current = iconFor(value)

  function pick(emoji) {
    setOpen(false)
    if (emoji !== value) onChange(emoji)
  }

  return (
    <>
      <button type="button" className="icon-pick" aria-label="Choose icon" onClick={() => setOpen(true)}>
        <ItemIcon value={value} fallback={fallback} />
      </button>
      {open && (
        <div
          className="backdrop picker-backdrop"
          onPointerDown={(e) => {
            e.stopPropagation()
            if (e.target === e.currentTarget) setOpen(false)
          }}
        >
          <div className="modal icon-picker">
            <div className="settings-head">
              <h2>Pick an icon</h2>
              <button type="button" onClick={() => setOpen(false)}>Close</button>
            </div>
            {PICKER_GROUPS.map((g) => (
              <section key={g.label} className="icon-group">
                <div className="field-label">{g.label}</div>
                <div className="icon-grid">
                  {g.items.map((p) => (
                    <button
                      type="button"
                      key={p.name}
                      className={current === p.name ? 'on' : ''}
                      aria-label={p.label}
                      title={p.label}
                      onClick={() => pick(p.emoji)}
                    >
                      <Icon name={p.name} />
                    </button>
                  ))}
                </div>
              </section>
            ))}
            <form
              className="icon-custom"
              onSubmit={(e) => {
                e.preventDefault()
                if (custom.trim()) pick(custom.trim())
              }}
            >
              <input value={custom} onChange={(e) => setCustom(e.target.value)} maxLength={4} placeholder="Or type any emoji" />
              <button type="submit">Use it</button>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
