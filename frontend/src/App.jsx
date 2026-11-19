import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import { api, subscribe } from './api.js'
import Header from './Header.jsx'
import EventModal, { draftFrom } from './EventModal.jsx'
import Settings from './Settings.jsx'
import Avatar from './avatars.jsx'
import Screensaver from './Screensaver.jsx'
import GroceryList from './GroceryList.jsx'
import Chores from './Chores.jsx'
import Marbles from './Marbles.jsx'
import Meals from './Meals.jsx'

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
  const [showSettings, setShowSettings] = useState(() =>
    new URLSearchParams(window.location.search).has('photos') ||
    new URLSearchParams(window.location.search).has('photos_error')
      ? 'photos'
      : false,
  )
  const [config, setConfig] = useState({ screensaver_minutes: 5, slide_seconds: 15 })
  const [photos, setPhotos] = useState([])
  const [screensaver, setScreensaver] = useState(false)
  const [section, setSection] = useState('calendar')
  const [groceryVersion, setGroceryVersion] = useState(0)
  const [choresVersion, setChoresVersion] = useState(0)
  const [marblesVersion, setMarblesVersion] = useState(0)
  const [mealsVersion, setMealsVersion] = useState(0)

  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])
  const refetch = useCallback(() => calRef.current?.getApi().refetchEvents(), [])

  const loadPeople = useCallback(() => api.people().then(setPeople).catch(() => {}), [])
  const loadWeather = useCallback(() => api.weather().then(setWeather).catch(() => {}), [])
  const loadHealth = useCallback(() => api.health().then(setHealth).catch(() => setHealth(null)), [])
  const loadPhotos = useCallback(() => api.photos().then(setPhotos).catch(() => {}), [])

  useEffect(() => {
    loadPeople()
    loadWeather()
    loadHealth()
    loadPhotos()
    api.config().then(setConfig).catch(() => {})
    if (window.location.search) window.history.replaceState(null, '', '/')
    const w = setInterval(loadWeather, 15 * 60 * 1000)
    const h = setInterval(loadHealth, 60 * 1000)
    const unsubscribe = subscribe((kind) => {
      if (kind === 'people') {
        loadPeople()
        setChoresVersion((v) => v + 1)
        setMarblesVersion((v) => v + 1)
      }
      if (kind === 'photos') return loadPhotos()
      if (kind === 'grocery') return setGroceryVersion((v) => v + 1)
      if (kind === 'chores') return setChoresVersion((v) => v + 1)
      if (kind === 'marbles') return setMarblesVersion((v) => v + 1)
      if (kind === 'meals') return setMealsVersion((v) => v + 1)
      refetch()
    })
    return () => {
      clearInterval(w)
      clearInterval(h)
      unsubscribe()
    }
  }, [loadPeople, loadWeather, loadHealth, loadPhotos, refetch])

  // Photo screensaver after SCREENSAVER_MINUTES untouched (only when there are photos and no dialog is open)
  useEffect(() => {
    if (!photos.length || draft || showSettings || screensaver) return
    let timer
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => setScreensaver(true), config.screensaver_minutes * 60 * 1000)
    }
    reset()
    window.addEventListener('pointerdown', reset)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('pointerdown', reset)
    }
  }, [photos.length, draft, showSettings, screensaver, config.screensaver_minutes])

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
        setShowSettings(false)
        setSection('calendar')
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

  // FullCalendar measures itself; re-measure when its section becomes visible again
  useEffect(() => {
    if (section === 'calendar') requestAnimationFrame(() => calRef.current?.getApi().updateSize())
  }, [section])

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
      <Header weather={weather}>
        <nav className="sections">
          <button className={section === 'calendar' ? 'on' : ''} onClick={() => setSection('calendar')}>
            📅 Calendar
          </button>
          <button className={section === 'grocery' ? 'on' : ''} onClick={() => setSection('grocery')}>
            🛒 Grocery
          </button>
          <button className={section === 'meals' ? 'on' : ''} onClick={() => setSection('meals')}>
            🍽️ Meals
          </button>
          <button className={section === 'chores' ? 'on' : ''} onClick={() => setSection('chores')}>
            ✅ Chores
          </button>
          <button className={section === 'marbles' ? 'on' : ''} onClick={() => setSection('marbles')}>
            🫙 Marbles
          </button>
        </nav>
      </Header>

      {section === 'grocery' && <GroceryList version={groceryVersion} />}
      {section === 'chores' && <Chores people={people} version={choresVersion} />}
      {section === 'meals' && <Meals version={mealsVersion} />}
      {section === 'marbles' && <Marbles people={people} version={marblesVersion} />}

      <div className="calendar-section" style={{ display: section === 'calendar' ? undefined : 'none' }}>
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
            <Avatar person={p} size={36} />
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
        <button className="settings-btn" onClick={() => setShowSettings('family')} aria-label="Settings">
          ⚙ Settings
        </button>
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
      </div>

      {showSettings && (
        <Settings
          people={people}
          initialTab={showSettings}
          onChanged={loadPeople}
          onClose={() => {
            setShowSettings(false)
            loadPhotos()
          }}
          onPreview={() => {
            setShowSettings(false)
            loadPhotos().then(() => setScreensaver(true))
          }}
        />
      )}

      {screensaver && photos.length > 0 && (
        <Screensaver photos={photos} slideSeconds={config.slide_seconds} onClose={() => setScreensaver(false)} />
      )}

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
