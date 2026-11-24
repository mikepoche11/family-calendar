import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { Icon } from './icons.jsx'
import { GOOGLE_COLORS } from './googleColors.js'

const shuffle = (arr) => {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const src = (name) => `/api/photos/file/${encodeURIComponent(name)}`
export const isVideo = (name) => /\.(mp4|webm)$/i.test(name)
const VIDEO_MAX_SECONDS = 60 // a long clip plays its first minute, then the slideshow moves on

/** A muted video that plays from the start while it's the current slide, then calls onDone. */
function VideoSlide({ name, active, paused, alone, onDone }) {
  const ref = useRef(null)
  useEffect(() => {
    const v = ref.current
    if (!v) return
    if (active && !paused) {
      if (v.ended) v.currentTime = 0
      v.play().catch(() => {})
    } else v.pause()
  }, [active, paused])
  // back to the start whenever it comes round again
  useEffect(() => {
    const v = ref.current
    if (active && v) v.currentTime = 0
  }, [active])
  return (
    <video
      ref={ref}
      className="photo video"
      src={src(name)}
      muted
      playsInline
      loop={alone}
      preload={active ? 'auto' : 'metadata'}
      onEnded={() => active && onDone()}
      onError={() => active && onDone()}
      onTimeUpdate={(e) => active && !alone && e.currentTarget.currentTime >= VIDEO_MAX_SECONDS && onDone()}
    />
  )
}
const timeText = (d) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

/** True when the time of day falls in night hours ("21:00" to "06:00" wraps past midnight). */
export function isNight(settings, now = new Date()) {
  if (!settings?.night) return false
  const mins = (t) => {
    const [h, m] = t.split(':').map(Number)
    return h * 60 + m
  }
  const n = now.getHours() * 60 + now.getMinutes()
  const s = mins(settings.night_start)
  const e = mins(settings.night_end)
  if (s === e) return false
  return s < e ? n >= s && n < e : n >= s || n < e
}

/** Events still to come today (and ones going on now), soonest first; all-day ones first. */
function useUpcoming(people, enabled) {
  const [rows, setRows] = useState([])
  useEffect(() => {
    if (!enabled) return
    const load = () => {
      const start = new Date()
      start.setHours(0, 0, 0, 0)
      const end = new Date(start)
      end.setDate(end.getDate() + 1)
      api
        .events(start.toISOString(), end.toISOString())
        .then((list) => {
          const now = new Date()
          const byId = Object.fromEntries(people.map((p) => [p.id, p]))
          setRows(
            list
              .filter((e) => e.all_day || new Date(e.end) > now)
              .sort((a, b) => (b.all_day - a.all_day) || a.start.localeCompare(b.start))
              .slice(0, 3)
              .map((e) => ({
                id: e.id,
                title: e.summary,
                when: e.all_day ? 'All day' : new Date(e.start) <= now ? 'Now' : timeText(new Date(e.start)),
                color: GOOGLE_COLORS[e.color_id]?.bg ?? (e.label_color || byId[e.person_id]?.color || '#cbd5e1'),
              })),
          )
        })
        .catch(() => {})
    }
    load()
    const t = setInterval(load, 5 * 60 * 1000)
    return () => clearInterval(t)
  }, [enabled, people])
  return rows
}

/**
 * Full-screen photo and video slideshow. Videos play muted to the end (first minute at most). Each photo fills the screen over a soft blurred copy of itself (no
 * black bars for tall phone photos) and drifts slowly. A pastel card shows the time, weather and
 * what's next today. During night hours it shows only a dim clock instead. Any touch closes it.
 */
export default function Screensaver({ photos, settings, weather, people = [], onClose }) {
  const [order, setOrder] = useState(() => shuffle(photos))
  const [index, setIndex] = useState(0)
  const [now, setNow] = useState(new Date())
  const night = isNight(settings, now)
  const showPhotos = !night && order.length > 0
  const card = settings?.card !== false
  const upcoming = useUpcoming(people, showPhotos && card)
  const slideSeconds = settings?.slide_seconds ?? 15
  const [paused, setPaused] = useState(false)
  const [quick, setQuick] = useState(false) // faster fade after a swipe
  const down = useRef(null)

  // Photos added or removed while it's running: keep the order, add new ones next
  useEffect(() => {
    setOrder((cur) => {
      const keep = cur.filter((n) => photos.includes(n))
      const fresh = photos.filter((n) => !cur.includes(n))
      return keep.length + fresh.length ? [...keep.slice(0, index + 1), ...fresh, ...keep.slice(index + 1)] : []
    })
  }, [photos])

  // Next photo after slideSeconds; a swipe restarts the wait, pause stops it.
  // A video moves on when it ends (or after a minute); the longer timer here is only a safety net.
  const curIsVideo = isVideo(order[index % (order.length || 1)] ?? '')
  const advance = () => {
    setQuick(false)
    setIndex((i) => (i + 1) % order.length)
  }
  useEffect(() => {
    if (!showPhotos || paused || order.length < 2) return
    const t = setTimeout(advance, (curIsVideo ? VIDEO_MAX_SECONDS + 10 : slideSeconds) * 1000)
    return () => clearTimeout(t)
  }, [showPhotos, paused, index, order.length, slideSeconds, curIsVideo])

  const step = (dir) => {
    if (order.length < 2) return
    setQuick(true)
    setIndex((i) => (i + dir + order.length) % order.length)
  }

  useEffect(() => {
    const c = setInterval(() => setNow(new Date()), 10000)
    return () => clearInterval(c)
  }, [])

  // Preload the next photo so the fade never shows a half-loaded image
  const cur = order.length ? index % order.length : 0
  const next = order.length ? (cur + 1) % order.length : 0
  const prev = order.length ? (cur - 1 + order.length) % order.length : 0
  useEffect(() => {
    if (showPhotos && order[next] && !isVideo(order[next])) new Image().src = src(order[next])
  }, [showPhotos, next, order])

  const close = (e) => {
    e.stopPropagation()
    onClose()
  }

  // Swipe left = next photo, swipe right = the one before; a plain tap goes back to the calendar
  // (closing waits for the click, so the tap doesn't also land on the calendar underneath)
  const swiped = useRef(false)
  const swipe = {
    onPointerDown: (e) => {
      down.current = { x: e.clientX, y: e.clientY }
      swiped.current = false
    },
    onPointerUp: (e) => {
      const start = down.current
      down.current = null
      if (!start) return
      const dx = e.clientX - start.x
      const dy = e.clientY - start.y
      if (Math.abs(dx) > 15 || Math.abs(dy) > 15) swiped.current = true
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1)
    },
    onPointerCancel: () => (down.current = null),
    onClick: (e) => {
      e.stopPropagation()
      if (!swiped.current) onClose()
      swiped.current = false
    },
  }

  if (!showPhotos) {
    // Night: a dim clock that wanders a little each minute so nothing burns into the screen
    const spot = now.getHours() * 60 + now.getMinutes()
    const x = 20 + ((spot * 37) % 60)
    const y = 20 + ((spot * 53) % 60)
    return (
      <div className="screensaver night" onClick={close}>
        <div className="night-clock" style={{ left: `${x}%`, top: `${y}%` }}>
          <div className="time">{timeText(now)}</div>
          <div className="date">{now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })}</div>
        </div>
      </div>
    )
  }

  return (
    <div className={`screensaver ${quick ? 'quick' : ''} ${paused ? 'paused' : ''}`} {...swipe} style={{ '--slide': `${slideSeconds + 2}s` }}>
      {order.map((name, i) => {
        if (i !== cur && i !== next && i !== prev) return null // the ones around it stay loaded for swipes
        return (
          <div key={name} className={`slide ${i === cur ? 'on' : ''}`}>
            {isVideo(name) ? (
              <VideoSlide name={name} active={i === cur} paused={paused} alone={order.length < 2} onDone={advance} />
            ) : (
              <>
                <img className="fill" src={src(name)} alt="" draggable={false} />
                <img className={`photo ${i % 2 ? 'drift-b' : 'drift-a'}`} src={src(name)} alt="" draggable={false} />
              </>
            )}
          </div>
        )
      })}
      <div className="ss-controls" onPointerDown={(e) => e.stopPropagation()} onPointerUp={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
        {paused && <span className="ss-paused">Paused</span>}
        <button
          className="ss-pause"
          aria-label={paused ? 'Play slideshow' : 'Pause slideshow'}
          onClick={(e) => {
            e.stopPropagation()
            setPaused((p) => !p)
          }}
        >
          {paused ? (
            <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" fill="currentColor" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><rect x="6.5" y="5" width="4" height="14" rx="1.5" fill="currentColor" /><rect x="13.5" y="5" width="4" height="14" rx="1.5" fill="currentColor" /></svg>
          )}
        </button>
      </div>
      {card ? (
        <div className="ss-card">
          <div className="ss-top">
            <div>
              <div className="time">{timeText(now)}</div>
              <div className="date">{now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })}</div>
            </div>
            {weather && (
              <div className="ss-weather">
                <Icon name={weather.icon} title={weather.label} size="1.6em" />
                <div>
                  <div className="temp">{weather.temperature}°</div>
                  {weather.days?.[0] && (
                    <div className="range">
                      {weather.days[0].high}° / {weather.days[0].low}°
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          {upcoming.length > 0 && (
            <ul className="ss-next">
              {upcoming.map((e) => (
                <li key={e.id}>
                  <span className="dot" style={{ background: e.color }} />
                  <span className="when">{e.when}</span>
                  <span className="what">{e.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="ss-clock">
          <div className="time">{timeText(now)}</div>
        </div>
      )}
    </div>
  )
}
