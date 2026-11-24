import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import { api, subscribe } from './api.js'
import Header from './Header.jsx'
import EventModal, { draftFrom } from './EventModal.jsx'
import EventView from './EventView.jsx'
import AgendaWeek, { PhoneSchedule } from './AgendaWeek.jsx'
import Settings from './Settings.jsx'
import Avatar from './avatars.jsx'
import useIsPhone from './useIsPhone.js'
import Screensaver, { isNight } from './Screensaver.jsx'
import GroceryList from './GroceryList.jsx'
import Chores from './Chores.jsx'
import Marbles, { ShowNightBadge } from './Marbles.jsx'
import Meals from './Meals.jsx'
import Routines from './Routines.jsx'
import { ROUTINE, activeKind } from './routineTime.js'
import Countdowns, { CountdownStrip } from './Countdowns.jsx'
import { Icon } from './icons.jsx'
import { GOOGLE_COLORS, textOn } from './googleColors.js'
import { applyTheme, themeById } from './themes.js'
import { ListDayStickers, StickerLayer, StickerPicker, toDay } from './Stickers.jsx'

const VIEWS = [
  { id: 'dayGridAgendaWeek', label: 'Week' },
  { id: 'dayGridMonth', label: 'Month' },
  { id: 'listTwoWeeks', label: 'Schedule' }, // phones only
]
const AGENDA = 'dayGridAgendaWeek'
const DEFAULT_VIEW = AGENDA
// A week of columns is unreadable on a phone, so phones get the two-week schedule list instead of Week.
// The wall has Week and Month only.
const PHONE_VIEW = 'listTwoWeeks'
const PHONE_VIEWS = new Set(['dayGridMonth', 'listTwoWeeks'])
const WALL_VIEWS = new Set(['dayGridAgendaWeek', 'dayGridMonth'])
const SWIPE_PX = 80 // a sideways swipe this long on the calendar moves to the next/previous week or month
function swallowNextClick() {
  const swallow = (ev) => { ev.stopPropagation(); ev.preventDefault() }
  window.addEventListener('click', swallow, { capture: true, once: true })
  setTimeout(() => window.removeEventListener('click', swallow, { capture: true }), 400)
}

const UNASSIGNED_COLOR = '#cbd5e1'
const IDLE_RESET_MS = 2 * 60 * 1000 // go back to today after 2 minutes untouched

export default function App() {
  const calRef = useRef(null)
  const isPhone = useIsPhone()
  const [people, setPeople] = useState([])
  const [weather, setWeather] = useState(null)
  const [health, setHealth] = useState(null)
  const [view, setView] = useState(DEFAULT_VIEW)
  const [fcEvents, setFcEvents] = useState([])
  const [showNight, setShowNight] = useState(null)
  const swipe = useRef(null)
  const mainRef = useRef(null)
  const sliding = useRef(false)
  const loading = useRef(false)
  const [weekStart, setWeekStart] = useState(null)
  const [viewing, setViewing] = useState(null) // { row, color } of the event being looked at
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
  // whose night it is to pick the TV show, for the badge on the calendar; re-checked hourly so it turns over at midnight
  useEffect(() => {
    const load = () => api.showNight().then(setShowNight).catch(() => {})
    load()
    const t = setInterval(load, 60 * 60 * 1000)
    return () => clearInterval(t)
  }, [marblesVersion])
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

  const ssSettings = useMemo(
    () => config.screensaver ?? { minutes: config.screensaver_minutes, slide_seconds: config.slide_seconds, night: false, card: true },
    [config.screensaver, config.screensaver_minutes, config.slide_seconds],
  )

  // The no-photos night clock goes away by itself in the morning
  useEffect(() => {
    if (screensaver && !photos.length && !isNight(ssSettings, clock)) setScreensaver(false)
  }, [screensaver, photos.length, ssSettings, clock])

  // Photo screensaver after SCREENSAVER_MINUTES untouched (only when there are photos and no dialog is open)
  useEffect(() => {
    // No photo slideshow while a routine is up on the wall
    // With no photos it still dims to a clock during night hours
    if (isPhone || draft || showSettings || screensaver || routineAuto) return
    if (!photos.length && !ssSettings.night) return
    let timer
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        if (photos.length || isNight(ssSettings)) setScreensaver(true)
        else reset()
      }, ssSettings.minutes * 60 * 1000)
    }
    reset()
    window.addEventListener('pointerdown', reset)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('pointerdown', reset)
    }
  }, [isPhone, photos.length, draft, showSettings, screensaver, routineAuto, ssSettings])

  // People colours are applied when events are fetched
  useEffect(() => {
    refetch()
  }, [people, refetch])

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
            rows.map((e) => {
                // The colour picked in Google Calendar wins, then the colour set for its Google event label;
                // family colours are for jars and chores
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
    [peopleById],
  )


  const cal = () => calRef.current?.getApi()

  // next / previous / today with a slide: the calendar sweeps off one side and the new one comes in from the other.
  // dir 1 = next, -1 = previous, 0 = today. fromX = where a finger drag already moved it.
  async function go(dir, fromX = 0) {
    const api = cal()
    const el = mainRef.current
    if (!api) return
    const move = () => (dir > 0 ? api.next() : dir < 0 ? api.prev() : api.today())
    let way = dir
    if (dir === 0) {
      const now = new Date()
      way = now < api.view.currentStart ? -1 : now >= api.view.currentEnd ? 1 : 0
    }
    const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (!el || !el.animate || sliding.current || !way || still) {
      if (el) el.style.transform = el.style.opacity = ''
      move()
      return
    }
    sliding.current = true
    try {
      const w = el.offsetWidth
      const out = el.animate(
        [
          { transform: `translateX(${fromX}px)`, opacity: Math.max(0.3, 1 - Math.abs(fromX) / w) },
          { transform: `translateX(${-way * w}px)`, opacity: 0 },
        ],
        { duration: 220 * (1 - Math.min(0.6, Math.abs(fromX) / w)), easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' },
      )
      el.style.transform = el.style.opacity = ''
      await out.finished
      move()
      // give the new week's events a moment to arrive so it doesn't slide in empty
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
      for (let t = 0; loading.current && t < 600; t += 30) await new Promise((r) => setTimeout(r, 30))
      const back = el.animate(
        [
          { transform: `translateX(${way * w}px)`, opacity: 0 },
          { transform: 'translateX(0)', opacity: 1 },
        ],
        { duration: 300, easing: 'cubic-bezier(.2,.8,.2,1)' },
      )
      out.cancel()
      await back.finished
    } catch {
      // an interrupted animation is fine: the calendar has already moved
    } finally {
      sliding.current = false
    }
  }

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

  // show night, stickers (and on phones, settings): beside the view buttons on the wall, their own row on phones
  const extras = (
    <div className="people">
      {health?.last_error && <span className="sync-error">Sync problem: check the backend logs</span>}
      {health?.mode === 'demo' && <span className="demo">Demo data</span>}
      <ShowNightBadge
        show={showNight}
        peopleById={peopleById}
        theme={config.theme ?? ''}
        onOpen={() => setSection('marbles')}
      />
      <button className="sticker-btn" onClick={() => setStickerPicker(true)}>
        <Icon name="star" /> Stickers
      </button>
      <button className="settings-btn" onClick={() => setShowSettings('family')} aria-label="Settings">
        <Icon name="gear" /> Settings
      </button>
    </div>
  )

  return (
    <div className="app">
      <nav className="sections rail">
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
        <button className="rail-settings" onClick={() => setShowSettings('family')}>
          <Icon name="gear" /> Settings
        </button>
      </nav>

      <div className="main">
      <Header weather={weather} themeIcons={themeById(config.theme).icons}>
        {/* wall: countdowns get the roomy middle of the top line, so their names show in full */}
        {!isPhone && section === 'calendar' && (
          <CountdownStrip countdowns={countdowns} max={2} onOpen={() => setSection('countdowns')} />
        )}
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
          <button onClick={() => go(-1)} aria-label="Previous">‹</button>
          <button onClick={() => go(0)}>Today</button>
          <button onClick={() => go(1)} aria-label="Next">›</button>
          <span className="range">{title}</span>
        </div>
        {isPhone && <CountdownStrip countdowns={countdowns} max={1} onOpen={() => setSection('countdowns')} />}
        {!isPhone && extras}
        <div className="views">
          {VIEWS.filter((v) => (isPhone ? PHONE_VIEWS : WALL_VIEWS).has(v.id)).map((v) => (
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

      {isPhone && extras}

      {placing && (
        <div className="placing-banner">
          <Icon name={placing} size="1.8em" /> Tap a day to stick it there
          <button onClick={() => setPlacing(null)}>Cancel</button>
        </div>
      )}

      <main
        ref={mainRef}
        className={`calendar${view === AGENDA ? ' agenda-mode' : ''}${view === PHONE_VIEW ? ' agenda-mode schedule-mode' : ''}`}
        onPointerDown={(e) => {
          // stickers have their own drag; leave those alone
          swipe.current = placing || sliding.current || e.target.closest('.sticker') ? null : { x: e.clientX, y: e.clientY, t: Date.now(), drag: false }
        }}
        onPointerMove={(e) => {
          // the calendar follows the finger once the move is clearly sideways
          const s = swipe.current
          const el = mainRef.current
          if (!s || !el) return
          const dx = e.clientX - s.x
          const dy = e.clientY - s.y
          if (!s.drag && Math.abs(dx) > 16 && Math.abs(dx) > Math.abs(dy) * 1.5) s.drag = true
          if (s.drag) {
            el.style.transform = `translateX(${dx}px)`
            el.style.opacity = String(Math.max(0.3, 1 - Math.abs(dx) / el.offsetWidth))
          }
        }}
        onPointerCancel={() => {
          swipe.current = null
          const el = mainRef.current
          if (el) el.style.transform = el.style.opacity = ''
        }}
        onPointerUp={(e) => {
          const s = swipe.current
          swipe.current = null
          if (!s) return
          const el = mainRef.current
          const dx = e.clientX - s.x
          const dy = e.clientY - s.y
          const isSwipe = Math.abs(dx) >= SWIPE_PX && Math.abs(dy) <= Math.abs(dx) * 0.6 && (s.drag || Date.now() - s.t <= 800)
          if (!isSwipe) {
            // not far enough: spring back
            if (s.drag && el?.animate) {
              el.animate([{ transform: el.style.transform, opacity: el.style.opacity }, { transform: 'translateX(0)', opacity: 1 }], { duration: 200, easing: 'ease-out' })
            }
            if (el) el.style.transform = el.style.opacity = ''
            if (s.drag) swallowNextClick()
            return
          }
          // a swipe, not a tap: don't let the click that follows open an event or a new-event form
          swallowNextClick()
          go(dx < 0 ? 1 : -1, s.drag ? dx : 0)
        }}
      >
        <FullCalendar
          ref={calRef}
          plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
          initialView={isPhone ? PHONE_VIEW : DEFAULT_VIEW}
          views={{
            // the wall's Week. FullCalendar keeps the dates and loads the events; AgendaWeek draws them
            dayGridAgendaWeek: {
              type: 'dayGrid',
              duration: { weeks: 1 },
            },
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
          eventsSet={setFcEvents}
          loading={(on) => { loading.current = on }}
          height="100%"
          nowIndicator
          selectable={isPhone}
          selectLongPressDelay={250}
          dayMaxEvents={isPhone ? 2 : 4}
          scrollTime="06:00:00"
          slotMinTime="06:00:00"
          slotMaxTime="21:00:00"
          expandRows
          allDayText="All day"
          events={fetchEvents}
          datesSet={(info) => {
            setView(info.view.type)
            setWeekStart(info.start)
            setTitle(info.view.title)
            setRange({ start: toDay(info.start), end: toDay(info.end), key: `${info.view.type} ${info.startStr}` })
          }}
          dateClick={(info) => setDraft(draftFrom({ start: info.date, allDay: info.allDay }))}
          select={(info) => setDraft(draftFrom({ start: info.start, end: info.end, allDay: info.allDay }))}
          eventClick={(info) => setViewing({ row: info.event.extendedProps.row, color: info.event.backgroundColor })}
        />
        {view === AGENDA && weekStart && (
          <AgendaWeek
            start={weekStart}
            events={fcEvents}
            peopleById={peopleById}
            weather={weather}
            mealsVersion={mealsVersion}
            onEvent={(ev) => setViewing({ row: ev.extendedProps.row, color: ev.backgroundColor })}
            onDay={(day) => {
              const start = new Date(day)
              start.setHours(9, 0, 0, 0)
              setDraft(draftFrom({ start }))
            }}
          />
        )}
        {view === PHONE_VIEW && weekStart && (
          <PhoneSchedule
            start={weekStart}
            events={fcEvents}
            peopleById={peopleById}
            weather={weather}
            mealsVersion={mealsVersion}
            stickersByDay={stickersByDay}
            renderStickers={(list) => <ListDayStickers stickers={list} />}
            onEvent={(ev) => setViewing({ row: ev.extendedProps.row, color: ev.backgroundColor })}
            onDay={(day) => {
              const start = new Date(day)
              start.setHours(9, 0, 0, 0)
              setDraft(draftFrom({ start }))
            }}
          />
        )}
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

      {screensaver && (photos.length > 0 || isNight(ssSettings)) && (
        <Screensaver
          photos={photos}
          settings={ssSettings}
          weather={weather}
          people={people}
          onClose={() => setScreensaver(false)}
        />
      )}

      {viewing && (
        <EventView
          row={viewing.row}
          color={viewing.color}
          people={people}
          onClose={() => setViewing(null)}
          onEdit={() => {
            setDraft(draftFrom({ event: viewing.row }))
            setViewing(null)
          }}
        />
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
