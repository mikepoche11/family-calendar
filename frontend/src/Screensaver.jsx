import { useEffect, useState } from 'react'

const shuffle = (arr) => {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/** Full-screen photo slideshow with a clock. Any touch closes it. */
export default function Screensaver({ photos, slideSeconds = 15, onClose }) {
  const [order] = useState(() => shuffle(photos))
  const [index, setIndex] = useState(0)
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setIndex((i) => (i + 1) % order.length), slideSeconds * 1000)
    const c = setInterval(() => setNow(new Date()), 15000)
    return () => {
      clearInterval(t)
      clearInterval(c)
    }
  }, [order.length, slideSeconds])

  // Preload the next photo so the fade never shows a half-loaded image
  useEffect(() => {
    const next = order[(index + 1) % order.length]
    if (next) new Image().src = `/api/photos/file/${encodeURIComponent(next)}`
  }, [index, order])

  return (
    <div
      className="screensaver"
      onClick={(e) => {
        e.stopPropagation()
        onClose()
      }}
    >
      {order.map((name, i) => (
        <img
          key={name}
          className={`slide ${i === index ? 'on' : ''}`}
          src={i === index || i === (index + 1) % order.length ? `/api/photos/file/${encodeURIComponent(name)}` : undefined}
          alt=""
        />
      ))}
      <div className="ss-clock">
        <div className="time">{now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</div>
        <div className="date">{now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })}</div>
      </div>
    </div>
  )
}
