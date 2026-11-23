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
  setTheme: (theme) => request('PUT', '/api/theme', { theme }),
  setThemeBackground: (theme, color) => request('PUT', '/api/theme/background', { theme, color }),
  health: () => request('GET', '/api/health'),
  people: () => request('GET', '/api/people'),
  createPerson: (body) => request('POST', '/api/people', body),
  updatePerson: (id, body) => request('PATCH', `/api/people/${id}`, body),
  deletePerson: (id) => request('DELETE', `/api/people/${id}`),
  weather: () => request('GET', '/api/weather'),
  grocery: () => request('GET', '/api/grocery'),
  addGrocery: (text) => request('POST', '/api/grocery', { text }),
  updateGrocery: (id, body) => request('PATCH', `/api/grocery/${id}`, body),
  deleteGrocery: (id) => request('DELETE', `/api/grocery/${id}`),
  addGroceryLines: (items) => request('POST', '/api/grocery/bulk', { items }),
  clearCheckedGrocery: () => request('POST', '/api/grocery/clear-checked'),
  chores: () => request('GET', '/api/chores'),
  choresToday: () => request('GET', '/api/chores/today'),
  createChore: (body) => request('POST', '/api/chores', body),
  updateChore: (id, body) => request('PATCH', `/api/chores/${id}`, body),
  deleteChore: (id) => request('DELETE', `/api/chores/${id}`),
  setChoreDone: (id, body) => request('POST', `/api/chores/${id}/done`, body),
  addStarterChores: (kid_ids) => request('POST', '/api/chores/starter', { kid_ids }),
  routines: () => request('GET', '/api/routines'),
  routinesToday: () => request('GET', '/api/routines/today'),
  setRoutineSettings: (body) => request('PUT', '/api/routines/settings', body),
  createRoutineStep: (body) => request('POST', '/api/routines/steps', body),
  updateRoutineStep: (id, body) => request('PATCH', `/api/routines/steps/${id}`, body),
  deleteRoutineStep: (id) => request('DELETE', `/api/routines/steps/${id}`),
  setRoutineDone: (id, body) => request('POST', `/api/routines/steps/${id}/done`, body),
  copyRoutine: (body) => request('POST', '/api/routines/copy', body),
  addStarterRoutines: (kid_ids) => request('POST', '/api/routines/starter', { kid_ids }),
  marbles: () => request('GET', '/api/marbles'),
  setShowNight: (person_ids) => request('PUT', '/api/show-night', { person_ids }),
  swapShowNight: () => request('POST', '/api/show-night/swap'),
  setJars: (person_ids) => request('PUT', '/api/marbles/jars', { person_ids }),
  removeJar: (pid) => request('DELETE', `/api/marbles/${pid}`),
  addMarbles: (pid, color, count = 1) => request('POST', `/api/marbles/${pid}/add`, { color, count }),
  spendMarbles: (pid, reward_id) => request('POST', `/api/marbles/${pid}/spend`, { reward_id }),
  cancelMarbles: (pid) => request('POST', `/api/marbles/${pid}/cancel`),
  undoMarbles: (pid) => request('POST', `/api/marbles/${pid}/undo`),
  createReward: (body) => request('POST', '/api/rewards', body),
  updateReward: (id, body) => request('PATCH', `/api/rewards/${id}`, body),
  deleteReward: (id) => request('DELETE', `/api/rewards/${id}`),
  meals: () => request('GET', '/api/meals'),
  createMeal: (body) => request('POST', '/api/meals', body),
  updateMeal: (id, body) => request('PATCH', `/api/meals/${id}`, body),
  deleteMeal: (id) => request('DELETE', `/api/meals/${id}`),
  addStarterMeals: () => request('POST', '/api/meals/starter'),
  mealIdeas: (q = '') => request('GET', `/api/meals/ideas${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  mealPlan: (start = '') => request('GET', `/api/meal-plan${start ? `?start=${start}` : ''}`),
  setMealPlan: (day, meal_id) => request('PUT', `/api/meal-plan/${day}`, { meal_id }),
  fillMealPlan: (start) => request('POST', `/api/meal-plan/fill?start=${start}`),
  countdowns: () => request('GET', '/api/countdowns'),
  createCountdown: (body) => request('POST', '/api/countdowns', body),
  updateCountdown: (id, body) => request('PATCH', `/api/countdowns/${id}`, body),
  deleteCountdown: (id) => request('DELETE', `/api/countdowns/${id}`),
  addHolidayCountdowns: () => request('POST', '/api/countdowns/holidays'),
  photos: () => request('GET', '/api/photos'),
  photoStatus: () => request('GET', '/api/photos/status'),
  startPick: () => request('POST', '/api/photos/pick'),
  cancelPick: () => request('DELETE', '/api/photos/pick'),
  disconnectPhotos: () => request('POST', '/api/photos/disconnect'),
  deletePhoto: (name) => request('DELETE', `/api/photos/file/${encodeURIComponent(name)}`),
  deleteAllPhotos: () => request('DELETE', '/api/photos'),
  stickers: (start, end) => request('GET', `/api/stickers?start=${start}&end=${end}`),
  addSticker: (body) => request('POST', '/api/stickers', body),
  updateSticker: (id, body) => request('PATCH', `/api/stickers/${id}`, body),
  deleteSticker: (id) => request('DELETE', `/api/stickers/${id}`),
  eventLabels: () => request('GET', '/api/event-labels'),
  setLabelColor: (id, color) => request('PUT', `/api/event-labels/${encodeURIComponent(id)}`, { color }),
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
