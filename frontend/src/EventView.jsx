import Avatar from './avatars.jsx'
import { Icon } from './icons.jsx'

const dayFmt = { weekday: 'long', month: 'long', day: 'numeric' }
const timeFmt = { hour: 'numeric', minute: '2-digit' }

/** "Tuesday, November 24 · 3:00 – 4:00 PM", or "All day" for all-day events (end date is exclusive). */
export function whenText(row) {
  if (row.all_day) {
    const s = new Date(row.start + 'T12:00')
    const e = new Date(row.end + 'T12:00')
    e.setDate(e.getDate() - 1)
    const first = s.toLocaleDateString([], dayFmt)
    return e > s ? `${first} to ${e.toLocaleDateString([], dayFmt)} · All day` : `${first} · All day`
  }
  const s = new Date(row.start)
  const e = new Date(row.end)
  const sameDay = s.toDateString() === e.toDateString()
  const t = (d) => d.toLocaleTimeString([], timeFmt)
  return sameDay
    ? `${s.toLocaleDateString([], dayFmt)} · ${t(s)} – ${t(e)}`
    : `${s.toLocaleDateString([], dayFmt)} ${t(s)} to ${e.toLocaleDateString([], dayFmt)} ${t(e)}`
}

// Google descriptions can hold simple HTML (links, line breaks); show it as plain text
function plain(html) {
  const div = document.createElement('div')
  div.innerHTML = (html || '').replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n')
  return div.textContent.trim()
}

/** Read-only look at an event. Edit opens the form; tapping outside or Close goes back to the calendar. */
export default function EventView({ row, color, people, onEdit, onClose }) {
  const person = people.find((p) => p.id === row.person_id)
  const notes = plain(row.description)
  return (
    <div className="backdrop" onClick={onClose}>
      <div className="modal event-view" style={{ '--ev': color }} onClick={(e) => e.stopPropagation()}>
        <div className="ev-head">
          <span className="ev-swatch" />
          <h2>{row.summary || '(No title)'}</h2>
        </div>
        <p className="ev-when">{whenText(row)}</p>
        {row.recurring && <p className="ev-line"><Icon name="swap" /> Repeats</p>}
        {person && (
          <p className="ev-line ev-person">
            <Avatar person={person} size={36} /> {person.name}
          </p>
        )}
        {row.location && <p className="ev-line"><span className="ev-label">Where</span> {row.location}</p>}
        {notes && <p className="ev-notes">{notes}</p>}
        <div className="actions">
          <span className="spacer" />
          <button onClick={onClose}>Close</button>
          <button className="primary" onClick={onEdit}>
            <Icon name="pencil" /> Edit
          </button>
        </div>
      </div>
    </div>
  )
}
