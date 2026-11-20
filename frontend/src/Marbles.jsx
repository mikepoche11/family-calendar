import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api.js'
import Avatar from './avatars.jsx'
import { Icon, ItemIcon } from './icons.jsx'
import IconPicker from './IconPicker.jsx'

// Inside of the glass, in px. Marbles are laid out from the bottom up.
const JAR_W = 216
const JAR_H = 268
const LEAVE_MS = 3200 // rise out, line up and pause, then disappear
const STAGGER_MS = 80 // delay between pairs starting to rise
const INSIDE_TOP = 36 // px from the top of the lid to the top of the jar's inside

/** Same rule as the backend: remove the top-most n marbles of one color. Returns removed indices. */
function topIndices(contents, color, n) {
  const out = []
  for (let i = contents.length - 1; i >= 0 && out.length < n; i--) if (contents[i] === color) out.push(i)
  return out
}

/** Pack n marbles into the jar in offset rows; shrinks marbles when the jar gets full. */
function layout(n) {
  let size = 30
  const fits = (s) => {
    const cols = Math.floor(JAR_W / s)
    let left = n
    let rows = 0
    while (left > 0) {
      left -= rows % 2 ? cols - 1 : cols
      rows++
    }
    return rows * s * 0.87 + s * 0.13 <= JAR_H
  }
  while (size > 8 && !fits(size)) size--
  const cols = Math.floor(JAR_W / size)
  const pad = (JAR_W - cols * size) / 2
  const pos = []
  let row = 0
  while (pos.length < n) {
    const odd = row % 2 === 1
    const inRow = odd ? cols - 1 : cols
    for (let c = 0; c < inRow && pos.length < n; c++) {
      const i = pos.length
      const jx = (((i * 9301 + 49297) % 233280) / 233280 - 0.5) * size * 0.12
      const jy = (((i * 4271 + 1103) % 7919) / 7919) * size * 0.06
      pos.push({
        x: pad + c * size + (odd ? size / 2 : 0) + jx,
        y: JAR_H - size - row * size * 0.87 - jy,
      })
    }
    row++
  }
  return { size, pos }
}

/**
 * Where each leaving marble waits above the jar (centre point, in jar-inside coordinates).
 * Cancel out: pairs side by side, white on the left of its blue. Spend: blues in a row.
 */
function lineup(leaving, size) {
  const L = Math.min(size, 26)
  const pairs = leaving.white.length > 0
  const n = pairs ? Math.min(leaving.white.length, leaving.blue.length) : leaving.blue.length
  const slotW = pairs ? 2 * L + 18 : L + 8
  const perRow = Math.max(1, Math.floor((JAR_W + 80) / slotW))
  const out = {}
  for (let k = 0; k < n; k++) {
    const row = Math.floor(k / perRow)
    const inRow = Math.min(perRow, n - row * perRow)
    const cx = JAR_W / 2 + ((k % perRow) - (inRow - 1) / 2) * slotW
    const cy = -INSIDE_TOP - 14 - L / 2 - row * (L + 10)
    const order = k
    if (pairs) {
      out[leaving.white[k]] = { x: cx - L / 2 - 2, y: cy, scale: L / size, order }
      out[leaving.blue[k]] = { x: cx + L / 2 + 2, y: cy, scale: L / size, order }
    } else {
      out[leaving.blue[k]] = { x: cx, y: cy, scale: L / size, order }
    }
  }
  return out
}

/** Marble jars, one per kid. Blue = good and spendable, white = stays until cancelled out. */
export default function Marbles({ people, version }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [spending, setSpending] = useState(null) // jar waiting for a reward choice
  const [settings, setSettings] = useState(false)
  const [leaving, setLeaving] = useState(null) // { pid, white: [...idx], blue: [...idx], label }
  const busy = useRef(false)
  const pending = useRef(false)

  const load = () => {
    if (busy.current) {
      pending.current = true // reload once the animation finishes
      return Promise.resolve()
    }
    return api
      .marbles()
      .then(setData)
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
  }, [version])

  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])

  async function run(fn) {
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    }
    load()
  }

  /** Animate marbles leaving the jar, then show the new contents. */
  async function removeWithAnimation(jar, white, blue, label, call) {
    setError(null)
    busy.current = true
    setLeaving({ pid: jar.person_id, white, blue, label })
    const pairs = Math.max(white.length, blue.length)
    const wait = new Promise((r) => setTimeout(r, LEAVE_MS + STAGGER_MS * Math.min(pairs, 12)))
    try {
      await Promise.all([call(), wait])
    } catch (e) {
      setError(e.message)
    }
    busy.current = false
    pending.current = false
    // Swap in the new contents and drop the animation in the same render, so nothing flashes back
    try {
      setData(await api.marbles())
    } catch (e) {
      setError(e.message)
    }
    setLeaving(null)
  }

  function cancelOut(jar) {
    const n = Math.min(jar.blue, jar.white)
    if (!n) return
    removeWithAnimation(
      jar,
      topIndices(jar.contents, 'w', n),
      topIndices(jar.contents, 'b', n),
      `${n} white + ${n} blue cancel out`,
      () => api.cancelMarbles(jar.person_id),
    )
  }

  function spend(jar, reward) {
    setSpending(null)
    removeWithAnimation(
      jar,
      [],
      topIndices(jar.contents, 'b', reward.cost),
      <><ItemIcon value={reward.icon} fallback="gift" /> {reward.title}!</>,
      () => api.spendMarbles(jar.person_id, reward.id),
    )
  }

  if (!data) return <main className="marbles">{error && <p className="error">{error}</p>}</main>

  const jars = data.jars.filter((j) => peopleById[j.person_id])
  const cheapest = Math.min(...data.rewards.map((r) => r.cost), Infinity)

  return (
    <main className="marbles">
      <div className="chores-head">
        <span className="chores-title">Marble jars</span>
        <button onClick={() => setSettings(true)}><Icon name="gear" /> Jars &amp; rewards</button>
      </div>
      {error && <p className="error">{error}</p>}

      {jars.length === 0 ? (
        <JarSetup people={people} onDone={load} />
      ) : (
        <div className="jars">
          {jars.map((jar) => {
            const person = peopleById[jar.person_id]
            const anim = leaving?.pid === jar.person_id ? leaving : null
            return (
              <section className="jar-card" key={jar.person_id} style={{ '--chip': person.color }}>
                <Jar jar={jar} person={person} leaving={anim} />
                <div className="jar-counts">
                  <span>
                    <i className="dot blue" /> {jar.blue} blue
                  </span>
                  <span>
                    <i className="dot white" /> {jar.white} white
                  </span>
                </div>
                <div className="jar-add">
                  <button
                    className="add-blue"
                    disabled={!!anim}
                    onClick={() => run(() => api.addMarbles(jar.person_id, 'blue'))}
                  >
                    + Blue
                  </button>
                  <button
                    className="add-white"
                    disabled={!!anim}
                    onClick={() => run(() => api.addMarbles(jar.person_id, 'white'))}
                  >
                    + White
                  </button>
                </div>
                <div className="jar-actions">
                  <button disabled={!!anim || jar.blue < cheapest} onClick={() => setSpending(jar)}>
                    <Icon name="bag" /> Spend
                  </button>
                  <button
                    className="cancel-out"
                    disabled={!!anim || !jar.blue || !jar.white}
                    onClick={() => cancelOut(jar)}
                  >
                    <Icon name="scale" /> Cancel out
                  </button>
                </div>
                <button
                  className="undo"
                  disabled={!!anim || !jar.last_action}
                  onClick={() => run(() => api.undoMarbles(jar.person_id))}
                >
                  <Icon name="undo" /> Undo last
                </button>
              </section>
            )
          })}
        </div>
      )}

      {spending && (
        <SpendPicker
          jar={spending}
          person={peopleById[spending.person_id]}
          rewards={data.rewards}
          onPick={(r) => spend(spending, r)}
          onClose={() => setSpending(null)}
        />
      )}
      {settings && (
        <JarSettings
          people={people}
          jars={data.jars}
          rewards={data.rewards}
          onChanged={load}
          onClose={() => setSettings(false)}
        />
      )}
    </main>
  )
}

export function Jar({ jar, person, leaving }) {
  const prev = useRef(jar.contents)
  const contents = jar.contents
  // Marbles appended since the last render drop in from the top
  const newFrom = contents.startsWith(prev.current) && contents.length > prev.current.length ? prev.current.length : contents.length
  useEffect(() => {
    prev.current = contents
  }, [contents])

  const { size, pos } = useMemo(() => layout(contents.length), [contents.length])
  // Leaving marbles rise out and line up above the lid, white next to its blue, then pause
  const targets = useMemo(() => (leaving ? lineup(leaving, size) : {}), [leaving, size])

  return (
    <div className="jar" aria-label={`${person.name}'s jar: ${jar.blue} blue, ${jar.white} white`}>
      <div className="jar-lid" />
      <div className="jar-glass">
        <div className="jar-inside" style={{ width: JAR_W, height: JAR_H }}>
          {pos.map((p, i) => {
            const t = targets[i]
            const color = contents[i] === 'b' ? 'blue' : 'white'
            const cls = `marble ${color} ${t ? 'leave' : ''} ${i >= newFrom ? 'drop' : ''}`
            return (
              <span
                key={i}
                className={cls}
                style={{
                  width: size,
                  height: size,
                  left: p.x,
                  top: p.y,
                  '--drop': `${-p.y - size - 40}px`,
                  '--tx': t ? `${t.x - p.x - size / 2}px` : undefined,
                  '--ty': t ? `${t.y - p.y - size / 2}px` : undefined,
                  '--k': t ? t.scale : undefined,
                  animationDelay: t ? `${t.order * STAGGER_MS}ms` : undefined,
                }}
              />
            )
          })}
        </div>
        <div className="jar-label">
          <Avatar person={person} size={40} />
          <span>{person.name}</span>
        </div>
        <div className="jar-shine" />
      </div>
      {leaving && <div className="jar-bubble">{leaving.label}</div>}
    </div>
  )
}

function SpendPicker({ jar, person, rewards, onPick, onClose }) {
  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal spend-picker">
        <h2>What is {person.name} getting?</h2>
        <p className="note">
          {jar.blue} blue marble{jar.blue === 1 ? '' : 's'} to spend
        </p>
        <div className="rewards">
          {rewards.map((r) => {
            const short = r.cost - jar.blue
            return (
              <button key={r.id} className="reward" disabled={short > 0} onClick={() => onPick(r)}>
                <span className="icon"><ItemIcon value={r.icon} fallback="gift" /></span>
                <span className="title">{r.title}</span>
                <span className="cost">
                  {r.cost} <i className="dot blue" />
                </span>
                {short > 0 && <span className="short">needs {short} more</span>}
              </button>
            )
          })}
        </div>
        <div className="actions">
          <span className="spacer" />
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

function JarSetup({ people, onDone }) {
  const [kids, setKids] = useState([])
  const [busy, setBusy] = useState(false)
  const toggle = (id) => setKids((k) => (k.includes(id) ? k.filter((x) => x !== id) : [...k, id]))
  return (
    <div className="starter">
      <p className="big">Who gets a marble jar?</p>
      <p className="hint">
        Blue marbles are for good behavior and can be spent on treats. White marbles stay in the jar until you press
        Cancel out, which takes away one blue for each white.
      </p>
      <div className="chips">
        {people.map((p) => (
          <button
            key={p.id}
            className={`chip ${kids.includes(p.id) ? 'on' : ''}`}
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
          disabled={!kids.length || busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.setJars(people.filter((p) => kids.includes(p.id)).map((p) => p.id))
            } catch {
              setBusy(false)
            }
            onDone()
          }}
        >
          Make jars
        </button>
      </div>
    </div>
  )
}

function JarSettings({ people, jars, rewards, onChanged, onClose }) {
  const [error, setError] = useState(null)
  const [confirm, setConfirm] = useState(null) // person whose jar is about to be removed
  const has = new Set(jars.map((j) => j.person_id))
  const run = async (fn) => {
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    }
    onChanged()
  }
  const toggle = (p) => {
    if (has.has(p.id)) return setConfirm(p)
    const ids = people.filter((x) => has.has(x.id) || x.id === p.id).map((x) => x.id)
    run(() => api.setJars(ids))
  }
  const confirmJar = confirm && jars.find((j) => j.person_id === confirm.id)

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal chore-editor">
        <div className="settings-head">
          <h2>Jars &amp; rewards</h2>
          <button className="primary" onClick={onClose}>
            Done
          </button>
        </div>
        <div className="field-label">Who has a jar</div>
        <div className="chips">
          {people.map((p) => (
            <button
              key={p.id}
              className={`chip ${has.has(p.id) ? 'on' : ''}`}
              style={{ '--chip': p.color }}
              onClick={() => toggle(p)}
            >
              <Avatar person={p} size={32} />
              {p.name}
            </button>
          ))}
        </div>
        {confirm && (
          <div className="row-actions">
            <span className="confirm-text">
              Remove {confirm.name}'s jar? Their {confirmJar?.blue ?? 0} blue and {confirmJar?.white ?? 0} white marbles
              will be gone for good.
            </span>
            <button onClick={() => setConfirm(null)}>Keep it</button>
            <button
              className="danger"
              onClick={() => {
                setConfirm(null)
                run(() => api.removeJar(confirm.id))
              }}
            >
              Remove jar
            </button>
          </div>
        )}

        <div className="field-label">Rewards</div>
        <div className="chore-rows">
          {rewards.map((r) => (
            <div className="chore-row" key={r.id}>
              <IconPicker value={r.icon} fallback="gift" onChange={(icon) => run(() => api.updateReward(r.id, { icon }))} />
              <input
                className="title-input-sm"
                defaultValue={r.title}
                maxLength={40}
                aria-label="Reward"
                onBlur={(e) => {
                  const v = e.target.value.trim()
                  if (v && v !== r.title) run(() => api.updateReward(r.id, { title: v }))
                }}
                onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
              />
              <div className="stepper" aria-label="Cost in blue marbles">
                <button onClick={() => r.cost > 1 && run(() => api.updateReward(r.id, { cost: r.cost - 1 }))}>−</button>
                <span>
                  {r.cost} <i className="dot blue" />
                </span>
                <button onClick={() => run(() => api.updateReward(r.id, { cost: r.cost + 1 }))}>+</button>
              </div>
              <button className="remove" aria-label={`Delete ${r.title}`} onClick={() => run(() => api.deleteReward(r.id))}>
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="actions">
          <button
            className="primary"
            onClick={() => run(() => api.createReward({ title: 'New reward', icon: '🎁', cost: 3 }))}
          >
            + Add reward
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}
