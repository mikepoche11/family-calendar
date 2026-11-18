async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {}
    throw new Error(detail)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  config: () => request('GET', '/api/config'),
  health: () => request('GET', '/api/health'),
  people: () => request('GET', '/api/people'),
  weather: () => request('GET', '/api/weather'),
  events: (start, end) =>
    request('GET', `/api/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
  createEvent: (body) => request('POST', '/api/events', body),
  updateEvent: (id, body) => request('PATCH', `/api/events/${encodeURIComponent(id)}`, body),
  deleteEvent: (id) => request('DELETE', `/api/events/${encodeURIComponent(id)}`),
}

/** Calls onChange whenever the backend reports new data; reconnects on its own. */
export function subscribe(onChange) {
  const es = new EventSource('/api/stream')
  es.addEventListener('changed', (e) => onChange(JSON.parse(e.data).kind))
  return () => es.close()
}
