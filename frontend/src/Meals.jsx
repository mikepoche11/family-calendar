import { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import { Icon, ItemIcon } from './icons.jsx'
import IconPicker from './IconPicker.jsx'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
// Things most kitchens already have: left unchecked when sending ingredients to the grocery list
const STAPLES = /^(salt|pepper|black pepper|water|cold water|hot water|sugar|olive oil|vegetable oil|oil|flour|butter|garlic powder|onion powder)\b/i

const parse = (iso) => new Date(`${iso}T12:00:00`)
const isoOf = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const addDays = (iso, n) => {
  const d = parse(iso)
  d.setDate(d.getDate() + n)
  return isoOf(d)
}
const short = (iso) => parse(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
const itemKey = (line) => line.split('(')[0].trim().toLowerCase()

/** Dinner plan: one card per night, Monday to Sunday. Tap a night to pick a meal or get ideas. */
export default function Meals({ version }) {
  const [start, setStart] = useState('') // '' = this week
  const [plan, setPlan] = useState(null)
  const [meals, setMeals] = useState([])
  const [picking, setPicking] = useState(null) // day being planned
  const [editing, setEditing] = useState(null) // meal object, or {} for a new one
  const [showBox, setShowBox] = useState(false)
  const [shopping, setShopping] = useState(null) // [{line, from}]
  const [toast, setToast] = useState(null)
  const [error, setError] = useState(null)

  const load = () =>
    Promise.all([api.mealPlan(start), api.meals()])
      .then(([p, m]) => {
        setPlan(p)
        setMeals(m)
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
  }, [version, start])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast])

  async function act(fn) {
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e.message)
    } finally {
      load()
    }
  }

  function shopFor(days) {
    const lines = []
    for (const d of days) {
      for (const line of d.meal?.ingredients ?? []) lines.push({ line, from: d.meal.name })
    }
    setShopping(lines)
  }

  if (!plan) return <main className="meals">{error && <p className="error">{error}</p>}</main>

  const planned = plan.days.filter((d) => d.meal)
  const isCurrent = plan.start === addDays(plan.today, -((parse(plan.today).getDay() + 6) % 7))

  return (
    <main className="meals">
      <div className="meals-head">
        <div className="nav">
          <button onClick={() => setStart(addDays(plan.start, -7))} aria-label="Previous week">‹</button>
          <button className={isCurrent ? '' : 'primary'} onClick={() => setStart('')}>This week</button>
          <button onClick={() => setStart(addDays(plan.start, 7))} aria-label="Next week">›</button>
          <span className="range">
            Dinners · {short(plan.start)} – {short(addDays(plan.start, 6))}
          </span>
        </div>
        <div className="meals-actions">
          <button
            disabled={!meals.length || planned.length === 7}
            onClick={() =>
              act(async () => {
                const r = await api.fillMealPlan(plan.start)
                setToast(r.filled ? `Planned ${r.filled} night${r.filled === 1 ? '' : 's'} from your meals` : 'No more meals to use this week')
              })
            }
          >
            <Icon name="dice" /> Fill empty nights
          </button>
          <button disabled={!planned.some((d) => d.meal.ingredients.length)} onClick={() => shopFor(planned)}>
            <Icon name="cart" /> Week's groceries
          </button>
          <button onClick={() => setShowBox(true)}><Icon name="book" /> Our meals</button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      {meals.length === 0 && <Starter onAdd={() => act(api.addStarterMeals)} />}

      <div className="meal-week">
        {plan.days.map((d, i) => {
          const today = d.date === plan.today
          const past = d.date < plan.today
          return (
            <section key={d.date} className={`meal-day ${today ? 'today' : ''} ${past ? 'past' : ''}`}>
              <header>
                <span className="dow">{today ? 'Tonight' : DAY_NAMES[i]}</span>
                <span className="date">{short(d.date)}</span>
              </header>
              <button className={`meal-card ${d.meal ? '' : 'empty'}`} onClick={() => setPicking(d.date)}>
                {d.meal ? (
                  <>
                    {d.meal.image ? (
                      <Thumb src={d.meal.image} />
                    ) : (
                      <span className="meal-icon"><ItemIcon value={d.meal.icon} fallback="plate" /></span>
                    )}
                    <span className="meal-name">{d.meal.name}</span>
                    {d.meal.ingredients.length > 0 && (
                      <ul className="meal-ingredients">
                        {d.meal.ingredients.slice(0, 7).map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                        {d.meal.ingredients.length > 7 && <li className="more">+{d.meal.ingredients.length - 7} more</li>}
                      </ul>
                    )}
                  </>
                ) : (
                  <span className="plus">+ Plan dinner</span>
                )}
              </button>
              {d.meal && d.meal.ingredients.length > 0 && (
                <button className="to-list" onClick={() => shopFor([d])}>
                  <Icon name="cart" /> Add to list
                </button>
              )}
            </section>
          )
        })}
      </div>

      {toast && <div className="toast">{toast}</div>}

      {picking && (
        <DayPicker
          day={picking}
          current={plan.days.find((d) => d.date === picking)?.meal}
          meals={meals}
          onPick={(meal) =>
            act(async () => {
              await api.setMealPlan(picking, meal ? meal.id : null)
              setPicking(null)
            })
          }
          onSaveIdea={(idea) =>
            act(async () => {
              const meal = await api.createMeal({
                name: idea.name.slice(0, 80),
                ingredients: idea.ingredients.slice(0, 40),
                url: idea.url,
                image: idea.image,
              })
              await api.setMealPlan(picking, meal.id)
              setPicking(null)
              setToast(`Saved "${meal.name}" to your meals`)
            })
          }
          onNew={() => setEditing({ planFor: picking })}
          onEdit={(meal) => setEditing(meal)}
          onClose={() => setPicking(null)}
        />
      )}

      {showBox && (
        <MealBox meals={meals} onEdit={(m) => setEditing(m)} onNew={() => setEditing({})} onClose={() => setShowBox(false)} />
      )}

      {editing && (
        <MealEditor
          meal={editing}
          onSave={(body) =>
            act(async () => {
              const meal = editing.id ? await api.updateMeal(editing.id, body) : await api.createMeal(body)
              if (editing.planFor) {
                await api.setMealPlan(editing.planFor, meal.id)
                setPicking(null)
              }
              setEditing(null)
            })
          }
          onDelete={() =>
            act(async () => {
              await api.deleteMeal(editing.id)
              setEditing(null)
            })
          }
          onClose={() => setEditing(null)}
        />
      )}

      {shopping && (
        <ShopPicker
          lines={shopping}
          onAdd={(items) =>
            act(async () => {
              const r = await api.addGroceryLines(items)
              setShopping(null)
              const skipped = r.skipped.length ? ` (${r.skipped.length} already on it)` : ''
              setToast(`Added ${r.added.length} item${r.added.length === 1 ? '' : 's'} to the grocery list${skipped}`)
            })
          }
          onClose={() => setShopping(null)}
        />
      )}
    </main>
  )
}

/** TheMealDB serves a small copy at <image>/preview; fall back to the full photo. */
function Thumb({ src }) {
  return (
    <img
      src={`${src}/preview`}
      alt=""
      onError={(e) => {
        if (e.currentTarget.src !== src) e.currentTarget.src = src
      }}
    />
  )
}

function Starter({ onAdd }) {
  const [busy, setBusy] = useState(false)
  return (
    <div className="starter">
      <p className="big">No meals saved yet. Start with some family favorites?</p>
      <p className="hint">
        Tacos, spaghetti and meatballs, red beans and rice, jambalaya, gumbo, breakfast for dinner, grilled cheese and
        tomato soup, pizza night, chicken tenders, plus "Leftovers" and "Eating out". Each comes with a grocery list you
        can change.
      </p>
      <div className="actions">
        <button
          className="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            await onAdd()
            setBusy(false)
          }}
        >
          Add starter meals
        </button>
      </div>
    </div>
  )
}

function DayPicker({ day, current, meals, onPick, onSaveIdea, onNew, onEdit, onClose }) {
  const [tab, setTab] = useState(meals.length ? 'ours' : 'ideas')
  const [filter, setFilter] = useState('')
  const [query, setQuery] = useState('')
  const [ideas, setIdeas] = useState(null)
  const [loading, setLoading] = useState(false)
  const [ideaError, setIdeaError] = useState(null)

  const label = parse(day).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
  const shown = useMemo(
    () => meals.filter((m) => m.name.toLowerCase().includes(filter.trim().toLowerCase())),
    [meals, filter],
  )

  async function fetchIdeas(q = '') {
    setLoading(true)
    setIdeaError(null)
    try {
      setIdeas((await api.mealIdeas(q)).ideas)
    } catch (e) {
      setIdeaError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => {
    if (tab === 'ideas' && ideas === null) fetchIdeas()
  }, [tab])

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal meal-picker">
        <div className="settings-head">
          <h2>Dinner for {label}</h2>
          <button onClick={onClose}>Close</button>
        </div>
        <div className="tabs">
          <button className={tab === 'ours' ? 'on' : ''} onClick={() => setTab('ours')}><Icon name="book" /> Our meals</button>
          <button className={tab === 'ideas' ? 'on' : ''} onClick={() => setTab('ideas')}><Icon name="bulb" /> Get ideas</button>
        </div>

        {tab === 'ours' ? (
          <>
            <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search our meals…" />
            <div className="meal-tiles">
              {shown.map((m) => (
                <button key={m.id} className={`meal-tile ${current?.id === m.id ? 'on' : ''}`} onClick={() => onPick(m)}>
                  {m.image ? <Thumb src={m.image} /> : <span className="meal-icon"><ItemIcon value={m.icon} fallback="plate" /></span>}
                  <span className="meal-name">{m.name}</span>
                </button>
              ))}
              <button className="meal-tile new" onClick={onNew}>
                <span className="meal-icon">＋</span>
                <span className="meal-name">New meal</span>
              </button>
            </div>
          </>
        ) : (
          <>
            <form
              className="idea-search"
              onSubmit={(e) => {
                e.preventDefault()
                fetchIdeas(query.trim())
              }}
            >
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search a dish or ingredient, like chicken…" />
              <button type="submit" className="primary">Search</button>
              <button type="button" onClick={() => { setQuery(''); fetchIdeas() }}><Icon name="dice" /> Surprise me</button>
            </form>
            {loading && <p className="note">Finding ideas…</p>}
            {ideaError && <p className="error">{ideaError}</p>}
            {!loading && ideas?.length === 0 && <p className="note">Nothing found. Try another word.</p>}
            {!loading && ideas && (
              <div className="idea-cards">
                {ideas.map((idea) => (
                  <div className="idea" key={idea.ext_id}>
                    {idea.image && <Thumb src={idea.image} />}
                    <div className="idea-body">
                      <div className="meal-name">{idea.name}</div>
                      <div className="idea-meta">
                        {[idea.area, idea.category].filter(Boolean).join(' · ')} · {idea.ingredients.length} ingredients
                      </div>
                      <button className="primary" onClick={() => onSaveIdea(idea)}>Plan it</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <p className="note small">Ideas from TheMealDB. "Plan it" saves the meal and its ingredients to your meals.</p>
          </>
        )}

        {current && (
          <div className="actions">
            <button onClick={() => onEdit(current)}><Icon name="pencil" /> Edit {current.name}</button>
            {current.url && (
              <a className="button" href={current.url} target="_blank" rel="noreferrer">Recipe ↗</a>
            )}
            <span className="spacer" />
            <button className="danger" onClick={() => onPick(null)}>Clear this night</button>
          </div>
        )}
      </div>
    </div>
  )
}

function MealBox({ meals, onEdit, onNew, onClose }) {
  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal meal-picker">
        <div className="settings-head">
          <h2>Our meals</h2>
          <button className="primary" onClick={onClose}>Done</button>
        </div>
        <p className="note">Tap a meal to change its name, ingredients or recipe link.</p>
        <div className="meal-tiles">
          {meals.map((m) => (
            <button key={m.id} className="meal-tile" onClick={() => onEdit(m)}>
              {m.image ? <Thumb src={m.image} /> : <span className="meal-icon"><ItemIcon value={m.icon} fallback="plate" /></span>}
              <span className="meal-name">{m.name}</span>
            </button>
          ))}
          <button className="meal-tile new" onClick={onNew}>
            <span className="meal-icon">＋</span>
            <span className="meal-name">New meal</span>
          </button>
        </div>
      </div>
    </div>
  )
}

function MealEditor({ meal, onSave, onDelete, onClose }) {
  const [name, setName] = useState(meal.name ?? '')
  const [icon, setIcon] = useState(meal.icon ?? '')
  const [ingredients, setIngredients] = useState((meal.ingredients ?? []).join('\n'))
  const [url, setUrl] = useState(meal.url ?? '')
  const [confirm, setConfirm] = useState(false)

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal meal-editor">
        <h2>{meal.id ? 'Edit meal' : 'New meal'}</h2>
        <div className="row">
          <label className="icon-label">
            Icon
            <IconPicker value={icon} fallback="plate" onChange={setIcon} />
          </label>
          <label>
            Name
            <input className="title-input" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} autoFocus={!meal.id} />
          </label>
        </div>
        <label>
          Ingredients, one per line (these go on the grocery list)
          <textarea value={ingredients} onChange={(e) => setIngredients(e.target.value)} rows={8} placeholder={'Ground beef (1 lb)\nTaco shells\nShredded cheese'} />
        </label>
        <label>
          Recipe link (optional)
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" inputMode="url" />
        </label>
        <div className="actions">
          {meal.id &&
            (confirm ? (
              <>
                <span className="confirm-text">Delete it and clear it from the plan?</span>
                <button className="danger" onClick={onDelete}>Delete</button>
                <button onClick={() => setConfirm(false)}>Keep</button>
              </>
            ) : (
              <button className="danger" onClick={() => setConfirm(true)}>Delete</button>
            ))}
          <span className="spacer" />
          <button onClick={onClose}>Cancel</button>
          <button
            className="primary"
            disabled={!name.trim()}
            onClick={() =>
              onSave({
                name: name.trim(),
                icon: icon.trim(),
                ingredients: ingredients.split('\n').map((s) => s.trim()).filter(Boolean),
                url: url.trim(),
              })
            }
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

function ShopPicker({ lines, onAdd, onClose }) {
  const [onList, setOnList] = useState(null)
  // Merge repeats across meals ("Onion" in two dinners shows once)
  const merged = useMemo(() => {
    const byKey = new Map()
    for (const { line, from } of lines) {
      const k = itemKey(line)
      if (byKey.has(k)) byKey.get(k).from.add(from)
      else byKey.set(k, { line, key: k, from: new Set([from]) })
    }
    return [...byKey.values()]
  }, [lines])
  const [picked, setPicked] = useState(() => new Set(merged.filter((m) => !STAPLES.test(m.line)).map((m) => m.key)))

  useEffect(() => {
    api.grocery().then((items) => {
      const open = new Set(items.filter((i) => !i.done).map((i) => itemKey(i.text)))
      setOnList(open)
      setPicked((p) => new Set([...p].filter((k) => !open.has(k))))
    }).catch(() => setOnList(new Set()))
  }, [])

  const toggle = (k) =>
    setPicked((s) => {
      const n = new Set(s)
      n.has(k) ? n.delete(k) : n.add(k)
      return n
    })
  const meals = new Set(lines.map((l) => l.from))

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal shop-picker">
        <h2>Add to the grocery list</h2>
        <p className="note">Uncheck anything you already have. Pantry basics start unchecked.</p>
        <div className="shop-lines">
          {merged.map((m) => {
            const already = onList?.has(m.key)
            return (
              <button key={m.key} className={`shop-line ${picked.has(m.key) ? 'on' : ''}`} disabled={already} onClick={() => toggle(m.key)}>
                <span className="box">{picked.has(m.key) ? '✓' : ''}</span>
                <span className="text">{m.line}</span>
                <span className="from">{already ? 'already on the list' : meals.size > 1 ? [...m.from].join(', ') : ''}</span>
              </button>
            )
          })}
        </div>
        <div className="actions">
          <span className="spacer" />
          <button onClick={onClose}>Cancel</button>
          <button
            className="primary"
            disabled={!picked.size}
            onClick={() => onAdd(merged.filter((m) => picked.has(m.key)).map((m) => m.line))}
          >
            Add {picked.size} item{picked.size === 1 ? '' : 's'}
          </button>
        </div>
      </div>
    </div>
  )
}
