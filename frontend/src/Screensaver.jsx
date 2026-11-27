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

// Shared-album photos are Google addresses; ask Google for one sized to this screen (no bigger than 2048 px)
const SIDE = Math.min(2048, Math.round(Math.max(window.screen?.width || 1920, window.screen?.height || 1080) * (window.devicePixelRatio || 1)))
export const isAlbum = (name) => name.startsWith('https://')
const src = (name) => (isAlbum(name) ? `${name}=w${SIDE}-h${SIDE}` : `/api/photos/file/${encodeURIComponent(name)}`)
const AHEAD = 3 // album photos fetched ahead of the one showing
const GIVE_UP = 5 // album photos in a row that won't load before switching to the uploaded ones
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
export default function Screensaver({ photos, album = false, settings, weather, people = [], onClose }) {
  // Uploads only: shuffle them all. With a shared album: ask the server for a few at a time, at random
  // from the album and the uploads together, and load each from Google just before it shows.
  const [order, setOrder] = useState(() => (album ? [] : shuffle(photos)))
  const [index, setIndex] = useState(0)
  const [localOnly, setLocalOnly] = useState(false) // Google's photos stopped loading: uploads only
  const [bad, setBad] = useState({}) // album photos that failed to load
  const fetching = useRef(false)
  const misses = useRef(0)
  const counted = useRef(-1) // the slide last counted as a miss
  const good = useRef(new Set()) // album photos that loaded
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
    if (album) return // new uploads come round in the next few the server hands out
    setOrder((cur) => {
      const keep = cur.filter((n) => photos.includes(n))
      const fresh = photos.filter((n) => !cur.includes(n))
      return keep.length + fresh.length ? [...keep.slice(0, index + 1), ...fresh, ...keep.slice(index + 1)] : []
    })
  }, [photos])

  // Next photo after slideSeconds; a swipe restarts the wait, pause stops it.
  // A video moves on when it ends (or after a minute); the longer timer here is only a safety net.
  const n = order.length
  const cur = !n ? 0 : album ? Math.min(index, n - 1) : index % n
  const next = !n ? 0 : album ? Math.min(cur + 1, n - 1) : (cur + 1) % n
  const prev = !n ? 0 : album ? Math.max(cur - 1, 0) : (cur - 1 + n) % n
  const curIsVideo = isVideo(order[cur] ?? '')
  const advance = () => {
    setQuick(false)
    setIndex((i) => (album ? (i + 1 < n ? i + 1 : i) : (i + 1) % n))
  }

  // Album: keep a few photos lined up ahead of the one showing (retries every 30 s if the server can't be reached)
  useEffect(() => {
    if (!album || cur + AHEAD < n) return
    const get = () => {
      if (fetching.current) return
      fetching.current = true
      api
        .nextPhotos(8, localOnly)
        .then((list) => list.length && setOrder((o) => [...o, ...list]))
        .catch(() => {})
        .finally(() => (fetching.current = false))
    }
    get()
    const t = setInterval(get, 30000)
    return () => clearInterval(t)
  }, [album, cur, n, localOnly])

  // Album photo that won't load (Google changed or removed it): skip it. Several in a row means
  // Google's addresses have stopped working, so switch to the uploaded photos and ask for a fresh list.
  const onBad = (name) => setBad((b) => (b[name] ? b : { ...b, [name]: true }))
  useEffect(() => {
    if (good.current.has(order[cur])) misses.current = 0
  }, [cur, order])
  useEffect(() => {
    if (!album || !bad[order[cur]]) return
    if (counted.current !== cur) misses.current += 1
    counted.current = cur
    if (misses.current >= GIVE_UP && !localOnly) {
      setLocalOnly(true)
      setOrder((o) => o.slice(0, cur + 1))
      api.checkAlbum().catch(() => {})
    }
    advance()
  }, [album, bad, cur, order])

  // The next few album photos load in the background so each one is ready when its turn comes
  useEffect(() => {
    if (!album || !showPhotos) return
    for (const name of order.slice(cur + 2, cur + 1 + AHEAD)) {
      if (!isAlbum(name)) continue
      const img = new Image()
      img.onerror = () => onBad(name)
      img.src = src(name)
    }
  }, [album, showPhotos, cur, order])

  useEffect(() => {
    if (!showPhotos || paused || order.length < 2) return
    const t = setTimeout(advance, (curIsVideo ? VIDEO_MAX_SECONDS + 10 : slideSeconds) * 1000)
    return () => clearTimeout(t)
  }, [showPhotos, paused, index, order.length, slideSeconds, curIsVideo])

  const step = (dir) => {
    if (order.length < 2) return
    setQuick(true)
    setIndex((i) => (album ? Math.max(0, Math.min(n - 1, i + dir)) : (i + dir + n) % n))
  }

  useEffect(() => {
    const c = setInterval(() => setNow(new Date()), 10000)
    return () => clearInterval(c)
  }, [])

  // Preload the next photo so the fade never shows a half-loaded image
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

  if (!showPhotos && album && !night) return <div className="screensaver" onClick={close} /> // first album photos on their way

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
          <div key={album ? `${i}-${name}` : name} className={`slide ${i === cur ? 'on' : ''}`}>
            {isVideo(name) ? (
              <VideoSlide name={name} active={i === cur} paused={paused} alone={order.length < 2} onDone={advance} />
            ) : (
              <>
                <img className="fill" src={src(name)} alt="" draggable={false} referrerPolicy="no-referrer" />
                <img
                  className={`photo ${i % 2 ? 'drift-b' : 'drift-a'}`}
                  src={src(name)}
                  alt=""
                  draggable={false}
                  referrerPolicy="no-referrer"
                  onLoad={() => {
                    good.current.add(name)
                    if (i === cur) misses.current = 0
                  }}
                  onError={() => isAlbum(name) && onBad(name)}
                />
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
