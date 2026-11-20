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

export default function Header({ weather, children }) {
  const now = useNow()
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  const date = now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
  return (
    <header className="header">
      <div className="clock">
        <div className="time">{time}</div>
        <div className="date">{date}</div>
      </div>
      {children}
      {weather && (
        <div className="weather">
          <div className="now">
            <span className="icon"><Icon name={weather.icon} title={weather.label} /></span>
            <span className="temp">{weather.temperature}°</span>
            <span className="label">{weather.label}</span>
          </div>
          <div className="days">
            {weather.days.slice(1, 5).map((d) => (
              <div className="day" key={d.date}>
                <div className="dow">
                  {new Date(d.date + 'T12:00').toLocaleDateString([], { weekday: 'short' })}
                </div>
                <div className="icon"><Icon name={d.icon} /></div>
                <div className="hilo">
                  {d.high}° <span className="lo">{d.low}°</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </header>
  )
}
