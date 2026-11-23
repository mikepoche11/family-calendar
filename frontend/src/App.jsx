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
import useIsPhone from './useIsPhone.js'
import Screensaver from './Screensaver.jsx'
import GroceryList from './GroceryList.jsx'
import Chores from './Chores.jsx'
import Marbles from './Marbles.jsx'
import Meals from './Meals.jsx'
import Routines from './Routines.jsx'
import { ROUTINE, activeKind } from './routineTime.js'
import Countdowns, { CountdownStrip } from './Countdowns.jsx'
import { Icon } from './icons.jsx'
import { GOOGLE_COLORS, textOn } from './googleColors.js'
import { applyTheme, themeById } from './themes.js'
import { ListDayStickers, StickerLayer, StickerPicker, toDay } from './Stickers.jsx'

const VIEWS = [
  { id: 'timeGridDay', label: 'Day' },
  { id: 'timeGridWeek', label: 'Week' },
  { id: 'dayGridMonth', label: 'Month' },
  { id: 'listTwoWeeks', label: 'Schedule' },
]
const DEFAULT_VIEW = 'timeGridWeek'
// A week of columns is unreadable on a phone, so phones start on the two-week schedule and skip Week
const PHONE_VIEW = 'listTwoWeeks'
const PHONE_VIEWS = new Set(['timeGridDay', 'dayGridMonth', 'listTwoWeeks'])
const UNASSIGNED_COLOR = '#cbd5e1'
const IDLE_RESET_MS = 2 * 60 * 1000 // go back to today after 2 minutes untouched

export default function App() {
  const calRef = useRef(null)
  const isPhone = useIsPhone()
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
  const [routinesVersion, setRoutinesVersion] = useState(0)
  const [routineSettings, setRoutineSettings] = useState(null)
  const [clock, setClock] = useState(() => new Date())
  const [countdowns, setCountdowns] = useState([])
  const [range, setRange] = useState(null) // visible days, for stickers
  const [stickers, setStickers] = useState([])
  const [stickerPicker, setStickerPicker] = useState(false)
  const [placing, setPlacing] = useState(null) // icon waiting to be tapped onto a day

  const stickersByDay = useMemo(() => {
    const by = {}
    for (const s of stickers) (by[s.day] ??= []).push(s)
    return by
  }, [stickers])
  const peopleById = useMemo(() => Object.fromEntries(people.map((p) => [p.id, p])), [people])
  const refetch = useCallback(() => calRef.current?.getApi().refetchEvents(), [])

  const loadPeople = useCallback(() => api.people().then(setPeople).catch(() => {}), [])
  const loadWeather = useCallback(() => api.weather().then(setWeather).catch(() => {}), [])
  const loadHealth = useCallback(() => api.health().then(setHealth).catch(() => setHealth(null)), [])
  const loadPhotos = useCallback(() => api.photos().then(setPhotos).catch(() => {}), [])
  const loadRoutineSettings = useCallback(() => api.routines().then((r) => setRoutineSettings(r.settings)).catch(() => {}), [])
  const loadCountdowns = useCallback(() => api.countdowns().then((r) => setCountdowns(r.countdowns)).catch(() => {}), [])
  const rangeRef = useRef(null)
  rangeRef.current = range
  const loadStickers = useCallback(() => {
    const r = rangeRef.current
    if (r) api.stickers(r.start, r.end).then(setStickers).catch(() => {})
  }, [])
  useEffect(loadStickers, [range?.start, range?.end, loadStickers])

  useEffect(() => {
    loadPeople()
    loadWeather()
    loadHealth()
    loadPhotos()
    loadRoutineSettings()
    loadCountdowns()
    const loadConfig = () => api.config().then(setConfig).catch(() => {})
    loadConfig()
    if (window.location.search) window.history.replaceState(null, '', '/')
    const w = setInterval(loadWeather, 15 * 60 * 1000)
    const h = setInterval(loadHealth, 60 * 1000)
    const cd = setInterval(loadCountdowns, 10 * 60 * 1000) // days left tick over at midnight
    const unsubscribe = subscribe((kind) => {
      if (kind === 'people') {
        loadPeople()
        setChoresVersion((v) => v + 1)
        setMarblesVersion((v) => v + 1)
      }
      if (kind === 'theme') return loadConfig()
      if (kind === 'photos') return loadPhotos()
      if (kind === 'grocery') return setGroceryVersion((v) => v + 1)
      if (kind === 'chores') return setChoresVersion((v) => v + 1)
      if (kind === 'routines') {
        loadRoutineSettings()
        return setRoutinesVersion((v) => v + 1)
      }
      if (kind === 'marbles') return setMarblesVersion((v) => v + 1)
      if (kind === 'meals') return setMealsVersion((v) => v + 1)
      if (kind === 'stickers') return loadStickers()
      if (kind === 'countdowns') return loadCountdowns()
      refetch()
    })
    return () => {
      clearInterval(w)
      clearInterval(h)
      clearInterval(cd)
      unsubscribe()
    }
  }, [loadPeople, loadWeather, loadHealth, loadPhotos, loadRoutineSettings, loadStickers, loadCountdowns, refetch])

  // Morning / bedtime routine that's on right now (the wall switches to it when nobody is using the screen)
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 30 * 1000)
    return () => clearInterval(t)
  }, [])
  const routineNow = activeKind(routineSettings, clock)
  const routineAuto = !isPhone && Boolean(routineSettings?.auto_show && routineNow)
  const homeSection = routineAuto ? 'routines' : 'calendar'
  const homeRef = useRef(homeSection)
  homeRef.current = homeSection
  const lastTouch = useRef(Date.now())
  useEffect(() => {
    const touch = () => (lastTouch.current = Date.now())
    window.addEventListener('pointerdown', touch)
    return () => window.removeEventListener('pointerdown', touch)
  }, [])
  // When a routine starts or ends while the screen sits idle, move to (or away from) it
  useEffect(() => {
    if (isPhone || draft || showSettings || Date.now() - lastTouch.current < IDLE_RESET_MS) return
    if (homeSection === 'routines') setScreensaver(false)
    setSection(homeSection)
  }, [homeSection])

  const themeBg = config.theme_backgrounds?.[config.theme ?? ''] ?? ''
  useEffect(() => applyTheme(config.theme ?? '', themeBg), [config.theme, themeBg])

  async function chooseBackground(theme, color) {
    setConfig((c) => {
      const next = { ...(c.theme_backgrounds ?? {}) }
      if (color) next[theme] = color
      else delete next[theme]
      return { ...c, theme_backgrounds: next }
    })
    try {
      await api.setThemeBackground(theme, color)
    } catch {
      api.config().then(setConfig).catch(() => {})
    }
  }

  async function chooseTheme(theme) {
    setConfig((c) => ({ ...c, theme }))
    try {
      await api.setTheme(theme)
    } catch {
      api.config().then(setConfig).catch(() => {})
    }
  }

  // Photo screensaver after SCREENSAVER_MINUTES untouched (only when there are photos and no dialog is open)
  useEffect(() => {
    // No photo slideshow while a routine is up on the wall
    if (isPhone || !photos.length || draft || showSettings || screensaver || routineAuto) return
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
  }, [isPhone, photos.length, draft, showSettings, screensaver, routineAuto, config.screensaver_minutes])

  // People colours and the filter are applied when events are fetched
  useEffect(() => {
    refetch()
  }, [people, hidden, refetch])

  // Return to the default view on today when nobody has touched the screen for a while (wall screen only)
  useEffect(() => {
    if (isPhone) return
    let timer
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        setDraft(null)
        setShowSettings(false)
        setStickerPicker(false)
        setPlacing(null)
        setSection(homeRef.current)
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
  }, [isPhone])

  // Turning a tablet or resizing a window across the phone width: leave Week, which doesn't fit
  useEffect(() => {
    const fc = calRef.current?.getApi()
    if (isPhone && fc && !PHONE_VIEWS.has(fc.view.type)) fc.changeView(PHONE_VIEW)
  }, [isPhone])

  const fetchEvents = useCallback(
    (info, success, failure) => {
      api
        .events(info.start.toISOString(), info.end.toISOString())
        .then((rows) =>
          success(
            rows
              .filter((e) => !hidden.has(e.person_id ?? 'none'))
              .map((e) => {
                // The colour picked in Google Calendar wins, then the colour set for its Google event label;
                // family colours are for jars, chores and filters
                const google = GOOGLE_COLORS[e.color_id]?.bg ?? (e.label_color || null)
                const color = google ?? peopleById[e.person_id]?.color ?? UNASSIGNED_COLOR
                return {
                  id: e.id,
                  title: e.summary,
                  start: e.start,
                  end: e.end,
                  allDay: e.all_day,
                  backgroundColor: color,
                  borderColor: color,
                  textColor: google ? textOn(google) : '#1e293b',
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
      <Header weather={weather} themeIcons={themeById(config.theme).icons}>
        <nav className="sections">
          <button className={section === 'calendar' ? 'on' : ''} onClick={() => setSection('calendar')}>
            <Icon name="calendar" /> Calendar
          </button>
          <button className={section === 'grocery' ? 'on' : ''} onClick={() => setSection('grocery')}>
            <Icon name="cart" /> Grocery
          </button>
          <button className={section === 'meals' ? 'on' : ''} onClick={() => setSection('meals')}>
            <Icon name="plate" /> Meals
          </button>
          <button className={section === 'chores' ? 'on' : ''} onClick={() => setSection('chores')}>
            <Icon name="chores" /> Chores
          </button>
          <button className={section === 'routines' ? 'on' : ''} onClick={() => setSection('routines')}>
            <Icon name={ROUTINE[routineNow ?? 'morning'].icon} /> Routines
          </button>
          <button className={section === 'marbles' ? 'on' : ''} onClick={() => setSection('marbles')}>
            <Icon name="jar" /> Marbles
          </button>
          <button className={section === 'countdowns' ? 'on' : ''} onClick={() => setSection('countdowns')}>
            <Icon name="hourglass" /> {isPhone ? 'Countdown' : 'Countdowns'}
          </button>
        </nav>
      </Header>

      {section === 'grocery' && <GroceryList version={groceryVersion} />}
      {section === 'chores' && <Chores people={people} version={choresVersion} />}
      {section === 'meals' && <Meals version={mealsVersion} />}
      {section === 'routines' && <Routines people={people} version={routinesVersion} />}
      {section === 'countdowns' && <Countdowns countdowns={countdowns} reload={loadCountdowns} />}
      {section === 'marbles' && <Marbles people={people} version={marblesVersion} theme={config.theme ?? ''} />}

      <div className="calendar-section" style={{ display: section === 'calendar' ? undefined : 'none' }}>
      <div className="toolbar">
        <div className="nav">
          <button onClick={() => cal()?.prev()} aria-label="Previous">‹</button>
          <button onClick={() => cal()?.today()}>Today</button>
          <button onClick={() => cal()?.next()} aria-label="Next">›</button>
          <span className="range">{title}</span>
        </div>
        <CountdownStrip countdowns={countdowns} max={isPhone ? 1 : 2} onOpen={() => setSection('countdowns')} />
        <div className="views">
          {VIEWS.filter((v) => !isPhone || PHONE_VIEWS.has(v.id)).map((v) => (
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
        <button className="sticker-btn" onClick={() => setStickerPicker(true)}>
          <Icon name="star" /> Stickers
        </button>
        <button className="settings-btn" onClick={() => setShowSettings('family')} aria-label="Settings">
          <Icon name="gear" /> Settings
        </button>
      </div>

      {placing && (
        <div className="placing-banner">
          <Icon name={placing} size="1.8em" /> Tap a day to stick it there
          <button onClick={() => setPlacing(null)}>Cancel</button>
        </div>
      )}

      <main className="calendar">
        <FullCalendar
          ref={calRef}
          plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
          initialView={isPhone ? PHONE_VIEW : DEFAULT_VIEW}
          views={{
            listTwoWeeks: {
              type: 'list',
              duration: { days: 14 },
              dayHeaderContent: (arg) => (
                <>
                  <a className="fc-list-day-text">{arg.text}</a>
                  <ListDayStickers stickers={stickersByDay[toDay(arg.date)]} />
                  <a className="fc-list-day-side-text">{arg.sideText}</a>
                </>
              ),
            },
          }}
          headerToolbar={false}
          height="100%"
          nowIndicator
          selectable
          selectLongPressDelay={250}
          dayMaxEvents={isPhone ? 2 : 4}
          scrollTime="07:00:00"
          slotMinTime="06:00:00"
          slotMaxTime="23:00:00"
          allDayText="All day"
          events={fetchEvents}
          datesSet={(info) => {
            setView(info.view.type)
            setTitle(info.view.title)
            setRange({ start: toDay(info.start), end: toDay(info.end), key: `${info.view.type} ${info.startStr}` })
          }}
          dateClick={(info) => setDraft(draftFrom({ start: info.date, allDay: info.allDay }))}
          select={(info) => setDraft(draftFrom({ start: info.start, end: info.end, allDay: info.allDay }))}
          eventClick={(info) => setDraft(draftFrom({ event: info.event.extendedProps.row }))}
        />
        <StickerLayer
          stickers={stickers}
          setStickers={setStickers}
          reload={loadStickers}
          viewType={view}
          layoutKey={range?.key}
          placing={placing}
          onPlaced={() => setPlacing(null)}
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
          theme={config.theme ?? ''}
          onTheme={chooseTheme}
          backgrounds={config.theme_backgrounds ?? {}}
          onBackground={chooseBackground}
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

      {stickerPicker && (
        <StickerPicker
          themeIcons={themeById(config.theme).icons}
          onClose={() => setStickerPicker(false)}
          onPick={(icon) => {
            setStickerPicker(false)
            setSection('calendar')
            setPlacing(icon)
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
