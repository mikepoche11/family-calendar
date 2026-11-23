import { useEffect, useState } from 'react'
import { api } from './api.js'
import { LABEL_PALETTE, textOn } from './googleColors.js'

const NAME = Object.fromEntries(LABEL_PALETTE.map(([n, c]) => [c, n]))

/**
 * Settings tab: one colour per Google event label. Google sends which label an event has but not the
 * label's colour, so it's picked here once (matching the Google app) and every event with that label uses it.
 */
export default function EventLabels() {
  const [labels, setLabels] = useState(null)
  const [open, setOpen] = useState(null) // label id whose palette is showing
  const [error, setError] = useState(null)

  useEffect(() => {
    api.eventLabels().then(setLabels).catch((e) => setError(e.message))
  }, [])

  async function pick(id, color) {
    setError(null)
    setLabels((ls) => ls.map((l) => (l.label_id === id ? { ...l, color: color ?? '' } : l)))
    setOpen(null)
    try {
      setLabels(await api.setLabelColor(id, color))
    } catch (e) {
      setError(e.message)
    }
  }

  if (!labels) return <div className="editor">{error && <p className="error">{error}</p>}</div>
  return (
    <div className="editor label-colors">
      <p className="hint">
        Google Calendar's event labels don't send their colour to other apps, so pick each label's colour here
        once. Every event with that label uses it. An event's own Google colour still comes first.
      </p>
      {labels.length === 0 && <p className="empty">No events with labels yet.</p>}
      {labels.map((l) => (
        <div className="label-row" key={l.label_id}>
          <button
            className={`label-chip ${l.color ? '' : 'none'}`}
            style={l.color ? { background: l.color, color: textOn(l.color) } : undefined}
            onClick={() => setOpen(open === l.label_id ? null : l.label_id)}
          >
            {l.examples[0]}
          </button>
          <div className="label-info">
            <div className="label-examples">{l.examples.join(' · ')}</div>
            <div className="label-meta">
              {l.count} event{l.count === 1 ? '' : 's'} · {l.color ? NAME[l.color] ?? l.color : 'no colour yet'}
              {!l.needs_color && ' · these already have their own Google colour'}
            </div>
          </div>
          <button onClick={() => setOpen(open === l.label_id ? null : l.label_id)}>Change</button>
          {open === l.label_id && (
            <div className="label-palette">
              {LABEL_PALETTE.map(([name, c]) => (
                <button
                  key={c}
                  className={`swatch ${l.color === c ? 'on' : ''}`}
                  style={{ '--swatch': c, background: c }}
                  title={name}
                  aria-label={name}
                  onClick={() => pick(l.label_id, c)}
                />
              ))}
              <button className="swatch default" title="No colour" aria-label="No colour" onClick={() => pick(l.label_id, null)} />
            </div>
          )}
        </div>
      ))}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
