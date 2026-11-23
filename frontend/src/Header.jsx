import { useEffect, useState } from 'react'
import { Icon } from './icons.jsx'

function useNow(intervalMs = 15000) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])
  return now
}

export default function Header({ weather, themeIcons = [], children }) {
  const now = useNow()
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  const date = now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
  return (
    <header className="header">
      <div className="clock">
        <div className="time">{time}</div>
        <div className="date">
          {date}
          {themeIcons.length > 0 && (
            <span className="theme-badges">
              {themeIcons.map((i) => <Icon key={i} name={i} size="1.3em" />)}
            </span>
          )}
        </div>
      </div>
      {children}
      {weather && (
        <div className="weather">
          <div className="now">
            <span className="icon"><Icon name={weather.icon} title={weather.label} /></span>
            <span className="temp">{weather.temperature}°</span>
            <span className="label">{weather.label}</span>
          </div>
        </div>
      )}
    </header>
  )
}
