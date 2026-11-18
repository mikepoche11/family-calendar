import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import { api, subscribe } from './api.js'
import Header from './Header.jsx'
import EventModal, { draftFrom } from './EventModal.jsx'

const VIEWS = [
  { id: 'timeGridDay', label: 'Day' },
  { id: 'timeGridWeek', label: 'Week' },
  { id: 'dayGridMonth', label: 'Month' },
  { id: 'listTwoWeeks', label: 'Schedule' },
]
const DEFAULT_VIEW = 'timeGridWeek'
const UNASSIGNED_COLOR = '#94a3b8'
const IDLE_RESET_MS = 2 * 60 * 1000 // go back to today after 2 minutes untouched

export default function App() {
  const calRef = useRef(null)
  const [people, setPeople] = useState([])
  const [hidden, setHidden] = useState(() => new Set())
  const [weather, setWeather] = useState(null)
  const [health, setHealth] = useState(null)
  const [view, setView] = useState(DEFAULT_VIEW)
  const [title, setTitle] = useState('')
  const [draft, setDraft] = useState(null)

  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])
  const refetch = useCallback(() => calRef.current?.getApi().refetchEvents(), [])

  const loadPeople = useCallback(() => api.people().then(setPeople).catch(() => {}), [])
  const loadWeather = useCallback(() => api.weather().then(setWeather).catch(() => {}), [])
  const loadHealth = useCallback(() => api.health().then(setHealth).catch(() => setHealth(null)), [])

  useEffect(() => {
    loadPeople()
    loadWeather()
    loadHealth()
    const w = setInterval(loadWeather, 15 * 60 * 1000)
    const h = setInterval(loadHealth, 60 * 1000)
    const unsubscribe = subscribe((kind) => {
      if (kind === 'people') loadPeople()
      refetch()
    })
    return () => {
      clearInterval(w)
      clearInterval(h)
      unsubscribe()
    }
  }, [loadPeople, loadWeather, loadHealth, refetch])

  // People colours and the filter are applied when events are fetched
  useEffect(() => {
    refetch()
  }, [people, hidden, refetch])

  // Return to the default view on today when nobody has touched the screen for a while
  useEffect(() => {
    let timer
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        setDraft(null)
        const cal = calRef.current?.getApi()
        if (cal) {
          cal.changeView(DEFAULT_VIEW)
          cal.today()
        }
      }, IDLE_RESET_MS)
    }
    reset()
    window.addEventListener('pointerdown', reset)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('pointerdown', reset)
    }
  }, [])

  const fetchEvents = useCallback(
    (info, success, failure) => {
      api
        .events(info.start.toISOString(), info.end.toISOString())
        .then((rows) =>
          success(
            rows
              .filter((e) => !hidden.has(e.person_id ?? 'none'))
              .map((e) => {
                const color = peopleById[e.person_id]?.color ?? UNASSIGNED_COLOR
                return {
                  id: e.id,
                  title: e.summary,
                  start: e.start,
                  end: e.end,
                  allDay: e.all_day,
                  backgroundColor: color,
                  borderColor: color,
                  extendedProps: { row: e },
                }
              }),
          ),
        )
        .catch(failure)
    },
    [hidden, peopleById],
  )

  const toggle = (key) =>
    setHidden((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })

  const cal = () => calRef.current?.getApi()

  async function save(id, body) {
    if (id) await api.updateEvent(id, body)
    else await api.createEvent(body)
    setDraft(null)
    refetch()
  }

  async function remove(id) {
    await api.deleteEvent(id)
    setDraft(null)
    refetch()
  }

  return (
    <div className="app">
      <Header weather={weather} />

      <div className="toolbar">
        <div className="nav">
          <button onClick={() => cal()?.prev()} aria-label="Previous">‹</button>
          <button onClick={() => cal()?.today()}>Today</button>
          <button onClick={() => cal()?.next()} aria-label="Next">›</button>
          <span className="range">{title}</span>
        </div>
        <div className="views">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              className={view === v.id ? 'on' : ''}
              onClick={() => cal()?.changeView(v.id)}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      <div className="people">
        {people.map((p) => (
          <button
            key={p.id}
            className={`chip ${hidden.has(p.id) ? '' : 'on'}`}
            style={{ '--chip': p.color }}
            onClick={() => toggle(p.id)}
          >
            {p.name}
          </button>
        ))}
        <button
          className={`chip ${hidden.has('none') ? '' : 'on'}`}
          style={{ '--chip': UNASSIGNED_COLOR }}
          onClick={() => toggle('none')}
        >
          Everyone
        </button>
        {health?.last_error && <span className="sync-error">Sync problem: check the backend logs</span>}
        {health?.mode === 'demo' && <span className="demo">Demo data</span>}
      </div>

      <main className="calendar">
        <FullCalendar
          ref={calRef}
          plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
          initialView={DEFAULT_VIEW}
          views={{ listTwoWeeks: { type: 'list', duration: { days: 14 } } }}
          headerToolbar={false}
          height="100%"
          nowIndicator
          selectable
          selectLongPressDelay={250}
          dayMaxEvents={4}
          scrollTime="07:00:00"
          slotMinTime="06:00:00"
          slotMaxTime="23:00:00"
          allDayText="All day"
          events={fetchEvents}
          datesSet={(info) => {
            setView(info.view.type)
            setTitle(info.view.title)
          }}
          dateClick={(info) => setDraft(draftFrom({ start: info.date, allDay: info.allDay }))}
          select={(info) => setDraft(draftFrom({ start: info.start, end: info.end, allDay: info.allDay }))}
          eventClick={(info) => setDraft(draftFrom({ event: info.event.extendedProps.row }))}
        />
      </main>

      <button className="fab" onClick={() => setDraft(draftFrom({}))} aria-label="Add event">
        +
      </button>

      {draft && (
        <EventModal
          draft={draft}
          people={people}
          onSave={save}
          onDelete={remove}
          onClose={() => setDraft(null)}
        />
      )}
    </div>
  )
}
