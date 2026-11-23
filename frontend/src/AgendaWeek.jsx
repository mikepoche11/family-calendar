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

function DayColumn({ day, events, isToday, size, peopleById, dinner, weather, onEvent, onDay }) {
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
    <section className={`agenda-day${isToday ? ' today' : ''}`} data-date={toDay(day)}>
      <header className="agenda-day-head">
        <span className="dow">{day.toLocaleDateString([], { weekday: 'short' })}</span>
        <span className="num">{day.getDate()}</span>
        {events.length > 0 && <span className="count">{events.length}</span>}
      </header>
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
  const perDay = days.map((d) => eventsOn(events, d))
  const size = sizeFor(Math.max(0, ...perDay.map((l) => l.length)))
  const dinners = useDinners(start, mealsVersion)
  const forecast = Object.fromEntries((weather?.days ?? []).map((d) => [d.date, d]))
  const today = toDay(new Date())
  return (
    <div className={`agenda-week ${size}`}>
      {days.map((d, i) => (
        <DayColumn
          key={toDay(d)}
          day={d}
          events={perDay[i]}
          isToday={toDay(d) === today}
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
