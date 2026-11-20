import { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import Avatar from './avatars.jsx'
import { Jar } from './Marbles.jsx'
import { Icon, ItemIcon } from './icons.jsx'
import IconPicker from './IconPicker.jsx'

const DAY_LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'] // Monday = 0, matches the backend
const ANYONE = 'anyone'

/** Today's chores, one column per person plus an "Anyone" column. Tap a tile to check it off. */
export default function Chores({ people, version }) {
  const [today, setToday] = useState(null)
  const [all, setAll] = useState([])
  const [whoFor, setWhoFor] = useState(null) // "anyone" chore waiting for who did it
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState(null)
  const [earned, setEarned] = useState(null) // marbles just added to (or taken from) a jar

  const load = () =>
    Promise.all([api.choresToday(), api.chores()])
      .then(([t, a]) => {
        setToday(t)
        setAll(a)
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
  }, [version])

  // New day: reload so yesterday's checkmarks clear at midnight
  useEffect(() => {
    const t = setInterval(() => {
      const d = new Date()
      const local = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      if (today && local !== today.date) load()
    }, 60 * 1000)
    return () => clearInterval(t)
  }, [today])

  async function setDone(chore, done, personId = null) {
    setError(null)
    // Optimistic update
    setToday((t) => ({
      ...t,
      chores: t.chores.map((c) =>
        c.id === chore.id ? { ...c, done, done_by: done ? chore.person_id ?? personId : null } : c,
      ),
    }))
    try {
      const r = await api.setChoreDone(chore.id, { done, person_id: personId })
      // Show the newest jar change: marbles earned, or taken back after unchecking
      const change = (r.marbles ?? []).filter((m) => m.jar).pop()
      if (change) setEarned({ ...change, key: Date.now() })
    } catch (e) {
      setError(e.message)
    }
    load()
  }

  function tap(chore) {
    if (chore.done) return setDone(chore, false)
    if (chore.person_id == null) return setWhoFor(chore)
    setDone(chore, true)
  }

  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])
  const columns = useMemo(() => {
    if (!today) return []
    const cols = people
      .map((p) => ({ key: p.id, person: p, chores: today.chores.filter((c) => c.person_id === p.id) }))
      .filter((c) => c.chores.length)
    const shared = today.chores.filter((c) => c.person_id == null)
    if (shared.length) cols.push({ key: ANYONE, person: null, chores: shared })
    return cols
  }, [today, people])

  if (!today) return <main className="chores">{error && <p className="error">{error}</p>}</main>

  return (
    <main className="chores">
      <div className="chores-head">
        <span className="chores-title">Today's chores</span>
        <button onClick={() => setEditing(true)}><Icon name="pencil" /> Edit chores</button>
      </div>
      {error && <p className="error">{error}</p>}

      {all.length === 0 ? (
        <Starter people={people} onAdded={load} />
      ) : columns.length === 0 ? (
        <p className="empty">No chores today. Enjoy the day off!</p>
      ) : (
        <div className="chore-columns">
          {columns.map((col) => {
            const done = col.chores.filter((c) => c.done).length
            const color = col.person?.color ?? '#cbd5e1'
            const finished = done === col.chores.length
            return (
              <section className="chore-col" key={col.key} style={{ '--chip': color }}>
                <header>
                  {col.person ? <Avatar person={col.person} size={56} /> : <span className="anyone-icon"><Icon name="anyone" /></span>}
                  <div>
                    <div className="name">{col.person?.name ?? 'Anyone'}</div>
                    <div className="progress">
                      <span style={{ width: `${(done / col.chores.length) * 100}%` }} />
                    </div>
                    <div className="count">
                      {done} of {col.chores.length}
                    </div>
                  </div>
                </header>
                {finished && col.person && <div className="all-done">All done! <Icon name="party" /></div>}
                {col.chores.map((c) => (
                  <button key={c.id} className={`chore-tile ${c.done ? 'done' : ''}`} onClick={() => tap(c)}>
                    <span className="icon"><ItemIcon value={c.icon} fallback="star" /></span>
                    <span className="title">{c.title}</span>
                    {c.marbles > 0 && (
                      <span className="chore-marbles" aria-label={`Worth ${c.marbles} blue marbles`}>
                        +{c.marbles} <i className="dot blue" />
                      </span>
                    )}
                    {c.done && col.key === ANYONE && peopleById[c.done_by] ? (
                      <Avatar person={peopleById[c.done_by]} size={36} />
                    ) : (
                      <span className="tick">{c.done ? '✓' : ''}</span>
                    )}
                  </button>
                ))}
              </section>
            )
          })}
        </div>
      )}

      {whoFor && (
        <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && setWhoFor(null)}>
          <div className="modal who-did-it">
            <h2>Who did "{whoFor.title}"?</h2>
            {whoFor.marbles > 0 && (
              <p className="note">
                Worth {whoFor.marbles} blue marble{whoFor.marbles === 1 ? '' : 's'} for whoever did it.
              </p>
            )}
            <div className="chips">
              {people.map((p) => (
                <button
                  key={p.id}
                  className="chip on"
                  style={{ '--chip': p.color }}
                  onClick={() => {
                    setDone(whoFor, true, p.id)
                    setWhoFor(null)
                  }}
                >
                  <Avatar person={p} size={36} />
                  {p.name}
                </button>
              ))}
            </div>
            <div className="actions">
              <span className="spacer" />
              <button onClick={() => setWhoFor(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {earned && (
        <MarblesEarned
          key={earned.key}
          change={earned}
          person={peopleById[earned.person_id]}
          onClose={() => setEarned(null)}
        />
      )}

      {editing && <ChoreEditor chores={all} people={people} onChanged={load} onClose={() => setEditing(false)} />}
    </main>
  )
}

/** After a chore worth marbles is checked: show the kid's jar with the new blues dropping in. */
function MarblesEarned({ change, person, onClose }) {
  const { count, jar } = change
  const gained = count > 0
  // Start with the jar as it was, then add the new marbles so they drop in from the top
  const [shown, setShown] = useState(() => (gained ? { ...jar, contents: jar.contents.slice(0, -count) } : jar))
  useEffect(() => {
    const t1 = gained ? setTimeout(() => setShown(jar), 350) : null
    const t2 = setTimeout(onClose, gained ? 3200 : 2600)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [])
  if (!person) return null
  const n = Math.abs(count)
  const what = `${n} blue marble${n === 1 ? '' : 's'}`

  if (!gained)
    return (
      <div className="marble-toast" role="status" onClick={onClose}>
        Took back {what} from {person.name}'s jar
      </div>
    )
  return (
    <div className="backdrop" onPointerDown={onClose}>
      <div className="modal marbles-earned" style={{ '--chip': person.color }} role="status">
        <h2>
          +{what} for {person.name}! <Icon name="party" />
        </h2>
        <Jar jar={shown} person={person} leaving={null} />
        <p className="note">
          {jar.blue} blue in the jar now. Tap anywhere to close.
        </p>
      </div>
    </div>
  )
}

function Starter({ people, onAdded }) {
  const [kids, setKids] = useState(() => new Set())
  const [busy, setBusy] = useState(false)
  const toggle = (id) =>
    setKids((s) => {
      const n = new Set(s)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  return (
    <div className="starter">
      <p className="big">No chores yet. Start with a suggested set?</p>
      <p className="hint">
        Each kid gets: make bed, dirty clothes in the hamper, clear plate after dinner, tidy bedroom (Saturdays), put
        away clean laundry. Shared: set the table, unload the dishwasher, take out the trash. You can change all of it.
      </p>
      <div className="field-label">Who are the kids?</div>
      <div className="chips">
        {people.map((p) => (
          <button
            key={p.id}
            className={`chip ${kids.has(p.id) ? 'on' : ''}`}
            style={{ '--chip': p.color }}
            onClick={() => toggle(p.id)}
          >
            <Avatar person={p} size={32} />
            {p.name}
          </button>
        ))}
      </div>
      <div className="actions">
        <button
          className="primary"
          disabled={!kids.size || busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.addStarterChores([...kids])
            } catch {
              setBusy(false)
            }
            onAdded()
          }}
        >
          Add starter chores
        </button>
      </div>
    </div>
  )
}

function ChoreEditor({ chores, people, onChanged, onClose }) {
  const [error, setError] = useState(null)
  const run = async (fn) => {
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    }
    onChanged()
  }
  const toggleDay = (c, d) => {
    const set = new Set(c.days)
    set.has(d) ? set.delete(d) : set.add(d)
    if (set.size) run(() => api.updateChore(c.id, { days: [...set].sort().join('') }))
  }

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal chore-editor">
        <div className="settings-head">
          <h2>Edit chores</h2>
          <button className="primary" onClick={onClose}>Done</button>
        </div>
        <p className="hint">
          The <i className="dot blue" /> number is how many blue marbles a chore earns. Checking it off drops them into
          that kid's jar; unchecking takes them back. Leave it at 0 for no marbles.
        </p>
        <div className="chore-rows">
          {chores.map((c) => (
            <div className="chore-row" key={c.id}>
              <IconPicker value={c.icon} fallback="star" onChange={(icon) => run(() => api.updateChore(c.id, { icon }))} />
              <input
                className="title-input-sm"
                defaultValue={c.title}
                maxLength={80}
                aria-label="Chore"
                onBlur={(e) => {
                  const v = e.target.value.trim()
                  if (v && v !== c.title) run(() => api.updateChore(c.id, { title: v }))
                }}
                onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
              />
              <select
                value={c.person_id ?? ''}
                aria-label="Who"
                onChange={(e) =>
                  run(() =>
                    api.updateChore(c.id, e.target.value ? { person_id: Number(e.target.value) } : { anyone: true }),
                  )
                }
              >
                <option value="">Anyone</option>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <div className="days">
                {DAY_LETTERS.map((l, i) => (
                  <button
                    key={i}
                    className={c.days.includes(String(i)) ? 'on' : ''}
                    onClick={() => toggleDay(c, String(i))}
                    aria-label={['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <div className="stepper" aria-label="Blue marbles earned">
                <button
                  aria-label="Fewer marbles"
                  disabled={!c.marbles}
                  onClick={() => run(() => api.updateChore(c.id, { marbles: c.marbles - 1 }))}
                >
                  −
                </button>
                <span className={c.marbles ? '' : 'none'}>
                  {c.marbles} <i className="dot blue" />
                </span>
                <button
                  aria-label="More marbles"
                  disabled={c.marbles >= 20}
                  onClick={() => run(() => api.updateChore(c.id, { marbles: c.marbles + 1 }))}
                >
                  +
                </button>
              </div>
              <button className="remove" aria-label={`Delete ${c.title}`} onClick={() => run(() => api.deleteChore(c.id))}>
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="actions">
          <button className="primary" onClick={() => run(() => api.createChore({ title: 'New chore', icon: '⭐' }))}>
            + Add chore
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}
