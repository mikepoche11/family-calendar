import { useState } from 'react'
import Avatar from './avatars.jsx'

const pad = (n) => String(n).padStart(2, '0')
const localDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const localTime = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
const addDays = (dateStr, n) => {
  const d = new Date(dateStr + 'T12:00')
  d.setDate(d.getDate() + n)
  return localDate(d)
}

/** Builds the initial form from an existing event, or from a tapped slot. */
export function draftFrom({ event, start, end, allDay }) {
  if (event) {
    const s = new Date(event.start)
    const e = new Date(event.end)
    return {
      id: event.id,
      summary: event.summary,
      person_id: event.person_id,
      all_day: event.all_day,
      date: event.all_day ? event.start : localDate(s),
      endDate: event.all_day ? addDays(event.end, -1) : localDate(e),
      startTime: event.all_day ? '09:00' : localTime(s),
      endTime: event.all_day ? '10:00' : localTime(e),
      location: event.location || '',
      recurring: event.recurring,
    }
  }
  const s = start ?? roundedNow()
  const e = end ?? new Date(s.getTime() + 60 * 60 * 1000)
  return {
    id: null,
    summary: '',
    person_id: null,
    all_day: !!allDay,
    date: localDate(s),
    endDate: allDay && end ? localDate(new Date(e.getTime() - 1)) : localDate(s),
    startTime: allDay ? '09:00' : localTime(s),
    endTime: allDay ? '10:00' : localTime(e),
    location: '',
    recurring: false,
  }
}

function roundedNow() {
  const d = new Date()
  d.setMinutes(0, 0, 0)
  d.setHours(d.getHours() + 1)
  return d
}

export default function EventModal({ draft, people, onSave, onDelete, onClose }) {
  const [f, setF] = useState(draft)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function save(e) {
    e.preventDefault()
    const body = {
      summary: f.summary.trim(),
      person_id: f.person_id,
      all_day: f.all_day,
      location: f.location,
      // Timed events are sent as exact UTC instants, so a phone in another time zone still saves the right time
      start: f.all_day ? f.date : new Date(`${f.date}T${f.startTime}`).toISOString(),
      end: f.all_day ? addDays(f.endDate < f.date ? f.date : f.endDate, 1) : new Date(`${f.date}T${f.endTime}`).toISOString(),
    }
    setBusy(true)
    setError(null)
    try {
      await onSave(f.id, body)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    try {
      await onDelete(f.id)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={save}>
        <h2>{f.id ? 'Edit event' : 'New event'}</h2>
        <input
          className="title-input"
          placeholder="What's happening?"
          value={f.summary}
          onChange={set('summary')}
          autoFocus
          required
        />

        <div className="field-label">Who</div>
        <div className="chips">
          <button
            type="button"
            className={`chip ${f.person_id == null ? 'on' : ''}`}
            onClick={() => setF({ ...f, person_id: null })}
          >
            Everyone
          </button>
          {people.map((p) => (
            <button
              type="button"
              key={p.id}
              className={`chip ${f.person_id === p.id ? 'on' : ''}`}
              style={{ '--chip': p.color }}
              onClick={() => setF({ ...f, person_id: p.id })}
            >
              <Avatar person={p} size={32} />
              {p.name}
            </button>
          ))}
        </div>

        <label className="toggle">
          <input type="checkbox" checked={f.all_day} onChange={set('all_day')} /> All day
        </label>

        <div className="row">
          <label>
            {f.all_day ? 'From' : 'Date'}
            <input type="date" value={f.date} onChange={set('date')} required />
          </label>
          {f.all_day ? (
            <label>
              To
              <input type="date" value={f.endDate} min={f.date} onChange={set('endDate')} required />
            </label>
          ) : (
            <>
              <label>
                Start
                <input type="time" value={f.startTime} onChange={set('startTime')} required />
              </label>
              <label>
                End
                <input type="time" value={f.endTime} onChange={set('endTime')} required />
              </label>
            </>
          )}
        </div>

        <label>
          Where
          <input value={f.location} onChange={set('location')} placeholder="Optional" />
        </label>

        {f.recurring && <p className="note">This is one event in a repeating series; changes apply to this one only.</p>}
        {error && <p className="error">{error}</p>}

        <div className="actions">
          {f.id && (
            <button type="button" className="danger" onClick={remove} disabled={busy}>
              Delete
            </button>
          )}
          <span className="spacer" />
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            Save
          </button>
        </div>
      </form>
    </div>
  )
}
