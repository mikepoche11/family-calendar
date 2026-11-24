import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import Avatar from './avatars.jsx'
import { Icon, ItemIcon } from './icons.jsx'
import { api } from './api.js'
import { toDay } from './Stickers.jsx'

const shortTime = (d) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }).replace(':00', '')
const addDays = (d, n) => {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}

// Card size follows the busiest day of the week: a light week gets big cards, a busy one smaller cards.
function sizeFor(most) {
  if (most <= 3) return 'size-xl'
  if (most <= 5) return 'size-l'
  return 'size-m'
}
const COMPACT_AT = 8 // a day with this many events or more switches to one-line cards

function eventsOn(events, day) {
  const next = addDays(day, 1)
  return events
    .filter((e) => e.start && e.start < next && (e.end ? e.end > day : e.start >= day))
    .sort((a, b) => (b.allDay - a.allDay) || (a.start - b.start) || a.title.localeCompare(b.title))
}

const dayIndex = (start, d) => Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - start) / 86400000)

/**
 * All-day events that cover two or more of the shown days become one bar across those days. That includes one
 * multi-day event and also a run of separate all-day events with the same title and colour on back-to-back days
 * (how a "No school" week is often entered). Bars are stacked into lanes so they never overlap.
 */
function buildSpans(events, start) {
  const groups = {}
  for (const e of events) {
    if (!e.allDay || !e.start) continue
    const key = `${e.title.trim().toLowerCase()}|${e.backgroundColor}`
    ;(groups[key] ??= []).push(e)
  }
  const runs = []
  for (const list of Object.values(groups)) {
    list.sort((a, b) => a.start - b.start)
    let run = null
    for (const e of list) {
      const end = e.end ?? addDays(e.start, 1)
      if (run && e.start <= run.end) {
        if (end > run.end) run.end = end
        run.events.push(e)
      } else {
        run = { ev: e, start: e.start, end, events: [e] }
        runs.push(run)
      }
    }
  }
  const spans = runs
    .map((r) => ({ ...r, from: Math.max(0, dayIndex(start, r.start)), to: Math.min(7, dayIndex(start, r.end)) }))
    .filter((r) => r.to - r.from >= 2)
    .sort((a, b) => a.from - b.from || (b.to - b.from) - (a.to - a.from))
  const lanes = [] // last day used in each lane
  for (const sp of spans) {
    let lane = lanes.findIndex((busyUntil) => busyUntil <= sp.from)
    if (lane === -1) lane = lanes.length
    lanes[lane] = sp.to
    sp.lane = lane
  }
  return spans
}

// "All day · Mon to Fri" (end is exclusive, so the last day is the day before it)
function spanLabel(sp) {
  const last = addDays(sp.end, -1)
  const wd = (d) => d.toLocaleDateString([], { weekday: 'short' })
  return `All day · ${wd(sp.start)} to ${wd(last)}`
}

function whenLabel(ev, compact) {
  if (ev.allDay) return 'All day'
  if (compact) return shortTime(ev.start) // one-line cards: start time only, so the title gets the room
  return ev.end ? `${shortTime(ev.start)} – ${shortTime(ev.end)}` : shortTime(ev.start)
}

/** Meal plan for the 7 shown days. Meal weeks start on Monday, so a Sunday-first week spans two of them. */
function useDinners(start, version) {
  const [byDay, setByDay] = useState({})
  const key = toDay(start)
  useEffect(() => {
    let live = true
    Promise.all([api.mealPlan(key), api.mealPlan(toDay(addDays(start, 6)))])
      .then((weeks) => {
        if (!live) return
        const out = {}
        weeks.forEach((w) => w.days.forEach((d) => { if (d.meal) out[d.date] = d.meal }))
        setByDay(out)
      })
      .catch(() => {})
    return () => { live = false }
  }, [key, version]) // eslint-disable-line react-hooks/exhaustive-deps
  return byDay
}

function DayColumn({ day, col, lanes, events, size, peopleById, dinner, weather, onEvent, onDay }) {
  const bodyRef = useRef(null)
  const [overflows, setOverflows] = useState(false)
  const compact = events.length >= COMPACT_AT
  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    const check = () => setOverflows(el.scrollHeight > el.clientHeight + 2 && el.scrollTop + el.clientHeight < el.scrollHeight - 2)
    check()
    const ro = new ResizeObserver(check)
    ro.observe(el)
    el.addEventListener('scroll', check)
    return () => { ro.disconnect(); el.removeEventListener('scroll', check) }
  }, [events.length, size])

  return (
    <section className="agenda-day" data-date={toDay(day)} style={{ gridColumn: col, gridRow: 2, '--lanes': lanes }}>
      <div
        ref={bodyRef}
        className={`agenda-day-body${compact ? ' compact' : ''}${overflows ? ' more' : ''}`}
        onClick={(e) => { if (e.target === e.currentTarget) onDay(day) }}
      >
        {events.map((ev) => {
          const row = ev.extendedProps.row
          const person = peopleById[row?.person_id]
          return (
            <button
              key={ev.id + toDay(day)}
              className="agenda-card"
              style={{ background: ev.backgroundColor, color: ev.textColor }}
              onClick={() => onEvent(ev)}
            >
              <span className="agenda-text">
                <span className="agenda-title">{ev.title}</span>
                <span className="agenda-when">{whenLabel(ev, compact)}</span>
              </span>
              {person && <Avatar person={person} size={compact ? 24 : 30} />}
            </button>
          )
        })}
        {events.length === 0 && (
          <button className="agenda-empty" onClick={() => onDay(day)}>+ Add</button>
        )}
      </div>
      <footer className="agenda-day-foot">
        {dinner ? (
          <span className="foot-dinner" title="Dinner">
            <ItemIcon value={dinner.icon} fallback="plate" /> <span className="foot-text">{dinner.name}</span>
          </span>
        ) : (
          <span className="foot-dinner none"><Icon name="plate" /> <span className="foot-text">No dinner planned</span></span>
        )}
        {weather && (
          <span className="foot-weather">
            <Icon name={weather.icon} /> {weather.high}° <span className="lo">{weather.low}°</span>
          </span>
        )}
      </footer>
    </section>
  )
}

/**
 * The wall's Week: seven columns, each a day heading, that day's events as cards sized to their text, and a
 * footer with that night's dinner and the day's weather. A crowded day shrinks its cards to one line and
 * then scrolls on its own; the other days stay put.
 */
export default function AgendaWeek({ start, events, peopleById, weather, mealsVersion, onEvent, onDay }) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i))
  const spans = buildSpans(events, start)
  const inSpan = new Set(spans.flatMap((sp) => sp.events))
  const perDay = days.map((d) => eventsOn(events, d))
  const cards = perDay.map((list) => list.filter((e) => !inSpan.has(e)))
  const size = sizeFor(Math.max(0, ...cards.map((l) => l.length)))
  // how many bar lanes sit over each day, so that day's cards start right under its own bars
  const lanesOn = days.map((_, i) => Math.max(0, ...spans.filter((sp) => sp.from <= i && i < sp.to).map((sp) => sp.lane + 1)))
  const dinners = useDinners(start, mealsVersion)
  const forecast = Object.fromEntries((weather?.days ?? []).map((d) => [d.date, d]))
  const today = toDay(new Date())
  return (
    <div className={`agenda-week ${size}`}>
      {days.map((d, i) => (
        <div key={`bg${i}`} className={`agenda-col${toDay(d) === today ? ' today' : ''}`} style={{ gridColumn: i + 1 }} />
      ))}
      {days.map((d, i) => (
        <header
          key={`h${i}`}
          className={`agenda-day-head${toDay(d) === today ? ' today' : ''}`}
          style={{ gridColumn: i + 1, gridRow: 1 }}
        >
          <span className="dow">{d.toLocaleDateString([], { weekday: 'short' })}</span>
          <span className="num">{d.getDate()}</span>
          {perDay[i].length > 0 && <span className="count">{perDay[i].length}</span>}
        </header>
      ))}
      {spans.length > 0 && (
        <div className="agenda-spans" style={{ gridColumn: '1 / -1', gridRow: 2 }}>
          {spans.map((sp) => {
            const row = sp.ev.extendedProps.row
            const person = peopleById[row?.person_id]
            return (
              <button
                key={sp.ev.id}
                className={`agenda-card agenda-span${dayIndex(start, sp.start) < 0 ? ' cont-left' : ''}${dayIndex(start, sp.end) > 7 ? ' cont-right' : ''}`}
                style={{
                  gridColumn: `${sp.from + 1} / ${sp.to + 1}`,
                  gridRow: sp.lane + 1,
                  background: sp.ev.backgroundColor,
                  color: sp.ev.textColor,
                }}
                onClick={() => onEvent(sp.ev)}
              >
                <span className="agenda-text">
                  <span className="agenda-title">{sp.ev.title}</span>
                  <span className="agenda-when">{spanLabel(sp)}</span>
                </span>
                {person && <Avatar person={person} size={28} />}
              </button>
            )
          })}
        </div>
      )}
      {days.map((d, i) => (
        <DayColumn
          key={toDay(d)}
          day={d}
          col={i + 1}
          lanes={lanesOn[i]}
          events={cards[i]}
          size={size}
          peopleById={peopleById}
          dinner={dinners[toDay(d)]}
          weather={forecast[toDay(d)]}
          onEvent={onEvent}
          onDay={onDay}
        />
      ))}
    </div>
  )
}
