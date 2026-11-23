import { useState } from 'react'
import { api } from './api.js'
import { Icon, ItemIcon } from './icons.jsx'
import IconPicker from './IconPicker.jsx'

/** "Repeats" choices. The holiday ones work out their own date every year. */
const REPEATS = [
  { id: '', label: 'Just once' },
  { id: 'yearly', label: 'Every year on this date' },
  { id: 'mardi-gras', label: 'Every year on Mardi Gras', name: 'Mardi Gras', icon: 'mardi-mask' },
  { id: 'easter', label: 'Every year on Easter', name: 'Easter', icon: 'easter-bunny' },
  { id: 'thanksgiving', label: 'Every year on Thanksgiving', name: 'Thanksgiving', icon: 'thanks-turkey' },
]
const MOVING = new Set(['mardi-gras', 'easter', 'thanksgiving'])
// Soft card colours, picked in turn so neighbouring cards differ
const TINTS = ['#fde68a', '#bbf7d0', '#bae6fd', '#fbcfe8', '#ddd6fe', '#fed7aa', '#99f6e4', '#fecdd3']

const asDate = (day) => new Date(day + 'T12:00')

export function whenText(days) {
  if (days === 0) return 'Today!'
  if (days === 1) return 'Tomorrow!'
  if (days < 0) return days === -1 ? 'Yesterday' : `${-days} days ago`
  return `${days} days`
}

export function longDate(day) {
  const d = asDate(day)
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', ...(sameYear ? {} : { year: 'numeric' }) })
}

/** Small pills for the calendar screen: the next one or two countdowns. Tapping one opens the Countdowns page. */
export function CountdownStrip({ countdowns, max = 2, onOpen }) {
  const next = countdowns.filter((c) => c.days >= 0).slice(0, max)
  if (!next.length) return null
  return (
    <div className="countdown-strip">
      {next.map((c) => (
        <button key={c.id} className={`countdown-pill ${c.days === 0 ? 'today' : ''}`} onClick={onOpen}>
          <ItemIcon value={c.icon} fallback="hourglass" size="1.6em" />
          <span className="num">{c.days === 0 ? 'Today!' : c.days}</span>
          <span className="what">
            {c.days === 0 ? c.name : <>{c.days === 1 ? 'day' : 'days'} until {c.name}</>}
          </span>
        </button>
      ))}
    </div>
  )
}

export default function Countdowns({ countdowns, reload }) {
  const [editing, setEditing] = useState(null) // countdown, or {} for a new one
  const [error, setError] = useState(null)

  const upcoming = countdowns.filter((c) => c.days >= 0)
  const past = countdowns.filter((c) => c.days < 0)
  const hasHolidays = ['christmas', 'halloween'].every((n) => countdowns.some((c) => c.name.toLowerCase() === n))

  async function addHolidays() {
    setError(null)
    try {
      await api.addHolidayCountdowns()
    } catch (e) {
      setError(e.message)
    }
    reload()
  }

  return (
    <main className="countdowns">
      <div className="chores-head">
        <span className="chores-title">
          <Icon name="hourglass" /> Countdowns
        </span>
        <div className="row-actions">
          {!hasHolidays && <button onClick={addHolidays}>Add holidays</button>}
          <button className="primary" onClick={() => setEditing({})}>+ Add countdown</button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      {countdowns.length === 0 && (
        <p className="empty">
          Nothing to count down to yet. Add a birthday, a trip or the last day of school, or tap Add holidays.
        </p>
      )}

      <div className="countdown-grid">
        {upcoming.map((c, i) => (
          <Card key={c.id} c={c} tint={TINTS[i % TINTS.length]} big={i === 0} onClick={() => setEditing(c)} />
        ))}
      </div>

      {past.length > 0 && (
        <>
          <div className="grocery-done-head">
            <span>Already happened</span>
          </div>
          <div className="countdown-grid past">
            {past.map((c) => (
              <Card key={c.id} c={c} tint="#e2e8f0" onClick={() => setEditing(c)} />
            ))}
          </div>
        </>
      )}

      {editing && (
        <Editor
          countdown={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </main>
  )
}

function Card({ c, tint, big = false, onClick }) {
  const today = c.days === 0
  return (
    <button className={`countdown-card ${big ? 'big' : ''} ${today ? 'today' : ''}`} style={{ '--tint': tint }} onClick={onClick}>
      <ItemIcon value={c.icon} fallback="hourglass" className="cd-icon" />
      <div className="cd-text">
        {today ? (
          <div className="cd-num">Today!</div>
        ) : c.days > 0 ? (
          <>
            <div className="cd-num">{c.days}</div>
            <div className="cd-unit">{c.days === 1 ? 'day until' : 'days until'}</div>
          </>
        ) : (
          <div className="cd-unit">{whenText(c.days)}</div>
        )}
        <div className="cd-name">{c.name}</div>
        <div className="cd-date">{longDate(c.next)}</div>
      </div>
    </button>
  )
}

function Editor({ countdown, onClose, onSaved }) {
  const isNew = !countdown.id
  const [name, setName] = useState(countdown.name ?? '')
  const [day, setDay] = useState(countdown.day ?? '')
  const [icon, setIcon] = useState(countdown.icon ?? '')
  const [repeat, setRepeat] = useState(countdown.repeat ?? '')
  const [error, setError] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const moving = MOVING.has(repeat)

  function chooseRepeat(id) {
    setRepeat(id)
    const r = REPEATS.find((x) => x.id === id)
    if (r?.name && !name.trim()) setName(r.name)
    if (r?.icon && !icon) setIcon(r.icon)
  }

  async function save(e) {
    e.preventDefault()
    if (!name.trim()) return setError('Give it a name')
    // Moving holidays ignore the date, but the server still wants one
    const body = { name: name.trim(), day: moving ? day || new Date().toLocaleDateString('en-CA') : day, icon, repeat }
    if (!body.day) return setError('Pick a date')
    setError(null)
    try {
      if (isNew) await api.createCountdown(body)
      else await api.updateCountdown(countdown.id, body)
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  async function remove() {
    try {
      await api.deleteCountdown(countdown.id)
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal countdown-editor" onSubmit={save}>
        <h2>{isNew ? 'New countdown' : 'Edit countdown'}</h2>
        <div className="row name-row">
          <IconPicker value={icon} fallback="hourglass" onChange={setIcon} />
          <input
            className="title-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Christmas, Aaron's birthday, beach trip…"
            maxLength={60}
            autoFocus={isNew}
          />
        </div>
        <label>
          Repeats
          <select value={repeat} onChange={(e) => chooseRepeat(e.target.value)}>
            {REPEATS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        {moving ? (
          <p className="note">
            The date changes every year, so the calendar works it out.
            {countdown.repeat === repeat && countdown.next ? ` Next one: ${longDate(countdown.next)}.` : ''}
          </p>
        ) : (
          <label>
            Date
            <input type="date" value={day} onChange={(e) => setDay(e.target.value)} required />
          </label>
        )}
        {repeat === 'yearly' && <p className="note">Good for birthdays: it starts counting again the day after.</p>}
        {error && <p className="error">{error}</p>}
        <div className="actions">
          {!isNew &&
            (confirm ? (
              <>
                <span className="confirm-text">Remove this countdown?</span>
                <button type="button" className="danger" onClick={remove}>Remove</button>
                <button type="button" onClick={() => setConfirm(false)}>Keep</button>
              </>
            ) : (
              <button type="button" className="danger" onClick={() => setConfirm(true)}>Remove</button>
            ))}
          <span className="spacer" />
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary">Save</button>
        </div>
      </form>
    </div>
  )
}
