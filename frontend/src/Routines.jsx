import { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import Avatar from './avatars.jsx'
import { Icon, ItemIcon } from './icons.jsx'
import IconPicker from './IconPicker.jsx'
import { MarblesEarned } from './Chores.jsx'
import { KINDS, ROUTINE, activeKind, fmtTime, localDate, shownKind } from './routineTime.js'

const DAY_LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'] // Monday = 0, matches the backend
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/**
 * Morning and bedtime routines: one column per kid with today's steps. The morning routine shows in the
 * morning and the bedtime routine in the evening (times in the editor); the buttons on top switch by hand.
 */
export default function Routines({ people, version }) {
  const [today, setToday] = useState(null)
  const [all, setAll] = useState([])
  const [error, setError] = useState(null)
  const [now, setNow] = useState(() => new Date())
  const [picked, setPicked] = useState(null) // routine chosen by hand; cleared when the clock moves to another
  const [editing, setEditing] = useState(false)
  const [earned, setEarned] = useState(null)
  const [cheer, setCheer] = useState(null) // finished a routine that earns no marbles

  const load = () =>
    Promise.all([api.routinesToday(), api.routines()])
      .then(([t, a]) => {
        setToday(t)
        setAll(a.steps)
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
  }, [version])

  // Clock tick: follow the routine times, and start fresh at midnight
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30 * 1000)
    return () => clearInterval(t)
  }, [])
  useEffect(() => {
    if (today && localDate(now) !== today.date) load()
  }, [now, today])

  const settings = today?.settings
  const auto = shownKind(settings, now)
  useEffect(() => setPicked(null), [auto])
  const kind = picked ?? auto
  const on = activeKind(settings, now) === kind

  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])
  const columns = useMemo(() => {
    if (!today) return []
    return people
      .map((p) => ({ person: p, steps: today.steps.filter((s) => s.kind === kind && s.person_id === p.id) }))
      .filter((c) => c.steps.length)
  }, [today, people, kind])

  async function tap(step) {
    setError(null)
    const done = !step.done
    setToday((t) => ({ ...t, steps: t.steps.map((s) => (s.id === step.id ? { ...s, done } : s)) }))
    try {
      const r = await api.setRoutineDone(step.id, { done })
      const person = peopleById[step.person_id]
      const change = (r.marbles ?? []).find((m) => m.jar)
      const finishedText = r.finished
        ? `${person?.name ?? ''} finished the ${ROUTINE[kind].label.toLowerCase()}!${r.bonus ? ` (+${r.bonus} bonus)` : ''}`
        : null
      if (change) setEarned({ ...change, key: Date.now(), extra: change.count > 0 ? finishedText : null })
      else if (r.finished && person) setCheer({ person, text: finishedText, key: Date.now() })
    } catch (e) {
      setError(e.message)
    }
    load()
  }

  if (!today) return <main className="chores routines">{error && <p className="error">{error}</p>}</main>

  const times = settings[kind]
  const bonusOf = (pid) => today.bonus.find((b) => b.kind === kind && b.person_id === pid)

  return (
    <main className={`chores routines ${kind}`}>
      <div className="chores-head routines-head">
        <span className="chores-title routine-title">
          <Icon name={ROUTINE[kind].icon} size="1.4em" /> {ROUTINE[kind].label}
          <span className={`routine-when ${on ? 'on' : ''}`}>
            {on ? `Until ${fmtTime(times.end)}` : `${fmtTime(times.start)} – ${fmtTime(times.end)}`}
          </span>
        </span>
        <div className="routine-switch" role="group" aria-label="Which routine">
          {KINDS.map((k) => (
            <button key={k} className={k === kind ? 'on' : ''} onClick={() => setPicked(k)}>
              <Icon name={ROUTINE[k].icon} /> {ROUTINE[k].short}
            </button>
          ))}
        </div>
        <button onClick={() => setEditing(true)}><Icon name="pencil" /> Edit routines</button>
      </div>
      {times.bonus > 0 && (
        <div className="routine-bonus">
          Finish every step for a bonus of <b>+{times.bonus}</b> <i className="dot blue" />
        </div>
      )}
      {error && <p className="error">{error}</p>}

      {all.length === 0 ? (
        <Starter people={people} onAdded={load} />
      ) : columns.length === 0 ? (
        <p className="empty">No {ROUTINE[kind].short.toLowerCase()} steps today. Tap Edit routines to add some.</p>
      ) : (
        <div className="chore-columns">
          {columns.map(({ person, steps }) => {
            const done = steps.filter((s) => s.done).length
            const finished = done === steps.length
            const bonus = bonusOf(person.id)
            return (
              <section className={`chore-col routine-col ${finished ? 'finished' : ''}`} key={person.id} style={{ '--chip': person.color }}>
                <header>
                  <Avatar person={person} size={56} />
                  <div>
                    <div className="name">{person.name}</div>
                    <div className="progress">
                      <span style={{ width: `${(done / steps.length) * 100}%` }} />
                    </div>
                    <div className="count">
                      {done} of {steps.length}
                    </div>
                  </div>
                </header>
                {finished && (
                  <div className="all-done">
                    All done! <Icon name="party" />
                    {bonus?.marbles > 0 && <span className="bonus-got"> +{bonus.marbles} <i className="dot blue" /></span>}
                  </div>
                )}
                {steps.map((s, i) => (
                  <button key={s.id} className={`chore-tile routine-step ${s.done ? 'done' : ''}`} onClick={() => tap(s)}>
                    <span className="step-num">{i + 1}</span>
                    <span className="icon"><ItemIcon value={s.icon} fallback="star" /></span>
                    <span className="title">{s.title}</span>
                    {s.marbles > 0 && (
                      <span className="chore-marbles" aria-label={`Worth ${s.marbles} blue marbles`}>
                        +{s.marbles} <i className="dot blue" />
                      </span>
                    )}
                    <span className="tick">{s.done ? '✓' : ''}</span>
                  </button>
                ))}
              </section>
            )
          })}
        </div>
      )}

      {earned && (
        <MarblesEarned
          key={earned.key}
          change={earned}
          person={peopleById[earned.person_id]}
          extra={earned.extra}
          onClose={() => setEarned(null)}
        />
      )}
      {cheer && <Cheer key={cheer.key} {...cheer} onClose={() => setCheer(null)} />}

      {editing && (
        <RoutineEditor
          steps={all}
          settings={settings}
          people={people}
          startKind={kind}
          onChanged={load}
          onClose={() => setEditing(false)}
        />
      )}
    </main>
  )
}

/** Short celebration when a routine is finished and no marbles were involved. */
function Cheer({ person, text, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 2600)
    return () => clearTimeout(t)
  }, [])
  return (
    <div className="backdrop" onPointerDown={onClose}>
      <div className="modal routine-cheer" style={{ '--chip': person.color }} role="status">
        <Avatar person={person} size={96} />
        <h2>
          {text} <Icon name="party" />
        </h2>
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
      <p className="big">No routines yet. Start with a suggested set?</p>
      <p className="hint">
        Morning: get dressed, eat breakfast, brush teeth, brush hair, shoes on, backpack ready (school days). Bedtime:
        bath or shower, pajamas on, brush teeth, clothes in the hamper, read a book, lights out. You can change all of
        it, and set marbles for any step.
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
              await api.addStarterRoutines([...kids])
            } catch {
              setBusy(false)
            }
            onAdded()
          }}
        >
          Add starter routines
        </button>
      </div>
    </div>
  )
}

function RoutineEditor({ steps, settings, people, startKind, onChanged, onClose }) {
  const [kind, setKind] = useState(startKind)
  const withSteps = people.filter((p) => steps.some((s) => s.person_id === p.id))
  const [pid, setPid] = useState(() => (withSteps[0] ?? people[0])?.id)
  const [error, setError] = useState(null)
  const [times, setTimes] = useState(settings)
  useEffect(() => setTimes(settings), [settings])

  const run = async (fn) => {
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    }
    onChanged()
  }
  const mine = steps.filter((s) => s.kind === kind && s.person_id === pid)
  const others = people.filter((p) => p.id !== pid && steps.some((s) => s.kind === kind && s.person_id === p.id))
  const person = people.find((p) => p.id === pid)

  const toggleDay = (s, d) => {
    const set = new Set(s.days)
    set.has(d) ? set.delete(d) : set.add(d)
    if (set.size) run(() => api.updateRoutineStep(s.id, { days: [...set].sort().join('') }))
  }
  const saveWindow = () => {
    const { start, end } = times[kind]
    if (start !== settings[kind].start || end !== settings[kind].end)
      run(() => api.setRoutineSettings({ [kind]: { start, end } }))
  }
  const saveTimes = (k, field, value) => {
    setTimes((t) => ({ ...t, [k]: { ...t[k], [field]: value } }))
    run(() => api.setRoutineSettings({ [k]: { [field]: value } }))
  }

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal chore-editor routine-editor">
        <div className="settings-head">
          <h2>Edit routines</h2>
          <button className="primary" onClick={onClose}>Done</button>
        </div>

        <div className="routine-switch" role="group" aria-label="Which routine">
          {KINDS.map((k) => (
            <button key={k} className={k === kind ? 'on' : ''} onClick={() => setKind(k)}>
              <Icon name={ROUTINE[k].icon} /> {ROUTINE[k].label}
            </button>
          ))}
        </div>

        <div className="routine-times">
          <label>
            Starts
            <input
              type="time"
              value={times[kind].start}
              onChange={(e) => e.target.value && setTimes((t) => ({ ...t, [kind]: { ...t[kind], start: e.target.value } }))}
              onBlur={saveWindow}
            />
          </label>
          <label>
            Ends
            <input
              type="time"
              value={times[kind].end}
              onChange={(e) => e.target.value && setTimes((t) => ({ ...t, [kind]: { ...t[kind], end: e.target.value } }))}
              onBlur={saveWindow}
            />
          </label>
          <div className="routine-bonus-edit">
            <div className="field-label">Bonus for finishing it all</div>
            <div className="stepper" aria-label="Bonus blue marbles">
              <button aria-label="Smaller bonus" disabled={!times[kind].bonus} onClick={() => saveTimes(kind, 'bonus', times[kind].bonus - 1)}>
                −
              </button>
              <span className={times[kind].bonus ? '' : 'none'}>
                {times[kind].bonus} <i className="dot blue" />
              </span>
              <button aria-label="Bigger bonus" disabled={times[kind].bonus >= 20} onClick={() => saveTimes(kind, 'bonus', times[kind].bonus + 1)}>
                +
              </button>
            </div>
          </div>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={times.auto_show}
            onChange={(e) => {
              const v = e.target.checked
              setTimes((t) => ({ ...t, auto_show: v }))
              run(() => api.setRoutineSettings({ auto_show: v }))
            }}
          />
          Switch the wall to the routine during these times when nobody is using it
        </label>

        <div className="person-tabs">
          {people.map((p) => (
            <button key={p.id} className={`person-tab ${p.id === pid ? 'on' : ''}`} style={{ '--chip': p.color }} onClick={() => setPid(p.id)}>
              <Avatar person={p} size={44} />
              {p.name}
            </button>
          ))}
        </div>

        <p className="hint">
          Steps show in this order. The <i className="dot blue" /> number is how many blue marbles a step earns (0 for
          none). Only kids with a marble jar get marbles.
        </p>
        <div className="chore-rows">
          {mine.length === 0 && <p className="empty">No {ROUTINE[kind].short.toLowerCase()} steps for {person?.name} yet.</p>}
          {mine.map((s, i) => (
            <div className="chore-row" key={s.id}>
              <div className="move">
                <button aria-label="Move up" disabled={i === 0} onClick={() => run(() => api.updateRoutineStep(s.id, { move: -1 }))}>▲</button>
                <button aria-label="Move down" disabled={i === mine.length - 1} onClick={() => run(() => api.updateRoutineStep(s.id, { move: 1 }))}>▼</button>
              </div>
              <IconPicker value={s.icon} fallback="star" onChange={(icon) => run(() => api.updateRoutineStep(s.id, { icon }))} />
              <input
                className="title-input-sm"
                defaultValue={s.title}
                maxLength={80}
                aria-label="Step"
                onBlur={(e) => {
                  const v = e.target.value.trim()
                  if (v && v !== s.title) run(() => api.updateRoutineStep(s.id, { title: v }))
                }}
                onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
              />
              <div className="days">
                {DAY_LETTERS.map((l, d) => (
                  <button
                    key={d}
                    className={s.days.includes(String(d)) ? 'on' : ''}
                    onClick={() => toggleDay(s, String(d))}
                    aria-label={DAY_NAMES[d]}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <div className="stepper" aria-label="Blue marbles earned">
                <button aria-label="Fewer marbles" disabled={!s.marbles} onClick={() => run(() => api.updateRoutineStep(s.id, { marbles: s.marbles - 1 }))}>
                  −
                </button>
                <span className={s.marbles ? '' : 'none'}>
                  {s.marbles} <i className="dot blue" />
                </span>
                <button aria-label="More marbles" disabled={s.marbles >= 20} onClick={() => run(() => api.updateRoutineStep(s.id, { marbles: s.marbles + 1 }))}>
                  +
                </button>
              </div>
              <button className="remove" aria-label={`Delete ${s.title}`} onClick={() => run(() => api.deleteRoutineStep(s.id))}>
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="actions">
          {others.length > 0 && (
            <select
              value=""
              aria-label="Copy steps from"
              onChange={(e) =>
                e.target.value &&
                run(() => api.copyRoutine({ kind, from_person_id: Number(e.target.value), to_person_id: pid }))
              }
            >
              <option value="">Copy steps from…</option>
              {others.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
          <span className="spacer" />
          <button
            className="primary"
            disabled={!pid}
            onClick={() => run(() => api.createRoutineStep({ kind, person_id: pid, title: 'New step', icon: '⭐' }))}
          >
            + Add step
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}
