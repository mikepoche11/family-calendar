import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { Icon, PICKER_GROUPS } from './icons.jsx'

/*
 * Calendar stickers: decorations dropped on a day. They live in the app's database only and never become
 * Google Calendar events. Each sticker remembers its day and where it sits inside that day (fractions of the
 * day's width and height), so it follows the date when you change weeks or views.
 */

const MAX_REF = 320 // the Day view column is very wide; keep stickers sticker-sized there
const NEW_SIZE = 0.5
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const refLen = (r) => Math.min(r.w, r.h, MAX_REF)

/** Local YYYY-MM-DD, the same form FullCalendar uses in data-date. */
export function toDay(date) {
  const p = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`
}

/** Where each visible day is drawn, relative to the sticker layer. */
function measureDays(layer, viewType) {
  const fc = layer.parentElement?.querySelector('.fc')
  if (!fc) return {}
  const base = layer.getBoundingClientRect()
  const out = {}
  const put = (date, r, bottom = r.bottom) => {
    if (r.width < 1) return
    out[date] = { left: r.left - base.left, top: r.top - base.top, w: r.width, h: bottom - r.top }
  }
  const agenda = layer.parentElement?.querySelectorAll('.agenda-day[data-date]')
  if (agenda?.length) {
    agenda.forEach((el) => put(el.dataset.date, el.getBoundingClientRect()))
  } else if (viewType.startsWith('timeGrid')) {
    // a day is its whole column: from the date heading down to the bottom of the visible hours
    const bottom = fc.querySelector('.fc-view-harness')?.getBoundingClientRect().bottom
    fc.querySelectorAll('.fc-col-header-cell[data-date]').forEach((el) =>
      put(el.dataset.date, el.getBoundingClientRect(), bottom),
    )
  } else if (viewType.startsWith('dayGrid')) {
    fc.querySelectorAll('.fc-daygrid-body .fc-daygrid-day[data-date]').forEach((el) =>
      put(el.dataset.date, el.getBoundingClientRect()),
    )
  }
  return out
}

function dayAt(days, x, y) {
  let best = null
  let bestDist = Infinity
  for (const [date, r] of Object.entries(days)) {
    const dx = Math.max(r.left - x, 0, x - (r.left + r.w))
    const dy = Math.max(r.top - y, 0, y - (r.top + r.h))
    const d = Math.hypot(dx, dy)
    if (d < bestDist) [best, bestDist] = [date, d]
  }
  return best
}

/**
 * The layer over the calendar. Tap a sticker to select it, then drag it, pull the corner to resize, the top
 * handle to turn it, pinch with two fingers to do both, or tap the x to remove it. Tap anywhere else to finish.
 */
export function StickerLayer({ stickers, setStickers, reload, viewType, layoutKey, placing, onPlaced }) {
  const layerRef = useRef(null)
  const dragRef = useRef(null)
  const [days, setDays] = useState({})
  const [selected, setSelected] = useState(null)
  const [live, setLive] = useState(null) // pixel geometry of the sticker being moved

  const measure = useCallback(() => {
    if (layerRef.current) setDays(measureDays(layerRef.current, viewType))
  }, [viewType])

  useLayoutEffect(() => {
    measure()
    const id = requestAnimationFrame(measure) // FullCalendar may still be laying out
    return () => cancelAnimationFrame(id)
  }, [measure, layoutKey])

  useEffect(() => {
    const parent = layerRef.current?.parentElement
    if (!parent) return
    const ro = new ResizeObserver(measure)
    ro.observe(parent)
    return () => ro.disconnect()
  }, [measure])

  // Leaving the calendar's dates or view drops the selection
  useEffect(() => setSelected(null), [layoutKey, viewType])

  const geometry = (s) => {
    if (live?.id === s.id) return live
    const r = days[s.day]
    if (!r) return null
    return { id: s.id, cx: r.left + s.x * r.w, cy: r.top + s.y * r.h, px: s.size * refLen(r), rot: s.rotation }
  }

  const point = (e) => {
    const b = layerRef.current.getBoundingClientRect()
    return { x: e.clientX - b.left, y: e.clientY - b.top }
  }

  async function remove(id) {
    setSelected(null)
    setStickers((list) => list.filter((s) => s.id !== id))
    try {
      await api.deleteSticker(id)
    } catch {
      reload()
    }
  }

  async function commit(g) {
    const date = dayAt(days, g.cx, g.cy)
    if (!date) return setLive(null)
    const r = days[date]
    const patch = {
      day: date,
      x: clamp((g.cx - r.left) / r.w, -1, 2),
      y: clamp((g.cy - r.top) / r.h, -1, 2),
      size: clamp(g.px / refLen(r), 0.1, 3),
      rotation: ((g.rot % 360) + 540) % 360 - 180,
    }
    setStickers((list) => list.map((s) => (s.id === g.id ? { ...s, ...patch } : s)))
    setLive(null)
    try {
      await api.updateSticker(g.id, patch)
    } catch {
      reload()
    }
  }

  function startDrag(e, s, mode) {
    e.stopPropagation()
    e.preventDefault()
    const g = geometry(s)
    if (!g) return
    const p = point(e)
    const drag = dragRef.current
    if (drag && drag.id === s.id && drag.pointers.size === 1) {
      addPinchPointer(e)
      return
    }
    e.currentTarget.setPointerCapture?.(e.pointerId)
    setSelected(s.id)
    dragRef.current = {
      id: s.id,
      mode,
      g0: g,
      start: p,
      startAngle: Math.atan2(p.y - g.cy, p.x - g.cx),
      startDist: Math.max(8, Math.hypot(p.x - g.cx, p.y - g.cy)),
      pointers: new Map([[e.pointerId, p]]),
      moved: mode !== 'move',
      last: g,
    }
  }

  // A second finger anywhere while a sticker is held turns the drag into pinch-to-resize-and-turn
  function addPinchPointer(e) {
    const drag = dragRef.current
    e.currentTarget.setPointerCapture?.(e.pointerId)
    drag.pointers.set(e.pointerId, point(e))
    const [a, b] = [...drag.pointers.values()]
    Object.assign(drag, {
      mode: 'pinch',
      g0: drag.last,
      moved: true,
      pinch0: { d: Math.max(8, Math.hypot(b.x - a.x, b.y - a.y)), ang: Math.atan2(b.y - a.y, b.x - a.x), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 },
    })
  }

  function onMove(e) {
    const drag = dragRef.current
    if (!drag || !drag.pointers.has(e.pointerId)) return
    const p = point(e)
    drag.pointers.set(e.pointerId, p)
    const { g0 } = drag
    let g = g0
    if (drag.mode === 'move') {
      const dx = p.x - drag.start.x
      const dy = p.y - drag.start.y
      if (!drag.moved && Math.hypot(dx, dy) < 5) return
      drag.moved = true
      g = { ...g0, cx: g0.cx + dx, cy: g0.cy + dy }
    } else if (drag.mode === 'resize') {
      const ratio = Math.hypot(p.x - g0.cx, p.y - g0.cy) / drag.startDist
      g = { ...g0, px: clamp(g0.px * ratio, 24, 900) }
    } else if (drag.mode === 'rotate') {
      const ang = Math.atan2(p.y - g0.cy, p.x - g0.cx)
      g = { ...g0, rot: g0.rot + ((ang - drag.startAngle) * 180) / Math.PI }
    } else if (drag.mode === 'pinch' && drag.pointers.size >= 2) {
      const [a, b] = [...drag.pointers.values()]
      const { d, ang, mx, my } = drag.pinch0
      g = {
        ...g0,
        cx: g0.cx + (a.x + b.x) / 2 - mx,
        cy: g0.cy + (a.y + b.y) / 2 - my,
        px: clamp((g0.px * Math.hypot(b.x - a.x, b.y - a.y)) / d, 24, 900),
        rot: g0.rot + ((Math.atan2(b.y - a.y, b.x - a.x) - ang) * 180) / Math.PI,
      }
    }
    drag.last = g
    setLive(g)
  }

  function onUp(e) {
    const drag = dragRef.current
    if (!drag || !drag.pointers.has(e.pointerId)) return
    dragRef.current = null
    if (drag.moved) commit(drag.last)
    else setLive(null)
  }

  function onLayerDown(e) {
    if (e.target !== e.currentTarget) return
    if (placing) {
      const p = point(e)
      const date = dayAt(days, p.x, p.y)
      const r = days[date]
      if (!r || p.x < r.left - 4 || p.x > r.left + r.w + 4 || p.y < r.top - 4 || p.y > r.top + r.h + 4) return
      e.preventDefault()
      onPlaced()
      api
        .addSticker({ day: date, icon: placing, x: (p.x - r.left) / r.w, y: (p.y - r.top) / r.h, size: NEW_SIZE })
        .then((s) => {
          setStickers((list) => [...list.filter((x) => x.id !== s.id), s])
          setSelected(s.id)
        })
        .catch(reload)
      return
    }
    if (dragRef.current?.pointers.size === 1) return addPinchPointer(e)
    e.preventDefault()
    setSelected(null)
  }

  // Keyboard on the wall PC: Delete removes the selected sticker, Escape lets go of it
  useEffect(() => {
    if (!selected) return
    const onKey = (e) => {
      if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return
      if (e.key === 'Delete' || e.key === 'Backspace') remove(selected)
      if (e.key === 'Escape') setSelected(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <div
      ref={layerRef}
      className={`sticker-layer${selected ? ' editing' : ''}${placing ? ' placing' : ''}`}
      onPointerDown={onLayerDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
    >
      {stickers.map((s) => {
        const g = geometry(s)
        if (!g) return null
        const on = selected === s.id
        return (
          <div
            key={s.id}
            className={`sticker${on ? ' on' : ''}`}
            style={{ left: g.cx - g.px / 2, top: g.cy - g.px / 2, width: g.px, height: g.px, transform: `rotate(${g.rot}deg)` }}
            onPointerDown={(e) => startDrag(e, s, 'move')}
          >
            <Icon name={s.icon} size="100%" />
            {on && (
              <>
                <button
                  className="st-handle st-delete"
                  aria-label="Remove sticker"
                  onPointerDown={(e) => {
                    e.stopPropagation()
                    e.preventDefault()
                    remove(s.id)
                  }}
                >
                  ×
                </button>
                <span className="st-handle st-rotate" aria-label="Turn" onPointerDown={(e) => startDrag(e, s, 'rotate')} />
                <span className="st-handle st-resize" aria-label="Resize" onPointerDown={(e) => startDrag(e, s, 'resize')} />
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}

/** Small sticker icons beside a date in the Schedule list (that view has no day boxes to drag on). */
export function ListDayStickers({ stickers }) {
  if (!stickers?.length) return null
  return (
    <span className="list-stickers">
      {stickers.map((s) => (
        <Icon key={s.id} name={s.icon} size="1.6em" />
      ))}
    </span>
  )
}

/** Grid of every icon, with the current holiday theme's set first. */
export function StickerPicker({ themeIcons = [], onPick, onClose }) {
  const prefix = themeIcons[0]?.split('-')[0]
  const groups = [...PICKER_GROUPS].sort(
    (a, b) => Number(Boolean(b.items[0]?.name.startsWith(prefix + '-'))) - Number(Boolean(a.items[0]?.name.startsWith(prefix + '-'))),
  )
  return (
    <div className="backdrop picker-backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal icon-picker">
        <div className="settings-head">
          <h2>Add a sticker</h2>
          <button type="button" onClick={onClose}>Close</button>
        </div>
        <p className="hint">Pick one, then tap the day to stick it on. Stickers stay in this app and are never added to Google Calendar.</p>
        {groups.map((g) => (
          <section key={g.label} className="icon-group">
            <div className="field-label">{g.label}</div>
            <div className="icon-grid">
              {g.items.map((p) => (
                <button type="button" key={p.name} aria-label={p.label} title={p.label} onClick={() => onPick(p.name)}>
                  <Icon name={p.name} />
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
